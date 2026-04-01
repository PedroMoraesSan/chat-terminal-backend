"""AES-256-CBC compatible with Node crypto (backend/auth/auth.ts)."""

import binascii
import logging
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from pyback.config import get_settings

logger = logging.getLogger(__name__)


def _key_from_string(key_string: str) -> bytes:
    padded = key_string.ljust(32, "0")[:32]
    return padded.encode("utf-8")


def encrypt_api_key(plaintext: str, encryption_key: str) -> str:
    if not encryption_key or not encryption_key.strip():
        raise ValueError("ENCRYPTION_KEY is not configured")
    key = _key_from_string(encryption_key.strip())
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode("utf-8")) + padder.finalize()
    ct = encryptor.update(padded) + encryptor.finalize()
    return iv.hex() + ":" + binascii.hexlify(ct).decode("ascii")


def _decrypt_with_key(key_string: str, encrypted: str) -> str:
    key = _key_from_string(key_string)
    parts = encrypted.split(":")
    if len(parts) != 2:
        raise ValueError("Invalid encrypted key format")
    iv = bytes.fromhex(parts[0])
    ciphertext = bytes.fromhex(parts[1])
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded) + unpadder.finalize()
    return data.decode("utf-8")


async def decrypt_api_key(encrypted_key: str, user_id: int | None, update_user_key) -> str:
    """
    Try ENCRYPTION_KEY first, then JWT_SECRET; optionally re-encrypt with ENCRYPTION_KEY.
    update_user_key: async callable(new_encrypted: str) -> None
    """
    settings = get_settings()
    enc_key = (settings.encryption_key or "").strip()
    jwt_secret = settings.jwt_secret.strip()
    encryption_key_configured = bool(enc_key)

    if enc_key:
        try:
            return _decrypt_with_key(enc_key, encrypted_key)
        except Exception:
            logger.info(
                "[Decrypt] Failed with ENCRYPTION_KEY (key may be old), trying JWT_SECRET fallback..."
            )

    if not jwt_secret:
        raise ValueError("JWT_SECRET is not configured")

    try:
        decrypted = _decrypt_with_key(jwt_secret, encrypted_key)
        logger.info("[Decrypt] Successfully decrypted API key using JWT_SECRET (backward compatibility)")

        if user_id and encryption_key_configured and enc_key:
            try:
                new_enc = encrypt_api_key(decrypted, enc_key)
                await update_user_key(new_enc)
                logger.info("[Decrypt] Migrated API key for user %s to ENCRYPTION_KEY", user_id)
            except Exception as e:
                logger.error("[Decrypt] Failed to migrate API key for user %s: %s", user_id, e)

        return decrypted
    except Exception as err:
        raise ValueError(
            f"Failed to decrypt API key with both ENCRYPTION_KEY and JWT_SECRET. Error: {err!s}"
        ) from err
