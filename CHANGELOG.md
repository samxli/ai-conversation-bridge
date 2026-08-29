# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
in the **0.x** range. This is a reference architecture: 0.x releases do not
promise API or deploy-surface stability.

## [Unreleased]

## [0.2.0] — 2026-08-28

> **Flowise sunset:** [Flowise](https://flowiseai.com/sunset) EOL **31 August 2026**. This release defaults to bundled LangGraph. `ORCHESTRATOR=flowise` remains as a deprecated opt-in for one release.

### Breaking

- Renamed `chat-connector/` to `bridge-service/` and the Cloud Run service name to `bridge-service` (create the new service and re-point callbacks; Cloud Run does not support renaming an existing service).
- **Default orchestrator is now `langgraph`** when `ORCHESTRATOR` and legacy `AI_PROVIDER` / `CHAT_PROVIDER` are unset (was implicit Flowise).
- Prefer `ORCHESTRATOR` over `AI_PROVIDER` / `CHAT_PROVIDER` (deprecated aliases still work for one release).
- LangGraph with `STATE_BACKEND=memory` requires `--max-instances=1` so conversation state is not fragmented across replicas.
- LangGraph fails process startup if MCP discovery fails, an allowlisted tool is missing from the server, or no usable tools remain.
- Startup validation requires orchestrator credentials on first container boot (deploy-then-configure in Cloud Run console no longer works for LangGraph).
- **LINE WORKS** rejects callbacks with HTTP 401 when `LW_API_20_BOT_SECRET` is unset (was fail-open).

### Added

- Orchestration Interface with typed failures and async bridging
- Bundled LangGraph orchestrator (`ORCHESTRATOR=langgraph`, default) with MCP allowlist and in-memory checkpointer
- `MCP_TOOL_ALLOWLIST` env override (`*` allow-all; missing names fail startup)
- LangGraph honors `LLM_SYSTEM_PROMPT` when set (unset keeps the Workday prompt + datetime), `LLM_MESSAGE_WINDOW` (default 20), and `LLM_REASONING_EFFORT`
- LangGraph and Direct LLM use the OpenAI Chat Completions API only (`POST {LLM_BASE_URL}/chat/completions`)
- Direct LLM orchestrator (`ORCHESTRATOR=direct_llm`, formerly OpenRouter path)
- Startup validation for required orchestrator settings
- Feishu (Lark) channel adapter (`/feishu/callback`)
- In-process webhook idempotency (Feishu `message_id`, DingTalk `msgId`, LINE WORKS body hash). `release()` runs on failed outbound sends (including Feishu IM `code != 0` → HTTP 502) so the platform can retry. A LangGraph **wait_for** timeout is different: the user gets a timeout chat message and the key **stays claimed** so the same turn is not retried (`request_my_time_off` is not end-to-end idempotent). An outer hang (`TimeoutError` after wait_for + 30s) still releases.
- Architecture diagram (`docs/assets/architecture.png`) for LangGraph-first hub-and-spoke design
- CI workflow: ruff, check scripts, Docker builds
- Outer orchestration `TimeoutError` cancels the in-flight asyncio task so a released webhook retry cannot overlap a still-running invoke

### Migration from v0.1.0

- [ ] Update local paths and `docker compose` / scripts to `bridge-service`
- [ ] Deploy a new Cloud Run service named `bridge-service` (do not attempt to rename `chat-connector`)
- [ ] Deploy `mcp-demo-server` first; set `MCP_SERVER_URL` to its `/mcp` URL on the first bridge revision
- [ ] Set `LLM_API_KEY` (and optional `LLM_BASE_URL` / `LLM_MODEL`) on first bridge deploy
- [ ] Re-point LINE WORKS, DingTalk, and Feishu callbacks (`/lineworks/callback`, `/dingtalk/callback`, `/feishu/callback`)
- [ ] Set `LW_API_20_BOT_SECRET` (LINE WORKS callbacks return 401 without it)
- [ ] If still on Flowise: set `ORCHESTRATOR=flowise` and `FLOWISE_API_URL` explicitly
- [ ] Delete the old `chat-connector` Cloud Run service after cutover

### Known limitations

- **DingTalk** (`/dingtalk/callback`) performs no inbound signature or timestamp verification. With a public URL, combine `DINGTALK_ALLOW_ALL_USERS=false`, a narrow `DINGTALK_ALLOWED_USERS` list, and `DINGTALK_REQUIRE_MENTION=true`. Narrow `MCP_TOOL_ALLOWLIST` to read-only tools outside controlled tests — the reference allowlist includes `request_my_time_off`.
- **Feishu** verifies the event token with plain `==`, not `hmac.compare_digest`; no `X-Lark-Signature` HMAC path. Encrypted payloads are rejected with 400.
- **Conversation state** lives in process memory (`STATE_BACKEND=memory` → `InMemorySaver`). Tool results can include HR data; there is no TTL or eviction. `STATE_BACKEND=firestore` is unimplemented.
- **Single replica:** use `--max-instances=1` with in-memory state. Do not use gunicorn `--preload` or `--workers > 1`.
- **Timeouts:** LangGraph `wait_for` (default 240s) replies in-chat and **keeps** the idempotency key — send a new message; the same webhook is not retried. `release()` + platform retry applies to failed **sends** (and a rarer outer hang), not that wait_for path.
- LangGraph on Cloud Run was exercised at **256Mi** memory; the deploy script does not pin memory.

## [0.1.0] — 2026-08-07

First tagged snapshot of the AI Conversation Bridge reference architecture.

### Added

- `chat-connector` webhook bridge for LINE WORKS and DingTalk
- Flowise orchestration path (recommended) and OpenRouter demo/experiment path
- `mcp-demo-server` with mock Workday MCP tools and sample APJ worker data
- `flowise/` importable flow templates
- Documentation and scripts for Cloud Run–style public deployment
- Localized README and architecture docs (zh-Hans, zh-Hant, ja, ko)

[0.2.0]: https://github.com/Workday/ai-conversation-bridge/releases/tag/v0.2.0
[0.1.0]: https://github.com/Workday/ai-conversation-bridge/releases/tag/v0.1.0
