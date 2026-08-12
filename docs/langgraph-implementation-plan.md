# Implementation Plan: LangGraph Orchestration (Proposal v2.1)

> **Historical record.** This plan described the work that shipped in v0.2.0 on
> `feat/langgraph-orchestration`. Do not treat it as an open backlog; see
> [`langgraph-orchestration-proposal-v2.md`](langgraph-orchestration-proposal-v2.md)
> (Status: Implemented in v0.2.0) and [CHANGELOG.md](../CHANGELOG.md).

| Field           | Value                                                                 |
| --------------- | --------------------------------------------------------------------- |
| Source of truth | [`docs/langgraph-orchestration-proposal-v2.md`](langgraph-orchestration-proposal-v2.md) (v2.1) |
| Repository      | Personal fork `samxli/ai-conversation-bridge`; `origin` is the fork, `upstream` is Workday |
| Target branch   | `feat/langgraph-orchestration` (landed)                               |
| Audience        | Implementing agent (historical)                                       |

## 0. How to use this plan

Read §1–§3 before writing any code. The phases in §5 are ordered so each one is independently verifiable and independently committable; do not merge phases. Every phase ends with acceptance criteria that can be checked without a test suite, because the repository has none.

**Constraints that apply throughout:**

- **Do not add a Claude/AI co-author trailer or signature to commit messages.** Subject and body only.
- Push to `origin` (the personal fork) only. Never push to `upstream`, and never open a PR against the Workday repository.
- Python is pinned to 3.13-slim in the Dockerfile. Lint with `ruff check` — config is in `pyproject.toml` (line length 120, rules `E`, `W`, `I`).
- Phases 1–3 must be **behavior-preserving**. A running Flowise deployment must produce byte-identical replies before and after. Phase 4 is the only phase that adds new user-visible behavior.

## 1. Context

The AI Conversation Bridge relays chat messages from LINE WORKS and DingTalk to an AI backend and posts the reply back through each platform's outbound API. Today the backend is either customer-hosted Flowise or OpenRouter, selected by the `AI_PROVIDER` environment variable.

This work adds **LangGraph as a bundled in-process orchestrator**, formalizes the provider boundary as an **Orchestration Interface**, and restructures the service around it. Flowise remains fully supported and unchanged in behavior.

Read the proposal for the reasoning. This plan does not repeat it.

## 2. Current-state facts

Verified against the working tree. Do not re-derive these; do verify they still hold before starting.

| Fact | Location |
| --- | --- |
| Service root is `chat-connector/`, Flask app factory in `app/__init__.py` | `chat-connector/` |
| `AI_PROVIDER` selects provider, with `CHAT_PROVIDER` as deprecated fallback | `app/config.py:29` |
| Provider clients are constructed **at module import**, not in the app factory | `app/routes.py:17-35` |
| Both provider clients expose `get_completion(user_message, user_id)` | `app/services/flowise.py:20`, `app/services/openrouter.py:49` |
| Neither client raises; both return a user-facing English string on every failure | `app/services/flowise.py:54-74`, `app/services/openrouter.py:92-112` |
| Session IDs are platform-scoped: `lineworks:<userId>`, and DingTalk's `message.session_id` | `app/routes.py:116`, `app/routes.py:161`, `app/services/dingtalk.py` |
| Flowise receives the session ID as `overrideConfig.sessionId` | `app/services/flowise.py:34` |
| OpenRouter keeps process-local per-user history, trimmed to 10 messages | `app/services/openrouter.py:23-38` |
| Container runs `gunicorn -b 0.0.0.0:8080 --timeout 180 main:app` — **defaults to 1 sync worker, 1 thread** | `chat-connector/Dockerfile` |
| Dockerfile copies only `app/` and `main.py` into the image | `chat-connector/Dockerfile` |
| No test suite exists (`git ls-files | grep test` is empty); CI is security scanners only | `.github/workflows/` |
| Runtime deps are 6 pins: Flask, PyJWT, cryptography, httpx, gunicorn, pytest | `chat-connector/requirements.txt` |
| Demo MCP server serves `streamable-http` at `/mcp` on port 8080, **no authentication** | `mcp-demo-server/main.py:222-231` |

