---
title: MCP-Routing-Map
author: agent-smith
date: 2026-07-28
tags: [mcp, routing, deterministic, orchestrator]
abstract: Konzept und Konfiguration der MCP-Routing-Map für deterministische Tool-Auswahl.
---

# MCP-Routing-Map

Die MCP-Routing-Map ist eine Konfiguration, die der Orchestrator konsultiert, **bevor** er einen Task in Subtasks zerlegt. Match-Treffer führen zu direkten MCP-Subtasks im Plan — die zur Laufzeit **deterministisch** (ohne LLM) ausgeführt werden.

## Konzept

```
User-Task
    ↓
Orchestrator (kennt die Map)
    ↓
Map-Lookup: keywords in MCP_ROUTING_MAP
    ↓ (Match)
Plan mit MCP-Subtasks → deterministische Ausführung
    ↓ (No Match)
Plan mit Agent-Subtasks → Standard-Delegation
```

**Ziel:** Für bekannte Task-Typen (Routen, Wetter, …) deterministische, reproduzierbare Ergebnisse liefern — ohne LLM-Roundtrip für die eigentliche Datenabfrage.

---

## Architektur

### Module

| Datei | Zweck |
|---|---|
| `agent_smith/mcp_routing.py` | `RoutingEntry` Dataclass + `MCP_ROUTING_MAP` + `find_routing()` |
| `agent_smith/mcp_clients.py` | `call_mcp_tool()` Dispatcher mit stillem Fallback |
| `agent_smith/approval.py` | `Subtask` mit `mcp_server`/`tool_name`/`args` Feldern |
| `agent_smith/agents/runner.py` | `run_agent_execute_phase` führt MCP-Subtasks deterministisch aus |
| `agent_smith/audit.py` | `mcp_call` und `mcp_call_result` Audit-Actions |
| `rules/orchestrator.md` | System-Prompt mit Map-Sektion |
| `mcp_servers/*/server.py` | FastMCP-Server (osm_router, weather, …) |
| `mcp_servers/*/client.py` | Sync Python-Wrapper (für Tests + direkte Aufrufe) |

### Datenfluss

1. **Plan-Phase:** Orchestrator sieht User-Task, prüft Map, erzeugt `Plan` mit gemischten Subtasks:
   ```json
   {
     "subtasks": [
       {"mcp_server": "osm_router", "tool_name": "get_route_distance", "args": {...}},
       {"agent": "WebSearchAgent", "task": "..."}
     ]
   }
   ```

2. **Execute-Phase:** `run_agent_execute_phase` iteriert über Subtasks:
   - **MCP-Subtask:** `call_mcp_tool(server, tool, args)` — synchron, deterministisch
   - **Agent-Subtask:** `_delegate_sync(agent, task)` — direkter Agent-Aufruf, kein LLM-Loop
   - **Final-Phase:** LLM kombiniert alle Ergebnisse in eine natürliche Antwort

---

## Aktuelle Map-Einträge

| Task Type | MCP Server | Tool | Keywords |
|---|---|---|---|
| `route_distance` | `osm_router` | `get_route_distance` | entfernung, distanz |
| `route_info` | `osm_router` | `get_route_info` | route, wegbeschreibung |
| `weather` | `weather` | `get_weather` | wetter, temperatur |
| `weather_forecast` | `weather` | `get_forecast` | vorhersage, forecast, wetter |

---

## Map erweitern

Eine neue Route hinzufügen in `agent_smith/mcp_routing.py`:

```python
MCP_ROUTING_MAP = (
    # ... bestehende Eintraege ...
    RoutingEntry(
        task_type="currency_convert",
        mcp_server="fx_rates",
        tool_name="convert",
        keywords=("wechselkurs", "umrechnen", "währung"),
        description="Währungsumrechnung mit aktuellen Wechselkursen.",
    ),
)
```

Plus den entsprechenden MCP-Server unter `mcp_servers/fx_rates/` anlegen.

---

## MCP-Server-Struktur

