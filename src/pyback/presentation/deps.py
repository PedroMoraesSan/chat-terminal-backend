from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from pyback.infrastructure.persistence.session import get_async_session
from pyback.infrastructure.security.jwt_service import verify_token


async def session_dep():
    async for s in get_async_session():
        yield s


SessionDep = Annotated[AsyncSession, Depends(session_dep)]


def user_id_from_token(token: str) -> int:
    decoded = verify_token(token)
    if not decoded:
        raise HTTPException(status_code=401, detail="Invalid token")
    return decoded[0]


async def auth_user_id_query(token: str | None = Query(None)) -> int:
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id_from_token(token)
