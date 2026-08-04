"""
Core agent runner.

The agentic loop is powered by `deepagents.create_deep_agent` (built on
LangChain + LangGraph). LangChain/LangGraph types are confined to this module
and `llm.py`; the rest of the codebase keeps using plain domain types.

Human-in-the-loop uses a direct bind_tools loop for the plan phase (with
automatic retry if the LLM skips submit_plan) and a deterministic execute
phase for agent subtask delegation.
"""

import logging
from dataclasses import dataclass, field

from deepagents import create_deep_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agent_smith.approval import Plan
from agent_smith.audit import AuditTrail
from agent_smith.llm import OllamaConfig, make_llm
from agent_smith.tools.builtins import get_tools
from agent_smith.tools.submit_plan import parse_plan_from_args
from agent_smith.types import AgentResult

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10


@dataclass(frozen=True)
class AgentConfig:
    name: str
    system_prompt: str
    llm: OllamaConfig = field(default_factory=OllamaConfig)
    tools: list[str] | None = None
    max_iterations: int = MAX_ITERATIONS
    context_window: int = 20
    subagents: list = field(default_factory=list)


def _trim(messages: list, max_messages: int) -> list:
    """Sliding window — always keep the system message if present."""
    if not messages:
        return []
    if isinstance(messages[0], SystemMessage):
        return [messages[0]] + messages[1:][-max(0, max_messages - 1):]
    return messages[-max_messages:]


def _build_deep_agent(config: AgentConfig):
    """Construct a DeepAgents compiled graph for the given AgentConfig.

    Kept as a thin wrapper so tests can patch `create_deep_agent` at module
    level without touching config wiring.
    """
    llm = make_llm(config.llm)
    tool_objs = get_tools(config.tools) if config.tools is not None else []
    return create_deep_agent(
        model=llm,
        tools=tool_objs,
        system_prompt=config.system_prompt,
        subagents=config.subagents or None,
    )


def _extract_final_output(messages: list) -> str:
    """Return the content of the last non-empty AIMessage, or '' if none."""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


def _collect_tool_steps(messages: list) -> list[dict]:
    """Collect intermediate ToolMessage steps for AgentResult.intermediate_steps."""
    steps = []
    for m in messages:
        if isinstance(m, ToolMessage):
            steps.append({"tool": getattr(m, "name", "?"), "content": m.content})
    return steps


def run_agent(task: str, config: AgentConfig, audit_trail: AuditTrail | None = None, level: int = 0) -> AgentResult:
    """
    Run the agentic loop for a single agent via DeepAgents.

    DeepAgents handles the model loop, tool binding, context management, and
    built-in filesystem/subagent tools. We map `max_iterations` to a LangGraph
    recursion limit and record the final AIMessage content as the result.

    For agents with `subagents` configured (e.g. the orchestrator), retries
    if the LLM answers directly instead of calling the `task` tool (known
    issue with gemma4:12b — `tool_choice=None` in LangChain's `create_agent`
    makes tool use optional). At most 3 outer attempts.
    """
    if audit_trail is None:
        audit_trail = AuditTrail()

    has_subagents = bool(config.subagents)
    max_outer_attempts = 3 if has_subagents else 1
    recursion_limit = max(8, config.max_iterations * 2)
    invoke_config = {"recursion_limit": recursion_limit}

    try:
        agent = _build_deep_agent(config)
    except Exception as e:
        logger.error("[%s] build deep_agent failed: %s", config.name, e)
        return AgentResult.fail(str(e), audit_trail=audit_trail)

    messages_input: list[dict] = [{"role": "user", "content": task}]
    last_messages: list = []

    for attempt in range(max_outer_attempts):
        audit_trail.log(
            level=level, agent=config.name,
            action="llm_call", iteration=attempt + 1,
        )

        try:
            result = agent.invoke(
                {"messages": messages_input},
                config=invoke_config,
            )
        except Exception as e:
            logger.error("[%s] deep_agent invoke failed (attempt %d): %s",
                         config.name, attempt + 1, e)
            return AgentResult.fail(str(e), audit_trail=audit_trail)

        last_messages = result.get("messages", []) if isinstance(result, dict) else []

        if not has_subagents or _has_task_delegation(last_messages) or attempt == max_outer_attempts - 1:
            break

        logger.info(
            "[%s] attempt %d — no task delegation, retrying",
            config.name, attempt + 1,
        )
        messages_input = _messages_to_input_dicts(last_messages)
        messages_input.append({
            "role": "user",
            "content": (
                "You must delegate this task to a specialist agent using "
                "the `task` tool. Do not answer the task directly."
            ),
        })

    output = _extract_final_output(last_messages)
    steps = _collect_tool_steps(last_messages)

    logger.info("[%s] deep_agent done — %d messages", config.name, len(last_messages))
    return AgentResult.ok(output=output, steps=steps, audit_trail=audit_trail)


def _has_task_delegation(messages: list) -> bool:
    """Return True if the LLM called the `task` tool (i.e. delegated to a SubAgent)."""
    for m in messages:
        if isinstance(m, AIMessage):
            for tc in (getattr(m, "tool_calls", None) or []):
                if tc.get("name") == "task":
                    return True
    return False


def _messages_to_input_dicts(messages: list) -> list[dict]:
    """Convert graph-state messages back to dicts for the next graph invoke."""
    out: list[dict] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            out.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            if m.content:
                out.append({"role": "assistant", "content": m.content})
        elif isinstance(m, ToolMessage):
            out.append({
                "role": "tool",
                "content": m.content,
                "tool_call_id": getattr(m, "tool_call_id", ""),
            })
    return out


