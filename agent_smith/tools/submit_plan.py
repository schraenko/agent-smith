"""
Plan submission tool for the OrchestratorAgent (Human-in-the-Loop).
Registered separately to avoid circular imports.
"""

import json

from langchain_core.tools import tool

from agent_smith.approval import VALID_AGENTS, Plan, Subtask


PLAN_SUBMITTED_MARKER = "PLAN_SUBMITTED"


def _coerce_subtasks(value) -> list[Subtask]:
    """Coerce LLM-supplied subtasks into a list of Subtask objects.

    Handles two common shapes:
    - list of dicts: [{"agent": "X", "task": "Y"}, ...]
    - JSON string: '[{"agent": "X", "task": "Y"}, ...]'
    """
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list):
        raise ValueError("subtasks must be a list")
    if not value:
        raise ValueError("subtasks must be non-empty")
    out: list[Subtask] = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"subtasks[{i}] must be an object")

        agent = item.get("agent", "").strip()
        task = item.get("task", "").strip()
        if agent not in VALID_AGENTS:
            raise ValueError(
                f"subtasks[{i}] has invalid agent '{agent}'. "
                f"Choose from: {list(VALID_AGENTS)}"
            )
        if not task:
            raise ValueError(f"subtasks[{i}] has empty 'task'")
        out.append(Subtask(agent=agent, task=task))
    return out


def parse_plan_from_args(args: dict) -> Plan:
    """Parse a Plan object from a submit_plan tool call's args.

    Accepts two formats:
    1. {"plan_json": "<json string>"} — backward compat with the old single-arg form
    2. {"subtasks": [...], "reasoning": "..."} — Qwen3's preferred structured form
    """
    if "plan_json" in args:
        return Plan.from_json(args["plan_json"])

    if "subtasks" in args:
        subtasks = _coerce_subtasks(args["subtasks"])
        return Plan(subtasks=subtasks, reasoning=str(args.get("reasoning", "")).strip())

    raise KeyError("plan_json")


@tool
def submit_plan(
    subtasks: list[dict],
    reasoning: str = "",
) -> str:
    """
    Submit a structured delegation plan for user approval.

    Args:
        subtasks: A list of subtask objects, each with:
                  - "agent": one of WebSearchAgent, CodeExecutionAgent,
                             DocumentAgent, APIAgent, DataAgent
                  - "task": natural language task description
        reasoning: Optional explanation of why this plan solves the task.

    Example:
        submit_plan(
            reasoning="Need to search then code",
            subtasks=[
                {"agent": "WebSearchAgent", "task": "Find X"},
                {"agent": "CodeExecutionAgent", "task": "Compute Y"}
            ]
        )

    After submission the system will pause and ask the user to approve or
    reject the plan. Only after approval may the `task` tool be called.
    """
    Plan(subtasks=_coerce_subtasks(subtasks), reasoning=reasoning)
    return PLAN_SUBMITTED_MARKER
