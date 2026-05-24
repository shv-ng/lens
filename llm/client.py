from groq import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
from langchain_groq import ChatGroq


def get_llm(temperature: float = 0.2):
    primary = ChatGroq(model="llama-3.3-70b-versatile", temperature=temperature)

    fallbacks = [
        ChatGroq(
            model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=temperature
        ),
        ChatGroq(model="qwen/qwen3-32b", temperature=temperature),
        ChatGroq(model="llama-3.1-8b-instant", temperature=temperature),
        ChatGroq(model="openai/gpt-oss-120b", temperature=temperature),
        ChatGroq(model="groq/compound", temperature=temperature),
        ChatGroq(model="groq/compound-mini", temperature=temperature),
    ]

    return primary.with_fallbacks(
        fallbacks,
        exceptions_to_handle=(
            RateLimitError,
            APIError,
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            BadRequestError,
        ),
    )
