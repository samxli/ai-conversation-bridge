# Enterprise Hardening Guide

<p align="center"><sub>
  English |
  <a href="../i18n/zh-Hans/docs/enterprise-guide.md">简体中文</a> |
  <a href="../i18n/zh-Hant/docs/enterprise-guide.md">繁體中文</a> |
  <a href="../i18n/ja/docs/enterprise-guide.md">日本語</a> |
  <a href="../i18n/ko/docs/enterprise-guide.md">한국어</a>
</sub></p>

---

> **Flowise sunset:** [Flowise](https://flowiseai.com/sunset) EOL date **31 August 2026**. New deployments should use bundled **LangGraph** (`ORCHESTRATOR=langgraph`).

Recommendations for teams moving the AI Conversation Bridge from prototype to production. This guide covers what comes next.

> **Start here:** The two highest-leverage steps are infrastructure choices, not code changes.

## Production Infrastructure

### Use Official Workday MCP Servers

The `mcp-demo-server/` in this repo is a mock with static JSON data and no authentication. Production deployments should connect to **Workday's official MCP servers** (e.g., Workday Agent Gateway), which provide real data access, OAuth 2.1 / mTLS authentication, audit logging, and compliance controls.

- **LangGraph path (default):** set `MCP_SERVER_URL` (and `MCP_AUTH_HEADER` when required) on the bridge service. With LangGraph selected, the bridge holds the LLM API key and MCP credential — treat them as secrets (Secret Manager / equivalent), not plain env files in production. `MCP_TOOL_ALLOWLIST` defaults to the bundled **reference allowlist** (includes mock read tools and `request_my_time_off`); use a comma-separated list for a narrower set. It is not a security boundary. `MCP_TOOL_ALLOWLIST=*` exposes every discovered tool and should be limited to controlled testing. Startup fails if the MCP server is unreachable, an allowlisted tool is missing, or no usable tools remain.

### Conversation-state retention and erasure

On the LangGraph path with `STATE_BACKEND=memory`, the bridge checkpointer keeps thread state **in process memory** for the life of the instance. That state includes user messages and tool results, which can contain HR data (leave balances, personal information, worker IDs). Treat it as regulated data:

- Define retention (how long threads may live) and an erasure path (user/admin request, offboarding).
- Expect cold starts and redeploys to wipe in-memory state; do not rely on that as the only deletion mechanism.
- Before scaling beyond one instance or claiming durable memory, move to a shared encrypted store with TTL, deletion APIs, and region-local placement — the in-memory backend is a reference, not an enterprise retention story.

---

## P1 — High Priority

### Log Sanitization

The bridge service logs user IDs and message metadata. In production, log output often flows to centralized systems where PII exposure creates compliance risk (GDPR, PIPL, etc.). Introduce a sanitization layer that redacts user identifiers and message content before they reach log output. Structured JSON logging makes this easier — log processors can redact specific fields rather than relying on pattern matching.

### Rate Limiting

The channel callback endpoints (`/lineworks/callback`, `/dingtalk/callback`, `/feishu/callback`, and the legacy LINE WORKS `/callback` alias) are publicly accessible. Without rate limiting, a misconfigured webhook or abuse scenario can exhaust downstream quotas (LLM provider or chat platform APIs). Add per-IP and per-user rate limits at the bridge service layer. For multi-instance deployments, back the rate limiter with a shared store (e.g., Redis) rather than in-memory counters.

Inbound webhook retries are suppressed in-process by an `IdempotencyStore` (Feishu `message_id`, DingTalk `msgId`, LINE WORKS SHA-256 of the raw body) with a 6-hour TTL. That does not span Cloud Run replicas — use a shared SET NX store if you raise `--max-instances`.

### Model Selection and Temperature

The reference deployment uses a free-tier model (`openrouter/free`). Free-tier models have aggressive rate limits (often 10-20 RPM) that will cause failures under real load. Switch to a paid model with strong function-calling support. Set temperature to near-0 for tool-calling agents — higher temperatures introduce non-determinism in intent recognition and tool argument generation, leading to hallucinated parameters or skipped tool calls.

### Structured Output Schemas

Without output constraints, the LLM can return responses in unpredictable formats. Consider constraining LangGraph output (for example via response schemas or post-validation) and including a `data_source` field (tool result vs. general knowledge) so downstream consumers can detect when the LLM answered from its own knowledge rather than from a Workday tool.

### User-to-Worker Identity Mapping

The demo server uses a single `CURRENT_USER_WORKER_ID` for all requests. In production, each chat user must map to their own Workday worker identity. The recommended approach is Workday-side resolution — the Agent Gateway resolves identity via tokens. 

---

## P2 — Medium Priority

### Retry Logic with Backoff

Transient failures (network blips, 502/503 from the LLM provider, token refresh races) are inevitable. Add retry logic with exponential backoff to outbound HTTP calls in the bridge service. Avoid retrying on `429` responses — those indicate you need to address rate limits at the provider level, not mask them with retries.

### Correlation IDs and Structured Logging

When a user reports "the bot didn't respond," you need to trace a single request across the bridge service, LangGraph, and MCP pipeline. Generate a request ID at the channel callback entry point, propagate it as an HTTP header through downstream calls, and attach it to all log entries. Structured JSON logging (rather than plain text) makes these traces queryable in Cloud Run, CloudWatch, and similar platforms.

### Prompt Injection Defenses

Users (or attackers replaying webhook payloads) can craft messages that attempt to override the LLM's system prompt. Layer multiple defenses: harden the system prompt with explicit override-rejection instructions, wrap user input in delimiters so it's harder for injected text to escape context, and optionally screen for common injection phrases as a logging signal. 

---

## P3 — Nice to Have

### Observability (Tracing and Metrics)

Add distributed tracing and metrics across the bridge service, LangGraph, and MCP pipeline. This enables end-to-end latency visibility, error rate alerting, and the ability to diagnose issues before users report them.

### Circuit Breakers

If the LLM or MCP endpoint is down or consistently erroring, a circuit breaker pattern lets the bridge service fail fast with a user-friendly message rather than waiting for timeouts on every request. After a cooldown period, the breaker allows a probe request to check if the service has recovered.

### Output Content Filtering

Even with tool-grounded responses, LLMs can surface sensitive data in edge cases (e.g., full ID numbers in a personal info response). Extend the existing response validator with PII pattern detection. For authorization-level filtering, the Workday Agent Gateway handles this natively — tool results are scoped to what the authenticated user is allowed to see, which is another reason to use official Workday MCP servers.