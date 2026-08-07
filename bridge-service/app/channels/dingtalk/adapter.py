"""DingTalk webhook adapter: parsing, access control, and session IDs."""

import logging
from urllib.parse import urlparse

from app.channels.base import InboundMessage
from app.channels.dingtalk.client import is_allowed_session_webhook

logger = logging.getLogger(__name__)


class DingTalkAdapter:
    """Adapter for DingTalk HTTP-mode robot callbacks."""

    def __init__(self, config, max_message_length: int):
        """Load DingTalk access-control settings from the application config."""
        self.allowed_users = {
            user.strip()
            for user in config.DINGTALK_ALLOWED_USERS.split(",")
            if user.strip()
        }
        self.allow_all_users = config.DINGTALK_ALLOW_ALL_USERS
        self.require_mention = config.DINGTALK_REQUIRE_MENTION
        self.group_sessions_per_user = config.DINGTALK_GROUP_SESSIONS_PER_USER
        self.max_message_length = max_message_length

    def validate_config(self):
        """Return True when at least one allowed-user policy is configured."""
        return self.allow_all_users or bool(self.allowed_users)

    def get_session_id(self, conversation_id: str, conversation_type: str, sender_user_id: str) -> str:
        """Build a platform-scoped AI session ID for the conversation."""
        if conversation_type == "2" and self.group_sessions_per_user:
            return f"dingtalk:{conversation_id}:{sender_user_id}"
        return f"dingtalk:{conversation_id}"

    def parse_inbound(self, payload: dict) -> InboundMessage | None:
        """Parse and validate a DingTalk callback payload into an InboundMessage."""
        if payload.get("msgtype") != "text":
            logger.info("Ignoring non-text DingTalk message.")
            return None

        text = self._extract_text(payload)
        text = text.strip() if text else ""
        if not text:
            logger.info("Ignoring DingTalk message without text content.")
            return None

        conversation_id = payload.get("conversationId")
        conversation_type = str(payload.get("conversationType", ""))
        sender_user_id = payload.get("senderStaffId")
        encrypted_sender_id = payload.get("senderId")
        session_webhook = payload.get("sessionWebhook")

        if not conversation_id:
            logger.warning("Ignoring DingTalk message without conversationId.")
            return None
        if not sender_user_id:
            logger.warning(
                "Ignoring DingTalk message without senderStaffId. "
                "Publish both the DingTalk app version and robot capability, then install "
                "the internal-app robot in an internal group so DingTalk sends the "
                "admin-console UserID. senderId=%s conversationType=%s",
                encrypted_sender_id,
                conversation_type,
            )
            return None
        if not session_webhook:
            logger.warning("Ignoring DingTalk message without sessionWebhook.")
            return None
        if not is_allowed_session_webhook(session_webhook):
            logger.warning(
                "Ignoring DingTalk message with sessionWebhook outside the allowed "
                "DingTalk hosts. host=%s",
                urlparse(session_webhook).hostname,
            )
            return None

        return InboundMessage(
            text=text,
            session_id=self.get_session_id(conversation_id, conversation_type, sender_user_id),
            reply_target=session_webhook,
            sender_id=sender_user_id,
        )

    def should_process(self, message: InboundMessage) -> tuple[bool, str | None]:
        """Return whether the message should be handled and an optional skip reason."""
        if not self.validate_config():
            return False, "DingTalk allowed users not configured."

        if not self.allow_all_users and message.sender_id not in self.allowed_users:
            return False, f"DingTalk sender {message.sender_id} is not allowed."

        # Mention gating needs conversation metadata; callers pass it via metadata on
        # the raw payload. For Phase 1 we re-check through should_process_payload.
        return True, None

    def should_process_payload(self, message: InboundMessage, payload: dict) -> tuple[bool, str | None]:
        """Return whether the message should be handled, including group-mention rules."""
        ok, reason = self.should_process(message)
        if not ok:
            return ok, reason

        conversation_type = str(payload.get("conversationType", ""))
        is_in_at_list = bool(payload.get("isInAtList"))
        if conversation_type == "2" and self.require_mention and not is_in_at_list:
            return False, "DingTalk group message did not mention the bot."

        return True, None

    def is_over_length(self, message: InboundMessage) -> bool:
        """Return True when the inbound text exceeds the configured max length."""
        return len(message.text) > self.max_message_length

    @staticmethod
    def _extract_text(payload: dict) -> str | None:
        """Extract text content from the canonical DingTalk text message payload."""
        text_payload = payload.get("text")
        if isinstance(text_payload, dict) and text_payload.get("content"):
            return str(text_payload.get("content"))
        return None
