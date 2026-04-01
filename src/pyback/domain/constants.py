DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant in a terminal-style chat interface. Be concise and friendly."
)
MAX_CONTEXT_MESSAGES = 20
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_BOT_NAME = "GroqBot"

DEPRECATED_MODELS: dict[str, str] = {
    "llama3-8b-8192": "llama-3.1-8b-instant",
    "llama3-70b-8192": "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768": "llama-3.1-8b-instant",
}

AVAILABLE_MODELS: list[dict[str, str]] = [
    {
        "id": "llama-3.1-8b-instant",
        "name": "Llama 3.1 8B Instant",
        "description": "Fast and efficient model for quick responses",
    },
    {
        "id": "llama-3.1-70b-versatile",
        "name": "Llama 3.1 70B Versatile",
        "description": "High-quality model for complex tasks",
    },
    {
        "id": "llama-3.3-70b-versatile",
        "name": "Llama 3.3 70B Versatile",
        "description": "Latest model with improved capabilities",
    },
    {
        "id": "gemma2-9b-it",
        "name": "Gemma2 9B",
        "description": "Compact model with good performance",
    },
    {
        "id": "mixtral-8x7b-32768",
        "name": "Mixtral 8x7B (Legacy)",
        "description": "Legacy model - may be deprecated",
    },
]
