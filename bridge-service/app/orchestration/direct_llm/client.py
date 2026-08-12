"""Direct LLM client: OpenAI Chat Completions (`POST {LLM_BASE_URL}/chat/completions`).

Demo/experiment only. Not the OpenAI Responses API or native Anthropic Messages.
Process-local per-session history is demo-grade: it does not survive process
restarts and is not shared across multiple Gunicorn workers.
"""

import logging
import time
from datetime import datetime

import httpx

from app.orchestration.base import OrchestrationRequest, OrchestrationResult
from app.orchestration.errors import FailureCode

logger = logging.getLogger(__name__)


class DirectLLMClient:
    """Demo/experiment orchestrator via OpenAI Chat Completions."""

    def __init__(self, api_key, model, api_url, system_prompt=None, reasoning_effort=None):
        """Store credentials, model selection, and in-memory history settings."""
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
        self.base_system_prompt = system_prompt
        self.reasoning_effort = reasoning_effort

        self.chat_history = {}
        self.history_limit = 10
        self._client = httpx.AsyncClient(timeout=120.0)

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    def _get_user_history(self, user_id):
        """Return the in-memory chat history list for a user, creating it if needed."""
        if user_id not in self.chat_history:
            self.chat_history[user_id] = []
        return self.chat_history[user_id]

    def _append_to_history(self, user_id, role, content):
        """Append a chat turn and trim history to the configured limit."""
        history = self._get_user_history(user_id)
        history.append({"role": role, "content": content})

        if len(history) > self.history_limit:
            self.chat_history[user_id] = history[-self.history_limit:]

    def _get_dynamic_system_prompt(self):
        """Build the system prompt, including today's date when configured."""
        current_date = datetime.now().strftime("%Y-%m-%d")
        date_prompt = f"Today's date is {current_date}."

        if self.base_system_prompt:
            return f"{self.base_system_prompt}\n{date_prompt}"
        return date_prompt

    async def invoke(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Send a chat completion request and return text or a typed failure."""
        if not self.api_key:
            logger.error("OPENROUTER_API_KEY / LLM_API_KEY not set.")
            return OrchestrationResult(
                text=None,
                failure=FailureCode.CONFIGURATION,
                detail="LLM API key not set",
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = [{"role": "system", "content": self._get_dynamic_system_prompt()}]
        user_id = request.session_id

        if user_id:
            self._append_to_history(user_id, "user", request.message)
            messages.extend(self._get_user_history(user_id))
        else:
            messages.append({"role": "user", "content": request.message})

        payload = {"model": self.model, "messages": messages}

        if self.reasoning_effort:
            payload["reasoning"] = {"effort": self.reasoning_effort}

        t0 = time.time()
        try:
            response = await self._client.post(self.api_url, headers=headers, json=payload)
            elapsed = time.time() - t0
            response.raise_for_status()
            data = response.json()

            if 'choices' in data and len(data['choices']) > 0:
                ai_text = data['choices'][0]['message']['content']
                if ai_text:
                    ai_text = ai_text.strip()
                if user_id:
                    self._append_to_history(user_id, "assistant", ai_text)
                logger.info(f"Direct LLM responded in {elapsed:.1f}s")
                return OrchestrationResult(text=ai_text)

            detail = f"Unexpected Direct LLM response format: {data}"
            logger.error(detail)
            return OrchestrationResult(
                text=None, failure=FailureCode.UNAVAILABLE, detail=detail
            )

        except httpx.TimeoutException as e:
            elapsed = time.time() - t0
            detail = f"Direct LLM timeout after {elapsed:.1f}s: {e}"
            logger.error(detail)
            return OrchestrationResult(text=None, failure=FailureCode.TIMEOUT, detail=detail)
        except httpx.HTTPStatusError as e:
            elapsed = time.time() - t0
            status = e.response.status_code
            detail = f"Direct LLM HTTP {status} after {elapsed:.1f}s: {e}"
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
            detail = f"Direct LLM call failed after {elapsed:.1f}s ({type(e).__name__}): {e}"
            logger.error(detail)
            return OrchestrationResult(text=None, failure=FailureCode.UNAVAILABLE, detail=detail)


# Backwards-compatible alias.
OpenRouterClient = DirectLLMClient
