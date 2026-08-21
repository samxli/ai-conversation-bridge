"""Feishu (Lark) webhook adapter: verification, parsing, and session IDs."""

import json
import logging
from typing import Any

from app.channels.base import InboundMessage

logger = logging.getLogger(__name__)


class FeishuAdapter:
    """Adapter for Feishu event-subscription callbacks."""

    def __init__(self, verification_token: str | None, max_message_length: int):
        """Store the event Verification Token and message length limit."""
        self.verification_token = verification_token
        self.max_message_length = max_message_length

    def is_encrypted(self, body: dict) -> bool:
        """Return True when the payload is Encrypt-Key ciphertext."""
        return bool(body.get("encrypt"))

    def is_url_verification(self, body: dict) -> bool:
        """Return True when this is a Feishu request-URL challenge."""
        return body.get("type") == "url_verification"

    def verify_url_token(self, body: dict) -> bool:
        """Return True when URL-verification token matches the configured token."""
        return bool(self.verification_token) and body.get("token") == self.verification_token

    def verify_event_token(self, body: dict) -> bool:
        """Return True when the event header token matches the configured token."""
        if not self.verification_token:
            return False
        header = body.get("header") or {}
        return header.get("token") == self.verification_token

    def event_type(self, body: dict) -> str | None:
        """Return the Feishu event_type from the v2 header, if present."""
        header = body.get("header") or {}
        return header.get("event_type")

    def parse_inbound(self, event: dict) -> InboundMessage | None:
        """Parse an im.message.receive_v1 event into an InboundMessage."""
        message = event.get("message") or {}
        if message.get("message_type") != "text":
            logger.info("Ignoring non-text message (%s)", message.get("message_type"))
            return None

        chat_id = message.get("chat_id")
        if not chat_id:
            logger.error("Missing chat_id on Feishu message")
            return None

        sender_id = _sender_id_from_event(event)
        user_message = _parse_text_content(message.get("content"))
        if not user_message:
            logger.warning("Empty user message; skipping")
            return None

        logger.info(
            "Feishu user %s in chat %s (message_len=%d)",
            sender_id or "unknown",
            chat_id,
            len(user_message),
        )

        return InboundMessage(
            text=user_message,
            session_id=self.session_id_for(chat_id, sender_id),
            reply_target=chat_id,
            sender_id=sender_id or "unknown",
        )

    def session_id_for(self, chat_id: str, sender_id: str | None) -> str:
        """Build a platform-scoped session ID for a Feishu chat and sender."""
        return f"feishu:{chat_id}:{sender_id or 'unknown'}"

    def is_over_length(self, message: InboundMessage) -> bool:
        """Return True when the inbound text exceeds the configured max length."""
        return len(message.text) > self.max_message_length


def _sender_id_from_event(event: dict[str, Any]) -> str | None:
    """Resolve sender id across user_id, open_id, and union_id."""
    sender_id = (event.get("sender") or {}).get("sender_id") or {}
    return (
        sender_id.get("user_id")
        or sender_id.get("open_id")
        or sender_id.get("union_id")
    )


def _parse_text_content(raw_content: Any) -> str:
    """Extract and trim user text from a Feishu message content field."""
    if not raw_content:
        return ""
    if isinstance(raw_content, dict):
        return str(raw_content.get("text") or "").strip()
    try:
        content_json = json.loads(str(raw_content))
        return str(content_json.get("text") or "").strip()
    except (json.JSONDecodeError, TypeError):
        return str(raw_content).strip()
