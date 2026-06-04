"""
Tests for Agent Smith (CrewAI edition).
Uses unittest.mock — no real Ollama or network calls.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from agent_smith_crewai.agents.runner import AgentConfig, run_agent
from agent_smith_crewai.llm import OllamaConfig
from agent_smith_crewai.memory.store import last_assistant_text, window
from agent_smith_crewai.tools.builtins import (
    delegate_to, execute_python, get_tools, read_file,
)
from agent_smith_crewai.types import AgentResult, Status
from agent_smith_crewai.workflows.engine import Step, run_sequential


# ─── Types ────────────────────────────────────────────────────────────────────

def test_agent_result_ok():
    r = AgentResult.ok("hello")
    assert r.success
    assert r.output == "hello"
    assert r.error is None
    assert r.status == Status.SUCCESS


def test_agent_result_fail():
    r = AgentResult.fail("broke")
    assert not r.success
    assert r.error == "broke"
    assert r.status == Status.FAILED


def test_agent_result_ok_with_steps():
    r = AgentResult.ok(42, steps=["a", "b"])
    assert r.output == 42
    assert r.intermediate_steps == ["a", "b"]


# ─── Memory ───────────────────────────────────────────────────────────────────

def test_last_assistant_text_found():
    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "?"},
        {"role": "assistant", "content": "world"},
    ]
    assert last_assistant_text(msgs) == "world"


def test_last_assistant_text_none():
    assert last_assistant_text([{"role": "user", "content": "hi"}]) is None


def test_last_assistant_text_empty():
    assert last_assistant_text([]) is None


def test_window_returns_last_n():
    msgs = [{"role": "user", "content": str(i)} for i in range(10)]
    result = window(msgs, 3)
    assert len(result) == 3
    assert result[-1]["content"] == "9"


def test_window_zero():
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]
    assert window(msgs, 0) == []


def test_window_empty():
    assert window([], 5) == []


# ─── Tools ────────────────────────────────────────────────────────────────────

def test_get_tools_by_name():
    names = [t.__name__ for t in get_tools(["web_search", "execute_python"])]
    assert "web_search" in names
    assert "execute_python" in names


def test_get_tools_all_when_none():
    all_tools = get_tools()
    assert len(all_tools) == 9


def test_execute_python_tool():
    result = execute_python("print(6 * 7)")
    assert result["returncode"] == 0
    assert "42" in result["stdout"]


def test_execute_python_error():
    result = execute_python("raise ValueError('boom')")
    assert result["returncode"] != 0
    assert "boom" in result["stderr"]


def test_read_file_tool(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("hello crewai edition")
    result = read_file(str(f))
    assert result["content"] == "hello crewai edition"
    assert not result["truncated"]


def test_read_file_missing():
    result = read_file("/nonexistent/file.txt")
    assert "error" in result


@patch("agent_smith_crewai.agents.builtins.run_web_search")
def test_delegate_to_web_search(mock_ws):
    mock_ws.return_value = AgentResult.ok("search results")
    result = delegate_to("WebSearchAgent", "find something")
    assert "search results" in result


def test_delegate_to_unknown():
    result = delegate_to("UnknownAgent", "task")
    assert "Unknown agent" in result


# ─── Agent Runner (mocked CrewAI) ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_crewai():
    """Pre-populate sys.modules so that `from crewai import ...` inside
    run_agent() returns MagicMock objects instead of trying to import
    the real crewai package (which requires incompatible langchain 0.1.x)."""
    mock_mod = MagicMock()
    mock_mod.Agent = MagicMock()
    mock_mod.Crew = MagicMock()
    mock_mod.Process = MagicMock()
    mock_mod.Task = MagicMock()
    with patch.dict("sys.modules", {"crewai": mock_mod}):
        yield mock_mod


def _config(tools=None):
    return AgentConfig(
        name="TestAgent",
        system_prompt="You are a test assistant.",
        llm=OllamaConfig(),
        tools=tools,
    )


def test_run_agent_simple(mock_crewai):
    mock_crew = MagicMock()
    mock_crew.kickoff.return_value = "42"
    mock_crewai.Crew.return_value = mock_crew

    result = run_agent("question", _config())
    assert result.success
    assert result.output == "42"


def test_run_agent_with_tools(mock_crewai):
    mock_crew = MagicMock()
    mock_crew.kickoff.return_value = "computed 42"
    mock_crewai.Crew.return_value = mock_crew

    result = run_agent("compute", _config(tools=["execute_python"]))
    assert result.success
    assert "42" in result.output


def test_run_agent_failure(mock_crewai):
    mock_crew = MagicMock()
    mock_crew.kickoff.side_effect = RuntimeError("Ollama down")
    mock_crewai.Crew.return_value = mock_crew

    result = run_agent("anything", _config())
    assert not result.success
    assert "Ollama down" in result.error


# ─── Workflows ────────────────────────────────────────────────────────────────


@patch("agent_smith_crewai.workflows.engine.run_agent")
def test_sequential_workflow(mock_run):
    mock_run.return_value = AgentResult.ok("done")
    config = _config()
    steps = [
        Step("step1", config, lambda _: "task one"),
        Step("step2", config, lambda r: f"after: {r['step1'].output}"),
    ]
    wf = run_sequential(steps)
    assert wf.success
    assert "step1" in wf.steps
    assert "step2" in wf.steps


@patch("agent_smith_crewai.workflows.engine.run_agent")
def test_sequential_stops_on_failure(mock_run):
    mock_run.return_value = AgentResult.fail("LLM unavailable")
    config = _config()
    steps = [
        Step("step1", config, lambda _: "task"),
        Step("step2", config, lambda _: "never reached"),
    ]
    wf = run_sequential(steps)
    assert not wf.success
    assert "step2" not in wf.steps


@patch("agent_smith_crewai.workflows.engine.run_agent")
def test_sequential_empty_steps(mock_run):
    wf = run_sequential([])
    assert wf.final is None
    assert wf.success
