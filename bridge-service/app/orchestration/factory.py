"""Orchestrator factory: map ORCHESTRATOR config to an implementation."""

import logging

from app.config import Config
from app.orchestration.direct_llm.client import DirectLLMClient
from app.orchestration.flowise.client import FlowiseClient

logger = logging.getLogger(__name__)


def create_orchestrator(config: type[Config] = Config):
    """Construct the orchestrator selected by config.ORCHESTRATOR."""
    name = config.ORCHESTRATOR
    if name == "flowise":
        logger.info("Orchestrator: flowise")
        return FlowiseClient(
            config.FLOWISE_API_URL,
            config.FLOWISE_API_KEY,
            config.FLOWISE_TIMEOUT,
        )
    if name == "direct_llm":
        logger.info("Orchestrator: direct_llm")
        return DirectLLMClient(
            api_key=config.LLM_API_KEY,
            model=config.LLM_MODEL,
            api_url=config.OPENROUTER_API_URL,
            system_prompt=config.LLM_SYSTEM_PROMPT,
            reasoning_effort=config.LLM_REASONING_EFFORT,
        )
    if name == "langgraph":
        # Imported lazily so Phases 1–3 do not require LangGraph packages until Phase 4.
        from app.orchestration.langgraph.runtime import LangGraphOrchestrator

        logger.info("Orchestrator: langgraph")
        return LangGraphOrchestrator(config)

    raise SystemExit(f"Unknown ORCHESTRATOR={name!r}")
