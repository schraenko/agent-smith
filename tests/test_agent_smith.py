"""
Tests for Agent Smith (LangChain edition).
Uses unittest.mock — no real Ollama or network calls.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent_smith.agents.runner import AgentConfig, _trim, run_agent, _parse_tool_calls_from_text
from agent_smith.llm import OllamaConfig
from agent_smith.memory.store import last_assistant_text
from agent_smith.tools.builtins import execute_python, get_tools, read_file
from agent_smith.types import AgentResult
from agent_smith.workflows.engine import Step, run_sequential


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


def test_execute_python_tool():
    result = execute_python.invoke({"code": "print(6 * 7)"})
    assert result["returncode"] == 0 and "42" in result["stdout"]


def test_execute_python_error():
    result = execute_python.invoke({"code": "raise ValueError('boom')"})
    assert result["returncode"] != 0 and "boom" in result["stderr"]


def test_read_file_tool(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("hello agent smith")
    result = read_file.invoke({"path": str(f)})
    assert result["content"] == "hello agent smith" and not result["truncated"]


# ─── Agent Runner ─────────────────────────────────────────────────────────────

def _config(tools=None):
    return AgentConfig(
        name="TestAgent", system_prompt="You are a test assistant.",
        llm=OllamaConfig(), tools=tools,
    )


@patch("agent_smith.agents.runner.make_llm")
def test_run_agent_simple(mock_make_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="42", tool_calls=[])
    mock_make_llm.return_value = mock_llm
    result = run_agent("question", _config())
    assert result.success and result.output == "42"


@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_run_agent_tool_call(mock_make_llm_wt):
    tc = {"id": "1", "name": "execute_python", "args": {"code": "print(2)"}}
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content="", tool_calls=[tc]),
        AIMessage(content="result is 2", tool_calls=[]),
    ]
    mock_make_llm_wt.return_value = mock_llm
    result = run_agent("compute", _config(tools=["execute_python"]))
    assert result.success and "2" in result.output


@patch("agent_smith.agents.runner.make_llm")
def test_run_agent_llm_failure(mock_make_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("Ollama unavailable")
    mock_make_llm.return_value = mock_llm
    result = run_agent("anything", _config())
    assert not result.success and "Ollama unavailable" in result.error


@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_run_agent_max_iterations(mock_make_llm_wt):
    tc = {"id": "1", "name": "execute_python", "args": {"code": "pass"}}
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="", tool_calls=[tc])
    mock_make_llm_wt.return_value = mock_llm
    config = AgentConfig(
        name="LoopAgent", system_prompt="loop",
        llm=OllamaConfig(), tools=["execute_python"], max_iterations=3,
    )
    result = run_agent("loop", config)
    assert not result.success and "Max iterations" in result.error


# ─── Workflows ────────────────────────────────────────────────────────────────

@patch("agent_smith.agents.runner.make_llm")
def test_sequential_workflow(mock_make_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="done", tool_calls=[])
    mock_make_llm.return_value = mock_llm
    config = _config()
    steps = [
        Step("step1", config, lambda _: "task one"),
        Step("step2", config, lambda r: f"after: {r['step1'].output}"),
    ]
    wf = run_sequential(steps)
    assert wf.success and "step1" in wf.steps and "step2" in wf.steps


@patch("agent_smith.agents.runner.make_llm")
def test_sequential_stops_on_failure(mock_make_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("LLM down")
    mock_make_llm.return_value = mock_llm
    config = _config()
    steps = [
        Step("step1", config, lambda _: "task"),
        Step("step2", config, lambda _: "never"),
    ]
    wf = run_sequential(steps)
    assert not wf.success and "step2" not in wf.steps


# ─── Fallback Tool Call Parsing ────────────────────────────────────────────────

def test_parse_tool_calls_from_xml():
    text = '<tool_call>{"name": "execute_python", "args": {"code": "print(1)"}}</tool_call>'
    calls = _parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "execute_python"
    assert calls[0]["args"]["code"] == "print(1)"


def test_parse_tool_calls_from_json():
    text = '{"name": "read_file", "args": {"path": "/tmp/test.txt"}}'
    calls = _parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "read_file"
    assert calls[0]["args"]["path"] == "/tmp/test.txt"


def test_parse_tool_calls_from_nested_json():
    text = '{"name": "execute_python", "args": {"code": "def add(a, b):\\n    return a + b\\n\\nresult = add(1, 2)\\nprint(result)"}}'
    calls = _parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "execute_python"
    assert "def add(a, b):" in calls[0]["args"]["code"]


def test_parse_tool_calls_from_python_function():
    text = 'delegate_to(WebSearchAgent, "What is the capital city of France?")'
    calls = _parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "delegate_to"
    assert calls[0]["args"]["agent"] == "WebSearchAgent"
    assert calls[0]["args"]["task"] == "What is the capital city of France?"


def test_parse_tool_calls_from_python_function_with_label():
    text = '''Delegate_to call:
```
delegate_to(WebSearchAgent, "What is the capital city of France?")
```
Explanation: The WebSearchAgent can perform a web search.'''
    calls = _parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "delegate_to"
    assert calls[0]["args"]["agent"] == "WebSearchAgent"
    assert "capital city of France" in calls[0]["args"]["task"]


def test_parse_multiple_tool_calls():
    text = """<tool_call>
{"name": "execute_python", "args": {"code": "print(1)"}}
</tool_call>
<tool_call>
{"name": "read_file", "args": {"path": "/tmp/test.txt"}}
</tool_call>"""
    calls = _parse_tool_calls_from_text(text)
    assert len(calls) == 2
    assert calls[0]["name"] == "execute_python"
    assert calls[1]["name"] == "read_file"


@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_run_agent_with_text_tool_calls(mock_make_llm_wt):
    """Test that tool calls parsed from text are executed."""
    # Simulate Ollama outputting tool calls as text
    text_with_tool_calls = '<tool_call>{"name": "execute_python", "args": {"code": "print(42)"}}</tool_call>'
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content=text_with_tool_calls, tool_calls=[]),
        AIMessage(content="42", tool_calls=[]),
    ]
    mock_make_llm_wt.return_value = mock_llm
    result = run_agent("compute", _config(tools=["execute_python"]))
    assert result.success and "42" in result.output
