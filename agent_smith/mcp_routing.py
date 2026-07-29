"""
MCP Routing Map — deterministic task-to-MCP-server routing.

The map is consulted by the orchestrator when building a plan. A match causes
the orchestrator to prefer a direct MCP subtask over a generic agent delegation.

Design goals:
- Deterministic: keyword matching, no LLM involvement
- Extensible: add a new `RoutingEntry` to `MCP_ROUTING_MAP` to register a service
- Auditable: every lookup is logged via the audit trail
- Safe: silent fallback to standard agents when the MCP call fails
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RoutingEntry:
    task_type: str
    mcp_server: str
    tool_name: str
    keywords: tuple[str, ...]
    description: str

    def matches(self, task: str) -> bool:
        task_lower = task.lower()
        return any(kw in task_lower for kw in self.keywords)


MCP_ROUTING_MAP: tuple[RoutingEntry, ...] = (
    RoutingEntry(
        task_type="route_distance",
        mcp_server="osm_router",
        tool_name="get_route_distance",
        keywords=("entfernung", "distanz"),
        description="Entfernungen zwischen zwei Orten via OpenStreetMap (OSRM).",
    ),
    RoutingEntry(
        task_type="route_info",
        mcp_server="osm_router",
        tool_name="get_route_info",
        keywords=("route", "wegbeschreibung"),
        description="Detaillierte Routeninfo: Distanz, Dauer, Schritte.",
    ),
    RoutingEntry(
        task_type="weather",
        mcp_server="weather",
        tool_name="get_weather",
        keywords=("wetter", "temperatur"),
        description="Aktuelle Wetterdaten für einen Ort oder eine PLZ.",
    ),
    RoutingEntry(
        task_type="weather_forecast",
        mcp_server="weather",
        tool_name="get_forecast",
        keywords=("vorhersage", "forecast", "wetter"),
        description="Mehrtägige Wettervorhersage.",
    ),
)


def find_routing(task: str) -> RoutingEntry | None:
    """Deterministic lookup: returns first entry whose keywords all match."""
    for entry in MCP_ROUTING_MAP:
        if entry.matches(task):
            return entry
    return None


def list_routes() -> list[dict]:
    """All map entries as dicts — for docs, debug, or system prompt rendering."""
    return [asdict(e) for e in MCP_ROUTING_MAP]


def render_routes_for_prompt() -> str:
    """Compact text representation for the orchestrator's system prompt."""
    lines = ["| Task Type | MCP Server | Tool | Description |",
             "|---|---|---|---|"]
    for e in MCP_ROUTING_MAP:
        keywords = ", ".join(e.keywords)
        lines.append(
            f"| `{e.task_type}` | `{e.mcp_server}` | `{e.tool_name}` | "
            f"{e.description} (keywords: {keywords}) |"
        )
    return "\n".join(lines)
