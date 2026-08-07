"""Build chat model clients from LLM_* configuration."""

from langchain_openai import ChatOpenAI

from app.config import Config


def build_chat_model(config: type[Config] = Config):
    """Return a ChatOpenAI client pointed at the configured OpenAI-compatible base URL."""
    return ChatOpenAI(
        model=config.LLM_MODEL,
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
        temperature=config.LLM_TEMPERATURE,
    )
