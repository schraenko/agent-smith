"""
Core agent runner.
The agentic loop is a plain function — no Agent class, no inheritance.
LangChain is used only for the LLM call and message types.
"""

import json
import logging
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agent_smith_lc.llm import OllamaConfig, make_llm, make_llm_with_tools
from agent_smith_lc.tools.builtins import TOOL_MAP, get_tools
from agent_smith_lc.types import AgentResult

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


def _execute_tool_calls(tool_calls: list) -> list[ToolMessage]:
    """Execute all tool calls and return ToolMessages."""
    results = []
    for call in tool_calls:
        name = call["name"]
        args = call["args"]
        tool_fn = TOOL_MAP.get(name)
        if tool_fn is None:
            content = json.dumps({"error": f"Unknown tool: {name}"})
        else:
            try:
                content = json.dumps(tool_fn.invoke(args))
                logger.debug("Tool %s → ok", name)
            except Exception as e:
                content = json.dumps({"error": str(e)})
                logger.error("Tool %s failed: %s", name, e)
        results.append(ToolMessage(content=content, tool_call_id=call["id"]))
    return results


def run_agent(task: str, config: AgentConfig) -> AgentResult:
    """
    Run the agentic loop for a single agent.

    Loop:
      1. Call LLM with current messages
      2. If tool calls → execute → append results → repeat
      3. If text response → done
    """
    tools = get_tools(config.tools) if config.tools is not None else []
    llm = make_llm_with_tools(config.llm, tools) if tools else make_llm(config.llm)

    messages = [
        SystemMessage(content=config.system_prompt),
        HumanMessage(content=task),
    ]
    intermediate_steps = []

    for iteration in range(config.max_iterations):
        logger.info("[%s] iteration %d/%d", config.name, iteration + 1, config.max_iterations)

        windowed = _trim(messages, config.context_window)

        try:
            response: AIMessage = llm.invoke(windowed)
        except Exception as e:
            logger.error("[%s] LLM call failed: %s", config.name, e)
            return AgentResult.fail(str(e))

        messages.append(response)

        if not response.tool_calls:
            logger.info("[%s] done after %d iterations", config.name, iteration + 1)
            return AgentResult.ok(output=response.content, steps=intermediate_steps)

        tool_messages = _execute_tool_calls(response.tool_calls)
        intermediate_steps.extend([
            {"tool": tc["name"], "args": tc["args"]}
            for tc in response.tool_calls
        ])
        messages.extend(tool_messages)

    logger.warning("[%s] reached max iterations", config.name)
    return AgentResult.fail(f"Max iterations ({config.max_iterations}) reached without a final answer.")
