"""User-facing failure messages keyed by FailureCode.

Locale-specific modules can replace DEFAULT_MESSAGES later without changing
orchestrator implementations.
"""

from app.orchestration.errors import FailureCode

# Exact strings from the pre-restructure Flowise client (canonical).
# OpenRouter previously used "AI model" for rate limits and
# "(API Key missing)" for configuration; those are collapsed onto this table.
DEFAULT_MESSAGES: dict[FailureCode, str] = {
    FailureCode.CONFIGURATION: "I am currently unable to think (Configuration Error).",
    FailureCode.TIMEOUT: (
        "Sorry, the AI service is taking longer than expected. "
        "Please try again in a moment."
    ),
    FailureCode.RATE_LIMITED: (
        "The AI service is temporarily rate-limited. "
        "Please wait a moment and try again."
    ),
    FailureCode.UPSTREAM_ERROR: "Sorry, the AI service returned an error. Please try again later.",
    FailureCode.UNAVAILABLE: "Sorry, I encountered an error while processing your request.",
}


def user_message_for(failure: FailureCode) -> str:
    """Return the user-facing English string for a failure code."""
    return DEFAULT_MESSAGES[failure]
