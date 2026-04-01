from datetime import UTC, datetime, timedelta

import jwt

from pyback.config import get_settings


def create_token(user_id: int, username: str) -> str:
    settings = get_settings()
    payload = {
        "userId": user_id,
        "username": username,
        "exp": datetime.now(UTC) + timedelta(days=7),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> tuple[int, str] | None:
    settings = get_settings()
    try:
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        uid = decoded.get("userId")
        uname = decoded.get("username")
        if uid is None or uname is None:
            return None
        return int(uid), str(uname)
    except jwt.PyJWTError:
        return None