### The sample Flowise flow

`flowise/flows/workday-mcp-agent.json` is the behavioral reference for the LangGraph graph. Its agent node specifies:

- Model: `chatOpenRouter`, `openrouter/free`, temperature `0.2`, base path `https://openrouter.ai/api/v1`, streaming `true`
- Memory: `agentEnableMemory: true`, `agentMemoryType: "windowSize"`
- System prompt: HTML embedded in JSON under `agentMessages` (begins `<h1>Your Role</h1><p>You are the Workday Intelligent Assistant...`)
- MCP tool (`customMCP`) with `approvalPolicy: "always"` and this allowlist in `mcpActions`:

```
find_employee_id_by_name, get_current_user_info, get_current_user_time_off_balance,
get_current_user_time_off_history, get_direct_reports, get_more_employee_data,
get_my_time_off_eligibility, get_personal_information, get_today_date_and_day_of_week,
request_my_time_off, get_time_off_balance
```

- A second tool, `requestsGet` (`get_rss_news`, an NPR RSS feed), used only for demonstration

## 3. Decisions already made — do not relitigate

These were settled during proposal review. If you believe one is wrong, raise it with the human rather than changing course.

| # | Decision |
| - | --- |
| 1 | `chat-connector/` is renamed to `bridge-service/`. This is a known breaking change and is accepted. |
| 2 | `flowise/` stays at the repository root. It is not moved into the service. |
| 3 | OpenRouter is re-homed as a `direct_llm` orchestrator, not deleted. |
| 4 | Orchestrator selection (`ORCHESTRATOR`) and model-provider selection (`LLM_*`) become separate config axes. |
| 5 | `AI_PROVIDER=openrouter` keeps working as a deprecated alias for `direct_llm`; `AI_PROVIDER=flowise` aliases `flowise`. |
| 6 | The interface is async. Flowise and Direct LLM convert to `httpx.AsyncClient`. |
| 7 | Failure codes map to the **exact** user-facing strings in use today, so behavior is preserved. |
| 8 | The default checkpointer is in-memory; the deployment is pinned to a single instance. Persistent backends are a later seam. |
| 9 | The graph does **not** implement `approvalPolicy: always`. Allowlisted tools execute without human approval. |
| 10 | The graph omits the flow's `requestsGet` RSS tool. |
| 11 | Tests are out of scope. Do not add a test suite, and do not gate any phase on one. |
| 12 | Execution stays synchronous-gunicorn (proposal §6.5 option A). Deferred replies and ASGI are future work. |

## 4. Phase 0 — Pre-work verification (blocking for Phase 4 only)

Phases 1–3 can start immediately. Phase 4 must not start until these are answered.

