# Setup Guide

<p align="center"><sub>
  English |
  <a href="../i18n/zh-Hans/docs/setup-guide.md">简体中文</a> |
  <a href="../i18n/zh-Hant/docs/setup-guide.md">繁體中文</a> |
  <a href="../i18n/ja/docs/setup-guide.md">日本語</a> |
  <a href="../i18n/ko/docs/setup-guide.md">한국어</a>
</sub></p>

---

This guide walks through setting up each component of the AI Conversation Bridge.

> **Important:** All components must be deployed to **public-facing cloud environments** so they can communicate with each other and receive webhooks from external platforms. This guide uses Google Cloud Run as the example, but any container platform with a public HTTPS endpoint works (AWS App Runner, Azure Container Apps, Alibaba Cloud Elastic Container Instance, Tencent Kubernetes Engine, etc.).

## Prerequisites

- A container hosting platform with public URLs (e.g., [Google Cloud Run](https://cloud.google.com/run))
- A Flowise instance ([cloud](https://flowiseai.com/) or [self-hosted](#self-hosting-flowise) on public-facing infrastructure)
- LINE WORKS Developer Console access and/or DingTalk Developer Console access (for bot credentials)

## 1. Demo MCP Server

The demo MCP server provides mock Workday tools for development and testing. Like the bridge service, it should be **deployed to a cloud environment** (e.g., Google Cloud Run) so that your Flowise instance can reach it. If you use a different provider (AWS App Runner, Azure Container Apps, Alibaba Cloud Elastic Container Instance, Tencent Kubernetes Engine, etc.), adapt the deployment commands accordingly.

> **Production note:** The demo MCP server is for development only and has no authentication. In production, configure your Flowise flow's MCP client node to point to **Workday's official MCP endpoints** via Agent Gateway, which provides OAuth 2.1, mTLS, and other enterprise security controls. See the [Production Security](../mcp-demo-server/README.md#production-security) section for details.

### Deploy to Cloud Run

```bash
gcloud run deploy mcp-demo-server \
  --source mcp-demo-server
```

After deployment, Cloud Run provides a public URL (e.g., `https://mcp-demo-server-abc123.us-west1.run.app`). Use this URL when configuring the Flowise MCP client node.

### Verify

The MCP server exposes tools via streamable HTTP transport at the `/mcp` path. You can connect to it from any MCP client (Flowise, Claude Desktop, etc.) at your deployed URL (e.g., `https://mcp-demo-server-abc123.us-west1.run.app/mcp`).

## 2. Flowise Flow

### Import the Flow

1. Open your Flowise instance
2. Navigate to **Agent Flows** → **Add New**
3. Click **Settings** (⚙️) → **Load Agentflow**
4. Select `flowise/flows/workday-mcp-agent.json`

### Configure the Agent Node

After importing, click the **AI Bridge Agent** node and configure:

1. **Model** — The flow defaults to OpenRouter with the free `openrouter/free` model router. Add an OpenRouter credential in Flowise, or switch to any other provider with your own API key. Good choices for APJ include Z.ai GLM, Qwen/Alibaba (Tongyi Qianwen), and DeepSeek for China-hosted deployments, or OpenAI, Anthropic, and Gemini elsewhere.
2. **Custom MCP Tool** — Update the MCP server URL in the tool configuration:
   - **Demo:** Your deployed demo MCP server URL + `/mcp` (e.g., `https://mcp-demo-server-abc123.us-west1.run.app/mcp`). For the demo server, you can omit the `Authorization` header.
   - **Production:** Your Workday Agent Gateway URL (replace the demo server with Workday's official MCP endpoints, which require proper authentication)

### Get the Prediction URL

1. Click the flow's **API Endpoint** button
2. Copy the prediction URL (e.g., `https://your-flowise.com/api/v1/prediction/<flow-id>`)
3. You'll need this for the bridge service configuration

## 3. Conversation Bridge Service

The bridge service receives webhooks from messaging platforms, so it **must be deployed to a public-facing environment** with an HTTPS URL. This guide uses Google Cloud Run as the example. If you use a different provider (AWS App Runner, Azure Container Apps, Alibaba Cloud Elastic Container Instance, Tencent Kubernetes Engine, etc.), adapt the deployment commands accordingly.

### Choose an orchestrator

| `ORCHESTRATOR` | When to use it | Required settings |
| --- | --- | --- |
| `flowise` (default) | Visual Flowise flows; MCP configured in Flowise | `FLOWISE_API_URL` |
| `langgraph` | Bundled code-first agent; MCP called from the bridge; LLM via OpenAI Chat Completions | `LLM_API_KEY`, `MCP_SERVER_URL` |
| `direct_llm` | Demo chat without tools; same Chat Completions API | `LLM_API_KEY` |

Legacy `AI_PROVIDER` / `CHAT_PROVIDER` (`flowise` or `openrouter`) still work when `ORCHESTRATOR` is unset; prefer `ORCHESTRATOR`.

### Configuration

Prepare your environment variables. You can use `bridge-service/.env.example` as a reference:

```bash
# Flowise path (default)
ORCHESTRATOR=flowise
FLOWISE_API_URL=https://your-flowise.com/api/v1/prediction/<flow-id>
FLOWISE_API_KEY=your-flowise-api-key

# Or LangGraph path:
# ORCHESTRATOR=langgraph
# LLM_API_KEY=your-openrouter-or-compatible-key
# LLM_MODEL=openrouter/free
# LLM_BASE_URL=https://openrouter.ai/api/v1   # Chat Completions root (…/v1)
# LLM_MESSAGE_WINDOW=20
# LLM_REASONING_EFFORT=
# MCP_SERVER_URL=https://mcp-demo-server-abc123.us-west1.run.app/mcp
# MCP_AUTH_HEADER=Bearer your-mcp-token
# MCP_TOOL_ALLOWLIST=find_employee_id_by_name,get_current_user_info
# STATE_BACKEND=memory

# LINE WORKS bot credentials
LW_API_20_CLIENT_ID=your-client-id
LW_API_20_CLIENT_SECRET=your-client-secret
LW_API_20_SERVICE_ACCOUNT_ID=your-service-account-id
LW_API_20_PRIVATEKEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
LW_API_20_BOT_ID=your-bot-id
LW_API_20_BOT_SECRET=your-bot-secret

# DingTalk HTTP robot settings
# Use admin-console employee UserID values. The connector requires DingTalk's senderStaffId field.
DINGTALK_ALLOWED_USERS=ding-user-id-1,ding-user-id-2
DINGTALK_ALLOW_ALL_USERS=false
DINGTALK_REQUIRE_MENTION=true
DINGTALK_GROUP_SESSIONS_PER_USER=true
```

For LangGraph, leave `MCP_TOOL_ALLOWLIST` unset to use the built-in safe
allowlist. Set it to a comma-separated list to select specific discovered
tools, or set it to `*` only when intentionally allowing every tool exposed by
the MCP server. Quote `*` when setting it from a shell. An empty value is
invalid and fails startup. Any allowlisted name the MCP server does not expose
also fails startup, as does an unreachable MCP server or a server that returns
no usable tools. Deploy the MCP server first; LangGraph will not boot a healthy
container without a working tool set.

Leave `LLM_SYSTEM_PROMPT` unset on LangGraph to keep the bundled Workday
prompt; current date and time are always appended. `LLM_MESSAGE_WINDOW`
defaults to 20 (last N messages). `LLM_REASONING_EFFORT` is optional and
OpenRouter-shaped; some models ignore it. `LLM_MESSAGE_WINDOW` must be `> 0`
or LangGraph startup fails.

LangGraph and Direct LLM call the **OpenAI Chat Completions** API
(`POST {LLM_BASE_URL}/chat/completions`). Set `LLM_BASE_URL` to an OpenAI-compatible
root such as `https://openrouter.ai/api/v1` or `https://api.openai.com/v1`. The
OpenAI Responses API and native Anthropic Messages API are not supported; Anthropic
models work only through a Chat Completions proxy (for example OpenRouter).

> **Security:** `LW_API_20_BOT_SECRET` enables webhook signature verification — the connector rejects any callback whose `X-WORKS-Signature` header doesn't match. You can find your Bot Secret in the LINE WORKS Developer Console under your bot's details. If omitted, signature verification is skipped with a warning (acceptable for local development, **not for production**).
>
> **Note on private keys:** When setting `LW_API_20_PRIVATEKEY` in your container platform, newline handling varies. You can paste the key directly (the connector normalizes the format automatically), use literal `\n` characters, or store the key in a secrets manager (recommended). See [Private Key Formatting](#private-key-formatting) below.
>
> **Compatibility:** `AI_PROVIDER` / `CHAT_PROVIDER` remain deprecated aliases when `ORCHESTRATOR` is unset.

### Deploy to Cloud Run

```bash
gcloud run deploy bridge-service \
  --source bridge-service
```

> **Important:** Don't forget to set your environment variables in the Cloud Run console after deploying! Configure `ORCHESTRATOR` and the matching credentials (see `bridge-service/.env.example`) as well as channel connector credentials.

After deployment, Cloud Run provides a public URL (e.g., `https://bridge-service-abc123.us-west1.run.app`). You'll use this as your webhook URL.

For sensitive values like `LW_API_20_PRIVATEKEY`, consider using [Google Secret Manager](https://cloud.google.com/run/docs/configuring/secrets) instead of plain environment variables:

```bash
gcloud run deploy bridge-service \
  --source bridge-service \
  --set-env-vars "ORCHESTRATOR=flowise,FLOWISE_API_URL=..." \
  --set-secrets "LW_API_20_PRIVATEKEY=lw-private-key:latest"
```

### LINE WORKS Bot Setup

1. Go to the [LINE WORKS Developer Console](https://developers.worksmobile.com/)
2. Create a Bot
3. Set the callback URL to your deployed bridge service's public URL + `/lineworks/callback` (e.g., `https://bridge-service-abc123.us-west1.run.app/lineworks/callback`)
4. Set the environment variables on your container platform with the bot credentials

`/callback` is still supported as a backwards-compatible LINE WORKS alias, but new deployments should use `/lineworks/callback`.

### DingTalk HTTP Robot Setup

1. Go to the [DingTalk Developer Console](https://open-dev.dingtalk.com/) and create an enterprise internal app.
2. Add the Robot capability to the app.
3. Configure robot message receiving in HTTP mode.
4. Set the callback URL to your deployed bridge service's public URL + `/dingtalk/callback` (e.g., `https://bridge-service-abc123.us-west1.run.app/dingtalk/callback`).
5. Create and publish an app version that includes the Robot capability. The app version and the robot capability must both be published before DingTalk includes `senderStaffId` in callbacks.
6. Add the published robot to an internal group in the same DingTalk organization from the DingTalk chat group settings: open the group, open group settings, go to **Group Management** → **Robots**, then add the published enterprise robot.
7. Set `DINGTALK_ALLOWED_USERS` to the DingTalk employee UserID values that may use the bot, or set `DINGTALK_ALLOW_ALL_USERS=true` only for controlled demos.

By default, DingTalk direct messages receive a response from allowed users. Group messages require an @mention (`DINGTALK_REQUIRE_MENTION=true`), and group chat sessions are isolated per user (`DINGTALK_GROUP_SESSIONS_PER_USER=true`).

The connector authorizes DingTalk users with `senderStaffId`, which corresponds to the employee UserID available in the DingTalk admin console. It intentionally ignores callbacks that only include encrypted `senderId` values, because those are not practical for admins to retrieve or manage. If logs show `Ignoring DingTalk message without senderStaffId`, confirm the DingTalk app version and robot capability are both published, and that the published robot is installed in an internal group for the same organization.

### Quick Test with Direct LLM

If you want to test the bridge without Flowise or LangGraph tools:

```bash
ORCHESTRATOR=direct_llm
LLM_API_KEY=your-openrouter-key
LLM_MODEL=openrouter/free
```

This connects configured chat channels directly to an OpenAI Chat Completions
endpoint (`POST {LLM_BASE_URL}/chat/completions`) — useful for verifying webhook
flows before adding orchestration.

### Private Key Formatting

Container platforms handle multi-line environment variables differently. The bridge service automatically normalizes the PEM private key, so all of these approaches work:

- **Paste directly** in the Cloud Run console or equivalent — newlines may become spaces, but the connector handles this
- **Use literal `\n`** when setting via CLI — e.g., `-----BEGIN PRIVATE KEY-----\nMIIEvQI...\n-----END PRIVATE KEY-----`
- **Use a secrets manager** (recommended) — stores the key with exact formatting preserved

### Scaling and execution model

The bridge service runs Gunicorn with **one worker and eight threads** (`--workers 1 --threads 8 --timeout 300`). Work is I/O-bound; threads share in-memory conversation state used by `ORCHESTRATOR=langgraph` with `STATE_BACKEND=memory`. Multiple workers (or multiple Cloud Run instances) would fragment that state.

The reference `scripts/deploy-cloud-run.sh` therefore pins Cloud Run to `--min-instances=1 --max-instances=1 --concurrency=8`. Keep `ORCHESTRATOR_TIMEOUT` (default 240) below the Gunicorn timeout so typed failures return before the worker is killed.

For Flowise-only deployments that do not rely on in-process memory, you may raise max instances later; for LangGraph + memory, stay on a single instance until a durable checkpointer is added.

## Self-Hosting Flowise

If you prefer to host your own Flowise instance instead of using [Flowise Cloud](https://flowiseai.com/), it must be deployed to **public-facing infrastructure** so that the bridge service can reach its prediction API. Deploy Flowise to Cloud Run, Alibaba Cloud Elastic Container Instance, Tencent Kubernetes Engine, a VM with a public IP, or any platform that provides an HTTPS endpoint. See the [Flowise self-hosting documentation](https://docs.flowiseai.com/configuration/deployment) for deployment options.
