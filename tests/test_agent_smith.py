"""
Tests for Agent Smith (LangChain edition).
Uses unittest.mock — no real Ollama or network calls.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agent_smith.agents.runner import AgentConfig, _has_task_delegation, _trim, run_agent
from agent_smith.llm import OllamaConfig
from agent_smith.memory.store import last_assistant_text
from agent_smith.tools.builtins import execute_python, get_tools
from agent_smith.types import AgentResult
from agent_smith.workflows.engine import Step, run_sequential


def _fake_agent(messages):
    """Build a stub compiled-graph object returning the given messages list."""
    fake = MagicMock()
    fake.invoke.return_value = {"messages": messages}
    return fake


def _config(tools=None, subagents=None):
    return AgentConfig(
        name="TestAgent", system_prompt="You are a test assistant.",
        llm=OllamaConfig(), tools=tools, subagents=subagents or [],
    )


# ─── Types ────────────────────────────────────────────────────────────────────

def test_agent_result_ok():
    r = AgentResult.ok("hello")
    assert r.success and r.output == "hello" and r.error is None


def test_agent_result_fail():
    r = AgentResult.fail("broke")
    assert not r.success and r.error == "broke"


# ─── Memory / trim ────────────────────────────────────────────────────────────

def test_trim_preserves_system():
    msgs = [SystemMessage(content="sys")] + [HumanMessage(content=str(i)) for i in range(5)]
    result = _trim(msgs, 3)
    assert isinstance(result[0], SystemMessage)
    assert len(result) == 3


def test_trim_no_system():
    msgs = [HumanMessage(content=str(i)) for i in range(10)]
    result = _trim(msgs, 4)
    assert len(result) == 4 and result[-1].content == "9"


def test_last_assistant_text():
    msgs = [HumanMessage(content="hi"), AIMessage(content="hello"),
            HumanMessage(content="?"), AIMessage(content="world")]
    assert last_assistant_text(msgs) == "world"


def test_last_assistant_text_none():
    assert last_assistant_text([HumanMessage(content="hi")]) is None


# ─── Tools ────────────────────────────────────────────────────────────────────

def test_get_tools_by_name():
    names = [t.name for t in get_tools(["web_search", "execute_python"])]
    assert "web_search" in names and "execute_python" in names


def test_read_file_not_in_custom_tools():
    """read_file is now a DeepAgents built-in, not a custom tool."""
    names = [t.name for t in get_tools()]
    assert "read_file" not in names
    assert "list_files" not in names


def test_execute_python_tool():
    result = execute_python.invoke({"code": "print(6 * 7)"})
    assert result["returncode"] == 0 and "42" in result["stdout"]


def test_execute_python_error():
    result = execute_python.invoke({"code": "raise ValueError('boom')"})
    assert result["returncode"] != 0 and "boom" in result["stderr"]


# ─── Agent Runner ─────────────────────────────────────────────────────────────


@patch("agent_smith.agents.runner.create_deep_agent")
def test_run_agent_simple(mock_cda):
    mock_cda.return_value = _fake_agent([AIMessage(content="42", tool_calls=[])])
    result = run_agent("question", _config())
    assert result.success and result.output == "42"


@patch("agent_smith.agents.runner.create_deep_agent")
def test_run_agent_tool_call(mock_cda):
    msgs = [
        AIMessage(content="", tool_calls=[{"id": "1", "name": "execute_python", "args": {"code": "print(2)"}}]),
        ToolMessage(content='{"stdout":"2\\n","stderr":"","returncode":0}', tool_call_id="1", name="execute_python"),
        AIMessage(content="result is 2", tool_calls=[]),
    ]
    mock_cda.return_value = _fake_agent(msgs)
    result = run_agent("compute", _config(tools=["execute_python"]))
    assert result.success and "2" in result.output


@patch("agent_smith.agents.runner.create_deep_agent")
def test_run_agent_llm_failure(mock_cda):
    mock_cda.return_value = MagicMock()
    mock_cda.return_value.invoke.side_effect = Exception("Ollama unavailable")
    result = run_agent("anything", _config())
    assert not result.success and "Ollama unavailable" in result.error


@patch("agent_smith.agents.runner.create_deep_agent")
def test_run_agent_max_iterations(mock_cda_wt):
    fake = MagicMock()
    fake.invoke.side_effect = Exception("GraphRecursionError: recursion limit reached")
    mock_cda_wt.return_value = fake
    config = AgentConfig(
        name="LoopAgent", system_prompt="loop",
        llm=OllamaConfig(), tools=["execute_python"], max_iterations=3,
    )
    result = run_agent("loop", config)
    assert not result.success and "GraphRecursionError" in result.error


# ─── Orchestrator delegation retry loop ───────────────────────────────────────

def test_has_task_delegation_true():
    msgs = [
        AIMessage(content="", tool_calls=[
            {"id": "1", "name": "task", "args": {"subagent_type": "WebSearchAgent"}}
        ]),
    ]
    assert _has_task_delegation(msgs) is True


def test_has_task_delegation_false_other_tool():
    msgs = [
        AIMessage(content="", tool_calls=[
            {"id": "1", "name": "web_search", "args": {}}
        ]),
    ]
    assert _has_task_delegation(msgs) is False


def test_has_task_delegation_false_no_tools():
    msgs = [AIMessage(content="I will answer directly", tool_calls=[])]
    assert _has_task_delegation(msgs) is False


@patch("agent_smith.agents.runner.create_deep_agent")
def test_run_agent_retries_until_delegation(mock_cda):
    """With subagents configured, retries up to 3 times if no task call is made."""
    # First 2 attempts: no task call. 3rd attempt: task call.
    msgs_no_delegation = [AIMessage(content="I'll answer directly", tool_calls=[])]
    msgs_with_delegation = [
        AIMessage(content="", tool_calls=[
            {"id": "1", "name": "task", "args": {"subagent_type": "WebSearchAgent"}}
        ]),
    ]
    fake = MagicMock()
    fake.invoke.side_effect = [
        {"messages": msgs_no_delegation},
        {"messages": msgs_no_delegation},
        {"messages": msgs_with_delegation},
    ]
    mock_cda.return_value = fake

    config = _config(subagents=[{
        "name": "WebSearchAgent", "description": "web",
        "system_prompt": "sys", "tools": [],
    }])
    result = run_agent("search X", config)
    assert result.success
    assert fake.invoke.call_count == 3


@patch("agent_smith.agents.runner.create_deep_agent")
def test_run_agent_gives_up_after_max_retries(mock_cda):
    """After 3 attempts without delegation, returns the last text result."""
    msgs = [AIMessage(content="final text", tool_calls=[])]
    fake = MagicMock()
    fake.invoke.return_value = {"messages": msgs}
    mock_cda.return_value = fake

    config = _config(subagents=[{
        "name": "WebSearchAgent", "description": "web",
        "system_prompt": "sys", "tools": [],
    }])
    result = run_agent("search X", config)
    assert result.success
    assert result.output == "final text"
    assert fake.invoke.call_count == 3


@patch("agent_smith.agents.runner.create_deep_agent")
def test_run_agent_no_subagents_no_retry(mock_cda):
    """Without subagents, no retry loop is used (single invoke)."""
    fake = MagicMock()
    fake.invoke.return_value = {"messages": [AIMessage(content="hi", tool_calls=[])]}
    mock_cda.return_value = fake

    result = run_agent("hi", _config(subagents=[]))
    assert result.success
    assert fake.invoke.call_count == 1


# ─── Workflows ────────────────────────────────────────────────────────────────

@patch("agent_smith.agents.runner.create_deep_agent")
def test_sequential_workflow(mock_cda):
    mock_cda.return_value = _fake_agent([AIMessage(content="done", tool_calls=[])])
    config = _config()
    steps = [
        Step("step1", config, lambda _: "task one"),
        Step("step2", config, lambda r: f"after: {r['step1'].output}"),
    ]
    wf = run_sequential(steps)
    assert wf.success and "step1" in wf.steps and "step2" in wf.steps


@patch("agent_smith.agents.runner.create_deep_agent")
def test_sequential_stops_on_failure(mock_cda):
    fake = MagicMock()
    fake.invoke.side_effect = Exception("LLM down")
    mock_cda.return_value = fake
    config = _config()
    steps = [
        Step("step1", config, lambda _: "task"),
        Step("step2", config, lambda _: "never"),
    ]
    wf = run_sequential(steps)
    assert not wf.success and "step2" not in wf.steps
