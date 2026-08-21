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
| Orchestrators table | `README.md` (Orchestrators) | Prefer `ORCHESTRATOR`; three paths including LangGraph / Direct LLM |
| Component table + architecture chain | `README.md` (Architecture) | Branched orchestrator; not Flowise-only |
| Quick Start prerequisites | `README.md` | Flowise is conditional on `ORCHESTRATOR=flowise` |
| System diagram + request flow | `docs/architecture.md` | Bridge Service + Orchestrator (not "Chat Connector" / "Flowise (The Core)") |
| Scaling / execution model | `docs/setup-guide.md`, `docs/architecture.md` | Gunicorn 1×8, Cloud Run `--concurrency=8`, single-instance pin for in-memory LangGraph state |
| Conversation-state retention | `docs/enterprise-guide.md` | New subsection for checkpointed HR data |
| Feishu (Lark) Bot Setup | `docs/setup-guide.md` | New section after DingTalk; callback `/feishu/callback` |

## Correctness fix that must propagate

Localized `architecture.md` files still carry the claim that the Bridge connects
systems **without storing sensitive data**. That is false on the LangGraph path
(`STATE_BACKEND=memory` checkpointer retains conversation history that can
include HR tool results). Do not leave the old sentence when translating —
replace it with the English wording under **Clean Separation of Concerns** /
**Data Sovereignty** in `docs/architecture.md`.
