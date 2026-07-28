"""
Tests for the Human-in-the-Loop (HITL) flow:
- Plan dataclass validation
- submit_plan tool
- run_agent_plan_phase / run_agent_execute_phase
- run_interactive with approval_callback
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from agent_smith.agents.runner import (
    AgentConfig,
    _parse_tool_calls_from_text,
    run_agent_execute_phase,
    run_agent_plan_phase,
)
from agent_smith.approval import (
    ApprovalDecision,
    Plan,
    Subtask,
    VALID_AGENTS,
)
from agent_smith.llm import OllamaConfig
from agent_smith.tools.submit_plan import (
    PLAN_SUBMITTED_MARKER,
    parse_plan_from_args,
    submit_plan,
)


# ─── Plan validation ─────────────────────────────────────────────────────────

def test_plan_from_json_minimal():
    raw = '{"subtasks": [{"agent": "WebSearchAgent", "task": "Find X"}]}'
    plan = Plan.from_json(raw)
    assert len(plan.subtasks) == 1
    assert plan.subtasks[0] == Subtask(agent="WebSearchAgent", task="Find X")
    assert plan.reasoning == ""


def test_plan_from_json_with_reasoning():
    raw = '''{
        "reasoning": "Need to search then code",
        "subtasks": [
            {"agent": "WebSearchAgent", "task": "Find X"},
            {"agent": "CodeExecutionAgent", "task": "Compute Y"}
        ]
    }'''
    plan = Plan.from_json(raw)
    assert plan.reasoning == "Need to search then code"
    assert len(plan.subtasks) == 2


def test_plan_from_json_roundtrip():
    plan = Plan(
        subtasks=[Subtask(agent="APIAgent", task="Call endpoint")],
        reasoning="Simple API call",
    )
    plan2 = Plan.from_json(plan.to_json())
    assert plan2.subtasks == plan.subtasks
    assert plan2.reasoning == plan.reasoning


def test_plan_from_json_rejects_invalid_agent():
    raw = '{"subtasks": [{"agent": "NotAnAgent", "task": "X"}]}'
    with pytest.raises(ValueError, match="invalid agent"):
        Plan.from_json(raw)


def test_plan_from_json_rejects_empty_subtasks():
    raw = '{"subtasks": []}'
    with pytest.raises(ValueError, match="non-empty"):
        Plan.from_json(raw)


def test_plan_from_json_rejects_empty_task():
    raw = '{"subtasks": [{"agent": "WebSearchAgent", "task": "  "}]}'
    with pytest.raises(ValueError, match="empty"):
        Plan.from_json(raw)


def test_plan_from_json_rejects_non_object():
    with pytest.raises(ValueError, match="object"):
        Plan.from_json("[]")


def test_plan_format_human_readable():
    plan = Plan(
        subtasks=[Subtask(agent="WebSearchAgent", task="Find X")],
        reasoning="Just search",
    )
    text = plan.format()
    assert "WebSearchAgent" in text
    assert "Find X" in text
    assert "Just search" in text


def test_valid_agents_constant():
    assert "WebSearchAgent" in VALID_AGENTS
    assert "CodeExecutionAgent" in VALID_AGENTS
    assert "DocumentAgent" in VALID_AGENTS
    assert "APIAgent" in VALID_AGENTS
    assert "DataAgent" in VALID_AGENTS


# ─── submit_plan tool ────────────────────────────────────────────────────────

def test_submit_plan_returns_marker_structured():
    """Qwen3's preferred structured form: subtasks + reasoning."""
    args = {
        "subtasks": [{"agent": "WebSearchAgent", "task": "Search"}],
        "reasoning": "Need to search",
    }
    result = submit_plan.invoke(args)
    assert result == PLAN_SUBMITTED_MARKER


def test_submit_plan_rejects_invalid_agent():
    with pytest.raises(Exception):
        submit_plan.invoke({"subtasks": [{"agent": "NotAnAgent", "task": "X"}]})


def test_submit_plan_rejects_empty_subtasks():
    with pytest.raises(Exception):
        submit_plan.invoke({"subtasks": []})


def test_parse_plan_from_args_structured():
    """Qwen3's preferred format: subtasks + reasoning as separate fields."""
    args = {
        "subtasks": [{"agent": "APIAgent", "task": "GET /x"}],
        "reasoning": "Simple API call",
    }
    plan = parse_plan_from_args(args)
    assert plan.subtasks[0].agent == "APIAgent"
    assert plan.reasoning == "Simple API call"


def test_parse_plan_from_args_structured_no_reasoning():
    args = {"subtasks": [{"agent": "WebSearchAgent", "task": "X"}]}
    plan = parse_plan_from_args(args)
    assert plan.reasoning == ""


def test_parse_plan_from_args_backward_compat():
    """Old format with plan_json string still works."""
    args = {"plan_json": '{"subtasks": [{"agent": "APIAgent", "task": "GET /x"}]}'}
    plan = parse_plan_from_args(args)
    assert plan.subtasks[0].agent == "APIAgent"


# ─── run_agent_plan_phase ────────────────────────────────────────────────────

def _config():
    return AgentConfig(
        name="OrchestratorAgent",
        system_prompt="You are a test orchestrator.",
        llm=OllamaConfig(),
        tools=["submit_plan", "delegate_to"],
        max_iterations=5,
    )


@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_plan_phase_captures_submitted_plan(mock_make_llm_wt):
    plan_json = (
        '{"subtasks": [{"agent": "WebSearchAgent", "task": "Search X"}]}'
    )
    tc = {"id": "1", "name": "submit_plan", "args": {"plan_json": plan_json}}
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="", tool_calls=[tc])
    mock_make_llm_wt.return_value = mock_llm

    plan, result = run_agent_plan_phase("test task", _config())
    assert plan is not None
    assert plan.subtasks[0].agent == "WebSearchAgent"
    assert any(e.action == "plan_submitted" for e in result.audit_trail.entries)


