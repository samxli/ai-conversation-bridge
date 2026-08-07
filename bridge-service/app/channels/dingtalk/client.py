"""DingTalk HTTP-mode robot client for outbound session-webhook replies."""

import logging
import re
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Only allow replies to be sent back to known DingTalk session-webhook hosts.
# This prevents SSRF where a forged callback supplies an attacker-controlled
# `sessionWebhook` URL (e.g. a cloud metadata endpoint or internal service).
ALLOWED_SESSION_WEBHOOK_HOSTS = frozenset({
    "oapi.dingtalk.com",
    "api.dingtalk.com",
})


def is_allowed_session_webhook(url: str) -> bool:
    """Return True if `url` is an https URL on a known DingTalk session-webhook host."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    return parsed.hostname in ALLOWED_SESSION_WEBHOOK_HOSTS


class DingTalkClient:
    """DingTalk HTTP-mode robot outbound client."""

    def generate_title_from_text(self, text: str, max_length: int = 50) -> str:
        """Derive a short Markdown title from the first line of a reply."""
        first_line = text.split('\n')[0].strip()
        first_line = re.sub(r'^#{1,6}\s*', '', first_line)
        return first_line[:max_length].rstrip()

    def send_text(self, session_webhook: str, text: str):
        """Send a Markdown reply through DingTalk's per-session webhook URL."""
        if not is_allowed_session_webhook(session_webhook):
            raise ValueError("Refusing to POST to non-DingTalk session webhook host.")
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": self.generate_title_from_text(text),
                "text": text
            }
        }
        response = httpx.post(session_webhook, json=payload, timeout=30.0)
        response.raise_for_status()
