#!/bin/bash
set -e

# Deploy the AI Conversation Bridge services to Google Cloud Run.
# Prerequisites: gcloud CLI authenticated and project configured.
#
# Usage:
#   ./scripts/deploy-cloud-run.sh [REGION]
#
# Environment variables are NOT set by this script — configure them
# in the Cloud Run console or via gcloud after deployment:
#   gcloud run services update <SERVICE> --region <REGION> --set-env-vars KEY=VALUE
#
# bridge-service is pinned to a single Cloud Run instance because the default
# LangGraph STATE_BACKEND=memory does not share conversation state across
# replicas (see docs/langgraph-orchestration-proposal-v2.md §6.3).

REGION="${1:-us-west1}"
REPO_ROOT="$(dirname "$0")/.."

echo "=== Deploying to Cloud Run (region: $REGION) ==="
echo ""

echo "--- 1/2: mcp-demo-server ---"
gcloud run deploy mcp-demo-server \
  --source "$REPO_ROOT/mcp-demo-server" \
  --region "$REGION" \
  --allow-unauthenticated

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
  --concurrency=8

echo ""
echo "=== Deployment Complete ==="
echo "Next steps:"
echo "  1. Set environment variables for each service:"
echo "     gcloud run services update bridge-service --region $REGION --set-env-vars KEY=VALUE"
echo "     gcloud run services update mcp-demo-server --region $REGION --set-env-vars KEY=VALUE"
echo "  2. For Flowise: update your flow's MCP URL to the deployed mcp-demo-server."
echo "     For LangGraph: set ORCHESTRATOR=langgraph, LLM_API_KEY, and MCP_SERVER_URL on bridge-service."
echo "     Optional MCP_TOOL_ALLOWLIST defaults to the safe built-in list; '*' allows all tools."
echo "     Deploy mcp-demo-server first: a down MCP server or missing allowlisted tools fail boot."
echo "  3. Set chat platform callbacks (service rename is a breaking change from chat-connector):"
echo "     LINE WORKS: bridge-service URL + /lineworks/callback"
echo "     DingTalk:   bridge-service URL + /dingtalk/callback"