@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_plan_phase_captures_structured_submission(mock_make_llm_wt):
    """Qwen3 calls submit_plan with subtasks+reasoning as separate args."""
    tc = {
        "id": "1",
        "name": "submit_plan",
        "args": {
            "subtasks": [{"agent": "WebSearchAgent", "task": "Search X"}],
            "reasoning": "Need to find X",
        },
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="", tool_calls=[tc])
    mock_make_llm_wt.return_value = mock_llm

    plan, result = run_agent_plan_phase("test task", _config())
    assert plan is not None
    assert plan.subtasks[0].agent == "WebSearchAgent"
    assert plan.reasoning == "Need to find X"
    assert any(e.action == "plan_submitted" for e in result.audit_trail.entries)


@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_plan_phase_returns_none_when_no_submission(mock_make_llm_wt):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="I'll do it directly", tool_calls=[])
    mock_make_llm_wt.return_value = mock_llm

    plan, result = run_agent_plan_phase("test task", _config())
    assert plan is None
    assert result.success
    assert all(e.action != "plan_submitted" for e in result.audit_trail.entries)


@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_plan_phase_rejects_invalid_plan_json(mock_make_llm_wt):
    tc = {"id": "1", "name": "submit_plan", "args": {"plan_json": "not json"}}
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="", tool_calls=[tc])
    mock_make_llm_wt.return_value = mock_llm

    plan, result = run_agent_plan_phase("test task", _config())
    assert plan is None
    assert not result.success
    assert "Invalid plan" in result.error


# ─── run_agent_execute_phase ─────────────────────────────────────────────────

@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_execute_phase_logs_approval_and_runs(mock_make_llm_wt):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="All done.", tool_calls=[])
    mock_make_llm_wt.return_value = mock_llm

    plan = Plan(subtasks=[Subtask(agent="WebSearchAgent", task="Search X")])
    result = run_agent_execute_phase("test task", plan, _config())
    assert result.success
    assert result.output == "All done."
    actions = [e.action for e in result.audit_trail.entries]
    assert "plan_approved" in actions


# ─── run_interactive ─────────────────────────────────────────────────────────

@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_run_interactive_approved_executes_plan(mock_make_llm_wt):
    plan_json = (
        '{"subtasks": [{"agent": "WebSearchAgent", "task": "Search X"}]}'
    )
    tc = {"id": "1", "name": "submit_plan", "args": {"plan_json": plan_json}}

    call_count = {"n": 0}

    def llm_side_effect(_msgs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return AIMessage(content="", tool_calls=[tc])
        return AIMessage(content="Final answer.", tool_calls=[])

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = llm_side_effect
    mock_make_llm_wt.return_value = mock_llm

    decisions = []
    def callback(plan: Plan) -> ApprovalDecision:
        decisions.append(plan)
        return ApprovalDecision(approved=True, feedback="ok")

    import agent_smith
    result = agent_smith.run_interactive("do something", callback)

    assert len(decisions) == 1
    assert decisions[0].subtasks[0].agent == "WebSearchAgent"
    assert result.success
    actions = [e.action for e in result.audit_trail.entries]
    assert "plan_submitted" in actions
    assert "plan_approved" in actions


@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_run_interactive_rejected_aborts(mock_make_llm_wt):
    plan_json = (
        '{"subtasks": [{"agent": "WebSearchAgent", "task": "Search X"}]}'
    )
    tc = {"id": "1", "name": "submit_plan", "args": {"plan_json": plan_json}}
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="", tool_calls=[tc])
    mock_make_llm_wt.return_value = mock_llm

    def callback(plan: Plan) -> ApprovalDecision:
        return ApprovalDecision(approved=False, feedback="too risky")

    import agent_smith
    result = agent_smith.run_interactive("do something", callback)

    assert not result.success
    assert "Plan rejected by user" in result.error
    assert "too risky" in result.error
    actions = [e.action for e in result.audit_trail.entries]
    assert "plan_rejected" in actions


@patch("agent_smith.agents.runner.make_llm_with_tools")
def test_run_interactive_no_plan_submitted(mock_make_llm_wt):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="I'll just do it.", tool_calls=[])
    mock_make_llm_wt.return_value = mock_llm

    callback_called = {"n": 0}
    def callback(plan: Plan) -> ApprovalDecision:
        callback_called["n"] += 1
        return ApprovalDecision(approved=True)

    import agent_smith
    result = agent_smith.run_interactive("task", callback)

    assert callback_called["n"] == 0
    assert result.success
    assert result.output == "I'll just do it."


# ─── Fallback parser for submit_plan ─────────────────────────────────────────

def test_parse_submit_plan_function_positional():
    """Qwen3 calls submit_plan as Python-style with positional JSON arg."""
    text = 'submit_plan(\'{"subtasks": [{"agent": "WebSearchAgent", "task": "X"}]}\')'
    calls = _parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "submit_plan"
    assert "plan_json" in calls[0]["args"]
    plan = Plan.from_json(calls[0]["args"]["plan_json"])
    assert plan.subtasks[0].agent == "WebSearchAgent"


def test_parse_submit_plan_function_kwarg():
    """Qwen3 calls submit_plan with plan_json= kwarg syntax."""
    text = 'submit_plan(plan_json=\'{"subtasks": [{"agent": "APIAgent", "task": "GET /x"}]}\')'
    calls = _parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "submit_plan"
    assert "plan_json" in calls[0]["args"]
    plan = Plan.from_json(calls[0]["args"]["plan_json"])
    assert plan.subtasks[0].agent == "APIAgent"
