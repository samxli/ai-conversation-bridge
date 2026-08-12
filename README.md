# AI Conversation Bridge

<p align="center"><sub>
  English |
  <a href="i18n/zh-Hans/README.md">简体中文</a> |
  <a href="i18n/zh-Hant/README.md">繁體中文</a> |
  <a href="i18n/ja/README.md">日本語</a> |
  <a href="i18n/ko/README.md">한국어</a>
</sub></p>

---

A reference architecture that connects enterprise messaging apps (LINE WORKS, WeChat, Feishu, etc.) to Workday using AI-powered orchestration. It's built for markets where you need to meet workers in the apps they already use every day.


https://github.com/user-attachments/assets/9b1ea495-5f23-4ae6-b735-18874acdd327



## Why we built this

Enterprise AI usually doesn't fail because of the tech. It fails because it doesn't reach the right people. 

In the APJ region (especially China, Japan, and South Korea), getting workers to actually use AI tools comes with a few major roadblocks:

- **Regulatory hurdles:** You can't just point workers in China to a US-hosted AI or LLMs. US/China policy environments create barriers to this and local regulations sometimes require local models.
- **Language and context:** Global models often don't understand company-specific jargon or local cultural nuances. Asking for "Golden Week off" needs to actually mean something to the AI.
- **Super-app dominance:** Workers in China live in WeChat and Feishu. In Japan, it's LINE. In Korea, KakaoTalk. Asking millions of people to download a separate enterprise app just doesn't work.
- **Android app availability:** The Google Play Store is blocked in China, meaning a huge chunk of the workforce can't even download the standard Workday Android app.

The result? Companies have Workday and want to use AI, but the workers who need it most are left out.

**The AI Conversation Bridge flips this around.** Instead of forcing workers to log into Workday, it brings Workday directly into their favorite chat apps. It uses local LLMs and infrastructure, so it respects regional rules and digital culture. A worker just sends a message in WeChat, and the AI handles the rest. Workday remains the secure source of truth, but the front door is wherever the worker already is.

While we built this with APJ in mind, the pattern works anywhere you want to use your own LLMs or chat platforms.



## Architecture

```text
Chat App  ←→  bridge service  ←→  orchestrator  ←→  MCP Server  ←→  Workday
                                    │
                    Flowise (external) or LangGraph (in-process)
```

The project has three main pieces. **The selected orchestrator is the brain** — it connects to the LLMs, figures out what the user wants, and calls Workday tools via MCP. The other two components act as its ears and hands: the bridge service listens to the chat apps, and the MCP Server executes actions in Workday.

*(For more details on boundaries and intended usage, check out [docs/architecture.md](docs/architecture.md).)*


| Component           | What it does                                                                                   | Where it lives                         |
| ------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------- |
| **bridge service**  | Channel adapters plus orchestrator selection; receives messages and sends replies.             | [bridge-service/](bridge-service/)   |
| **Flowise Flows**   | Visual orchestration when `ORCHESTRATOR=flowise` — LLM, intent, and MCP tool calling.          | [flowise/](flowise/)                 |
| **LangGraph**       | Bundled in-process ReAct agent when `ORCHESTRATOR=langgraph` — MCP from the bridge.            | [bridge-service/](bridge-service/)   |
| **Demo MCP Server** | Mock Workday tools for testing and development. (Swap this out for the Workday Agent Gateway in production). | [mcp-demo-server/](mcp-demo-server/) |


## Quick Start

### What you'll need

