# Architecture

<p align="center"><sub>
  English |
  <a href="../i18n/zh-Hans/docs/architecture.md">简体中文</a> |
  <a href="../i18n/zh-Hant/docs/architecture.md">繁體中文</a> |
  <a href="../i18n/ja/docs/architecture.md">日本語</a> |
  <a href="../i18n/ko/docs/architecture.md">한국어</a>
</sub></p>

---

## Overview
<p align="center">
   <img width="900" height="490" alt="high level architecture" src="https://github.com/user-attachments/assets/cdd3bcc0-ece8-48ab-9631-0006513cb5a8" />
</p>

The AI Conversation Bridge is a reference architecture for connecting enterprise messaging platforms to Workday through AI-powered orchestration. It addresses four key challenges in the APJ region:

1. **Regulatory restrictions** — Chinese regulations block foreign-hosted LLMs
2. **Language/context gaps** — Enterprise LLMs don't handle customer-specific jargon well
3. **Super-app dominance** — Workers in China use WeChat, Japan uses LINE, Korea uses KakaoTalk
4. **Android unavailability** — Google Play Store is blocked in China

## What This Repo Is / Is Not

### What this repo is

- A reference implementation of the bridge pattern: chat adapters → orchestrator (Flowise or bundled LangGraph) → MCP tools → Workday system of action.
- A development and demo environment with a mock MCP server so teams can prototype flows safely.
- A starting point for customers and partners to build production deployments in their own environments.

### What this repo is not

- Not a production-ready Workday MCP endpoint or substitute for Workday Agent Gateway.
- Not a complete multi-platform adapter pack in a single release.
- Not a managed runtime for Flowise or LLM hosting.

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                          AI CONVERSATION BRIDGE                                │
│                                                                                │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  ┌───────────┐   │
│  │ Chat Platform  │  │    Bridge      │  │   Orchestrator   │  │    MCP    │   │
│  │  (External)    │─▶│    Service     │─▶│ Flowise /        │─▶│  Server   │   │
│  │                │◀─│                │◀─│ LangGraph /      │◀─│ (Workday) │   │
│  └────────────────┘  └────────────────┘  │ Direct LLM       │  └───────────┘   │
│                                          └──────────────────┘                  │
│  LINE WORKS          Webhook adapter     LLM orchestration      Tool execution │
│  DingTalk            Message routing     Intent recognition     Workday APIs   │
│  WeChat/KakaoTalk    Response delivery   Jargon translation     Mock data(dev) │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Conversation Bridge Service (`bridge-service/`)

A Flask application that:

- Receives webhooks from messaging platforms (channel adapters)
- Invokes the selected orchestrator (`ORCHESTRATOR`: Flowise, LangGraph, or Direct LLM)
- Sends the AI response back to the user

Channel adapters stay thin. Flowise remains an external runtime; LangGraph runs in-process inside this service. Multiple channels can be active in the same deployment.

Because it receives webhooks from external messaging platforms, the bridge service **must be deployed to a public-facing environment** with an HTTPS endpoint. Google Cloud Run is the reference example, but any container platform that provides a public URL works (AWS App Runner, Azure Container Apps, Alibaba Cloud Elastic Container Instance, Tencent Kubernetes Engine, etc.).

**Runtime:** Python / Gunicorn (1 worker, 8 threads) / Cloud Run (or equivalent)

### Flowise (`flowise/`)

When `ORCHESTRATOR=flowise`, Flowise is the orchestration runtime that:

- Receives messages from the bridge service
- Processes them through a customer-chosen LLM
- Recognizes intent and translates jargon
- Calls Workday tools via MCP
- Returns formatted responses

Flowise is managed by the customer in their own cloud environment. This project provides flow templates, not a Flowise runtime. If self-hosting Flowise, it must be deployed to **public-facing infrastructure** so that the bridge service can reach its prediction API.

**Runtime:** Customer-managed Flowise instance (cloud or self-hosted on public-facing infrastructure)

### LangGraph (bundled)

When `ORCHESTRATOR=langgraph`, the bridge service compiles a reference ReAct graph at startup, discovers MCP tools from `MCP_SERVER_URL`, filters them through the built-in safe allowlist (or `MCP_TOOL_ALLOWLIST` when configured), and keeps conversation state in an in-memory checkpointer (`STATE_BACKEND=memory`). Discovery, missing allowlist names, or zero usable tools fail process startup. Pin to a single Cloud Run instance for the reference deploy.

### MCP Server (`mcp-demo-server/`)

This project includes a demo MCP server with mock Workday tools and sample data for development and testing. Deploy it to a cloud environment so **Flowise** (Flowise path) or **the bridge service** (LangGraph path) can reach it.

The demo server has **no authentication** and is not suitable for production use. In production, replace it with **Workday's official MCP endpoints** via Agent Gateway, which provides enterprise-grade security (OAuth 2.1, mTLS, audit logging, network policies). Point the orchestrator at that URL: update the MCP tool URL in your Flowise flow (`ORCHESTRATOR=flowise`), or set `MCP_SERVER_URL` on the bridge (`ORCHESTRATOR=langgraph`).

**Runtime:** Python / FastMCP / Cloud Run (demo) or Workday Agent Gateway (prod)

## Request Flow

```
1. User sends "How many vacation days do I have?" in LINE WORKS or DingTalk
   │
2. Chat platform POSTs webhook to bridge service
   - LINE WORKS: /lineworks/callback (or legacy /callback)
   - DingTalk: /dingtalk/callback
   │
3. bridge service extracts message + platform-scoped session id, invokes the
   selected orchestrator (ORCHESTRATOR)
   │
4. Orchestrator LLM recognizes intent: get_current_user_time_off_balance
   - Flowise: prediction API on the customer's Flowise instance
   - LangGraph: in-process ReAct graph inside the bridge
   │
5. Orchestrator MCP client calls MCP server → get_current_user_time_off_balance()
   │
6. MCP server returns: { vacation: { available: 12, used: 3 } }
   │
7. Orchestrator LLM formats response: "You have 12 vacation days remaining (3 used of 15 total)"
   │
8. bridge service receives response, sends it back through the original chat platform
```

## Key Design Principles

### Clean Separation of Concerns

- **Workday** stays the secure "system of action" via MCP
- **Customer** controls the AI layer (their own LLM) and messaging/UI
- **The Bridge** connects chat platforms to the selected orchestrator. On the Flowise path, conversation memory lives in the customer's Flowise instance. On the LangGraph path with `STATE_BACKEND=memory`, the bridge checkpointer retains conversation history (including tool results that may contain HR data) in process memory for the life of the instance — plan retention and erasure accordingly (see [Enterprise Hardening Guide](enterprise-guide.md)).

### Data Sovereignty

The customer's LLM runs in their own environment. Messages are processed through their infrastructure. Where the bridge holds conversation state (LangGraph + in-memory checkpointer), that state is subject to the same residency and retention controls as the rest of the customer's deployment.

### Platform Agnostic

The bridge service pattern is repeatable for any messaging platform. Orchestrators do not need platform-specific webhook or reply logic; the bridge passes a platform-scoped session id such as `lineworks:<userId>` or `dingtalk:<conversationId>:<senderStaffId>` so simultaneous chat channels do not collide in conversation memory.

### Production Hardening

This reference architecture implements baseline security (webhook signature verification, input limits, response validation). For production deployments, see the [Enterprise Hardening Guide](enterprise-guide.md) for additional recommendations on rate limiting, PII handling, retry logic, identity mapping, observability, and infrastructure choices (official Workday MCP servers, Flowise Cloud Enterprise).
