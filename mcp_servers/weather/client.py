"""
Synchronous Python client for the Weather MCP server.

Mirrors the server's tool surface so `agent_smith.mcp_clients` can dispatch
MCP subtasks without launching the full FastMCP SSE server.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class WeatherClient:
    name = "weather"

    def call(self, tool: str, args: dict) -> str:
        from mcp_servers.weather.server import get_weather, get_forecast
        try:
            if tool == "get_weather":
                return _format(get_weather(**args))
            if tool == "get_forecast":
                return _format(get_forecast(**args))
            return f"Unknown tool '{tool}' for weather"
        except Exception as e:
            logger.warning("[weather] call %s failed: %s", tool, e)
            return f"WEATHER_ERROR: {e}"


def _format(result: Any) -> str:
    import json
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, indent=2)
    if isinstance(result, list):
        return json.dumps(result, ensure_ascii=False, indent=2)
    return str(result)


WEATHER_CLIENT = WeatherClient()
