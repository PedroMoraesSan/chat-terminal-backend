import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from pyback.domain.utils import generate_random_chat_name
from pyback.infrastructure.persistence import repos
from pyback.presentation.deps import SessionDep, auth_user_id_query
from pyback.presentation.schemas import (
    ChatMessageSchema,
    ChatOut,
    CreateChatRequest,
    CreateChatResponse,
    DeleteChatResponse,
    ListChatsResponse,
    MessagesResponse,
    UpdateChatNameRequest,
    UpdateChatNameResponse,
)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=ListChatsResponse)
async def list_chats(
    session: SessionDep,
    user_id: Annotated[int, Depends(auth_user_id_query)],
):
    rows = await repos.list_chats_for_user(session, user_id)
    return ListChatsResponse(
        chats=[
            ChatOut(
                id=r["id"],
                name=r["name"],
                created_at=r["created_at"],
                last_activity=r["last_activity"],
                message_count=r["message_count"],
            )
            for r in rows
        ]
    )


@router.post("", response_model=CreateChatResponse)
async def create_chat(req: CreateChatRequest, session: SessionDep):
    if not req.token:
        raise HTTPException(status_code=401, detail="Authentication required")
    from pyback.infrastructure.security.jwt_service import verify_token

    dec = verify_token(req.token)
    if not dec:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = dec[0]

    sid = str(uuid.uuid4())
    name = req.name.strip() if req.name and req.name.strip() else generate_random_chat_name()
    row = await repos.insert_chat_session(session, user_id, sid, name)
    return CreateChatResponse(
        chat=ChatOut(
            id=row.session_id,
            name=row.chat_name,
            created_at=row.created_at,
            last_activity=row.last_activity,
            message_count=0,
        )
    )


@router.delete("/delete", response_model=DeleteChatResponse)
async def delete_chat(
    session: SessionDep,
    user_id: Annotated[int, Depends(auth_user_id_query)],
    chat_id: str = Query(..., alias="id"),
):
    if not chat_id:
        raise HTTPException(status_code=400, detail="Chat ID is required")
    if not await repos.chat_session_owned(session, chat_id, user_id):
        raise HTTPException(status_code=400, detail="Chat not found or access denied")
    await repos.delete_chat_session(session, chat_id, user_id)
    return DeleteChatResponse(success=True)


@router.put("/update", response_model=UpdateChatNameResponse)
async def update_chat_name(req: UpdateChatNameRequest, session: SessionDep):
    if not req.token:
        raise HTTPException(status_code=401, detail="Authentication required")
    from pyback.infrastructure.security.jwt_service import verify_token

    dec = verify_token(req.token)
    if not dec:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = dec[0]

    if not req.id:
        raise HTTPException(status_code=400, detail="Chat ID is required")
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Chat name is required")

    row = await repos.get_chat_session_row(session, req.id, user_id)
    if not row:
        raise HTTPException(status_code=400, detail="Chat not found or access denied")

    await repos.update_chat_name(session, req.id, user_id, req.name.strip())
    await session.refresh(row)
    return UpdateChatNameResponse(
        chat=ChatOut(
            id=row.session_id,
            name=req.name.strip(),
            created_at=row.created_at,
            last_activity=row.last_activity,
            message_count=0,
        )
    )


@router.get("/{session_id}/messages", response_model=MessagesResponse)
async def get_messages(
    session: SessionDep,
    user_id: Annotated[int, Depends(auth_user_id_query)],
    session_id: str,
):
    if not await repos.chat_session_owned(session, session_id, user_id):
        raise HTTPException(status_code=400, detail="Chat not found or access denied")
    rows = await repos.get_chat_messages_rows(session, session_id, user_id)
    return MessagesResponse(
        messages=[
            ChatMessageSchema(
                username=m.username,
                message=m.message,
                timestamp=m.timestamp,
                user_id=m.user_id,
            )
            for m in rows
        ]
    )
