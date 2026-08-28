# i18n follow-up after bridge-service rename and LangGraph

Path and code identifiers in localized README / architecture docs were updated
from `chat-connector` to `bridge-service`. Prose that still describes the
"chat connector" conceptually, and new orchestrator (`ORCHESTRATOR` /
LangGraph) sections, need human translation in:

- `i18n/ja/`
- `i18n/ko/`
- `i18n/zh-Hans/`
- `i18n/zh-Hant/`

English sources of truth: `README.md`, `docs/architecture.md`, `docs/setup-guide.md`,
`docs/enterprise-guide.md`.

## Sections that need translation (or re-translation)

Bring localized docs in line with the English sources for at least:

| Area | English location | Notes |
| --- | --- | --- |
| Flowise sunset banner | `README.md`, `docs/architecture.md`, `docs/setup-guide.md`, `docs/enterprise-guide.md` | EOL 31 Aug 2026; link flowiseai.com/sunset and archived GitHub repo |
| Default orchestrator | `README.md`, `docs/setup-guide.md`, release notes | `langgraph` is default; Flowise deprecated opt-in |
| Orchestrators table | `README.md` (Orchestrators) | LangGraph first; Flowise marked deprecated |
| Component table + architecture chain | `README.md` (Architecture) | LangGraph in-process; not Flowise-as-core |
| Quick Start / deploy | `README.md`, `docs/setup-guide.md` | Env on first Cloud Run revision; `LLM_API_KEY` + `MCP_SERVER_URL` |
| Architecture image | `docs/architecture.md` | `docs/assets/architecture.png` (img src updated in localized architecture.md) |
| System diagram + request flow | `docs/architecture.md` | LangGraph-first hub-and-spoke |
| Scaling / execution model | `docs/setup-guide.md`, `docs/architecture.md` | Gunicorn 1×8, Cloud Run `--concurrency=8`, single-instance pin; 256Mi test note |
| Conversation-state retention | `docs/enterprise-guide.md` | LangGraph in-memory checkpointer retains HR data |
| Feishu (Lark) Bot Setup | `docs/setup-guide.md` | `/feishu/callback`; `message_id` dedup |
| Deprecated Flowise path | `docs/setup-guide.md`, `flowise/README.md` | Moved to end; fork archived repo |

## Correctness fix that must propagate

Localized `architecture.md` files still carry the claim that the Bridge connects
systems **without storing sensitive data**. That is false on the LangGraph path
(`STATE_BACKEND=memory` checkpointer retains conversation history that can
include HR tool results). Do not leave the old sentence when translating —
replace it with the English wording under **Clean Separation of Concerns** /
**Data Sovereignty** in `docs/architecture.md`.
