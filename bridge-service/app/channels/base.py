"""Channel adapter protocol and shared inbound message shape."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class InboundMessage:
    """Normalized inbound chat message from a channel adapter."""

    text: str
    session_id: str
    reply_target: Any
    sender_id: str


class ChannelAdapter(Protocol):
    """Protocol for chat-platform webhook adapters."""

    def parse_inbound(self, *args, **kwargs) -> InboundMessage | None:
        """Parse a platform payload into an InboundMessage, or None to ignore."""
        ...
