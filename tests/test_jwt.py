import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("JWT_SECRET", "unit-test-jwt-secret-32chars-min")
os.environ.setdefault("ENCRYPTION_KEY", "unit-test-enc-key-32chars-min!!")

from pyback.infrastructure.security.jwt_service import create_token, verify_token


def test_create_and_verify_roundtrip():
    token = create_token(42, "alice")
    decoded = verify_token(token)
    assert decoded == (42, "alice")


def test_verify_invalid():
    assert verify_token("not-a-jwt") is None
