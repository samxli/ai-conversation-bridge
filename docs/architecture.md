# Architecture

<p align="center"><sub>
  English |
  <a href="../i18n/zh-Hans/docs/architecture.md">简体中文</a> |
  <a href="../i18n/zh-Hant/docs/architecture.md">繁體中文</a> |
  <a href="../i18n/ja/docs/architecture.md">日本語</a> |
  <a href="../i18n/ko/docs/architecture.md">한국어</a>
</sub></p>

---

> **Flowise sunset:** [Flowise](https://flowiseai.com/sunset) reached end of life on **31 August 2026**. This repo defaults to bundled **LangGraph** (`ORCHESTRATOR=langgraph`). `ORCHESTRATOR=flowise` remains as a deprecated compatibility path for one release if you self-host from the [archived Flowise repository](https://github.com/FlowiseAI/Flowise). Do not start new Flowise integrations here.

## Overview
<p align="center">
   <img width="900" alt="AI Conversation Bridge architecture overview" src="assets/architecture.png" />
</p>

The AI Conversation Bridge is a reference architecture for connecting enterprise messaging platforms to Workday through AI-powered orchestration. It addresses four key challenges in the APJ region:

1. **Regulatory restrictions** — Chinese regulations block foreign-hosted LLMs
2. **Language/context gaps** — Enterprise LLMs don't handle customer-specific jargon well
3. **Super-app dominance** — Workers in China use WeChat, Japan uses LINE, Korea uses KakaoTalk
4. **Android unavailability** — Google Play Store is blocked in China

## What This Repo Is / Is Not

### What this repo is

- A reference implementation of the bridge pattern: chat adapters → bundled LangGraph orchestrator → MCP tools → Workday system of action.
- A development and demo environment with a mock MCP server so teams can prototype flows safely.
- A starting point for customers and partners to build production deployments in their own environments.

### What this repo is not

- Not a production-ready Workday MCP endpoint or substitute for Workday Agent Gateway.
- Not a complete multi-platform adapter pack in a single release.
- Not a managed runtime for LLM hosting.

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                          AI CONVERSATION BRIDGE                                │
│                                                                                │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │ Chat Services  │  │    Bridge      │  │    LangGraph     │  │ Workday   │ │
│  │  (External)    │─▶│    Service     │─▶│  (in-process)    │─▶│   MCP     │ │
│  │                │◀─│                │◀─│  + LLM providers │◀─│           │ │
│  └────────────────┘  └────────────────┘  └──────────────────┘  └───────────┘ │
│                                                                                │
│  LINE / Lark /     Webhook adapters      ReAct agent + tools    Mock (dev) or │
│  DingTalk / Feishu Message routing       OpenAI Chat Completions Agent Gateway│
└────────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Conversation Bridge Service (`bridge-service/`)

A Flask application that:

- Receives webhooks from messaging platforms (channel adapters)
- Invokes the selected orchestrator (`ORCHESTRATOR`: LangGraph by default, or Direct LLM / deprecated Flowise)
- Sends the AI response back to the user

Channel adapters stay thin. LangGraph runs in-process inside this service. Multiple channels can be active in the same deployment.

Because it receives webhooks from external messaging platforms, the bridge service **must be deployed to a public-facing environment** with an HTTPS endpoint. Google Cloud Run is the reference example, but any container platform that provides a public URL works (AWS App Runner, Azure Container Apps, Alibaba Cloud Elastic Container Instance, Tencent Kubernetes Engine, etc.).

**Runtime:** Python / Gunicorn (1 worker, 8 threads) / Cloud Run (or equivalent). LangGraph has been exercised on Cloud Run at 256Mi; leave memory at the platform default unless you hit OOM.

### LangGraph (bundled, default)

When `ORCHESTRATOR=langgraph` (the default), the bridge service compiles a reference ReAct graph at startup, calls the LLM through the **OpenAI Chat Completions** API (`ChatOpenAI` at `LLM_BASE_URL`, typically `POST …/v1/chat/completions`), discovers MCP tools from `MCP_SERVER_URL`, filters them through the built-in safe allowlist (or `MCP_TOOL_ALLOWLIST` when configured), and keeps conversation state in an in-memory checkpointer (`STATE_BACKEND=memory`). The OpenAI Responses API and native Anthropic Messages are not used. Discovery, missing allowlist names, or zero usable tools fail process startup. Pin to a single Cloud Run instance for the reference deploy.

### Flowise (`flowise/`, deprecated)

When `ORCHESTRATOR=flowise`, the bridge service forwards messages to a customer-hosted Flowise prediction API. Flowise reached EOL on 31 August 2026; this path is retained for one release only. Fork the [archived Flowise repository](https://github.com/FlowiseAI/Flowise) if you must continue self-hosting.

### MCP Server (`mcp-demo-server/`)

This project includes a demo MCP server with **mock** Workday tools and sample data for development and testing. Deploy it to a cloud environment so the bridge service can reach it at `MCP_SERVER_URL` (include the `/mcp` path).

The demo server has **no authentication** and is not suitable for production use. In production, replace it with **Workday's official MCP endpoints** via Agent Gateway, which provides enterprise-grade security (OAuth 2.1, mTLS, audit logging, network policies). Set `MCP_SERVER_URL` on the bridge to that URL.

**Runtime:** Python / FastMCP / Cloud Run (demo) or Workday Agent Gateway (prod)

## Request Flow

```
1. User sends "How many vacation days do I have?" in LINE WORKS, DingTalk, or Feishu
   │
2. Chat platform POSTs webhook to bridge service
   - LINE WORKS: /lineworks/callback (or legacy /callback)
   - DingTalk: /dingtalk/callback
   - Feishu: /feishu/callback
   │
3. bridge service extracts message + platform-scoped session id, claims a
   delivery key so platform retries skip a second orchestrator call, invokes
   the LangGraph orchestrator (default)
   │
4. LangGraph LLM recognizes intent: get_current_user_time_off_balance
   │
5. LangGraph MCP client calls MCP server → get_current_user_time_off_balance()
   │
6. MCP server returns mock data: { vacation: { available: 12, used: 3 } }
   │
7. LangGraph LLM formats response: "You have 12 vacation days remaining (3 used of 15 total)"
   │
8. bridge service receives response, sends it back through the original chat platform
```

## Key Design Principles

### Clean Separation of Concerns

- **Workday** stays the secure "system of action" via MCP
- **Customer** controls the AI layer (their own LLM) and messaging/UI
- **The Bridge** connects chat platforms to the LangGraph orchestrator. With `STATE_BACKEND=memory`, the bridge checkpointer retains conversation history (including tool results that may contain HR data) in process memory for the life of the instance — plan retention and erasure accordingly (see [Enterprise Hardening Guide](enterprise-guide.md)).

### Data Sovereignty

The customer's LLM runs in their own environment. Messages are processed through their infrastructure. Where the bridge holds conversation state (LangGraph + in-memory checkpointer), that state is subject to the same residency and retention controls as the rest of the customer's deployment.

### Platform Agnostic

The bridge service pattern is repeatable for any messaging platform. Orchestrators do not need platform-specific webhook or reply logic; the bridge passes a platform-scoped session id such as `lineworks:<userId>`, `dingtalk:<conversationId>:<senderStaffId>`, or `feishu:<chat_id>:<sender_id>` so simultaneous chat channels do not collide in conversation memory.

### Production Hardening

This reference architecture implements baseline security (webhook signature verification, input limits, response validation). For production deployments, see the [Enterprise Hardening Guide](enterprise-guide.md) for additional recommendations on rate limiting, PII handling, retry logic, identity mapping, observability, and infrastructure choices (official Workday MCP servers).
