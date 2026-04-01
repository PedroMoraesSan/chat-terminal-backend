import ssl
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import AliasChoices, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


def _to_asyncpg_driver_url(u: str) -> str:
    u = u.strip()
    if "+asyncpg" in u:
        return u
    if "+psycopg2" in u:
        return u.replace("+psycopg2", "+asyncpg", 1)
    if u.startswith("postgres://"):
        return "postgresql+asyncpg://" + u[len("postgres://") :]
    if u.startswith("postgresql://"):
        return "postgresql+asyncpg://" + u[len("postgresql://") :]
    return u


# Query keys que o SQLAlchemy repassa ao asyncpg.connect() mas o asyncpg não aceita (são do libpq/psycopg2).
_ASYNCPG_UNSUPPORTED_QUERY_KEYS = frozenset(
    {
        "channel_binding",
        "gssencmode",
        "sslrootcert",
        "sslcert",
        "sslkey",
        "sslcrl",
        "sslpassword",
        "krbsrvname",
        "gsslib",
        "target_session_attrs",
    }
)


def _asyncpg_url_and_connect_args(async_url: str) -> tuple[str, dict]:
    """
    asyncpg.connect() não aceita vários parâmetros de query estilo libpq (sslmode, channel_binding, …).
    Remove-os da URL; sslmode/ssl=require viram connect_args TLS quando aplicável.
    """
    parsed = urlparse(async_url)
    if not parsed.query:
        return async_url, {}

    need_ssl = False
    kept: list[tuple[str, str]] = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        kl = k.lower()
        vl = (v or "").lower()
        if kl in _ASYNCPG_UNSUPPORTED_QUERY_KEYS:
            continue
        if kl == "sslmode":
            if vl not in ("disable", "allow", ""):
                need_ssl = True
        elif kl == "ssl" and vl in ("1", "true", "require", "yes", "on"):
            need_ssl = True
        else:
            kept.append((k, v))

    new_query = urlencode(kept)
    clean = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )
    connect_args: dict = {}
    if need_ssl:
        connect_args["ssl"] = ssl.create_default_context()
    return clean, connect_args


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    database_url: str = Field(
        ...,
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "database_url",
            "NEON_DATABASE_URL",
            "POSTGRES_URL",
            "PGURL",
        ),
    )
    jwt_secret: str = Field(
        ...,
        validation_alias=AliasChoices("JWT_SECRET", "jwt_secret"),
    )
    encryption_key: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    api_public_base_url: str = "http://127.0.0.1:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def async_database_url(self) -> str:
        """URL para SQLAlchemy async (asyncpg), sem query params incompatíveis."""
        return _asyncpg_url_and_connect_args(_to_asyncpg_driver_url(self.database_url))[0]

    @property
    def async_connect_args(self) -> dict:
        """Ex.: TLS para Neon quando a URL traz sslmode=require."""
        return _asyncpg_url_and_connect_args(_to_asyncpg_driver_url(self.database_url))[1]

    @property
    def sync_database_url(self) -> str:
        """Alembic / ferramentas síncronas — psycopg2."""
        u = self.database_url.strip()
        if "+asyncpg" in u:
            return u.replace("+asyncpg", "+psycopg2", 1)
        if "+psycopg2" in u:
            return u
        if u.startswith("postgres://"):
            return "postgresql+psycopg2://" + u[len("postgres://") :]
        if u.startswith("postgresql://"):
            return "postgresql+psycopg2://" + u[len("postgresql://") :]
        return u


def _load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        raise RuntimeError(
            "Variáveis de ambiente obrigatórias ausentes ou inválidas.\n"
            "No Railway: abra o serviço → Variables e defina pelo menos:\n"
            "  • DATABASE_URL (string do Postgres/Neon; ou referencie a variável do plugin Postgres)\n"
            "  • JWT_SECRET (string longa e secreta)\n"
            "Também aceitos: NEON_DATABASE_URL, POSTGRES_URL ou PGURL no lugar de DATABASE_URL.\n"
            f"Detalhe: {e}"
        ) from e


@lru_cache
def get_settings() -> Settings:
    return _load_settings()
