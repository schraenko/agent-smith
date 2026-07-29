"""
Tests for the MCP routing map and the related execute-phase changes.
"""

import json
from unittest.mock import patch

import pytest

from agent_smith.approval import Plan, Subtask, _parse_subtask
from agent_smith.audit import AuditEntry, AuditTrail
from agent_smith.mcp_clients import call_mcp_tool, list_servers
from agent_smith.mcp_routing import (
    MCP_ROUTING_MAP,
    find_routing,
    list_routes,
    render_routes_for_prompt,
)


# ─── find_routing ────────────────────────────────────────────────────────────

def test_find_routing_match_route_distance():
    r = find_routing("Wie ist die Entfernung von Berlin nach Hamburg?")
    assert r is not None
    assert r.task_type == "route_distance"
    assert r.mcp_server == "osm_router"
    assert r.tool_name == "get_route_distance"


def test_find_routing_match_weather():
    r = find_routing("Was ist das Wetter in Muenchen?")
    assert r is not None
    assert r.task_type == "weather"
    assert r.mcp_server == "weather"


def test_find_routing_no_match():
    r = find_routing("Was ist Python?")
    assert r is None


def test_find_routing_case_insensitive():
    r = find_routing("ENTFERNUNG Berlin Hamburg")
    assert r is not None


def test_find_routing_uses_any_keyword():
    """Only one keyword needs to match."""
    r = find_routing("Distanz zwischen zwei Städten")
    assert r is not None
    assert r.task_type == "route_distance"


def test_find_routing_first_match_wins():
    """The first matching entry in the map is returned."""
    r = find_routing("Wetter und Regen")
    assert r is not None
    assert r.task_type == "weather"


def test_list_routes_returns_all_entries():
    routes = list_routes()
    assert len(routes) == len(MCP_ROUTING_MAP)
    for r in routes:
        assert "task_type" in r
        assert "mcp_server" in r
        assert "tool_name" in r


def test_render_routes_for_prompt_contains_all():
    text = render_routes_for_prompt()
    for entry in MCP_ROUTING_MAP:
        assert entry.task_type in text
        assert entry.mcp_server in text


# ─── Subtask: MCP variant ────────────────────────────────────────────────────

def test_subtask_is_mcp_detection():
    agent_sub = Subtask(agent="WebSearchAgent", task="search")
    mcp_sub = Subtask(mcp_server="osm_router", tool_name="get_route_distance", args={})
    assert not agent_sub.is_mcp
    assert mcp_sub.is_mcp


def test_subtask_to_dict_agent():
    s = Subtask(agent="WebSearchAgent", task="search X")
    assert s.to_dict() == {"agent": "WebSearchAgent", "task": "search X"}


def test_subtask_to_dict_mcp():
    s = Subtask(mcp_server="osm_router", tool_name="get_route_distance",
                args={"start": "Berlin", "end": "Hamburg"})
    d = s.to_dict()
    assert d == {
        "mcp_server": "osm_router",
        "tool_name": "get_route_distance",
        "args": {"start": "Berlin", "end": "Hamburg"},
    }


def test_parse_subtask_mcp_valid():
    item = {
        "mcp_server": "weather",
        "tool_name": "get_weather",
        "args": {"location": "Berlin"},
    }
    s = _parse_subtask(0, item)
    assert s.is_mcp
    assert s.mcp_server == "weather"


def test_parse_subtask_mcp_missing_server():
    with pytest.raises(ValueError, match="mcp_server"):
        _parse_subtask(0, {"tool_name": "get_weather", "args": {}})


def test_parse_subtask_mcp_invalid_args():
    with pytest.raises(ValueError, match="args"):
        _parse_subtask(0, {"mcp_server": "x", "tool_name": "y", "args": "not-a-dict"})


def test_plan_from_json_mcp_subtask():
    raw = json.dumps({
        "reasoning": "use osm",
        "subtasks": [
            {"mcp_server": "osm_router", "tool_name": "get_route_distance",
             "args": {"start": "Berlin", "end": "Hamburg"}}
        ],
    })
    plan = Plan.from_json(raw)
    assert len(plan.subtasks) == 1
    assert plan.subtasks[0].is_mcp


