from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    groq_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    groq_model: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="llama-3.1-8b-instant"
    )
    bot_name: Mapped[str] = mapped_column(String(50), nullable=False, server_default="GroqBot")
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    sessions: Mapped[list["ChatSessionModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    chat_name: Mapped[str] = mapped_column(String(100), nullable=False, server_default="Chat 1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_activity: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["UserModel"] = relationship(back_populates="sessions")


class ChatContextModel(Base):
    __tablename__ = "chat_context"
    __table_args__ = (UniqueConstraint("session_id", "user_id", name="idx_chat_context_session_unique"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, server_default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("chat_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
