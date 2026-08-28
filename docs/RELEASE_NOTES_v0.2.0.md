# Release notes: v0.2.0 (bridge-service + LangGraph)

Migration checklist for the first release after the Orchestration Interface work.
Canonical change list: [CHANGELOG.md](../CHANGELOG.md) (`[Unreleased] — 0.2.0`).

> **Flowise sunset:** [Flowise](https://flowiseai.com/sunset) reached end of life on **31 August 2026**. v0.2.0 defaults to **LangGraph** (`ORCHESTRATOR=langgraph`). `ORCHESTRATOR=flowise` remains as a deprecated opt-in for one release if you self-host from the [archived Flowise repository](https://github.com/FlowiseAI/Flowise).

## Breaking changes

1. **Directory rename:** `chat-connector/` → `bridge-service/`.
2. **Cloud Run service name:** deploy script now deploys `bridge-service`. The public URL changes.
3. **Callback URLs:** re-point LINE WORKS, DingTalk, and Feishu webhooks to the new `bridge-service` URL (`/lineworks/callback`, `/dingtalk/callback`, `/feishu/callback`).
4. **Default orchestrator:** `ORCHESTRATOR` now defaults to `langgraph` (was implicit `flowise` via legacy aliases). Set `ORCHESTRATOR=flowise` explicitly if you still use self-hosted Flowise.
5. **Startup validation:** LangGraph requires `LLM_API_KEY` and `MCP_SERVER_URL` at container boot — set env vars on the **first** Cloud Run revision, not after deploy.
6. **Single-instance pin (LangGraph):** with `STATE_BACKEND=memory`, keep `--min-instances=1 --max-instances=1` (see `scripts/deploy-cloud-run.sh`). Multiple replicas fragment in-memory conversation state.
7. **LangGraph MCP fail-closed:** a down MCP server, missing allowlisted tool names, or zero usable tools fail container startup instead of serving a healthy process that cannot call tools.

## Migration checklist

- [ ] Update local paths and `docker compose` / scripts to `bridge-service`
- [ ] Redeploy Cloud Run as `bridge-service` (or rename the existing service)
- [ ] Deploy `mcp-demo-server` first; set `MCP_SERVER_URL` to its `/mcp` URL
- [ ] Set `LLM_API_KEY` (and optional `LLM_BASE_URL` / `LLM_MODEL`) on first bridge deploy
- [ ] Update LINE WORKS bot callback URL
- [ ] Update DingTalk robot HTTP callback URL
- [ ] Update Feishu event subscription URL (`/feishu/callback`) if using Feishu
- [ ] If still on Flowise: set `ORCHESTRATOR=flowise` and `FLOWISE_API_URL` explicitly

## Non-breaking additions

- Health JSON includes `orchestrator` (keeps `ai_provider` for compatibility)
- Typed orchestration failures with stable user-facing strings
- LangGraph and Direct LLM orchestrator options
- LangGraph and Direct LLM use OpenAI Chat Completions (`POST {LLM_BASE_URL}/chat/completions`), not the Responses API or native Anthropic Messages
- Feishu (Lark) channel adapter (`/feishu/callback`)
- Webhook idempotency with release on failed deliveries
- Architecture diagram updated for LangGraph-first design (`docs/assets/architecture.png`)

## Reference testing notes

LangGraph on Cloud Run was exercised at **256Mi** memory. The deploy script does not pin memory — use platform defaults unless you hit OOM.
