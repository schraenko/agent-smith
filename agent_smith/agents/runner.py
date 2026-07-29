"""
Core agent runner.
The agentic loop is a plain function — no Agent class, no inheritance.
LangChain is used only for the LLM call and message types.
"""

import json
import logging
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agent_smith.approval import Plan
from agent_smith.audit import AuditTrail, set_audit_context, reset_audit_context
from agent_smith.llm import OllamaConfig, make_llm, make_llm_with_tools
from agent_smith.tools.builtins import TOOL_MAP, get_tools
from agent_smith.tools.submit_plan import PLAN_SUBMITTED_MARKER, parse_plan_from_args
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


def _trim(messages: list, max_messages: int) -> list:
    """Sliding window — always keep the system message if present."""
    if not messages:
        return []
    if isinstance(messages[0], SystemMessage):
        return [messages[0]] + messages[1:][-max(0, max_messages - 1):]
    return messages[-max_messages:]


def _execute_tool_calls(tool_calls: list, audit_trail: AuditTrail | None = None, level: int = 0, agent_name: str = "") -> list[ToolMessage]:
    """Execute all tool calls and return ToolMessages."""
    results = []
    for call in tool_calls:
        name = call["name"]
        args = call["args"]
        tool_fn = TOOL_MAP.get(name)
        if tool_fn is None:
            content = json.dumps({"error": f"Unknown tool: {name}"})
            if audit_trail:
                audit_trail.log(level=level, agent=agent_name, action="tool_call", tool_name=name, args=args, success=False)
                audit_trail.log(level=level, agent=agent_name, action="tool_result", tool_name=name, result=content, success=False)
        else:
            if audit_trail:
                audit_trail.log(level=level, agent=agent_name, action="tool_call", tool_name=name, args=args)
            try:
                tokens = set_audit_context(audit_trail, level) if audit_trail else None
                try:
                    content = json.dumps(tool_fn.invoke(args))
                finally:
                    reset_audit_context(tokens) if tokens else None
                logger.debug("Tool %s -> ok", name)
                if audit_trail:
                    audit_trail.log(level=level, agent=agent_name, action="tool_result", tool_name=name, result=content, success=True)
            except Exception as e:
                content = json.dumps({"error": str(e)})
                logger.error("Tool %s failed: %s", name, e)
                if audit_trail:
                    audit_trail.log(level=level, agent=agent_name, action="tool_result", tool_name=name, result=content, success=False)
        results.append(ToolMessage(content=content, tool_call_id=call["id"]))
    return results


def run_agent(task: str, config: AgentConfig, audit_trail: AuditTrail | None = None, level: int = 0) -> AgentResult:
    """
    Run the agentic loop for a single agent.

    Loop:
      1. Call LLM with current messages
      2. If tool calls -> execute -> append results -> repeat
      3. If text response -> done
    """
    if audit_trail is None:
        audit_trail = AuditTrail()

    tools = get_tools(config.tools) if config.tools is not None else []
    llm = make_llm_with_tools(config.llm, tools) if tools else make_llm(config.llm)

    messages = [
        SystemMessage(content=config.system_prompt),
        HumanMessage(content=task),
    ]
    intermediate_steps = []

    for iteration in range(config.max_iterations):
        logger.info("[%s] iteration %d/%d", config.name, iteration + 1, config.max_iterations)
        audit_trail.log(level=level, agent=config.name, action="llm_call", iteration=iteration + 1)

        windowed = _trim(messages, config.context_window)

        try:
            response: AIMessage = llm.invoke(windowed)
        except Exception as e:
            logger.error("[%s] LLM call failed: %s", config.name, e)
            return AgentResult.fail(str(e), audit_trail=audit_trail)

        messages.append(response)

        tool_calls = response.tool_calls

        if not tool_calls:
            logger.info("[%s] done after %d iterations", config.name, iteration + 1)
            return AgentResult.ok(output=response.content, steps=intermediate_steps, audit_trail=audit_trail)

        tool_messages = _execute_tool_calls(tool_calls, audit_trail=audit_trail, level=level, agent_name=config.name)
        intermediate_steps.extend([
            {"tool": tc["name"], "args": tc["args"]}
            for tc in tool_calls
        ])
        messages.extend(tool_messages)

    logger.warning("[%s] reached max iterations", config.name)
    return AgentResult.fail(f"Max iterations ({config.max_iterations}) reached without a final answer.", audit_trail=audit_trail)


