from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from pyback.domain.constants import DEPRECATED_MODELS
from pyback.domain.utils import generate_random_chat_name
from pyback.infrastructure.persistence.models import (
    ChatContextModel,
    ChatMessageModel,
    ChatSessionModel,
    UserModel,
)


async def user_by_username(session: AsyncSession, username: str) -> UserModel | None:
    r = await session.execute(select(UserModel).where(UserModel.username == username))
    return r.scalar_one_or_none()


async def user_by_id(session: AsyncSession, user_id: int) -> UserModel | None:
    r = await session.execute(select(UserModel).where(UserModel.id == user_id))
    return r.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    username: str,
    password_hash: str,
    groq_model: str,
    bot_name: str,
    system_prompt: str,
) -> UserModel:
    u = UserModel(
        username=username,
        password_hash=password_hash,
        groq_model=groq_model,
        bot_name=bot_name,
        system_prompt=system_prompt,
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u


async def update_user_groq_key(session: AsyncSession, user_id: int, encrypted: str) -> None:
    await session.execute(
        update(UserModel).where(UserModel.id == user_id).values(groq_api_key_encrypted=encrypted)
    )


async def update_user_model(session: AsyncSession, user_id: int, model: str) -> None:
    await session.execute(update(UserModel).where(UserModel.id == user_id).values(groq_model=model))


async def update_user_bot_name(session: AsyncSession, user_id: int, name: str) -> None:
    await session.execute(update(UserModel).where(UserModel.id == user_id).values(bot_name=name))


async def update_user_system_prompt(session: AsyncSession, user_id: int, prompt: str) -> None:
    await session.execute(update(UserModel).where(UserModel.id == user_id).values(system_prompt=prompt))


async def list_chats_for_user(session: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    cnt = (
        select(ChatMessageModel.session_id, func.count(ChatMessageModel.id).label("c"))
        .where(ChatMessageModel.user_id == user_id)
        .group_by(ChatMessageModel.session_id)
    ).subquery()
    q = (
        select(
            ChatSessionModel.session_id,
            ChatSessionModel.chat_name,
            ChatSessionModel.created_at,
            ChatSessionModel.last_activity,
            func.coalesce(cnt.c.c, 0).label("message_count"),
        )
        .outerjoin(cnt, ChatSessionModel.session_id == cnt.c.session_id)
        .where(ChatSessionModel.user_id == user_id)
        .order_by(ChatSessionModel.last_activity.desc())
    )
    rows = (await session.execute(q)).all()
    return [
        {
            "id": r.session_id,
            "name": r.chat_name or "Chat 1",
            "created_at": r.created_at,
            "last_activity": r.last_activity,
            "message_count": int(r.message_count or 0),
        }
        for r in rows
    ]


async def insert_chat_session(
    session: AsyncSession, user_id: int, session_id: str, name: str
) -> ChatSessionModel:
    now = datetime.utcnow()
    cs = ChatSessionModel(
        user_id=user_id,
        session_id=session_id,
        chat_name=name,
        created_at=now,
        last_activity=now,
    )
    session.add(cs)
    await session.flush()
    await session.refresh(cs)
    return cs


async def chat_session_owned(session: AsyncSession, session_id: str, user_id: int) -> bool:
    r = await session.execute(
        select(ChatSessionModel.id).where(
            ChatSessionModel.session_id == session_id,
            ChatSessionModel.user_id == user_id,
        )
    )
    return r.scalar_one_or_none() is not None


async def delete_chat_session(session: AsyncSession, session_id: str, user_id: int) -> None:
    await session.execute(
        delete(ChatSessionModel).where(
            ChatSessionModel.session_id == session_id,
            ChatSessionModel.user_id == user_id,
        )
    )


async def update_chat_name(session: AsyncSession, session_id: str, user_id: int, name: str) -> None:
    await session.execute(
        update(ChatSessionModel)
        .where(
            ChatSessionModel.session_id == session_id,
            ChatSessionModel.user_id == user_id,
        )
        .values(chat_name=name)
    )


async def get_chat_session_row(session: AsyncSession, session_id: str, user_id: int):
    r = await session.execute(
        select(ChatSessionModel).where(
            ChatSessionModel.session_id == session_id,
            ChatSessionModel.user_id == user_id,
        )
    )
    return r.scalar_one_or_none()


async def save_chat_message(
    session: AsyncSession,
    session_id: str,
    user_id: int,
    username: str,
    message: str,
    ts: datetime,
) -> None:
    cm = ChatMessageModel(
        session_id=session_id,
        user_id=user_id,
        username=username,
        message=message,
        timestamp=ts,
    )
    session.add(cm)


async def get_chat_messages_rows(
    session: AsyncSession, session_id: str, user_id: int
) -> list[ChatMessageModel]:
    r = await session.execute(
        select(ChatMessageModel)
        .where(
            ChatMessageModel.session_id == session_id,
            ChatMessageModel.user_id == user_id,
        )
        .order_by(ChatMessageModel.timestamp.asc())
    )
    return list(r.scalars().all())


async def get_context_row(
    session: AsyncSession, session_id: str, user_id: int
) -> ChatContextModel | None:
    r = await session.execute(
        select(ChatContextModel).where(
            ChatContextModel.session_id == session_id,
            ChatContextModel.user_id == user_id,
        )
    )
    return r.scalar_one_or_none()


async def upsert_context_messages(
    session: AsyncSession,
    session_id: str,
    user_id: int,
    messages: list[dict[str, str]],
) -> None:
    now = datetime.utcnow()
    stmt = insert(ChatContextModel).values(
        session_id=session_id,
        user_id=user_id,
        messages=messages,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["session_id", "user_id"],
        set_={
            "messages": stmt.excluded.messages,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)


async def ensure_session_row(session: AsyncSession, session_id: str, user_id: int, chat_name: str | None):
    existing = await session.execute(
        select(ChatSessionModel).where(ChatSessionModel.session_id == session_id)
    )
    row = existing.scalar_one_or_none()
    now = datetime.utcnow()
    if row is None:
        name = chat_name or generate_random_chat_name()
        session.add(
            ChatSessionModel(
                user_id=user_id,
                session_id=session_id,
                chat_name=name,
                created_at=now,
                last_activity=now,
            )
        )
    else:
        await session.execute(
            update(ChatSessionModel)
            .where(ChatSessionModel.session_id == session_id)
            .values(last_activity=now)
        )


async def apply_deprecated_model_updates(session: AsyncSession) -> None:
    for old, new in DEPRECATED_MODELS.items():
        await session.execute(update(UserModel).where(UserModel.groq_model == old).values(groq_model=new))


async def count_users_by_models(session: AsyncSession, models: list[str]) -> int:
    total = 0
    for m in models:
        r = await session.execute(
            select(func.count()).select_from(UserModel).where(UserModel.groq_model == m)
        )
        total += int(r.scalar_one())
    return total