def test_plan_from_json_mixed_subtasks():
    raw = json.dumps({
        "reasoning": "mix",
        "subtasks": [
            {"mcp_server": "weather", "tool_name": "get_weather", "args": {"location": "Berlin"}},
            {"agent": "WebSearchAgent", "task": "Find hotels in Berlin"},
        ],
    })
    plan = Plan.from_json(raw)
    assert len(plan.subtasks) == 2
    assert plan.subtasks[0].is_mcp
    assert not plan.subtasks[1].is_mcp


def test_plan_format_shows_mcp_label():
    plan = Plan(subtasks=[
        Subtask(mcp_server="osm_router", tool_name="get_route_distance",
                args={"start": "Berlin", "end": "Hamburg"}),
    ], reasoning="test")
    text = plan.format()
    assert "MCP:osm_router.get_route_distance" in text


# ─── call_mcp_tool ───────────────────────────────────────────────────────────

def test_call_mcp_tool_unknown_server():
    result = call_mcp_tool("nonexistent", "tool", {})
    assert "MCP_ERROR" in result
    assert "Unknown server" in result


def test_call_mcp_tool_osm_router():
    result = call_mcp_tool("osm_router", "get_route_distance",
                           {"start": "Berlin", "end": "Hamburg"})
    assert "MCP_ERROR" not in result
    data = json.loads(result)
    assert "distance_km" in data
    assert "duration_hours" in data
    assert data["start"] == "Berlin"
    assert data["end"] == "Hamburg"


def test_call_mcp_tool_weather():
    result = call_mcp_tool("weather", "get_weather", {"location": "Berlin"})
    assert "MCP_ERROR" not in result
    data = json.loads(result)
    assert "temperature_c" in data
    assert data["location"] == "Berlin"


def test_call_mcp_tool_unknown_tool():
    result = call_mcp_tool("weather", "nonexistent_tool", {})
    assert "Unknown tool" in result


def test_list_servers():
    servers = list_servers()
    assert "osm_router" in servers
    assert "weather" in servers


# ─── Audit: mcp_call action ──────────────────────────────────────────────────

def test_audit_entry_mcp_call():
    entry = AuditEntry(
        timestamp="2026-01-01T00:00:00Z",
        level=0,
        agent="osm_router",
        action="mcp_call",
        tool_name="get_route_distance",
        args={"start": "Berlin", "end": "Hamburg"},
    )
    assert entry.action == "mcp_call"
    assert entry.tool_name == "get_route_distance"


def test_audit_trail_logs_mcp_call(capsys):
    trail = AuditTrail()
    trail.log(
        level=0,
        agent="osm_router",
        action="mcp_call",
        tool_name="get_route_distance",
        args={"start": "Berlin"},
    )
    trail.log(
        level=0,
        agent="osm_router",
        action="mcp_call_result",
        tool_name="get_route_distance",
        result="289.4 km",
        success=True,
    )
    text = trail.format()
    assert "MCP_CALL" in text
    assert "MCP_CALL_RESULT" in text
    assert "Server: osm_router" in text
    assert "Tool: get_route_distance" in text


# ─── Execute phase: MCP subtask end-to-end ──────────────────────────────────

def test_execute_phase_runs_mcp_subtask_deterministically():
    from agent_smith.agents.runner import run_agent_execute_phase, AgentConfig
    from agent_smith.llm import OllamaConfig

    plan = Plan(subtasks=[
        Subtask(mcp_server="osm_router", tool_name="get_route_distance",
                args={"start": "Berlin", "end": "Hamburg"}),
    ])

    config = AgentConfig(
        name="OrchestratorAgent",
        system_prompt="test",
        llm=OllamaConfig(),
        tools=[],
        max_iterations=5,
        context_window=10,
    )

    result = run_agent_execute_phase("how far?", plan, config)
    assert result.success
    assert "MCP" in result.output
    assert "Berlin" in result.output
    actions = [e.action for e in result.audit_trail.entries]
    assert "plan_approved" in actions
    assert "mcp_call" in actions
    assert "mcp_call_result" in actions


# ─── MCP Fallback (bei MCP-Fehler → Standard-Agent) ──────────────────────────

def test_mcp_fallback_agent_osm_router():
    from agent_smith.agents.runner import _mcp_fallback_agent
    assert _mcp_fallback_agent("osm_router", "get_route_distance") == "WebSearchAgent"
    assert _mcp_fallback_agent("osm_router", "get_route_info") == "WebSearchAgent"


