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


def _parse_tool_calls_from_text(text: str) -> list:
    """
    Parse tool calls from text when Ollama outputs them as raw text
    instead of using the structured tool_calls format.
    
    Handles formats like:
    - <tool_call>{"name": "tool_name", "args": {...}}</tool_call>
    - {"name": "tool_name", "args": {...}}
    - tool_name("arg1", "arg2")  (Python function call style)
    - tool_name(key="value", key2="value2")
    - Multiple tool calls in sequence
    """
    import re
    tool_calls = []
    
    # Try to find tool_call XML tags first
    xml_pattern = r'<tool_call>(.*?)</tool_call>'
    xml_matches = re.findall(xml_pattern, text, re.DOTALL)
    
    if xml_matches:
        for match in xml_matches:
            try:
                call_data = json.loads(match.strip())
                if "name" in call_data and "args" in call_data:
                    tool_calls.append({
                        "name": call_data["name"],
                        "args": call_data.get("args", {}),
                        "id": f"parsed_{len(tool_calls)}"
                    })
            except json.JSONDecodeError:
                continue
        return tool_calls
    
    # Try to find JSON objects that look like tool calls
    # This handles nested JSON by looking for the pattern with proper bracket matching
    try:
        # Try to parse the entire text as JSON first
        data = json.loads(text)
        if isinstance(data, dict) and "name" in data and "args" in data:
            tool_calls.append({
                "name": data["name"],
                "args": data.get("args", {}),
                "id": f"parsed_{len(tool_calls)}"
            })
            return tool_calls
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON objects by looking for balanced braces
    i = 0
    while i < len(text):
        if text[i] == '{':
            # Find matching closing brace
            brace_count = 1
            j = i + 1
            while j < len(text) and brace_count > 0:
                if text[j] == '{':
                    brace_count += 1
                elif text[j] == '}':
                    brace_count -= 1
                j += 1
            
            if brace_count == 0:
                json_str = text[i:j]
                try:
                    data = json.loads(json_str)
                    if isinstance(data, dict) and "name" in data and "args" in data:
                        tool_calls.append({
                            "name": data["name"],
                            "args": data.get("args", {}),
                            "id": f"parsed_{len(tool_calls)}"
                        })
                except json.JSONDecodeError:
                    pass
                i = j
            else:
                i += 1
        else:
            i += 1
    
    if tool_calls:
        return tool_calls
    
    # Try to find Python-style function calls: tool_name(args)
    # Pattern: word characters followed by parentheses with content
    func_pattern = r'(\w+)\s*\(([^)]*)\)'
    func_matches = re.findall(func_pattern, text)
    
    for func_name, args_str in func_matches:
        # Skip common non-tool functions
        if func_name.lower() in ('print', 'len', 'range', 'str', 'int', 'float', 'dict', 'list', 'set', 'tuple'):
            continue
        
        # Check if this function name exists in TOOL_MAP
        if func_name not in TOOL_MAP:
            # Try case-insensitive match
            for tool_name in TOOL_MAP:
                if tool_name.lower() == func_name.lower():
                    func_name = tool_name
                    break
            else:
                continue
        
        # Parse the arguments
        args = {}
        args_str = args_str.strip()

        if args_str:
            # Try to parse as positional arguments
            # Simple heuristic: split by comma, handle quoted strings
            try:
                # Remove outer quotes if present
                if args_str.startswith('"') and args_str.endswith('"'):
                    args_str = args_str[1:-1]
                elif args_str.startswith("'") and args_str.endswith("'"):
                    args_str = args_str[1:-1]

                # Special case for submit_plan: the arg is a JSON object
                # that contains commas internally. Try to parse the whole
                # arg_str as JSON first; if it works, the entire string
                # is the plan_json payload.
                if func_name == "submit_plan":
                    try:
                        json.loads(args_str)
                        args = {"plan_json": args_str}
                        tool_calls.append({
                            "name": func_name,
                            "args": args,
                            "id": f"parsed_{len(tool_calls)}",
                        })
                        continue
                    except json.JSONDecodeError:
                        pass  # fall through to generic handling

                # Try to parse as a single string argument (common for delegate_to)
                if ',' in args_str:
                    # Multiple arguments - try to parse as key=value or positional
                    parts = []
                    current = ""
                    in_quotes = False
                    quote_char = None

                    for char in args_str:
                        if char in ('"', "'") and not in_quotes:
                            in_quotes = True
                            quote_char = char
                        elif char == quote_char and in_quotes:
                            in_quotes = False
                            quote_char = None
                        elif char == ',' and not in_quotes:
                            parts.append(current.strip())
                            current = ""
                            continue
                        current += char
                    parts.append(current.strip())

                    # Check for kwarg syntax: plan_json="..." or plan_json='...'
                    kwarg_args = {}
                    positional_parts = []
                    for part in parts:
                        if "=" in part and not part.startswith("="):
                            k, _, v = part.partition("=")
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            kwarg_args[k] = v
                        else:
                            positional_parts.append(part.strip().strip('"').strip("'"))

                    if kwarg_args:
                        args = kwarg_args
                    else:
                        # Map positional args based on tool signature
                        if func_name == "delegate_to" and len(positional_parts) >= 2:
                            args = {"agent": positional_parts[0], "task": positional_parts[1]}
                        else:
                            # Generic: try to map to arg1, arg2, etc.
                            for idx, part in enumerate(positional_parts):
                                args[f"arg{idx+1}"] = part
                else:
                    # Single argument
                    if func_name == "delegate_to":
                        # Special handling for delegate_to with single arg
                        args = {"agent": "WebSearchAgent", "task": args_str.strip('"\'')}
                    else:
                        args = {"query": args_str.strip('"\'')}
            except Exception:
                continue
        
        tool_calls.append({
            "name": func_name,
            "args": args,
            "id": f"parsed_{len(tool_calls)}"
        })
    
    return tool_calls


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

        # Check for tool calls in structured format first
        tool_calls = response.tool_calls

        # If no structured tool calls, try to parse from text content
        if not tool_calls and response.content:
            parsed_calls = _parse_tool_calls_from_text(response.content)
            if parsed_calls:
                tool_calls = parsed_calls
                logger.info("[%s] parsed %d tool calls from text", config.name, len(parsed_calls))

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
        if not tool_calls and response.content:
            parsed_calls = _parse_tool_calls_from_text(response.content)
            if parsed_calls:
                tool_calls = parsed_calls

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


