# AI Conversation Bridge

<p align="center"><sub>
  English |
  <a href="i18n/zh-Hans/README.md">简体中文</a> |
  <a href="i18n/zh-Hant/README.md">繁體中文</a> |
  <a href="i18n/ja/README.md">日本語</a> |
  <a href="i18n/ko/README.md">한국어</a>
</sub></p>

---

> **Flowise sunset:** [Flowise](https://flowiseai.com/sunset) reached end of life on **31 August 2026**. This repo now defaults to bundled **LangGraph** (`ORCHESTRATOR=langgraph`). `ORCHESTRATOR=flowise` remains as a deprecated compatibility path for one release if you self-host from the [archived Flowise repository](https://github.com/FlowiseAI/Flowise). Do not start new Flowise integrations here.

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
Chat platforms  ←→  bridge service (LangGraph)  ←→  MCP server  ←→  Workday
```

The project has three deployable pieces. **The bridge service is the brain** — channel adapters plus in-process LangGraph (LLM + MCP tool calls). The MCP server executes Workday actions (mock data in the demo).

*(For more details on boundaries and intended usage, check out [docs/architecture.md](docs/architecture.md).)*


| Component           | What it does                                                                                   | Where it lives                         |
| ------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------- |
| **bridge service**  | Channel adapters + in-process LangGraph (`ORCHESTRATOR=langgraph`); receives messages and sends replies. | [bridge-service/](bridge-service/)   |
| **Demo MCP Server** | Mock Workday tools for testing and development. (Swap for Workday Agent Gateway in production). | [mcp-demo-server/](mcp-demo-server/) |
| **Flowise Flows**   | Deprecated visual orchestration (`ORCHESTRATOR=flowise`); Flowise EOL 31 Aug 2026.             | [flowise/](flowise/)                 |


## Quick Start

### What you'll need

- A container hosting platform with public HTTPS endpoints (like [Google Cloud Run](https://cloud.google.com/run))
- LINE WORKS Bot credentials and/or DingTalk robot access (for the bridge service)
- **LangGraph (default):** OpenAI Chat Completions API key (`LLM_BASE_URL` + `LLM_API_KEY`) and a reachable MCP server URL (include `/mcp`)
- **Direct LLM (optional):** same Chat Completions credentials for demos without tools
- **Flowise (deprecated):** only if you explicitly set `ORCHESTRATOR=flowise` and self-host from the archived repo

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

> **Going to production?** Replace the demo server with **Workday's official MCP endpoints** via Agent Gateway. Set `MCP_SERVER_URL` on the bridge to that URL.

### 3. Deploy the bridge service

```bash
LLM_API_KEY=your-key \
MCP_SERVER_URL=https://mcp-demo-server-abc123.us-west1.run.app/mcp \
  ./scripts/deploy-cloud-run.sh
```

Or deploy manually with env vars on the **first** revision (startup validation requires `LLM_API_KEY` and `MCP_SERVER_URL` for the default LangGraph path):

```bash
gcloud run deploy bridge-service \
  --source bridge-service \
  --min-instances=1 --max-instances=1 --concurrency=8 \
  --set-env-vars "ORCHESTRATOR=langgraph,LLM_API_KEY=your-key,MCP_SERVER_URL=https://mcp-demo-server-abc123.us-west1.run.app/mcp"
```

LangGraph has been exercised on Cloud Run at **256Mi**; memory is not pinned in the deploy script — raise it only if you OOM. See `bridge-service/.env.example` for channel credentials and optional LangGraph settings (`LLM_MESSAGE_WINDOW`, `MCP_TOOL_ALLOWLIST`, etc.). Deploy the MCP server before the bridge; a down MCP server or missing allowlisted tools fail container startup.

### 4. Connect Chat Channels

Set your chat platform callback URLs to the channel-specific endpoints:

- LINE WORKS: `https://bridge-service-abc123.us-west1.run.app/lineworks/callback`
- DingTalk HTTP robot: `https://bridge-service-abc123.us-west1.run.app/dingtalk/callback`
- Feishu (Lark): `https://bridge-service-abc123.us-west1.run.app/feishu/callback`

The legacy `/callback` path is still accepted as a LINE WORKS alias for existing deployments.

## Orchestrators

The bridge service supports three orchestrators. Prefer `ORCHESTRATOR`; legacy `AI_PROVIDER` / `CHAT_PROVIDER` remain aliases when unset.


| Orchestrator | When to use it | Config |
| --- | --- | --- |
| **LangGraph** (default) | Bundled code-first agent; MCP from the bridge | `LLM_API_KEY`, `MCP_SERVER_URL` |
| **Direct LLM** | Demos without tools (OpenAI Chat Completions) | `ORCHESTRATOR=direct_llm`, `LLM_API_KEY` |
| **Flowise** (deprecated) | Legacy self-hosted Flowise only; EOL 31 Aug 2026 | `ORCHESTRATOR=flowise`, `FLOWISE_API_URL` |


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
- [Flowise Configuration](flowise/README.md) — Deprecated flow templates (Flowise EOL 31 Aug 2026)
- [Contributing](CONTRIBUTING.md) — How to contribute to this project
- [Changelog](CHANGELOG.md) — Tagged releases (`v0.x`; reference architecture, no stability promise)

## License

This project is licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for details.