1. **Verify the LangGraph package set and current APIs.** Confirm the actual package names, versions, and import paths for the graph library, the checkpoint package (including the in-memory saver's current class name), and the LangChain MCP adapter. This plan deliberately does not pin them — the ecosystem moves and the names in older documentation are stale. Pin exact versions in `requirements.txt`, matching the existing pin style.
2. **Confirm the model-provider integration.** The flow uses an OpenRouter base URL with an OpenAI-compatible API. Decide whether to use an OpenAI-compatible chat model class pointed at OpenRouter, or a dedicated integration, and pin that package.
3. **Licence review.** Report the transitive dependency tree added by the above, with licences, to the human before installing. This is a published repository and the review is a precondition, not a follow-up.
4. **Report the image-size delta** after a trial `docker build`, for the record.

Deliverable: a short written summary to the human covering items 1–4. Wait for a go-ahead before Phase 4.

## 5. Phases

### Phase 1 — Rename and restructure (no behavior change)

**Goal:** `chat-connector/` becomes `bridge-service/` with the target layout, and provider construction moves into the app factory. No logic changes.

**Target layout** (from proposal §8):

```text
bridge-service/
├── app/
│   ├── __init__.py                  # create_app(); builds adapters and orchestrator
│   ├── config.py
│   ├── api/
│   │   └── routes.py
│   ├── channels/
│   │   ├── base.py
│   │   ├── lineworks/{adapter.py,client.py}
│   │   └── dingtalk/{adapter.py,client.py}
│   ├── orchestration/
│   │   ├── base.py
│   │   ├── errors.py
│   │   ├── factory.py
│   │   ├── models.py
│   │   ├── flowise/client.py
│   │   ├── direct_llm/client.py
│   │   └── langgraph/…            # created in Phase 4
│   └── core/
│       ├── response_validator.py
│       ├── messages.py
│       └── logging.py
├── tests/                           # empty placeholder
├── Dockerfile
├── requirements.txt
└── main.py
```

**Tasks:**

1. `git mv chat-connector bridge-service`. Use `git mv` throughout so history is preserved.
2. Create the package directories with `__init__.py` files.
3. Split each platform module in two:
   - `channels/lineworks/client.py` — JWT auth, token acquisition, `send_message`, `validate_config`
   - `channels/lineworks/adapter.py` — signature verification, webhook parsing, session-ID derivation (`lineworks:<userId>`), over-length check
   - `channels/dingtalk/client.py` — session-webhook send
   - `channels/dingtalk/adapter.py` — `parse_message`, `should_process`, session-ID derivation
4. Define `channels/base.py` with a `ChannelAdapter` protocol and an `InboundMessage` dataclass carrying at minimum: `text`, `session_id`, `reply_target`, `sender_id`.
5. Move `response_validator.py` to `core/`.
6. Move provider client construction out of `routes.py` module scope into `create_app()`. Attach the built objects to the Flask app (e.g. `app.extensions`) or pass them into a blueprint factory. `routes.py` must no longer read configuration at import time.
7. Keep `main.py` and the Dockerfile working; update `COPY` paths only if the layout requires it.

**Do not** change any request/response behavior, any user-facing string, or any environment variable name in this phase.

**Acceptance:**

- `python -c "from app import create_app; create_app()"` succeeds from `bridge-service/`
- `ruff check .` is clean
- `docker compose build` succeeds after the compose service path is updated
- Grep confirms no module-level provider construction remains in `api/routes.py`
- `curl localhost:8080/` returns the health JSON with the same keys as before

### Phase 2 — Orchestration interface and error contract

**Goal:** a declared contract with typed failures, mapped to today's exact strings.

**`app/orchestration/errors.py`:**

```python
class FailureCode(str, Enum):
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UPSTREAM_ERROR = "upstream_error"
    UNAVAILABLE = "unavailable"
```

Default English messages — these must match the current code **exactly**, so existing deployments see identical output:

| Code | Message |
| --- | --- |
| `configuration` | `I am currently unable to think (Configuration Error).` |
| `timeout` | `Sorry, the AI service is taking longer than expected. Please try again in a moment.` |
| `rate_limited` | `The AI service is temporarily rate-limited. Please wait a moment and try again.` |
| `upstream_error` | `Sorry, the AI service returned an error. Please try again later.` |
| `unavailable` | `Sorry, I encountered an error while processing your request.` |

Note two pre-existing divergences to collapse onto the table above: OpenRouter's rate-limit string says "AI model" rather than "AI service", and its configuration string says "(API Key missing)". Both are replaced by the canonical strings. Flag this in the commit body — it is the one intentional wording change in Phases 1–3.

**`app/orchestration/base.py`:**

```python
@dataclass(frozen=True)
class OrchestrationRequest:
    message: str
    session_id: str          # becomes Flowise sessionId / LangGraph thread_id
    metadata: dict | None = None

@dataclass(frozen=True)
class OrchestrationResult:
    text: str | None
    failure: FailureCode | None = None
    detail: str | None = None       # internal only; never shown to users

class Orchestrator(Protocol):
    async def invoke(self, request: OrchestrationRequest) -> OrchestrationResult: ...
```

**Tasks:**

1. Add `base.py` and `errors.py`.
2. Add `core/messages.py` mapping `FailureCode` to user-facing text, structured so a locale can be added later without touching orchestrators.
3. Convert `orchestration/flowise/client.py` to implement `Orchestrator`: replace each `return "<string>"` in the exception handlers with the corresponding `OrchestrationResult(failure=...)`, and convert to `httpx.AsyncClient`.
4. In the channel layer, render the failure through `core/messages.py` and send it exactly as today.
5. **Async bridging.** Flask is synchronous. Do **not** call `asyncio.run()` per request — it destroys the event loop each time, which prevents MCP session and connection reuse in Phase 4. Instead, `create_app()` starts one long-lived asyncio event loop on a dedicated daemon thread, and the route layer submits coroutines with `asyncio.run_coroutine_threadsafe(...).result(timeout=...)`. Encapsulate this in a small helper so routes never touch asyncio directly. This is the one non-obvious piece of engineering in the plan; get it right here and Phase 4 is straightforward.
6. Log failures at `error` with the code and detail, so operators can distinguish an outage from an answer for the first time.

**Acceptance:**

- A Flowise deployment returns byte-identical replies for success, timeout, 429, and HTTP-error cases
- Missing `FLOWISE_API_URL` still yields the configuration message at request time (fail-fast startup validation arrives in Phase 3)
- `ruff check .` clean; app factory imports cleanly

### Phase 3 — Direct LLM re-home and config axis split

**Goal:** OpenRouter becomes `direct_llm`; orchestrator and model selection become independent; configuration validates at startup.

**Config mapping:**

| New | Replaces | Notes |
| --- | --- | --- |
| `ORCHESTRATOR` | `AI_PROVIDER` | Values: `flowise`, `langgraph`, `direct_llm`. Default `flowise`. |
| `LLM_API_KEY` | `OPENROUTER_API_KEY` | Used by `direct_llm` and `langgraph` |
| `LLM_MODEL` | `OPENROUTER_MODEL` | Default `openrouter/free` |
| `LLM_BASE_URL` | hard-coded OpenRouter URL | Default `https://openrouter.ai/api/v1` |
| `LLM_TEMPERATURE` | — | Default `0.2`, matching the flow |
| `LLM_SYSTEM_PROMPT` | `OPENROUTER_SYSTEM_PROMPT` | `direct_llm` only |
| `LLM_REASONING_EFFORT` | `OPENROUTER_REASONING_EFFORT` | `direct_llm` only |
| `STATE_BACKEND` | — | `memory` (default). Phase 4. |
| `MCP_SERVER_URL`, `MCP_AUTH_HEADER` | — | Phase 4 |
| `MCP_TOOL_ALLOWLIST` | — | Optional comma-separated names; unset uses the built-in safe list, `*` allows all |

**Backward compatibility (required):** `AI_PROVIDER` and `CHAT_PROVIDER` continue to be read when `ORCHESTRATOR` is unset. `openrouter` maps to `direct_llm`, `flowise` maps to `flowise`. Log a deprecation warning naming the replacement. All `OPENROUTER_*` variables continue to be honoured as fallbacks for their `LLM_*` equivalents. Follow the existing fallback style in `config.py:29`.

**Tasks:**

1. Move `services/openrouter.py` to `orchestration/direct_llm/client.py`; implement `Orchestrator`; convert to `httpx.AsyncClient`; keep the process-local history but mark it demo-grade in the docstring.
2. Add `orchestration/models.py`: one function turning `LLM_*` config into a configured model client, consumed by both `direct_llm` and (in Phase 4) `langgraph`.
3. Add `orchestration/factory.py`: `ORCHESTRATOR` → implementation, called from `create_app()`.
4. Add per-orchestrator startup validation in `config.py`. Missing required settings must **fail the process at boot** with a clear message naming the variable and the selected orchestrator — not answer users politely at request time. Required sets: `flowise` → `FLOWISE_API_URL`; `direct_llm` → `LLM_API_KEY`; `langgraph` → `LLM_API_KEY`, `MCP_SERVER_URL`.
5. Update the health endpoint to report `orchestrator` (keep `ai_provider` as a duplicate key for one release).

**Acceptance:**

- `ORCHESTRATOR=direct_llm` and legacy `AI_PROVIDER=openrouter` both work, the latter logging a deprecation warning
- `ORCHESTRATOR=flowise` with `FLOWISE_API_URL` unset fails at startup with a named-variable error
- No `services/` directory remains

### Phase 4 — LangGraph reference implementation

**Goal:** an in-process graph that matches proposal §7.4.

**Files:**

```text
app/orchestration/langgraph/
├── runtime.py        # implements Orchestrator; owns graph compilation and invocation
├── graph.py          # graph definition: model node, tool node, conditional loop
├── prompts.py        # system prompt, mirroring the flow
├── tools/mcp.py      # MCP client, allowlist filtering, schema caching
└── state/
    ├── factory.py    # make_checkpointer(config) -> BaseCheckpointSaver
    └── firestore.py  # stub only; raise NotImplementedError with a pointer to the proposal
```

**Tasks:**

1. **Prompt.** Port the flow's system prompt from HTML-in-JSON to plain text in `prompts.py`, preserving role and directives. Add a comment stating it mirrors `flowise/flows/workday-mcp-agent.json` and that the two must be updated together. Add the reciprocal note to `flowise/README.md`.
2. **MCP tools.** Connect to `MCP_SERVER_URL` over streamable HTTP, sending `MCP_AUTH_HEADER` when set. Filter discovered tools to the built-in 11-name allowlist in §2 by default; accept `MCP_TOOL_ALLOWLIST` as a comma-separated override, with `*` as an explicit allow-all setting. An unset variable remains fail-closed, while an empty value fails startup. Log discovered, retained, and configured-but-missing names. Fail process startup if discovery fails, any allowlisted name is missing from the server, or no usable tools remain. **Discover and cache tool schemas once at startup**, not per request.
3. **Graph.** Model node → conditional edge → tool node → back to model, terminating on a final response. Bound the loop with a maximum iteration count so a misbehaving model cannot run until the gunicorn timeout kills the worker (see the risk table in proposal §10).
4. **Memory.** Windowed message history matching the flow's `windowSize`, trimmed inside the graph. Persist through the checkpointer.
5. **Checkpointer.** `state/factory.py` returns the in-memory saver for `STATE_BACKEND=memory`, and raises a clear error naming the supported values otherwise. Do **not** invent an abstraction over `BaseCheckpointSaver` — it is already the portable seam.
6. **Runtime.** `runtime.py` maps `OrchestrationRequest.session_id` to the graph's `thread_id`, invokes the compiled graph on the shared event loop from Phase 2, extracts the final message text, and maps exceptions to `FailureCode` per Phase 2.
7. Register `langgraph` in the factory.

**Explicitly not implemented:** the flow's `approvalPolicy: "always"` (no channel approval surface exists) and its `requestsGet` RSS tool. Note both in `prompts.py` or a module docstring so the omission reads as deliberate.

**Acceptance:**

- With the demo MCP server running locally, `ORCHESTRATOR=langgraph` answers a time-off balance question by calling an MCP tool
- Two consecutive messages on the same session ID show conversation continuity; a different session ID does not
- Startup logs list discovered tools, the subset retained after allowlist filtering, and any allowlisted names missing from the server; `MCP_TOOL_ALLOWLIST=*` logs an explicit warning
- Missing allowlisted tools, zero usable tools, or MCP discovery failure fail process startup (`SystemExit`)
- Killing the MCP server after startup produces a typed failure and a user-facing message, not a stack trace or a hang
- `ruff check .` clean

### Phase 5 — Execution and deployment settings

**Goal:** apply proposal §6.5 option A.

**Tasks:**

1. Update the Dockerfile CMD to set workers and threads explicitly. Use **threads, not multiple workers** — the work is I/O-bound, and multiple worker processes would fragment in-memory conversation state, whereas threads share it. Suggested starting point, to be tuned:
   `gunicorn -b 0.0.0.0:8080 --workers 1 --threads 8 --timeout 300 main:app`
2. Raise the request timeout above the worst-case tool loop; keep the orchestrator's own timeout below the gunicorn timeout so a `timeout` failure is returned rather than the worker being killed.
3. Update `scripts/deploy-cloud-run.sh` to pass `--min-instances=1 --max-instances=1 --concurrency=<matching thread count>` and to rename the service. Add a comment explaining that the instance pinning is required by the in-memory state backend, referencing proposal §6.3.
4. Document the settings and their rationale in `docs/setup-guide.md`.

**Acceptance:** container builds and serves; two concurrent requests are handled without the second blocking on the first.

### Phase 6 — Documentation, configuration examples, and tooling

**Tasks:**

1. `bridge-service/.env.example` — restructure into sections per orchestrator; add `ORCHESTRATOR`, `LLM_*`, `STATE_BACKEND`, `MCP_SERVER_URL`, `MCP_AUTH_HEADER`, and optional `MCP_TOOL_ALLOWLIST`; mark `AI_PROVIDER`/`OPENROUTER_*` as deprecated aliases.
2. `docker-compose.yml`, root `.env.example`, `scripts/setup.sh`, `scripts/deploy-cloud-run.sh` — update paths and the Cloud Run service name.
3. `.github/dependabot.yml` — update both `chat-connector` entries (pip and docker) to `bridge-service`.
4. `README.md`, `CONTRIBUTING.md`, `docs/architecture.md`, `docs/setup-guide.md` — update paths, add an orchestrator-selection section, and make the MCP-ownership statements conditional. `docs/architecture.md` currently tells readers to update the MCP URL in their Flowise flow; that is true only for the Flowise path.
5. Add a secret-custody note to `docs/enterprise-guide.md` reflecting proposal §6.4 — with LangGraph selected, the bridge holds the LLM key and MCP credential.
6. Mirror all documentation changes across `i18n/ja/`, `i18n/ko/`, `i18n/zh-Hans/`, `i18n/zh-Hant/`. If you cannot translate accurately, update the paths and code identifiers only and list the prose sections needing human translation.
7. Draft release notes covering the breaking change: the directory rename, the Cloud Run **service name** change, and the resulting new service URL that requires re-pointing the LINE WORKS and DingTalk callback URLs.

**Acceptance:** no reference to `chat-connector` remains outside historical documents (`git grep -n chat-connector`), and the Dependabot config points at real directories.

## 6. Manual verification

There is no test suite, so verification is manual. After each phase:

```bash
cd bridge-service && ruff check . && python -c "from app import create_app; create_app()"
```

For end-to-end checks, run the demo MCP server locally (`streamable-http` on `/mcp`, port 8080, no auth) and exercise the health endpoint plus a synthetic webhook POST against each orchestrator. Note that the LINE WORKS callback verifies a signature, so synthetic requests need a correctly computed `X-WORKS-Signature`; the DingTalk callback is easier to exercise directly.

## 7. Out of scope

Do not implement, and do not expand scope into: a test suite or CI test job; a persistent checkpointer backend (leave `firestore.py` a stub); cross-thread long-term memory; human-in-the-loop tool approval; deferred replies or a queue; a migration to ASGI; streaming; A2A or a Remote Agent Proxy; any change to `mcp-demo-server/`; any change to the Flowise flow template beyond the reciprocal update note.

## 8. Open items for the human

Raise these rather than deciding alone:

1. Phase 0 dependency and licence review — needs sign-off before Phase 4.
2. Whether the LangGraph system prompt should be overridable by environment variable, or code-only for the reference implementation.
3. Whether the health endpoint should report the resolved state backend and MCP connectivity, which is useful but discloses configuration on an unauthenticated endpoint.
4. Final gunicorn thread count and timeout values, which depend on the expected tool-loop length.
