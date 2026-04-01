"""Application ports (interfaces for infrastructure)."""

from typing import Protocol


class TokenPort(Protocol):
    def create_token(self, user_id: int, username: str) -> str: ...
    def verify_token(self, token: str) -> tuple[int, str] | None: ...


class EncryptionPort(Protocol):
    def encrypt_api_key(self, plaintext: str) -> str: ...


class LlmPort(Protocol):
    async def generate(
        self,
        api_key: str,
        message: str,
        context: list[dict[str, str]],
        model: str,
        system_prompt: str,
    ) -> tuple[str, str]: ...
