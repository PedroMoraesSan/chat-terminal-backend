import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pyback.application import chat_context
from pyback.domain.constants import DEFAULT_BOT_NAME, DEFAULT_GROQ_MODEL, DEFAULT_SYSTEM_PROMPT, DEPRECATED_MODELS
from pyback.infrastructure import groq_client
from pyback.infrastructure.persistence import repos
from pyback.infrastructure.persistence.session import AsyncSessionLocal
from pyback.infrastructure.security.encryption import decrypt_api_key
from pyback.infrastructure.security.jwt_service import verify_token
from pyback.presentation.ws_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


def _parse_client_timestamp(val: Any) -> datetime | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(s)
        if d.tzinfo is not None:
            d = d.astimezone(timezone.utc).replace(tzinfo=None)
        return d
    except ValueError:
        return None


def _client_msg_id(raw: dict[str, Any]) -> str | None:
    v = raw.get("client_msg_id")
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    return s[:128]


def _msg_payload(
    username: str,
    message: str,
    ts: datetime | None = None,
    user_id: int | None = None,
    client_msg_id: str | None = None,
) -> dict[str, Any]:
    t = ts or datetime.utcnow()
    out: dict[str, Any] = {
        "username": username,
        "message": message,
        "timestamp": t.isoformat() + "Z",
    }
    if user_id is not None:
        out["user_id"] = user_id
    if client_msg_id:
        out["client_msg_id"] = client_msg_id
    return out


async def _send(ws: WebSocket, **kwargs):
    await ws.send_json(_msg_payload(**kwargs))