def run_agent_execute_phase(
    task: str,
    plan: Plan,
    config: AgentConfig,
    audit_trail: AuditTrail | None = None,
    level: int = 0,
) -> AgentResult:
    """
    Phase 2 of the human-in-the-loop flow.

    Runs the agentic loop with `delegate_to` as the only available tool,
    asking the agent to execute the approved plan subtasks in order.
    """
    if audit_trail is None:
        audit_trail = AuditTrail()

    audit_trail.log(
        level=level,
        agent=config.name,
        action="plan_approved",
    )

    subtask_lines = "\n".join(
        f"  {i}. [{s.agent}] {s.task}"
        for i, s in enumerate(plan.subtasks, 1)
    )
    follow_up = (
        f"The user approved the following plan. Execute each subtask in order "
        f"by calling `delegate_to` for each one. After all subtasks finish, "
        f"write a final natural-language answer that combines the results.\n\n"
        f"Approved plan:\n{subtask_lines}\n\n"
        f"Original task: {task}"
    )

    execute_config = AgentConfig(
        name=config.name,
        system_prompt=config.system_prompt,
        llm=config.llm,
        tools=["delegate_to"],
        max_iterations=config.max_iterations,
        context_window=config.context_window,
    )

    return run_agent(follow_up, execute_config, audit_trail=audit_trail, level=level)
