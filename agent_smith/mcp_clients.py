"""
MCP client dispatcher.

`call_mcp_tool(server, tool, args)` routes a call to the right client and
returns the serialized result. Any failure is converted into a structured
fallback string so the execute phase can transparently fall back to a
standard agent (WebSearchAgent) for known MCP servers.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_clients() -> dict[str, Any]:
    from mcp_servers.osm_router.client import ROUTER_CLIENT
    from mcp_servers.weather.client import WEATHER_CLIENT
    return {
        ROUTER_CLIENT.name: ROUTER_CLIENT,
        WEATHER_CLIENT.name: WEATHER_CLIENT,
    }


def call_mcp_tool(server: str, tool: str, args: dict) -> str:
    """
    Dispatch a call to the named MCP server.

    Returns the tool output as a JSON string. On any failure, returns a
    structured fallback string (does not raise).
    """
    clients = _get_clients()
    client = clients.get(server)
    if client is None:
        logger.warning("[mcp] unknown server: %s", server)
        return f"MCP_ERROR: Unknown server '{server}'"
    try:
        return client.call(tool, args or {})
    except Exception as e:
        logger.warning("[mcp] %s.%s failed: %s", server, tool, e)
        return f"MCP_ERROR: {server}.{tool}: {e}"


def list_servers() -> list[str]:
    """Names of all registered MCP servers (for debug/docs)."""
    return list(_get_clients().keys())
