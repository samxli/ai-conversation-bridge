"""Feishu (Lark) Open API client: tenant token and outbound IM messages."""

import json
import logging
import threading
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class FeishuClient:
    """Feishu Open API: tenant token + send IM messages."""

    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    MESSAGES_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

    def __init__(self, app_id: str | None, app_secret: str | None):
        """Store Feishu app credentials and initialize token cache state."""
        self._app_id = app_id
        self._app_secret = app_secret
        self._token: str | None = None
        self._token_expire_at: float = 0.0
        self._lock = threading.Lock()

    def validate_config(self) -> bool:
        """Return True when Feishu app credentials are configured."""
        return bool(self._app_id and self._app_secret)

    def get_tenant_access_token(self) -> str:
        """Return a cached tenant access token, refreshing when near expiry."""
        with self._lock:
            if self._token and time.monotonic() < self._token_expire_at - 60:
                return self._token

            if not self.validate_config():
                raise RuntimeError("FEISHU_APP_ID or FEISHU_APP_SECRET missing")

            payload = {"app_id": self._app_id, "app_secret": self._app_secret}
            with httpx.Client(timeout=10.0) as client:
                r = client.post(
                    self.TOKEN_URL,
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    json=payload,
                )
                r.raise_for_status()
                data = r.json()

            if data.get("code") != 0:
                raise RuntimeError(f"Feishu token API error: {data.get('msg')}")

            self._token = data["tenant_access_token"]
            expire_sec = int(data.get("expire", 7200))
            self._token_expire_at = time.monotonic() + expire_sec
            logger.info("Tenant access token refreshed")
            return self._token

    def send_text_to_chat(self, chat_id: str, text: str, timeout: float = 10.0) -> dict[str, Any]:
        """Send a text message to a Feishu chat via the IM v1 API."""
        token = self.get_tenant_access_token()
        url = f"{self.MESSAGES_URL}?receive_id_type=chat_id"
        body = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        with httpx.Client(timeout=timeout) as client:
            r = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Feishu send_text_to_chat failed: status=%s body=%s",
                    e.response.status_code,
                    e.response.text,
                )
                raise
            return r.json()
