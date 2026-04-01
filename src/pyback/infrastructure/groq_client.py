import logging

from groq import Groq

from pyback.domain.constants import DEFAULT_GROQ_MODEL, DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

ContextMessage = dict[str, str]


def generate_response(
    api_key: str,
    message: str,
    context: list[ContextMessage],
    model: str = DEFAULT_GROQ_MODEL,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> tuple[str, str]:
    client = Groq(api_key=api_key)

    valid_context: list[ContextMessage] = []
    for msg in context:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role not in ("system", "user", "assistant") or not isinstance(content, str):
            continue
        valid_context.append({"role": role, "content": content})

    context_without_system = [m for m in valid_context if m["role"] != "system"]
    messages: list[ContextMessage] = [
        {"role": "system", "content": system_prompt},
        *context_without_system,
        {"role": "user", "content": message},
    ]

    logger.info("[Groq] Sending %s messages (%s from context)", len(messages), len(valid_context))

    try:
        completion = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=0.7,
            max_tokens=1024,
        )
        choice = completion.choices[0].message.content if completion.choices else None
        content = choice or "Sorry, I couldn't generate a response."
        return content, completion.model or model
    except Exception as e:
        logger.exception("Groq API error")
        raise RuntimeError(f"Groq API error: {e!s}") from e
