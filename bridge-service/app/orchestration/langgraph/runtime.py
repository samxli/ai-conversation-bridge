"""LangGraph orchestrator: compiles the reference graph and serves invoke()."""

from __future__ import annotations

import asyncio
import logging

from langchain_core.messages import HumanMessage

from app.config import Config
from app.core import async_runner
from app.orchestration.base import OrchestrationRequest, OrchestrationResult
from app.orchestration.errors import FailureCode
from app.orchestration.langgraph.graph import build_graph, extract_final_text
from app.orchestration.langgraph.state.factory import make_checkpointer
from app.orchestration.langgraph.tools.mcp import load_mcp_tools
from app.orchestration.models import build_chat_model

logger = logging.getLogger(__name__)


class LangGraphOrchestrator:
    """In-process LangGraph orchestrator implementing the Orchestrator protocol."""

    def __init__(self, config: type[Config] = Config):
        """Discover MCP tools and compile the graph once at construction (startup)."""
        self.config = config
        self._graph = None
        try:
            async_runner.run_coroutine(self._build_graph(), timeout=120.0)
        except Exception as e:
            raise SystemExit(f"LangGraph startup failed: {type(e).__name__}: {e}") from e

    async def _build_graph(self) -> None:
        model = build_chat_model(self.config)
        tools = await load_mcp_tools(
            self.config.MCP_SERVER_URL,
            self.config.MCP_AUTH_HEADER,
            self.config.MCP_TOOL_ALLOWLIST,
        )
        checkpointer = make_checkpointer(self.config)
        self._graph = build_graph(
            model,
            tools,
            checkpointer,
            system_prompt=self.config.LLM_SYSTEM_PROMPT,
            message_window=self.config.LLM_MESSAGE_WINDOW,
        )
        logger.info("LangGraph reference graph compiled with %d tools", len(tools))

    async def invoke(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Run one user turn against the compiled graph using session_id as thread_id."""
        if self._graph is None:
            return OrchestrationResult(
                text=None,
                failure=FailureCode.UNAVAILABLE,
                detail="LangGraph graph was not initialized",
            )

        config = {"configurable": {"thread_id": request.session_id}}
        timeout = float(self.config.ORCHESTRATOR_TIMEOUT)
        try:
            result = await asyncio.wait_for(
                self._graph.ainvoke(
                    {"messages": [HumanMessage(content=request.message)], "iterations": 0},
                    config=config,
                ),
                timeout=timeout,
            )
            text = extract_final_text(result.get("messages", []))
            if not text:
                return OrchestrationResult(
                    text=None,
                    failure=FailureCode.UNAVAILABLE,
                    detail="LangGraph returned no assistant text",
                )
            return OrchestrationResult(text=text)
        except TimeoutError as e:
            return OrchestrationResult(
                text=None,
                failure=FailureCode.TIMEOUT,
                detail=f"LangGraph timed out after {timeout}s: {e}",
            )
        except Exception as e:
            detail = f"LangGraph invoke failed ({type(e).__name__}): {e}"
            logger.error(detail)
            return OrchestrationResult(text=None, failure=FailureCode.UNAVAILABLE, detail=detail)
