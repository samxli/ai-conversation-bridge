# AI Conversation Bridge

<p align="center"><sub>
  English |
  <a href="i18n/zh-Hans/README.md">简体中文</a> |
  <a href="i18n/zh-Hant/README.md">繁體中文</a> |
  <a href="i18n/ja/README.md">日本語</a> |
  <a href="i18n/ko/README.md">한국어</a>
</sub></p>

---

> **Flowise sunset:** [Flowise](https://flowiseai.com/sunset) EOL date **31 August 2026**. This repo defaults to bundled **LangGraph** (`ORCHESTRATOR=langgraph`). `ORCHESTRATOR=flowise` remains in v0.2.0 as a deprecated opt-in if you self-host from the [archived Flowise repository](https://github.com/FlowiseAI/Flowise). Do not start new Flowise integrations here.

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

**Included chat adapters:** LINE WORKS, DingTalk, and Feishu. WeChat and KakaoTalk are common APJ examples but are not shipped in this repo yet.

The bridge service runs channel webhooks and in-process LangGraph in one process. The demo MCP server returns mock Workday data. For production, plan a full MCP integration — not just a URL change. See [docs/setup-guide.md](docs/setup-guide.md) and [docs/architecture.md](docs/architecture.md).

| Component | What it does | Where it lives |
| --- | --- | --- |
| **bridge service** | Webhooks + in-process LangGraph (`ORCHESTRATOR=langgraph`) | [bridge-service/](bridge-service/) |
| **demo MCP server** | Mock Workday tools for development | [mcp-demo-server/](mcp-demo-server/) |
| **Flowise flows** | Deprecated templates (`ORCHESTRATOR=flowise`); Flowise EOL 31 Aug 2026 | [flowise/](flowise/) |

## Quick Start

Pick one path:

| Path | Use when |
| --- | --- |
| **LangGraph on Cloud Run** (default) | You want the full demo with MCP tools |
| **Local Compose smoke test** | You want to verify containers build locally |
| **Direct LLM** | You only need to test webhooks without MCP tools |

Full steps, verification commands, and channel setup live in [docs/setup-guide.md](docs/setup-guide.md). Summary for Cloud Run:

### Prerequisites

- `gcloud` installed, authenticated, and pointed at a project with billing enabled
- An OpenRouter API key (defaults target OpenRouter) or another OpenAI-compatible Chat Completions provider
- Chat credentials for at least one supported platform

Only the **bridge webhook URL** must be publicly reachable. Keep MCP and LLM endpoints private or authenticated when you can.

### Deploy

**`.env` is for local Docker Compose only.** Cloud Run reads env vars from the service configuration (console or `gcloud`), not from `bridge-service/.env`. See [bridge-service/.env.example](bridge-service/.env.example) for variable names.

```bash
git clone https://github.com/Workday/ai-conversation-bridge.git
cd ai-conversation-bridge

REGION=us-west1

# 1) Demo MCP server (no secrets)
gcloud run deploy mcp-demo-server \
  --source mcp-demo-server \
  --region "$REGION" \
  --allow-unauthenticated

# 2) Bridge — first revision only (LangGraph needs these two vars to boot)
gcloud run deploy bridge-service \
  --source bridge-service \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances=1 \
  --concurrency=8 \
  --set-env-vars "LLM_API_KEY=your-openrouter-key,MCP_SERVER_URL=https://<mcp-service-url>/mcp"
```

Or use the helper script (same first-time flow; derives `MCP_SERVER_URL` when omitted):

```bash
LLM_API_KEY=your-openrouter-key ./scripts/deploy-cloud-run.sh "$REGION"
```

**3)** Add LINE WORKS, DingTalk, and Feishu credentials in the Cloud Run console (**Variables & secrets**). Do not rerun step 2 with `--set-env-vars` — it replaces every env var.

**4)** Later code-only deploys:

```bash
gcloud run deploy bridge-service --source bridge-service --region "$REGION"
```

Point your chat platform at `https://<bridge-service-url>/lineworks/callback`, `/dingtalk/callback`, or `/feishu/callback`.

### Verify

```bash
curl -sS "https://<bridge-service-url>/"
# Expect: {"status":"ok","orchestrator":"langgraph",...}

gcloud run services logs read bridge-service --region "$REGION" --limit 50 \
  | grep -E "LangGraph|MCP tools|startup failed"
# Expect tool discovery logs and no startup failure
```

Send one real chat message to confirm end-to-end delivery.

## Orchestrators

| Orchestrator | When to use it | Config |
| --- | --- | --- |
| **LangGraph** (default) | Bundled agent with MCP tools | `LLM_API_KEY`, `MCP_SERVER_URL` |
| **Direct LLM** | Webhook smoke tests without tools | `ORCHESTRATOR=direct_llm`, `LLM_API_KEY` |
| **Flowise** (deprecated) | Legacy self-hosted Flowise only | `ORCHESTRATOR=flowise`, `FLOWISE_API_URL` |

See [bridge-service/.env.example](bridge-service/.env.example) for the variable catalog (Compose / local). Cloud Run uses the console after first deploy.

## Project Structure

```text
ai-conversation-bridge/
├── bridge-service/          # Webhooks + LangGraph orchestrator
│   ├── app/channels/        # LINE WORKS, DingTalk, Feishu
│   ├── app/orchestration/   # LangGraph, Direct LLM, deprecated Flowise
│   └── .env.example
├── mcp-demo-server/         # Mock Workday MCP tools
├── flowise/                 # Deprecated Flowise templates
├── docs/                    # Architecture, setup, enterprise guide
└── scripts/                 # setup.sh, deploy-cloud-run.sh
```

## Documentation

- [Setup Guide](docs/setup-guide.md) — Install, configure, verify, and clean up
- [Architecture](docs/architecture.md) — Boundaries, state, and security model
- [Enterprise Hardening Guide](docs/enterprise-guide.md) — Production gaps and mitigations
- [Changelog](CHANGELOG.md) — Release history and v0.2.0 migration from v0.1.0
- [Flowise templates (deprecated)](flowise/README.md)
- [Contributing](CONTRIBUTING.md)

## License

This project is licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for details.