def test_mcp_fallback_agent_weather():
    from agent_smith.agents.runner import _mcp_fallback_agent
    assert _mcp_fallback_agent("weather", "get_weather") == "WebSearchAgent"
    assert _mcp_fallback_agent("weather", "get_forecast") == "WebSearchAgent"


def test_mcp_fallback_agent_unknown():
    from agent_smith.agents.runner import _mcp_fallback_agent
    assert _mcp_fallback_agent("nonexistent", "tool") is None


def test_mcp_fallback_task_distance():
    from agent_smith.agents.runner import _mcp_fallback_task
    task = _mcp_fallback_task("get_route_distance", {"start": "Berlin", "end": "Hamburg"})
    assert "Berlin" in task
    assert "Hamburg" in task
    assert "Entfernung" in task


def test_mcp_fallback_task_weather():
    from agent_smith.agents.runner import _mcp_fallback_task
    task = _mcp_fallback_task("get_weather", {"location": "Berlin"})
    assert "Berlin" in task
    assert "Wetter" in task


def test_execute_phase_fallback_on_mcp_error():
    """Bekannter MCP-Server schlaegt fehl -> Fallback zu WebSearchAgent."""
    from unittest.mock import patch
    from agent_smith.agents.runner import run_agent_execute_phase, AgentConfig
    from agent_smith.llm import OllamaConfig

    plan = Plan(subtasks=[
        Subtask(mcp_server="osm_router", tool_name="get_route_distance",
                args={"start": "Berlin", "end": "Hamburg"}),
    ])

    config = AgentConfig(
        name="OrchestratorAgent",
        system_prompt="test",
        llm=OllamaConfig(),
        tools=[],
        max_iterations=5,
        context_window=10,
    )

    with (
        patch("agent_smith.mcp_clients.call_mcp_tool", return_value="MCP_ERROR: osm_router down"),
        patch("agent_smith.agents.runner._delegate_sync", return_value="Fallback: 289 km"),
    ):
        result = run_agent_execute_phase("test", plan, config)
    assert result.success
    assert "Fallback: 289 km" in result.output
    actions = [e.action for e in result.audit_trail.entries]
    assert "mcp_fallback" in actions
    assert "mcp_fallback_result" in actions


def test_execute_fallback_audit_logs_both_attempts():
    """Audit-Trail enthaelt sowohl MCP-Fehler als auch Fallback."""
    from unittest.mock import patch
    from agent_smith.agents.runner import run_agent_execute_phase, AgentConfig
    from agent_smith.llm import OllamaConfig

    plan = Plan(subtasks=[
        Subtask(mcp_server="osm_router", tool_name="get_route_distance",
                args={"start": "Berlin", "end": "Hamburg"}),
    ])

    config = AgentConfig(
        name="OrchestratorAgent",
        system_prompt="test",
        llm=OllamaConfig(),
        tools=[],
        max_iterations=5,
        context_window=10,
    )

    with (
        patch("agent_smith.mcp_clients.call_mcp_tool", return_value="MCP_ERROR: down"),
        patch("agent_smith.agents.runner._delegate_sync", return_value="fallback ok"),
    ):
        result = run_agent_execute_phase("test", plan, config)

    audit_actions = {e.action for e in result.audit_trail.entries}
    assert "mcp_call" in audit_actions
    assert "mcp_call_result" in audit_actions
    assert "mcp_fallback" in audit_actions
    assert "mcp_fallback_result" in audit_actions


def test_execute_phase_unknown_mcp_server():
    from agent_smith.agents.runner import run_agent_execute_phase, AgentConfig
    from agent_smith.llm import OllamaConfig

    plan = Plan(subtasks=[
        Subtask(mcp_server="nonexistent", tool_name="x", args={}),
    ])

    config = AgentConfig(
        name="OrchestratorAgent",
        system_prompt="test",
        llm=OllamaConfig(),
        tools=[],
        max_iterations=5,
        context_window=10,
    )

    result = run_agent_execute_phase("test", plan, config)
    assert result.success
    assert "MCP_ERROR" in result.output
    assert any(e.success is False for e in result.audit_trail.entries if e.action == "mcp_call_result")
