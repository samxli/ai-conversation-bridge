"""Typed failure codes for orchestration outcomes."""

from enum import Enum


class FailureCode(str, Enum):
    """Machine-readable orchestration failure categories."""

    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UPSTREAM_ERROR = "upstream_error"
    UNAVAILABLE = "unavailable"