def run_agent_plan_phase(
    task: str,
    config: AgentConfig,
    audit_trail: AuditTrail | None = None,
    level: int = 0,
) -> tuple[Plan | None, AgentResult]:
    """
    Phase 1 of the human-in-the-loop flow.

    Uses a direct model loop with bind_tools to force the LLM to call
    submit_plan. Retries if the LLM answers directly instead of using
    the tool (known issue with gemma4:12b — tool_choice=None in
    LangGraph's create_agent makes tool use optional).
    """
    if audit_trail is None:
        audit_trail = AuditTrail()

    llm = make_llm(config.llm)
    tool_objs = get_tools(["submit_plan"])
    bound_llm = llm.bind_tools(tool_objs)

    messages: list = [
        SystemMessage(content=config.system_prompt),
        HumanMessage(content=task),
    ]

    max_attempts = max(3, config.max_iterations)

    for attempt in range(max_attempts):
        audit_trail.log(
            level=level, agent=config.name,
            action="llm_call", iteration=attempt + 1,
        )

        try:
            response = bound_llm.invoke(messages)
        except Exception as e:
            logger.error("[%s] plan-phase invoke failed (attempt %d): %s",
                         config.name, attempt + 1, e)
            return None, AgentResult.fail(str(e), audit_trail=audit_trail)

        messages.append(response)

        if getattr(response, "tool_calls", None):
            for tc in response.tool_calls:
                if tc["name"] == "submit_plan":
                    try:
                        plan = parse_plan_from_args(tc["args"])
                    except (ValueError, KeyError, TypeError) as e:
                        logger.error("[%s] invalid plan submitted: %s",
                                     config.name, e)
                        return None, AgentResult.fail(
                            f"Invalid plan from submit_plan: {e}",
                            audit_trail=audit_trail,
                        )
                    audit_trail.log(
                        level=level, agent=config.name,
                        action="plan_submitted", task=plan.to_json(),
                    )
                    return plan, AgentResult.ok(
                        output=plan.to_json(), audit_trail=audit_trail,
                    )

        logger.info(
            "[%s] plan-phase attempt %d — no submit_plan, retrying",
            config.name, attempt + 1,
        )
        messages.append(HumanMessage(
            content="You must call submit_plan with a structured list of "
                    "subtasks. Do NOT answer the task directly."
        ))

    logger.warning(
        "[%s] plan-phase ended without submit_plan after %d attempts",
        config.name, max_attempts,
    )
    return None, AgentResult.ok(
        output=_extract_final_output(messages), audit_trail=audit_trail,
    )


def run_agent_execute_phase(
    task: str,
    plan: Plan,
    config: AgentConfig,
    audit_trail: AuditTrail | None = None,
    level: int = 0,
) -> AgentResult:
    """
    Phase 2 of the human-in-the-loop flow.

    Executes the approved plan deterministically:
    - Agent subtasks are dispatched via `_delegate_sync`.
    - A final LLM call combines the per-subtask results into a natural-language answer.
    """
    if audit_trail is None:
        audit_trail = AuditTrail()

    audit_trail.log(
        level=level,
        agent=config.name,
        action="plan_approved",
    )

    subtask_results: list[str] = []

    for i, subtask in enumerate(plan.subtasks, 1):
        audit_trail.log(
            level=level,
            agent=subtask.agent,
            action="delegate",
            task=subtask.task,
        )
        agent_result = _delegate_sync(subtask.agent, subtask.task, audit_trail, level)
        audit_trail.log(
            level=level,
            agent=subtask.agent,
            action="delegate_result",
            result=agent_result,
            success=True,
        )
        subtask_results.append(f"Subtask {i} [{subtask.agent}]:\n{agent_result}")

    if not subtask_results:
        return AgentResult.ok(output="", audit_trail=audit_trail)

    combine_prompt = (
        f"Original task: {task}\n\n"
        f"The following plan has been executed. Combine the per-subtask results "
        f"into a single coherent natural-language answer for the user.\n\n"
        + "\n\n".join(subtask_results)
    )
    try:
        llm = make_llm(config.llm)
        final = llm.invoke(
            [
                SystemMessage(content="You are a helpful assistant. Summarize the results into a final answer."),
                HumanMessage(content=combine_prompt),
            ]
        )
        return AgentResult.ok(
            output=str(final.content),
            audit_trail=audit_trail,
        )
    except Exception as e:
        logger.error("[%s] combine phase failed: %s", config.name, e)
        return AgentResult.ok(
            output="\n\n".join(subtask_results),
            audit_trail=audit_trail,
        )


def _delegate_sync(agent: str, task: str, audit_trail: AuditTrail, level: int) -> str:
    """Direct agent delegation, bypassing the orchestrator's agentic loop."""
    from agent_smith.agents.builtins import (
        run_api, run_code, run_data, run_document, run_web_search,
    )
    dispatch = {
        "WebSearchAgent": run_web_search,
        "CodeExecutionAgent": run_code,
        "DocumentAgent": run_document,
        "APIAgent": run_api,
        "DataAgent": run_data,
    }
    runner = dispatch.get(agent)
    if runner is None:
        return f"Unknown agent: {agent}. Choose from: {list(dispatch.keys())}"
    result = runner(task, audit_trail=audit_trail, level=level + 1)
    return result.output if result.success else f"Agent failed: {result.error}"
