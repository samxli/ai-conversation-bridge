"""Orchestration Interface: request/result types and Orchestrator protocol."""

from dataclasses import dataclass
from typing import Protocol

from app.orchestration.errors import FailureCode


@dataclass(frozen=True)
class OrchestrationRequest:
    """Inbound message and session context for an orchestrator."""

    message: str
    session_id: str  # becomes Flowise sessionId / LangGraph thread_id
    metadata: dict | None = None


@dataclass(frozen=True)
class OrchestrationResult:
    """Orchestrator outcome: either reply text or a typed failure."""

    text: str | None
    failure: FailureCode | None = None
    detail: str | None = None  # internal only; never shown to users


class Orchestrator(Protocol):
    """Async contract implemented by Flowise, Direct LLM, and LangGraph."""

    async def invoke(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Run one turn of orchestration for the given request."""
        ...
