"""
OpenStreetMap Routing MCP Server.

Deterministic route calculations via OSRM (public demo endpoint).
Two well-defined tools:
- get_route_distance(start, end, mode) -> {distance_km, duration_hours}
- get_route_info(start, end, mode) -> same + step list

When OSRM is unreachable (offline / test env), a deterministic mock
based on a hash of (start, end, mode) is returned. The mock values are
stable for the same input, so callers can rely on reproducibility.
"""

import hashlib
import json
import logging
import os
import urllib.parse

import httpx
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("OSM Router", port=8081)

logger = logging.getLogger(__name__)

OSRM_URL = "https://router.project-osrm.org/route/v1/{profile}/{coords}"
PROFILES = {
    "driving": "driving",
    "walking": "foot",
    "cycling": "bike",
}

MOCK_CITY_COORDS: dict[str, tuple[float, float]] = {
    "berlin": (13.4050, 52.5200),
    "hamburg": (9.9937, 53.5511),
    "muenchen": (11.5820, 48.1351),
    "münchen": (11.5820, 48.1351),
    "koeln": (6.9603, 50.9375),
    "köln": (6.9603, 50.9375),
    "frankfurt": (8.6821, 50.1109),
    "stuttgart": (9.1829, 48.7758),
    "leipzig": (12.3731, 51.3397),
    "dresden": (13.7373, 51.0504),
    "hannover": (9.7332, 52.3744),
    "nürnberg": (11.0775, 49.4521),
    "nuernberg": (11.0775, 49.4521),
    "bremen": (8.8017, 53.0793),
    "rostock": (12.0991, 54.0924),
    "flensburg": (9.4368, 54.7836),
    "bruchsal": (8.5980,49.1256),
    "nußloch": (8.8333,49.3167)
}


def _resolve_coord(place: str) -> tuple[float, float] | None:
    key = place.strip().lower()
    if key in MOCK_CITY_COORDS:
        return MOCK_CITY_COORDS[key]
    return None


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    from math import asin, cos, radians, sin, sqrt
    lon1, lat1 = a
    lon2, lat2 = b
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    h = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(h))


def _mock_route(start: str, end: str, mode: str) -> dict:
    a = _resolve_coord(start)
    b = _resolve_coord(end)
    seed = int(hashlib.sha256(f"{start}|{end}|{mode}".encode()).hexdigest()[:8], 16)
    if a is None or b is None:
        distance_km = round((seed % 600) + 50.0, 1)
    else:
        distance_km = round(_haversine_km(a, b), 1)
    speed_kmh = {"driving": 90.0, "walking": 5.0, "cycling": 15.0}.get(mode, 90.0)
    duration_h = round(distance_km / speed_kmh, 2)
    return {
        "start": start,
        "end": end,
        "mode": mode,
        "distance_km": distance_km,
        "duration_hours": duration_h,
        "source": "mock",
    }


def _live_route(start: str, end: str, mode: str) -> dict | None:
    a = _resolve_coord(start)
    b = _resolve_coord(end)
    if a is None or b is None:
        return None
    profile = PROFILES.get(mode, "driving")
    coords = f"{a[0]},{a[1]};{b[0]},{b[1]}"
    url = OSRM_URL.format(profile=profile, coords=coords)
    url += "?overview=false&steps=false"
    try:
        with httpx.Client(timeout=8) as client:
            r = client.get(url)
        if r.status_code != 200:
            return None
        data = r.json()
        routes = data.get("routes") or []
        if not routes:
            return None
        route = routes[0]
        return {
            "start": start,
            "end": end,
            "mode": mode,
            "distance_km": round(route["distance"] / 1000.0, 1),
            "duration_hours": round(route["duration"] / 3600.0, 2),
            "source": "osrm",
        }
    except Exception as e:
        logger.warning("[osm_router] live OSRM call failed: %s", e)
        return None


def _route(start: str, end: str, mode: str) -> dict:
    live = _live_route(start, end, mode)
    if live is not None:
        return live
    return _mock_route(start, end, mode)


@mcp.tool()
def get_route_distance(start: str, end: str, mode: str = "driving") -> dict:
    """
    Calculate the distance between two places.

    Args:
        start: Starting place (e.g. 'Berlin').
        end: Destination place (e.g. 'Hamburg').
        mode: Travel mode: 'driving' (default), 'walking', 'cycling'.
    """
    return _route(start, end, mode)


@mcp.tool()
def get_route_info(start: str, end: str, mode: str = "driving") -> dict:
    """
    Detailed route information including distance, duration, and a summary step list.

    Args:
        start: Starting place.
        end: Destination place.
        mode: Travel mode: 'driving', 'walking', 'cycling'.
    """
    base = _route(start, end, mode)
    base["steps"] = [
        f"Start at {start}",
        f"Follow {mode} route towards {end}",
        f"Arrive at {end}",
    ]
    return base


if __name__ == "__main__":
    port = int(os.environ.get("OSM_ROUTER_PORT", "8081"))
    print(f"OSM Router MCP Server starting on http://localhost:{port}/sse")
    mcp.run(transport="sse")
