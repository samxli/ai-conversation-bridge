# Release notes: v0.2.0 (bridge-service + LangGraph)

Migration checklist for the first release after the Orchestration Interface work.
Canonical change list: [CHANGELOG.md](../CHANGELOG.md) (`[Unreleased] — 0.2.0`).

## Breaking changes

1. **Directory rename:** `chat-connector/` → `bridge-service/`.
2. **Cloud Run service name:** deploy script now deploys `bridge-service`. The public URL changes.
3. **Callback URLs:** re-point LINE WORKS and DingTalk webhooks to the new `bridge-service` URL (`/lineworks/callback`, `/dingtalk/callback`).
4. **Config:** prefer `ORCHESTRATOR` (`flowise` | `langgraph` | `direct_llm`). Legacy `AI_PROVIDER` / `CHAT_PROVIDER` and `OPENROUTER_*` remain aliases for one release.
5. **Single-instance pin (LangGraph):** with `STATE_BACKEND=memory`, keep `--min-instances=1 --max-instances=1` (see `scripts/deploy-cloud-run.sh`). Multiple replicas fragment in-memory conversation state.
6. **LangGraph MCP fail-closed:** a down MCP server, missing allowlisted tool names, or zero usable tools fail container startup instead of serving a healthy process that cannot call tools.

## Migration checklist

- [ ] Update local paths and `docker compose` / scripts to `bridge-service`
- [ ] Redeploy Cloud Run as `bridge-service` (or rename the existing service)
- [ ] Update LINE WORKS bot callback URL
- [ ] Update DingTalk robot HTTP callback URL
- [ ] Set `ORCHESTRATOR` (default `flowise` preserves prior behavior if `FLOWISE_API_URL` is set)
- [ ] For LangGraph: set `LLM_API_KEY`, `MCP_SERVER_URL`, keep a single Cloud Run instance while `STATE_BACKEND=memory`; deploy the MCP server first (missing allowlisted tools or a down MCP server fail boot)

## Non-breaking additions

- Health JSON includes `orchestrator` (keeps `ai_provider` for compatibility)
- Typed orchestration failures with stable user-facing strings
- LangGraph and Direct LLM orchestrator options
