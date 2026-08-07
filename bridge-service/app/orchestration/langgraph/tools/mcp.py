"""MCP tool discovery and allowlist filtering for the LangGraph orchestrator."""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

# Authoritative allowlist from flowise/flows/workday-mcp-agent.json mcpActions.
# A tool the server exposes but this list omits must not reach the model.
MCP_TOOL_ALLOWLIST = frozenset({
    "find_employee_id_by_name",
    "get_current_user_info",
    "get_current_user_time_off_balance",
    "get_current_user_time_off_history",
    "get_direct_reports",
    "get_more_employee_data",
    "get_my_time_off_eligibility",
    "get_personal_information",
    "get_today_date_and_day_of_week",
    "request_my_time_off",
    "get_time_off_balance",
})


async def load_mcp_tools(server_url: str, auth_header: str | None = None) -> list[BaseTool]:
    """Discover MCP tools once, filter to the allowlist, and return LangChain tools."""
    headers = {}
    if auth_header:
        # Accept either a full "Authorization: Bearer …" value or a raw token.
        if ":" in auth_header and not auth_header.lower().startswith("authorization"):
            # "Authorization: Bearer x" style already
            name, _, value = auth_header.partition(":")
            headers[name.strip()] = value.strip()
        elif auth_header.lower().startswith("bearer ") or auth_header.lower().startswith("authorization"):
            headers["Authorization"] = (
                auth_header.split(":", 1)[-1].strip()
                if auth_header.lower().startswith("authorization")
                else auth_header
            )
        else:
            headers["Authorization"] = auth_header

    connection: dict = {
        "transport": "streamable_http",
        "url": server_url,
    }
    if headers:
        connection["headers"] = headers

    client = MultiServerMCPClient({"workday": connection})
    discovered = await client.get_tools()
    discovered_names = [t.name for t in discovered]
    filtered = [t for t in discovered if t.name in MCP_TOOL_ALLOWLIST]
    retained = [t.name for t in filtered]

    logger.info("MCP tools discovered (%d): %s", len(discovered_names), discovered_names)
    logger.info("MCP tools retained after allowlist (%d): %s", len(retained), retained)
    omitted = sorted(set(discovered_names) - set(retained))
    if omitted:
        logger.info("MCP tools omitted by allowlist: %s", omitted)

    return filtered
