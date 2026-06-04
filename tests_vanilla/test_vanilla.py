"""
Tests for Agent Smith.
Uses unittest.mock to avoid real Ollama / network calls.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agent_smith_vanilla.agents.runner import AgentConfig, run_agent
from agent_smith_vanilla.llm.ollama import OllamaConfig
from agent_smith_vanilla.memory.store import MemoryStore, empty_store, window
from agent_smith_vanilla.tools.registry import execute_tool_call, get_tool, tool
from agent_smith_vanilla.types import AgentContext, Message, Role, ToolCall
from agent_smith_vanilla.workflows.engine import Step, run_sequential


# ─── Types ────────────────────────────────────────────────────────────────────

def test_agent_context_immutability():
    ctx = AgentContext()
    msg = Message(role=Role.USER, content="hello")
    new_ctx = ctx.with_message(msg)
    assert len(ctx.messages) == 0
    assert len(new_ctx.messages) == 1


def test_agent_context_with_memory():
    ctx = AgentContext()
    ctx2 = ctx.with_memory("key", "value")
    assert ctx.memory == {}
    assert ctx2.memory["key"] == "value"


# ─── Memory ───────────────────────────────────────────────────────────────────

def test_memory_store_immutable():
    store = empty_store()
    store2 = store.set("x", 42)
    assert store.get("x") is None
    assert store2.get("x") == 42


def test_memory_store_delete():
    store = empty_store().set("a", 1).set("b", 2)
    store2 = store.delete("a")
    assert store2.get("a") is None
    assert store2.get("b") == 2


def test_window_preserves_system_message():
    msgs = [
        Message(role=Role.SYSTEM, content="sys"),
        Message(role=Role.USER, content="1"),
        Message(role=Role.USER, content="2"),
        Message(role=Role.USER, content="3"),
    ]
    result = window(msgs, max_messages=3)
    assert result[0].role == Role.SYSTEM
    assert len(result) == 3


def test_window_no_system():
    msgs = [Message(role=Role.USER, content=str(i)) for i in range(10)]
    result = window(msgs, max_messages=4)
    assert len(result) == 4
    assert result[-1].content == "9"


# ─── Tools ────────────────────────────────────────────────────────────────────

def test_tool_registration():
    @tool(
        name="test_add",
        description="Add two numbers",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
    def add(a: float, b: float) -> float:
        return a + b

    t = get_tool("test_add")
    assert t is not None
    assert t.name == "test_add"


def test_tool_execution():
    call = ToolCall(id="1", name="test_add", arguments={"a": 2, "b": 3})
    result = execute_tool_call(call)
    assert result.success
    assert result.result == 5.0


def test_tool_execution_unknown():
    call = ToolCall(id="x", name="does_not_exist", arguments={})
    result = execute_tool_call(call)
    assert not result.success
    assert "Unknown tool" in result.error


def test_execute_python_tool():
    from agent_smith_vanilla.tools.builtins import execute_python
    result = execute_python("print(1 + 1)")
    assert result["returncode"] == 0
    assert "2" in result["stdout"]


def test_execute_python_error():
    from agent_smith_vanilla.tools.builtins import execute_python
    result = execute_python("raise ValueError('oops')")
    assert result["returncode"] != 0
    assert "oops" in result["stderr"]


def test_read_file_tool(tmp_path):
    from agent_smith_vanilla.tools.builtins import read_file
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    result = read_file(str(f))
    assert result["content"] == "hello world"
    assert not result["truncated"]


# ─── Agent Runner ─────────────────────────────────────────────────────────────

def _make_config(tools=None):
    return AgentConfig(
        name="TestAgent",
        system_prompt="You are a test agent.",
        llm=OllamaConfig(model="llama3.2"),
        tools=tools,
    )


@patch("agent_smith_vanilla.agents.runner.complete")
def test_run_agent_simple(mock_complete):
    mock_complete.return_value = ("The answer is 42.", [])
    config = _make_config()
    result = run_agent("What is the answer?", config)
    assert result.success
    assert result.output == "The answer is 42."


@patch("agent_smith_vanilla.agents.runner.complete")
def test_run_agent_with_tool_call(mock_complete):
    tool_call = ToolCall(id="1", name="test_add", arguments={"a": 1, "b": 2})
    # First call returns tool use, second returns final text
    mock_complete.side_effect = [
        ("", [tool_call]),
        ("The result is 3.", []),
    ]
    config = _make_config(tools=["test_add"])
    result = run_agent("Add 1 and 2", config)
    assert result.success
    assert "3" in result.output


@patch("agent_smith_vanilla.agents.runner.complete")
def test_run_agent_max_iterations(mock_complete):
    # Always returns a tool call → should hit max_iterations
    tool_call = ToolCall(id="1", name="test_add", arguments={"a": 1, "b": 1})
    mock_complete.return_value = ("", [tool_call])
    config = AgentConfig(
        name="LoopAgent",
        system_prompt="loop",
        llm=OllamaConfig(),
        tools=["test_add"],
        max_iterations=3,
    )
    result = run_agent("loop forever", config)
    assert not result.success
    assert "Max iterations" in result.error


# ─── Workflows ────────────────────────────────────────────────────────────────

@patch("agent_smith_vanilla.agents.runner.complete")
def test_sequential_workflow(mock_complete):
    mock_complete.return_value = ("done", [])
    config = _make_config()

    steps = [
        Step(name="step1", agent=config, task_fn=lambda _: "task one"),
        Step(name="step2", agent=config, task_fn=lambda r: f"task two, prev: {r['step1'].output}"),
    ]

    workflow = run_sequential(steps)
    assert workflow.success
    assert "step1" in workflow.steps
    assert "step2" in workflow.steps


@patch("agent_smith_vanilla.agents.runner.complete")
def test_sequential_stops_on_failure(mock_complete):
    mock_complete.side_effect = Exception("LLM unavailable")
    config = _make_config()

    steps = [
        Step(name="step1", agent=config, task_fn=lambda _: "task"),
        Step(name="step2", agent=config, task_fn=lambda _: "never reached"),
    ]

    workflow = run_sequential(steps)
    assert not workflow.success
    assert "step2" not in workflow.steps