def run_agent_plan_phase(
    task: str,
    config: AgentConfig,
    audit_trail: AuditTrail | None = None,
    level: int = 0,
) -> tuple[Plan | None, AgentResult]:
    """
    Phase 1 of the human-in-the-loop flow.

    Runs the agentic loop until `submit_plan` is called, then stops
    immediately and returns the captured plan. The plan is recovered from
    the `submit_plan` tool call's `plan_json` argument. Only `submit_plan`
    is available as a tool in this phase.
    """
    if audit_trail is None:
        audit_trail = AuditTrail()

    from langchain_core.messages import HumanMessage, SystemMessage

    tools = get_tools(["submit_plan"])
    llm = make_llm_with_tools(config.llm, tools)

    messages = [
        SystemMessage(content=config.system_prompt),
        HumanMessage(content=task),
    ]
    intermediate_steps: list = []

    for iteration in range(config.max_iterations):
        logger.info("[%s] plan-phase iteration %d/%d", config.name, iteration + 1, config.max_iterations)
        audit_trail.log(level=level, agent=config.name, action="llm_call", iteration=iteration + 1)

        windowed = _trim(messages, config.context_window)
        try:
            response: AIMessage = llm.invoke(windowed)
        except Exception as e:
            logger.error("[%s] LLM call failed: %s", config.name, e)
            return None, AgentResult.fail(str(e), audit_trail=audit_trail)

        messages.append(response)

        tool_calls = response.tool_calls

        if not tool_calls:
            return None, AgentResult.ok(
                output=response.content, steps=intermediate_steps, audit_trail=audit_trail
            )

        plan_call = next((tc for tc in tool_calls if tc["name"] == "submit_plan"), None)
        if plan_call is not None:
            try:
                plan = parse_plan_from_args(plan_call["args"])
            except (ValueError, KeyError, TypeError) as e:
                logger.error(
                    "[%s] invalid plan submitted: %s (args keys: %s)",
                    config.name, e, list(plan_call["args"].keys()),
                )
                return None, AgentResult.fail(
                    f"Invalid plan JSON from submit_plan: {e}. "
                    f"Received args keys: {list(plan_call['args'].keys())}",
                    audit_trail=audit_trail,
                )

        tool_messages = _execute_tool_calls(
            tool_calls, audit_trail=audit_trail, level=level, agent_name=config.name
        )
        intermediate_steps.extend(
            {"tool": tc["name"], "args": tc["args"]} for tc in tool_calls
        )
        messages.extend(tool_messages)

        if plan_call is not None:
            assert plan is not None
            audit_trail.log(
                level=level,
                agent=config.name,
                action="plan_submitted",
                task=plan.to_json(),
            )
            return plan, AgentResult.ok(
                output=plan.to_json(), steps=intermediate_steps, audit_trail=audit_trail
            )

    logger.warning("[%s] plan-phase reached max iterations without submit_plan", config.name)
    return None, AgentResult.fail(
        f"Plan phase reached max iterations ({config.max_iterations}) without a submitted plan.",
        audit_trail=audit_trail,
    )


def _mcp_fallback_agent(mcp_server: str, tool_name: str) -> str | None:
    """Map an MCP server+tool to a fallback agent, or None if no fallback exists."""
    FALLBACK_MAP: dict[str, dict[str, str]] = {
        "osm_router": {
            "get_route_distance": "WebSearchAgent",
            "get_route_info": "WebSearchAgent",
        },
        "weather": {
            "get_weather": "WebSearchAgent",
            "get_forecast": "WebSearchAgent",
        },
    }
    return FALLBACK_MAP.get(mcp_server, {}).get(tool_name)


def _mcp_fallback_task(tool_name: str, args: dict) -> str:
    """Build a natural-language task for the fallback agent from MCP args."""
    if tool_name == "get_route_distance":
        return (
            f"Finde die Entfernung von {args.get('start', '?')} "
            f"nach {args.get('end', '?')} und gib sie in Kilometern an."
        )
    if tool_name == "get_route_info":
        return (
            f"Finde eine Route von {args.get('start', '?')} "
            f"nach {args.get('end', '?')} mit detaillierten Schritten."
        )
    if tool_name == "get_weather":
        loc = args.get("location", args.get("plz", "?"))
        return f"Wie ist das aktuelle Wetter in {loc}?"
    if tool_name == "get_forecast":
        loc = args.get("location", "?")
        days = args.get("days", 3)
        return f"Wie ist die Wettervorhersage für {loc} für die nächsten {days} Tage?"
    return f"{tool_name}({args})"


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
    - MCP subtasks are dispatched directly to the named server tool.
    - If an MCP subtask fails, it falls back to a standard agent (WebSearchAgent).
    - Agent subtasks are dispatched via `delegate_to`.
    - A final LLM call combines the per-subtask results into a natural-language answer.
    """
    if audit_trail is None:
        audit_trail = AuditTrail()

    audit_trail.log(
        level=level,
        agent=config.name,
        action="plan_approved",
    )

    from agent_smith.mcp_clients import call_mcp_tool
    from langchain_core.messages import HumanMessage, SystemMessage

    subtask_results: list[str] = []
    has_agent_subtask = False

    for i, subtask in enumerate(plan.subtasks, 1):
        if subtask.is_mcp:
            audit_trail.log(
                level=level,
                agent=subtask.mcp_server,
                action="mcp_call",
                tool_name=subtask.tool_name,
                args=subtask.args,
            )
            result = call_mcp_tool(subtask.mcp_server, subtask.tool_name, subtask.args)
            success = not result.startswith("MCP_ERROR")

            if not success:
                fallback_agent = _mcp_fallback_agent(subtask.mcp_server, subtask.tool_name)
                if fallback_agent:
                    audit_trail.log(
                        level=level,
                        agent=config.name,
                        action="mcp_fallback",
                        tool_name=subtask.tool_name,
                        result=f"MCP failed, falling back to {fallback_agent}",
                        success=False,
                    )
                    fallback_task = _mcp_fallback_task(subtask.tool_name, subtask.args)
                    fallback_result = _delegate_sync(fallback_agent, fallback_task, audit_trail, level)
                    if "MCP_ERROR" not in fallback_result and "Agent failed" not in fallback_result:
                        result = fallback_result
                        success = True
                        audit_trail.log(
                            level=level,
                            agent=config.name,
                            action="mcp_fallback_result",
                            tool_name=subtask.tool_name,
                            result="Fallback succeeded",
                            success=True,
                        )

            audit_trail.log(
                level=level,
                agent=subtask.mcp_server,
                action="mcp_call_result",
                tool_name=subtask.tool_name,
                result=result,
                success=success,
            )
            subtask_results.append(f"Subtask {i} [MCP:{subtask.mcp_server}.{subtask.tool_name}]:\n{result}")
        else:
            has_agent_subtask = True
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

    if not has_agent_subtask and all(s.is_mcp for s in plan.subtasks):
        return AgentResult.ok(
            output="\n\n".join(subtask_results),
            audit_trail=audit_trail,
        )

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
