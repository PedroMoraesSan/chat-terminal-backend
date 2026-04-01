import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pyback.domain.constants import MAX_CONTEXT_MESSAGES
from pyback.infrastructure.persistence import repos

logger = logging.getLogger(__name__)

Role = str  # "system" | "user" | "assistant"


async def get_session_context(
    session: AsyncSession, session_id: str, user_id: int
) -> list[dict[str, str]]:
    row = await repos.get_context_row(session, session_id, user_id)
    if row is None or row.messages is None:
        return []

    raw = row.messages
    try:
        if isinstance(raw, str):
            parsed: Any = json.loads(raw)
            if isinstance(parsed, str):
                messages = json.loads(parsed)
            else:
                messages = parsed
        else:
            messages = raw
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("[Context] Failed to parse JSON for session %s: %s", session_id, e)
        return []

    if not isinstance(messages, list):
        return []

    valid: list[dict[str, str]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role not in ("system", "user", "assistant") or not isinstance(content, str):
            continue
        valid.append({"role": role, "content": content})

    return valid[-MAX_CONTEXT_MESSAGES:]


async def add_to_context(
    session: AsyncSession,
    session_id: str,
    user_id: int,
    message: str,
    role: Role,
) -> None:
    ctx_msg = {"role": role, "content": message}
    existing = await repos.get_context_row(session, session_id, user_id)

    if existing and existing.messages is not None:
        existing_messages = _normalize_messages(existing.messages)
        valid = _filter_valid(existing_messages)
        updated = (valid + [ctx_msg])[-MAX_CONTEXT_MESSAGES:]
    else:
        updated = [ctx_msg]

    await repos.upsert_context_messages(session, session_id, user_id, updated)


def _normalize_messages(raw: Any) -> list[Any]:
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, str):
                return json.loads(parsed)
            return parsed
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(raw, list):
        return raw
    return []


def _filter_valid(messages: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if not role or not content:
            continue
        out.append({"role": str(role), "content": str(content)})
    return out


async def ensure_session(
    session: AsyncSession, session_id: str, user_id: int, chat_name: str | None = None
) -> None:
    await repos.ensure_session_row(session, session_id, user_id, chat_name)
