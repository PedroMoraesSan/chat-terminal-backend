"""Hash de senha com bcrypt (evita passlib + bcrypt 5.x incompatíveis)."""

import bcrypt

_ROUNDS = 10


def hash_password(plain: str) -> str:
    pw = plain.encode("utf-8")
    if len(pw) > 72:
        pw = pw[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt(rounds=_ROUNDS)).decode("ascii")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        pw = plain.encode("utf-8")
        if len(pw) > 72:
            pw = pw[:72]
        return bcrypt.checkpw(pw, password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False
