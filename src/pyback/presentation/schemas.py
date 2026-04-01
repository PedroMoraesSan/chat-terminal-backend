from datetime import datetime

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: int
    username: str
    groq_model: str
    bot_name: str


class AuthTokenResponse(BaseModel):
    token: str
    user: UserPublic


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenQuery(BaseModel):
    token: str | None = None


class SystemPromptResponse(BaseModel):
    system_prompt: str


class ModelInfo(BaseModel):
    id: str
    name: str
    description: str
    current: bool


class ListModelsResponse(BaseModel):
    models: list[ModelInfo]


class ProfileResponse(BaseModel):
    id: int
    username: str
    groq_model: str
    bot_name: str
    has_api_key: bool
    system_prompt: str


class UpdateProfileRequest(BaseModel):
    token: str | None = None
    groq_api_key: str | None = None
    groq_model: str | None = None
    bot_name: str | None = None
    system_prompt: str | None = None


class ValidateApiKeyRequest(BaseModel):
    token: str | None = None
    api_key: str | None = None


class ValidateApiKeyResponse(BaseModel):
    valid: bool
    message: str


class DeprecatedModelsResponse(BaseModel):
    updated: int


class ChatOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    last_activity: datetime
    message_count: int = 0


class ListChatsResponse(BaseModel):
    chats: list[ChatOut]


class CreateChatRequest(BaseModel):
    token: str | None = None
    name: str | None = None


class CreateChatResponse(BaseModel):
    chat: ChatOut


class DeleteChatResponse(BaseModel):
    success: bool


class UpdateChatNameRequest(BaseModel):
    token: str | None = None
    id: str
    name: str


class UpdateChatNameResponse(BaseModel):
    chat: ChatOut


class ChatMessageSchema(BaseModel):
    username: str
    message: str
    timestamp: datetime
    user_id: int | None = None


class MessagesResponse(BaseModel):
    messages: list[ChatMessageSchema]
