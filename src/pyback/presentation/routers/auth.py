import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from groq import Groq
from pyback.domain.constants import (
    AVAILABLE_MODELS,
    DEFAULT_BOT_NAME,
    DEFAULT_GROQ_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEPRECATED_MODELS,
)
from pyback.infrastructure.persistence import repos
from pyback.infrastructure.security.encryption import encrypt_api_key
from pyback.infrastructure.security.jwt_service import create_token, verify_token
from pyback.infrastructure.security.password import hash_password, verify_password
from pyback.presentation.deps import SessionDep, auth_user_id_query
from pyback.presentation.schemas import (
    AuthTokenResponse,
    DeprecatedModelsResponse,
    ListModelsResponse,
    LoginRequest,
    ModelInfo,
    ProfileResponse,
    RegisterRequest,
    SystemPromptResponse,
    UpdateProfileRequest,
    UserPublic,
    ValidateApiKeyRequest,
    ValidateApiKeyResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _require_body_token(token: str | None) -> None:
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/register", response_model=AuthTokenResponse)
async def register(req: RegisterRequest, session: SessionDep):
    u = req.username.strip() if req.username else ""
    if len(u) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters long")
    if not req.password or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

    if await repos.user_by_username(session, u):
        raise HTTPException(status_code=400, detail="Username already exists")

    password_hash = hash_password(req.password)
    user = await repos.create_user(
        session,
        username=u,
        password_hash=password_hash,
        groq_model=DEFAULT_GROQ_MODEL,
        bot_name=DEFAULT_BOT_NAME,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
    )
    token = create_token(user.id, user.username)
    return AuthTokenResponse(
        token=token,
        user=UserPublic(
            id=user.id,
            username=user.username,
            groq_model=user.groq_model,
            bot_name=user.bot_name,
        ),
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(req: LoginRequest, session: SessionDep):
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    user = await repos.user_by_username(session, req.username.strip())
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    if user.groq_model in DEPRECATED_MODELS:
        new_m = DEPRECATED_MODELS[user.groq_model]
        await repos.update_user_model(session, user.id, new_m)
        user.groq_model = new_m

    token = create_token(user.id, user.username)
    return AuthTokenResponse(
        token=token,
        user=UserPublic(
            id=user.id,
            username=user.username,
            groq_model=user.groq_model,
            bot_name=user.bot_name,
        ),
    )


@router.get("/system-prompt", response_model=SystemPromptResponse)
async def get_system_prompt(
    session: SessionDep,
    user_id: Annotated[int, Depends(auth_user_id_query)],
):
    user = await repos.user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    prompt = user.system_prompt or DEFAULT_SYSTEM_PROMPT
    return SystemPromptResponse(system_prompt=prompt)


@router.get("/models", response_model=ListModelsResponse)
async def list_models(
    session: SessionDep,
    user_id: Annotated[int, Depends(auth_user_id_query)],
):
    user = await repos.user_by_id(session, user_id)
    current = user.groq_model if user else DEFAULT_GROQ_MODEL
    models = [
        ModelInfo(
            id=m["id"],
            name=m["name"],
            description=m["description"],
            current=(current == m["id"]),
        )
        for m in AVAILABLE_MODELS
    ]
    return ListModelsResponse(models=models)


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    session: SessionDep,
    user_id: Annotated[int, Depends(auth_user_id_query)],
):
    user = await repos.user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    return ProfileResponse(
        id=user.id,
        username=user.username,
        groq_model=user.groq_model,
        bot_name=user.bot_name,
        has_api_key=user.groq_api_key_encrypted is not None,
        system_prompt=user.system_prompt or DEFAULT_SYSTEM_PROMPT,
    )


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(req: UpdateProfileRequest, session: SessionDep):
    _require_body_token(req.token)
    user_id = verify_token(req.token or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = user_id[0]

    from pyback.config import get_settings

    settings = get_settings()

    if req.groq_api_key is not None and req.groq_api_key.strip():
        try:
            enc = encrypt_api_key(req.groq_api_key.strip(), settings.encryption_key)
            await repos.update_user_groq_key(session, uid, enc)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.exception("encrypt api key")
            raise HTTPException(status_code=400, detail=f"Failed to encrypt API key: {e!s}") from e

    if req.groq_model:
        await repos.update_user_model(session, uid, req.groq_model)
    if req.bot_name:
        await repos.update_user_bot_name(session, uid, req.bot_name)
    if req.system_prompt is not None:
        prompt_val = DEFAULT_SYSTEM_PROMPT if req.system_prompt.strip() == "" else req.system_prompt.strip()
        await repos.update_user_system_prompt(session, uid, prompt_val)

    user = await repos.user_by_id(session, uid)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    return ProfileResponse(
        id=user.id,
        username=user.username,
        groq_model=user.groq_model,
        bot_name=user.bot_name,
        has_api_key=user.groq_api_key_encrypted is not None,
        system_prompt=user.system_prompt or DEFAULT_SYSTEM_PROMPT,
    )


@router.post("/validate-api-key", response_model=ValidateApiKeyResponse)
async def validate_api_key(req: ValidateApiKeyRequest, session: SessionDep):
    _require_body_token(req.token)
    if not req.api_key or not req.api_key.strip():
        raise HTTPException(status_code=400, detail="API key is required")

    def _call():
        client = Groq(api_key=req.api_key.strip())
        client.chat.completions.create(
            messages=[{"role": "user", "content": "test"}],
            model=DEFAULT_GROQ_MODEL,
            max_tokens=1,
        )

    try:
        await asyncio.to_thread(_call)
        return ValidateApiKeyResponse(valid=True, message="API key is valid")
    except Exception as e:
        logger.exception("API key validation")
        err = getattr(e, "status_code", None) or getattr(e, "status", None)
        code = getattr(e, "code", None)
        if err == 401 or code == "invalid_api_key":
            return ValidateApiKeyResponse(
                valid=False,
                message="Invalid API key. Please check your key from console.groq.com",
            )
        return ValidateApiKeyResponse(valid=False, message=f"API key validation failed: {e!s}")


@router.post("/update-deprecated-models", response_model=DeprecatedModelsResponse)
async def update_deprecated_models(req: ValidateApiKeyRequest, session: SessionDep):
    """Body only needs token (reuse schema with optional api_key ignored)."""
    _require_body_token(req.token)
    await repos.apply_deprecated_model_updates(session)
    replacement_models = list(set(DEPRECATED_MODELS.values()))
    total = await repos.count_users_by_models(session, replacement_models)
    return DeprecatedModelsResponse(updated=total)
