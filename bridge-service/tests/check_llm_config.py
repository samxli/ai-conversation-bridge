"""Assert LangGraph prompt, window, and reasoning config semantics.

Run: PYTHONPATH=. python tests/check_llm_config.py
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from app.config import Config
from app.orchestration.langgraph.prompts import SYSTEM_PROMPT, build_system_prompt
from app.orchestration.models import chat_model_kwargs

DATETIME_SUFFIX = re.compile(r"\n\nCurrent date and time: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def main() -> None:
    default_prompt = build_system_prompt()
    assert default_prompt.startswith(SYSTEM_PROMPT)
    assert DATETIME_SUFFIX.search(default_prompt), default_prompt

    override = build_system_prompt("Only HR tools.")
    assert override.startswith("Only HR tools.")
    assert SYSTEM_PROMPT not in override
    assert DATETIME_SUFFIX.search(override), override

    class FakeLangGraph:
        ORCHESTRATOR = "langgraph"
        LLM_API_KEY = "k"
        MCP_SERVER_URL = "https://example.test/mcp"
        MCP_TOOL_ALLOWLIST = None
        LLM_MESSAGE_WINDOW = 0

    try:
        Config.validate_for_orchestrator.__func__(FakeLangGraph)
    except SystemExit as e:
        assert "LLM_MESSAGE_WINDOW" in str(e)
    else:
        raise AssertionError("LLM_MESSAGE_WINDOW=0 must fail LangGraph startup")

    base = SimpleNamespace(
        LLM_MODEL="m",
        LLM_API_KEY="k",
        LLM_BASE_URL="https://example.test/v1",
        LLM_TEMPERATURE=0.2,
        LLM_REASONING_EFFORT=None,
    )
    kwargs = chat_model_kwargs(base)
    assert "extra_body" not in kwargs

    base.LLM_REASONING_EFFORT = "low"
    kwargs = chat_model_kwargs(base)
    assert kwargs["extra_body"] == {"reasoning": {"effort": "low"}}

    print("llm config checks passed")


if __name__ == "__main__":
    main()
