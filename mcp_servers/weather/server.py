"""
Weather MCP Server.

Provides deterministic weather data for known German cities and PLZ ranges.
In production this would call a real weather API; for tests/offline mode,
we return stable, hash-based mock values so the same query yields the same
result.
"""

import hashlib
import json
import logging
import os

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("Weather", port=8082)

logger = logging.getLogger(__name__)


PLZ_CITY: dict[str, str] = {
    "10115": "Berlin",
    "20095": "Hamburg",
    "80331": "Muenchen",
    "50667": "Koeln",
    "60311": "Frankfurt",
    "70173": "Stuttgart",
    "04109": "Leipzig",
    "01067": "Dresden",
    "30159": "Hannover",
    "90402": "Nuernberg",
    "28195": "Bremen",
    "18055": "Rostock",
    "24937": "Flensburg",
}


def _mock_weather(location: str, plz: str | None) -> dict:
    seed = int(hashlib.sha256(f"{location}|{plz or ''}|current".encode()).hexdigest()[:8], 16)
    base_temp = (seed % 30) - 5
    return {
        "location": location,
        "plz": plz,
        "temperature_c": base_temp + ((seed // 7) % 5),
        "humidity": 40 + (seed % 50),
        "rain_mm": round(((seed >> 3) % 100) / 10.0, 1),
        "wind_kmh": 5 + (seed % 25),
        "condition": ["sonnig", "bewoelkt", "regen", "leicht_regen", "klar"][seed % 5],
        "source": "mock",
    }


def _mock_forecast(location: str, days: int) -> list[dict]:
    forecast = []
    for d in range(days):
        day_seed = int(hashlib.sha256(f"{location}|{d}|forecast".encode()).hexdigest()[:8], 16)
        forecast.append({
            "day": d + 1,
            "temperature_min_c": -5 + (day_seed % 15),
            "temperature_max_c": 5 + (day_seed % 25),
            "rain_mm": round(((day_seed >> 3) % 100) / 10.0, 1),
            "condition": ["sonnig", "bewoelkt", "regen", "leicht_regen", "klar"][day_seed % 5],
        })
    return forecast


@mcp.tool()
def get_weather(location: str, plz: str | None = None) -> dict:
    """
    Current weather for a location (or PLZ).

    Args:
        location: Place name (e.g. 'Berlin'). If plz is given, plz is used to resolve city.
        plz: Optional 5-digit German postal code.
    """
    if plz and plz in PLZ_CITY:
        location = PLZ_CITY[plz]
    return _mock_weather(location, plz)


@mcp.tool()
def get_forecast(location: str, days: int = 3) -> dict:
    """
    Multi-day weather forecast for a location.

    Args:
        location: Place name.
        days: Number of days (1-7). Default: 3.
    """
    days = max(1, min(7, days))
    return {
        "location": location,
        "days": days,
        "forecast": _mock_forecast(location, days),
        "source": "mock",
    }


if __name__ == "__main__":
    port = int(os.environ.get("WEATHER_PORT", "8082"))
    print(f"Weather MCP Server starting on http://localhost:{port}/sse")
    mcp.run(transport="sse")
