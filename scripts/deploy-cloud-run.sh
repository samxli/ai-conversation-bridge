#!/bin/bash
set -e

# First-time Cloud Run deploy helper.
# Prerequisites: gcloud CLI authenticated and project configured.
#
# Usage:
#   LLM_API_KEY=... ./scripts/deploy-cloud-run.sh [REGION]
#
# Optional: MCP_SERVER_URL=https://.../mcp (derived from mcp-demo-server deploy when omitted)
#
# Sets only LLM_API_KEY and MCP_SERVER_URL on the first bridge revision (LangGraph boot
# requirements). Add channel credentials in the Cloud Run console afterward.
#
# For code-only updates, redeploy WITHOUT --set-env-vars so console env vars are preserved:
#   gcloud run deploy bridge-service --source bridge-service --region REGION
#
# --max-instances=1 keeps in-memory LangGraph state on one replica.
# --concurrency=8 matches gunicorn --threads 8 in bridge-service/Dockerfile.

REGION="${1:-us-west1}"
REPO_ROOT="$(dirname "$0")/.."

if [[ -z "${LLM_API_KEY:-}" ]]; then
  echo "Error: LLM_API_KEY must be set for the default LangGraph orchestrator." >&2
  echo "Example: LLM_API_KEY=sk-... $0 $REGION" >&2
  exit 1
fi

echo "=== First-time deploy to Cloud Run (region: $REGION) ==="
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

echo ""
echo "--- 2/2: bridge-service (first revision only) ---"
gcloud run deploy bridge-service \
  --source "$REPO_ROOT/bridge-service" \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances=1 \
  --concurrency=8 \
  --set-env-vars "LLM_API_KEY=${LLM_API_KEY},MCP_SERVER_URL=${MCP_SERVER_URL}"

echo ""
echo "=== Deployment Complete ==="
echo "Next steps:"
echo "  1. Add channel credentials in the Cloud Run console (Variables & secrets)."
echo "     Do not rerun this script — --set-env-vars replaces all env vars."
echo "  2. Verify: curl -sS https://<bridge-service-url>/"
echo "  3. Set chat platform callbacks:"
echo "     LINE WORKS: bridge-service URL + /lineworks/callback"
echo "     DingTalk:   bridge-service URL + /dingtalk/callback"
echo "     Feishu:     bridge-service URL + /feishu/callback"
echo "  4. Future code deploys (preserves console env vars):"
echo "     gcloud run deploy bridge-service --source bridge-service --region $REGION"
