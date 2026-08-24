# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
in the **0.x** range. This is a reference architecture: 0.x releases do not
promise API or deploy-surface stability.

## [Unreleased] — 0.2.0

### Breaking

- Renamed `chat-connector/` to `bridge-service/` and the Cloud Run service name to `bridge-service` (re-point LINE WORKS and DingTalk callback URLs).
- Prefer `ORCHESTRATOR` over `AI_PROVIDER` / `CHAT_PROVIDER` (deprecated aliases still work for one release).
- LangGraph with `STATE_BACKEND=memory` requires a single Cloud Run instance (`--min-instances=1 --max-instances=1`); conversation state is not shared across replicas.
- LangGraph fails process startup if MCP discovery fails, an allowlisted tool is missing from the server, or no usable tools remain.

### Added

- Orchestration Interface with typed failures and async bridging
- Bundled LangGraph orchestrator (`ORCHESTRATOR=langgraph`) with MCP allowlist and in-memory checkpointer
- `MCP_TOOL_ALLOWLIST` env override (`*` allow-all; missing names fail startup)
- LangGraph honors `LLM_SYSTEM_PROMPT` when set (unset keeps the Workday prompt + datetime), `LLM_MESSAGE_WINDOW` (default 20), and `LLM_REASONING_EFFORT`
- LangGraph and Direct LLM use the OpenAI Chat Completions API only (`POST {LLM_BASE_URL}/chat/completions`)
- Direct LLM orchestrator (`ORCHESTRATOR=direct_llm`, formerly OpenRouter path)
- Startup validation for required orchestrator settings
- Feishu (Lark) channel adapter (`/feishu/callback`)
- In-process webhook idempotency (Feishu `message_id`, DingTalk `msgId`, LINE WORKS body hash) so platform retries do not double-call the orchestrator

## [0.1.0] — 2026-08-07

First tagged snapshot of the AI Conversation Bridge reference architecture.

### Added

- `chat-connector` webhook bridge for LINE WORKS and DingTalk
- Flowise orchestration path (recommended) and OpenRouter demo/experiment path
- `mcp-demo-server` with mock Workday MCP tools and sample APJ worker data
- `flowise/` importable flow templates
- Documentation and scripts for Cloud Run–style public deployment
- Localized README and architecture docs (zh-Hans, zh-Hant, ja, ko)

[0.1.0]: https://github.com/samxli/ai-conversation-bridge/releases/tag/v0.1.0
