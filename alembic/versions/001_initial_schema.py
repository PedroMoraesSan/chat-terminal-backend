"""Initial schema (Encore migrations 1-7 consolidated).

Revision ID: 001
Revises:
Create Date: 2025-04-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("groq_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "groq_model",
            sa.String(length=50),
            server_default="llama-3.1-8b-instant",
            nullable=False,
        ),
        sa.Column("bot_name", sa.String(length=50), server_default="GroqBot", nullable=False),
        sa.Column(
            "system_prompt",
            sa.Text(),
            server_default=(
                "You are a helpful AI assistant in a terminal-style chat interface. "
                "Be concise and friendly."
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_users_username", "users", ["username"], unique=True)

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("chat_name", sa.String(length=100), server_default="Chat 1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("last_activity", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("idx_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("idx_chat_sessions_session_id", "chat_sessions", ["session_id"])
    op.create_index("idx_chat_sessions_user_name", "chat_sessions", ["user_id", "chat_name"])

    op.create_table(
        "chat_context",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "messages",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.session_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "user_id", name="idx_chat_context_session_unique"),
    )
    op.create_index("idx_chat_context_session_id", "chat_context", ["session_id"])
    op.create_index("idx_chat_context_user_id", "chat_context", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.session_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("idx_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index(
        "idx_chat_messages_timestamp",
        "chat_messages",
        ["session_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("idx_chat_messages_timestamp", table_name="chat_messages")
    op.drop_index("idx_chat_messages_user_id", table_name="chat_messages")
    op.drop_index("idx_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("idx_chat_context_user_id", table_name="chat_context")
    op.drop_index("idx_chat_context_session_id", table_name="chat_context")
    op.drop_table("chat_context")
    op.drop_index("idx_chat_sessions_user_name", table_name="chat_sessions")
    op.drop_index("idx_chat_sessions_session_id", table_name="chat_sessions")
    op.drop_index("idx_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
    op.drop_index("idx_users_username", table_name="users")
    op.drop_table("users")