@router.websocket("/chat")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    user_id: int | None = None
    username: str | None = None
    session_id: str | None = None
    user_groq_api_key: str | None = None
    user_groq_model = DEFAULT_GROQ_MODEL
    bot_name = DEFAULT_BOT_NAME
    user_system_prompt = DEFAULT_SYSTEM_PROMPT
    authenticated = False
    existing: list = []

    try:
        while True:
            raw = await websocket.receive_json()
            message_text = (raw.get("message") or "").strip()

            if not authenticated:
                if message_text.startswith("AUTH:"):
                    parts = message_text.split(":")
                    token = (parts[1] or "").strip() if len(parts) > 1 else ""
                    dec = verify_token(token)
                    if dec:
                        uid, uname = dec
                        user_id, username = uid, uname
                        session_id = (
                            (parts[2] or "").strip()
                            if len(parts) > 2 and parts[2]
                            else str(uuid.uuid4())
                        )
                        authenticated = True

                        async with AsyncSessionLocal() as session:
                            try:
                                user = await repos.user_by_id(session, user_id)
                                if user:
                                    if user.groq_model in DEPRECATED_MODELS:
                                        new_m = DEPRECATED_MODELS[user.groq_model]
                                        await repos.update_user_model(session, user_id, new_m)
                                        user_groq_model = new_m
                                    else:
                                        user_groq_model = user.groq_model
                                    bot_name = user.bot_name
                                    user_system_prompt = user.system_prompt or DEFAULT_SYSTEM_PROMPT
                                    if user.groq_api_key_encrypted:

                                        async def update_key(enc: str) -> None:
                                            async with AsyncSessionLocal() as s2:
                                                await repos.update_user_groq_key(s2, user_id, enc)
                                                await s2.commit()

                                        try:
                                            user_groq_api_key = await decrypt_api_key(
                                                user.groq_api_key_encrypted,
                                                user_id,
                                                update_key,
                                            )
                                        except Exception as e:
                                            logger.exception("decrypt api key")
                                            await _send(
                                                websocket,
                                                username="SYSTEM",
                                                message=(
                                                    "Warning: Failed to decrypt API key. "
                                                    f"Please reconfigure it in settings. Error: {e!s}"
                                                ),
                                            )
                                await chat_context.ensure_session(session, session_id, user_id)
                                existing = await repos.get_chat_messages_rows(
                                    session, session_id, user_id
                                )
                                await session.commit()
                            except Exception:
                                await session.rollback()
                                raise

                        for m in existing:
                            await _send(
                                websocket,
                                username=m.username,
                                message=m.message,
                                ts=m.timestamp,
                                user_id=m.user_id,
                            )

                        await _send(websocket, username="SYSTEM", message="Connected successfully")
                        await manager.register(user_id, websocket)
                    else:
                        await _send(websocket, username="SYSTEM", message="Invalid authentication token")
                        await websocket.close()
                        return
                else:
                    await _send(
                        websocket,
                        username="SYSTEM",
                        message="Please authenticate first. Send 'AUTH:your_token'",
                    )
                continue

            assert user_id is not None and username is not None and session_id is not None

            if not message_text:
                continue

            if message_text.startswith("/ai "):
                ai_message = message_text[4:].strip()
                if not ai_message:
                    await _send(
                        websocket,
                        username=bot_name,
                        message="Please provide a message after /ai",
                        user_id=user_id,
                    )
                    continue

                ts_user = _parse_client_timestamp(raw.get("timestamp")) or datetime.utcnow()
                cid = _client_msg_id(raw)
                user_msg = _msg_payload(
                    username,
                    f"/ai {ai_message}",
                    ts=ts_user,
                    user_id=user_id,
                    client_msg_id=cid,
                )
                await manager.broadcast_user(user_id, user_msg)

                async with AsyncSessionLocal() as session:
                    try:
                        await chat_context.add_to_context(session, session_id, user_id, ai_message, "user")
                        await repos.save_chat_message(
                            session,
                            session_id,
                            user_id,
                            username,
                            user_msg["message"],
                            ts_user,
                        )
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

                async with AsyncSessionLocal() as session:
                    ctx = await chat_context.get_session_context(session, session_id, user_id)

                if not user_groq_api_key:
                    err = _msg_payload(
                        bot_name,
                        "Groq API key not configured. Please configure it in settings.",
                        user_id=user_id,
                    )
                    await manager.broadcast_user(user_id, err)
                    continue

                try:
                    content, _model = await asyncio.to_thread(
                        groq_client.generate_response,
                        user_groq_api_key,
                        ai_message,
                        ctx,
                        user_groq_model,
                        user_system_prompt,
                    )
                except Exception as e:
                    logger.exception("groq")
                    err_msg = "Failed to generate response"
                    es = str(e)
                    if "Invalid API Key" in es or "invalid_api_key" in es:
                        err_msg = (
                            "Invalid Groq API key. Please check and update your API key in settings "
                            "(console.groq.com)."
                        )
                    elif "401" in es:
                        err_msg = "Authentication failed with Groq API. Please verify your API key in settings."
                    elif es:
                        err_msg = f"Error: {es}"
                    await manager.broadcast_user(user_id, _msg_payload(bot_name, err_msg, user_id=user_id))
                    continue

                async with AsyncSessionLocal() as session:
                    try:
                        await chat_context.add_to_context(session, session_id, user_id, content, "assistant")
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

                ts_ai = datetime.utcnow()
                ai_resp = _msg_payload(bot_name, content, ts=ts_ai, user_id=user_id)
                async with AsyncSessionLocal() as session:
                    try:
                        await repos.save_chat_message(
                            session,
                            session_id,
                            user_id,
                            bot_name,
                            content,
                            ts_ai,
                        )
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

                await manager.broadcast_user(user_id, ai_resp)
            else:
                ts = _parse_client_timestamp(raw.get("timestamp")) or datetime.utcnow()
                cid = _client_msg_id(raw)
                full = _msg_payload(username, message_text, ts=ts, user_id=user_id, client_msg_id=cid)
                await manager.broadcast_user(user_id, full)
                async with AsyncSessionLocal() as session:
                    try:
                        await repos.save_chat_message(
                            session,
                            session_id,
                            user_id,
                            username,
                            message_text,
                            ts,
                        )
                        await chat_context.add_to_context(session, session_id, user_id, message_text, "user")
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception("Stream error: %s", e)
        try:
            await _send(websocket, username="SYSTEM", message=f"Stream error: {e!s}")
        except Exception:
            pass
    finally:
        if user_id is not None:
            manager.disconnect(user_id, websocket)
