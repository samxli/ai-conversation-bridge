"""Build chat model clients from LLM_* configuration.

LangGraph uses the OpenAI Chat Completions API only (`POST {LLM_BASE_URL}/chat/completions`),
via langchain-openai ChatOpenAI. The OpenAI Responses API and native Anthropic Messages
are not supported. OpenRouter and other OpenAI-compatible proxies work when they expose
Chat Completions at that path.
"""

from langchain_openai import ChatOpenAI

from app.config import Config


def chat_model_kwargs(config: type[Config] = Config) -> dict:
    """Return ChatOpenAI kwargs from LLM_* config; omit reasoning when unset."""
    kwargs = {
        "model": config.LLM_MODEL,
        "api_key": config.LLM_API_KEY,
        "base_url": config.LLM_BASE_URL,
        "temperature": config.LLM_TEMPERATURE,
    }
    if config.LLM_REASONING_EFFORT:
        kwargs["extra_body"] = {"reasoning": {"effort": config.LLM_REASONING_EFFORT}}
    return kwargs


def build_chat_model(config: type[Config] = Config):
    """Return a ChatOpenAI client for OpenAI Chat Completions at LLM_BASE_URL."""
    return ChatOpenAI(**chat_model_kwargs(config))
