#!/bin/bash
set -e

# Deploy the AI Conversation Bridge services to Google Cloud Run.
# Prerequisites: gcloud CLI authenticated and project configured.
#
# Usage:
#   LLM_API_KEY=... ./scripts/deploy-cloud-run.sh [REGION]
#
# Optional: MCP_SERVER_URL=https://.../mcp (derived from mcp-demo-server deploy when omitted)
#
# bridge-service defaults to ORCHESTRATOR=langgraph and requires LLM_API_KEY and
# MCP_SERVER_URL on the first revision (startup validation fails without them).
# LangGraph at 256Mi on Cloud Run was sufficient in reference testing; memory is
# not pinned here — raise it only if you OOM.
#
# bridge-service is pinned to a single Cloud Run instance because the default
# LangGraph STATE_BACKEND=memory does not share conversation state across
# replicas (see docs/architecture.md and docs/enterprise-guide.md).

REGION="${1:-us-west1}"
REPO_ROOT="$(dirname "$0")/.."

if [[ -z "${LLM_API_KEY:-}" ]]; then
  echo "Error: LLM_API_KEY must be set for the default LangGraph orchestrator." >&2
  echo "Example: LLM_API_KEY=sk-... $0 $REGION" >&2
  exit 1
fi

echo "=== Deploying to Cloud Run (region: $REGION) ==="
echo ""

echo "--- 1/2: mcp-demo-server ---"
gcloud run deploy mcp-demo-server \
  --source "$REPO_ROOT/mcp-demo-server" \
  --region "$REGION" \
  --allow-unauthenticated

if [[ -z "${MCP_SERVER_URL:-}" ]]; then
  MCP_BASE=$(gcloud run services describe mcp-demo-server \
    --region "$REGION" \
    --format='value(status.url)')
  MCP_SERVER_URL="${MCP_BASE}/mcp"
  echo "Derived MCP_SERVER_URL=${MCP_SERVER_URL}"
fi

BRIDGE_ENV="ORCHESTRATOR=langgraph,STATE_BACKEND=memory,LLM_API_KEY=${LLM_API_KEY},MCP_SERVER_URL=${MCP_SERVER_URL}"
if [[ -n "${LLM_MODEL:-}" ]]; then
  BRIDGE_ENV="${BRIDGE_ENV},LLM_MODEL=${LLM_MODEL}"
fi
if [[ -n "${LLM_BASE_URL:-}" ]]; then
  BRIDGE_ENV="${BRIDGE_ENV},LLM_BASE_URL=${LLM_BASE_URL}"
fi
if [[ -n "${DINGTALK_ALLOWED_USERS:-}" ]]; then
  BRIDGE_ENV="${BRIDGE_ENV},DINGTALK_ALLOWED_USERS=${DINGTALK_ALLOWED_USERS}"
fi

echo ""
echo "--- 2/2: bridge-service ---"
# Concurrency matches gunicorn --threads 8. min/max instances=1 keeps in-memory
# session state coherent for the reference LangGraph path.
gcloud run deploy bridge-service \
  --source "$REPO_ROOT/bridge-service" \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=1 \
  --concurrency=8 \
  --set-env-vars "$BRIDGE_ENV"

echo ""
echo "=== Deployment Complete ==="
echo "Next steps:"
echo "  1. Add channel credentials with --update-env-vars (do not use bare --set-env-vars on"
echo "     an existing service — that replaces all env vars):"
echo "     gcloud run services update bridge-service --region $REGION \\"
echo "       --update-env-vars DINGTALK_ALLOWED_USERS=your-staff-id"
echo "  2. Verify: curl -sS https://<bridge-service-url>/"
echo "  3. Set chat platform callbacks (service rename is a breaking change from chat-connector):"
echo "     LINE WORKS: bridge-service URL + /lineworks/callback"
echo "     DingTalk:   bridge-service URL + /dingtalk/callback"
echo "     Feishu:     bridge-service URL + /feishu/callback"
echo "  4. Deprecated Flowise path: set ORCHESTRATOR=flowise and FLOWISE_API_URL instead."