- A container hosting platform with public HTTPS endpoints (like [Google Cloud Run](https://cloud.google.com/run))
- LINE WORKS Bot credentials and/or DingTalk robot access (for the bridge service)
- Depending on orchestrator:
  - **Flowise** (`ORCHESTRATOR=flowise`, default): a [Flowise](https://flowiseai.com/) instance (cloud or self-hosted, public-facing)
  - **LangGraph** (`ORCHESTRATOR=langgraph`): an OpenAI Chat Completions API key (`LLM_BASE_URL` + `LLM_API_KEY`) and a reachable MCP server URL
  - **Direct LLM** (`ORCHESTRATOR=direct_llm`): same Chat Completions credentials (demos without tools)

*Note: Everything needs to be deployed to a public-facing cloud environment. We use Google Cloud Run in these examples, but any container platform works (AWS App Runner, Azure Container Apps, Alibaba Cloud Elastic Container Instance, Tencent Kubernetes Engine, etc.).*

### 1. Clone the repo

```bash
git clone https://github.com/your-org/ai-conversation-bridge.git
cd ai-conversation-bridge
```

### 2. Deploy the demo MCP server

```bash
gcloud run deploy mcp-demo-server \
  --source mcp-demo-server
```

> **Going to production?** Replace this demo server with **Workday's official MCP endpoints** via Agent Gateway for real enterprise-grade security and authentication. On the Flowise path, update the MCP URL in your flow; on the LangGraph path, set `MCP_SERVER_URL` on the bridge.

### 3. Configure the orchestrator (Flowise path)

Skip this step if you use `ORCHESTRATOR=langgraph` or `direct_llm` — see [Orchestrators](#orchestrators) and [Setup Guide](docs/setup-guide.md).

1. Open your Flowise instance.
2. Go to **Agent Flows** → **Add New** → **Settings** (⚙️) → **Load Agentflow**.
3. Import `flowise/flows/workday-mcp-agent.json`.
4. Set up your LLM credentials.
5. Update the MCP server URL in the Agent node's Custom MCP tool to point to your deployed demo server (e.g., `https://mcp-demo-server-abc123.us-west1.run.app/mcp`).

*(Need more help? See [flowise/README.md](flowise/README.md).)*

### 4. Deploy the bridge service

```bash
gcloud run deploy bridge-service \
  --source bridge-service
```

> **Important:** Set environment variables in the Cloud Run console after deploying. Prefer `ORCHESTRATOR` (`flowise` | `langgraph` | `direct_llm`) plus the matching credentials — for Flowise, `FLOWISE_API_URL`; for LangGraph, `LLM_API_KEY` and `MCP_SERVER_URL`. LangGraph and Direct LLM call the OpenAI Chat Completions API (`POST {LLM_BASE_URL}/chat/completions`), not Responses or native Anthropic. LangGraph uses its built-in safe MCP tool allowlist unless `MCP_TOOL_ALLOWLIST` is set; use a comma-separated list for specific tools or `*` for an explicit allow-all override. Missing allowlisted tools or a down MCP server fail container startup. Leave `LLM_SYSTEM_PROMPT` unset to keep the bundled Workday prompt; optional `LLM_MESSAGE_WINDOW` (default 20) and `LLM_REASONING_EFFORT` apply on this path. Also set chat channel settings. See `bridge-service/.env.example`. For LangGraph with `STATE_BACKEND=memory`, pin to a single instance (`--min-instances=1 --max-instances=1`); the reference [deploy script](scripts/deploy-cloud-run.sh) already does this.

### 5. Connect Chat Channels

Set your chat platform callback URLs to the channel-specific endpoints:

- LINE WORKS: `https://bridge-service-abc123.us-west1.run.app/lineworks/callback`
- DingTalk HTTP robot: `https://bridge-service-abc123.us-west1.run.app/dingtalk/callback`

The legacy `/callback` path is still accepted as a LINE WORKS alias for existing deployments.

## Orchestrators

The bridge service supports three orchestrators. Prefer `ORCHESTRATOR`; legacy `AI_PROVIDER` / `CHAT_PROVIDER` remain aliases when unset.


| Orchestrator | When to use it | Config |
| --- | --- | --- |
| **Flowise** (default) | Production visual flows and MCP in Flowise | `ORCHESTRATOR=flowise` |
| **LangGraph** | Bundled code-first agent; MCP from the bridge | `ORCHESTRATOR=langgraph` |
| **Direct LLM** | Demos without tools (OpenAI Chat Completions) | `ORCHESTRATOR=direct_llm` |


## Demo MCP Tools

The demo MCP server comes with mock Workday tools and data so you can test the whole pipeline. When you're ready for production, just swap it out for Workday's official MCP endpoints.


| Tool                                | What it does                                         |
| ----------------------------------- | ---------------------------------------------------- |
| `find_employee_id_by_name`          | Look up an employee's worker ID by name              |
| `get_current_user_info`             | Get the current user's profile                       |
| `get_current_user_time_off_balance` | Get the current user's leave balances                |
| `get_current_user_time_off_history` | Get the current user's leave request history         |
| `get_time_off_balance`              | Get leave balances for any worker by ID              |
| `get_direct_reports`                | List direct reports for a manager                    |
| `get_more_employee_data`            | Get extended employee data                           |
| `get_my_time_off_eligibility`       | Check which leave types the current user can request |
| `get_personal_information`          | Get personal info (address, emergency contact)       |
| `get_today_date_and_day_of_week`    | Get the current date and time                        |
| `request_my_time_off`               | Submit a time-off request for the current user       |


*Fun fact: The mock data includes workers across China, Japan, and South Korea with localized names and currencies!*

## Project Structure

```text
ai-conversation-bridge/
├── bridge-service/          # Channel adapters + orchestrators (Flask, Python)
│   ├── app/channels/        # LINE WORKS, DingTalk
│   ├── app/orchestration/   # Flowise, LangGraph, Direct LLM
│   ├── Dockerfile
│   └── .env.example
├── flowise/                 # Flow templates (Flowise path)
│   ├── flows/
│   └── screenshots/
├── mcp-demo-server/         # Demo Workday MCP server
│   ├── mock_data/
│   ├── Dockerfile
│   └── .env.example
├── docs/                    # Architecture, setup, proposals
├── scripts/                 # Local setup and Cloud Run deploy
├── docker-compose.yml
└── .github/
```

## Documentation

- [Architecture](docs/architecture.md) — Detailed system design and request flow
- [Setup Guide](docs/setup-guide.md) — Step-by-step setup for each component
- [Enterprise Hardening Guide](docs/enterprise-guide.md) — Security, reliability, and operational recommendations for production
- [Release notes v0.2.0](docs/RELEASE_NOTES_v0.2.0.md) — Migration checklist (canonical list in [Changelog](CHANGELOG.md))
- [Flowise Configuration](flowise/README.md) — How to import and configure the flow templates
- [Contributing](CONTRIBUTING.md) — How to contribute to this project
- [Changelog](CHANGELOG.md) — Tagged releases (`v0.x`; reference architecture, no stability promise)

## License

This project is licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for details.
