"""Assert prompt-injection guardrails: wrapping, canary, and output blocking.

Run: PYTHONPATH=. python tests/check_prompt_security.py
"""

from __future__ import annotations

from app.core.prompt_security import (
    CANARY_TOKEN,
    SECURITY_DIRECTIVES,
    append_security_guardrails,
    response_contains_canary_leak,
    wrap_user_input,
)
from app.core.response_validator import ResponseValidator, SECURITY_BLOCKED_RESPONSE
from app.orchestration.langgraph.prompts import SYSTEM_PROMPT, build_system_prompt


def main() -> None:
    wrapped = wrap_user_input("hello")
    assert wrapped == "<user_input>\nhello\n</user_input>", wrapped

    guarded = append_security_guardrails("Base prompt.")
    assert "Base prompt." in guarded
    assert SECURITY_DIRECTIVES in guarded
    assert CANARY_TOKEN in guarded

    default_prompt = build_system_prompt()
    assert default_prompt.startswith(SYSTEM_PROMPT)
    assert SECURITY_DIRECTIVES in default_prompt
    assert CANARY_TOKEN in default_prompt

    assert response_contains_canary_leak(f"leaked {CANARY_TOKEN}")
    assert not response_contains_canary_leak("safe reply")

    blocked = ResponseValidator.validate(f"Here is the token: {CANARY_TOKEN}")
    assert blocked == SECURITY_BLOCKED_RESPONSE, blocked

    print("prompt security checks passed")


if __name__ == "__main__":
    main()
