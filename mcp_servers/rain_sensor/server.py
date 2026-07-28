"""
Rain Sensor Network MCP Server

Mock-MCP-Server für ein gefaktes Regensensor-Netzwerk.
Sensordaten werden mit Zufallszahlen generiert.
"""

import random
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Rain Sensor Network", port=8080)

SENSORS = [
    {"id": "sensor_01", "name": "Berlin-Mitte", "lat": 52.5200, "lon": 13.4050},
    {"id": "sensor_02", "name": "Hamburg-Sued", "lat": 53.5511, "lon": 9.9937},
    {"id": "sensor_03", "name": "Muenchen-Zentrum", "lat": 48.1351, "lon": 11.5820},
    {"id": "sensor_04", "name": "Koeln-Innenstadt", "lat": 50.9375, "lon": 6.9603},
    {"id": "sensor_05", "name": "Frankfurt-West", "lat": 50.1109, "lon": 8.6821},
    {"id": "sensor_06", "name": "Stuttgart-Nord", "lat": 48.7758, "lon": 9.1829},
]


def _generate_mock_data(sensor: dict) -> dict:
    """Generiere Mock-Daten für einen Sensor."""
    return {
        "id": sensor["id"],
        "name": sensor["name"],
        "location": {"lat": sensor["lat"], "lon": sensor["lon"]},
        "rain_mm": round(random.uniform(0.0, 25.0), 1),
        "humidity": random.randint(30, 100),
        "temperature": round(random.uniform(-5.0, 35.0), 1),
        "status": random.choice(["online", "online", "online", "offline", "error"]),
        "last_update": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def get_all_sensors() -> list[dict]:
    """Gibt alle Regensensoren mit aktuellen Werten zurueck."""
    return [_generate_mock_data(s) for s in SENSORS]


@mcp.tool()
def get_sensor(sensor_id: str) -> dict:
    """Gibt einen einzelnen Regensensor nach ID zurueck.

    Args:
        sensor_id: Die Sensor-ID (z.B. sensor_01)
    """
    for s in SENSORS:
        if s["id"] == sensor_id:
            return _generate_mock_data(s)
    return {"error": f"Sensor '{sensor_id}' nicht gefunden. Verfuegbare IDs: {[x['id'] for x in SENSORS]}"}


@mcp.tool()
def get_rain_level() -> dict:
    """Berechnet den durchschnittlichen Regenpegel aller Sensoren."""
    data = [_generate_mock_data(s) for s in SENSORS]
    online = [d for d in data if d["status"] == "online"]

    if not online:
        return {"average_rain_mm": 0.0, "max_rain_mm": 0.0, "min_rain_mm": 0.0, "online_sensors": 0}

    rain_values = [d["rain_mm"] for d in online]
    return {
        "average_rain_mm": round(sum(rain_values) / len(rain_values), 1),
        "max_rain_mm": max(rain_values),
        "min_rain_mm": min(rain_values),
        "online_sensors": len(online),
    }


@mcp.tool()
def get_alerts(threshold: float = 5.0) -> list[dict]:
    """Gibt Sensoren zurueck, deren Regenpegel den Schwellenwert ueberschreiten.

    Args:
        threshold: Schwellenwert in mm (Standard: 5.0)
    """
    data = [_generate_mock_data(s) for s in SENSORS]
    return [d for d in data if d["rain_mm"] > threshold and d["status"] == "online"]


if __name__ == "__main__":
    print("Rain Sensor MCP Server startet auf http://localhost:8080/sse")
    mcp.run(transport="sse")