```python
# mcp_servers/fx_rates/server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("FX Rates", port=8083)

@mcp.tool()
def convert(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert currency."""
    return {"amount": amount, "from": from_currency, "to": to_currency, "result": ...}
```

```python
# mcp_servers/fx_rates/client.py
from mcp_servers.fx_rates.server import convert

class FXRatesClient:
    name = "fx_rates"
    def call(self, tool: str, args: dict) -> str:
        if tool == "convert":
            return json.dumps(convert(**args))
        return f"Unknown tool '{tool}'"

FX_CLIENT = FXRatesClient()
```

```python
# agent_smith/mcp_clients.py (Dispatcher erweitern)
def _get_clients() -> dict[str, Any]:
    from mcp_servers.fx_rates.client import FX_CLIENT
    return {
        ROUTER_CLIENT.name: ROUTER_CLIENT,
        WEATHER_CLIENT.name: WEATHER_CLIENT,
        FX_CLIENT.name: FX_CLIENT,
    }
```

---

## Verhalten

| Szenario | Verhalten |
|---|---|
| Map-Match + MCP erreichbar | Plan enthält MCP-Subtask, deterministisch ausgeführt |
| Map-Match + MCP nicht erreichbar | Tool-Call liefert `MCP_ERROR: ...` (stiller Fallback) |
| Kein Map-Match | Plan enthält Standard-Agent-Subtasks |
| Mix aus MCP- und Agent-Subtasks | Beide Typen werden in Plan-Order ausgeführt |

**Stiller Fallback:** Bei MCP-Fehler wird der Fehler als String zurückgegeben — die Orchestrierung läuft weiter. Der User/LLM kann den Fehler interpretieren.

---

## Audit-Trail

Jeder MCP-Call wird mit zwei Audit-Entries protokolliert:

```
[0] MCP_CALL: osm_router.get_route_distance({'start': 'Berlin', 'end': 'Hamburg'})
[0] MCP_RESULT [OK] from osm_router.get_route_distance
    Output: {"distance_km": 289.4, ...}
```

Bei Fehler:

```
[0] MCP_CALL: weather.get_weather({...})
[0] MCP_RESULT [FAILED] from weather.get_weather
    Output: MCP_ERROR: ...
```

---

## Tests

`tests/test_mcp_routing.py` deckt ab:

- Map-Lookup (Match, No-Match, Case-Insensitive, Multi-Keyword)
- Subtask-Serialisierung (Agent + MCP)
- `call_mcp_tool` mit Live-MCP-Servern
- Audit-Trail mit `mcp_call` Action
- Execute-Phase mit deterministischer MCP-Ausführung
- Stiller Fallback bei unbekanntem Server

**26 Tests** insgesamt.

---

## Best Practices

1. **Deterministische Tools:** MCP-Server sollten idempotent und parameter-stabil sein
2. **Klare Keywords:** 2-3 präzise Keywords pro Eintrag (nicht zu generisch)
3. **Stille Fehler:** `MCP_ERROR: ...` Prefix ermöglicht LLM-Fallback in natürlicher Sprache
4. **Mock-First:** Tests laufen mit deterministischen Mock-Daten (siehe `_mock_route`, `_mock_weather`)
5. **Live-Optional:** Produktive Server können echte APIs ansprechen (z.B. OSRM), fallen aber auf Mock zurück
6. **Erste Match gewinnt:** Reihenfolge in `MCP_ROUTING_MAP` ist relevant
7. **Audit ist Pflicht:** Jeder MCP-Call erscheint im Trail für Debugging und Compliance

---

## Bekannte Limitierungen

- **Keyword-Matching nur case-insensitive Substring:** Keine Regex, keine Mehrwort-Phrasen
- **Keine Argument-Extraktion:** Map matcht nur auf Task-Keywords, nicht auf Argumente
- **Kein Multi-Language:** Keywords sind deutsch
- **Kein LLM-Fallback im Tool:** `MCP_ERROR` ist nur ein String, keine automatische Web-Suche
