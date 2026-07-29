"""
Synchronous Python client for the OSM Router MCP server.

Used by `agent_smith.mcp_clients` to dispatch MCP subtasks without
launching the full FastMCP SSE server. The client mirrors the server's
tool surface but in pure-Python form so tests can run offline.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OSMRouterClient:
    name = "osm_router"

    def call(self, tool: str, args: dict) -> str:
        from mcp_servers.osm_router.server import get_route_distance, get_route_info
        try:
            if tool == "get_route_distance":
                return _format(get_route_distance(**args))
            if tool == "get_route_info":
                return _format(get_route_info(**args))
            return f"Unknown tool '{tool}' for osm_router"
        except Exception as e:
            logger.warning("[osm_router] call %s failed: %s", tool, e)
            return f"OSM_ROUTER_ERROR: {e}"


def _format(result: Any) -> str:
    import json
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, indent=2)
    return str(result)


ROUTER_CLIENT = OSMRouterClient()
