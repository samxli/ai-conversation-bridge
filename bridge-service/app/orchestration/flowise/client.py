"""Flowise prediction API client implementing the Orchestrator protocol."""

import logging
import time

import httpx

from app.orchestration.base import OrchestrationRequest, OrchestrationResult
from app.orchestration.errors import FailureCode

logger = logging.getLogger(__name__)


class FlowiseClient:
    """Primary chat orchestrator via Flowise prediction API."""

    def __init__(self, api_url, api_key=None, timeout=120):
        """Store Flowise endpoint settings and request timeout."""
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def invoke(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Send a user message to Flowise and return text or a typed failure."""
        if not self.api_url:
            logger.error("FLOWISE_API_URL not set.")
            return OrchestrationResult(
                text=None,
                failure=FailureCode.CONFIGURATION,
                detail="FLOWISE_API_URL not set",
            )

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict = {"question": request.message}
        if request.session_id:
            payload["overrideConfig"] = {"sessionId": request.session_id}

        t0 = time.time()
        try:
            response = await self._client.post(self.api_url, headers=headers, json=payload)
            elapsed = time.time() - t0
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict):
                text = data.get("text", data.get("answer", str(data)))
            else:
                text = str(data)

            if text and not isinstance(text, str):
                text = str(text)

            logger.info(f"Flowise responded in {elapsed:.1f}s")
            cleaned = text.strip() if text else text
            return OrchestrationResult(text=cleaned)

        except httpx.TimeoutException as e:
            elapsed = time.time() - t0
            detail = f"Flowise timeout after {elapsed:.1f}s: {e}"
            logger.error(detail)
            return OrchestrationResult(text=None, failure=FailureCode.TIMEOUT, detail=detail)
        except httpx.HTTPStatusError as e:
            elapsed = time.time() - t0
            status = e.response.status_code
            detail = f"Flowise HTTP {status} after {elapsed:.1f}s: {e}"
            logger.error(detail)
            if status == 429:
                return OrchestrationResult(
                    text=None, failure=FailureCode.RATE_LIMITED, detail=detail
                )
            return OrchestrationResult(
                text=None, failure=FailureCode.UPSTREAM_ERROR, detail=detail
            )
        except Exception as e:
            elapsed = time.time() - t0
            detail = f"Flowise call failed after {elapsed:.1f}s ({type(e).__name__}): {e}"
            logger.error(detail)
            return OrchestrationResult(text=None, failure=FailureCode.UNAVAILABLE, detail=detail)
