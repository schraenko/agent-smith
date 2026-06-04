"""
Core agent runner.
An agent is just a function: (task, context, config) -> AgentResult.
This module provides the agentic loop — LLM call → tool execution → repeat.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from agent_smith_vanilla.llm.ollama import OllamaConfig, complete
from agent_smith_vanilla.memory.store import window
from agent_smith_vanilla.tools.registry import execute_tool_calls, get_tools
from agent_smith_vanilla.types import (
    AgentContext,
    AgentResult,
    Message,
    Role,
    Status,
    Tool,
    ToolCall,
    ToolResult,
)

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10


@dataclass(frozen=True)
class AgentConfig:
    name: str
    system_prompt: str
    llm: OllamaConfig = field(default_factory=OllamaConfig)
    tools: list[str] | None = None        # None = no tools, [] = all tools
    max_iterations: int = MAX_ITERATIONS
    context_window: int = 20              # max messages kept in context


def run_agent(
    task: str,
    config: AgentConfig,
    context: AgentContext | None = None,
) -> AgentResult:
    """
    Run the agentic loop for a single agent.

    Loop:
      1. Call LLM with current messages
      2. If tool calls → execute → append results → repeat
      3. If text response → done
    """
    ctx = context or AgentContext()
    ctx = ctx.with_message(Message(role=Role.USER, content=task))

    available_tools = get_tools(config.tools) if config.tools is not None else []

    for iteration in range(config.max_iterations):
        logger.info("[%s] iteration %d/%d", config.name, iteration + 1, config.max_iterations)

        windowed = window(ctx.messages, config.context_window)

        try:
            text, tool_calls = complete(
                messages=windowed,
                config=config.llm,
                tools=available_tools if available_tools else None,
                system=config.system_prompt,
            )
        except Exception as e:
            logger.error("[%s] LLM call failed: %s", config.name, e)
            return AgentResult.fail(str(e), ctx)

        # No tool calls → final answer
        if not tool_calls:
            ctx = ctx.with_message(Message(role=Role.ASSISTANT, content=text))
            logger.info("[%s] finished after %d iterations", config.name, iteration + 1)
            return AgentResult.ok(output=text, context=ctx)

        # Append assistant's intent
        ctx = ctx.with_message(
            Message(
                role=Role.ASSISTANT,
                content=text or f"[calling {len(tool_calls)} tool(s)]",
            )
        )

        # Execute tools and append results
        results = execute_tool_calls(tool_calls)
        for r in results:
            content = json.dumps(r.result) if r.success else f"ERROR: {r.error}"
            ctx = ctx.with_message(
                Message(role=Role.TOOL, content=content, tool_call_id=r.tool_call_id)
            )
            logger.debug("[%s] tool %s → %s", config.name, r.name, "ok" if r.success else "error")

    logger.warning("[%s] reached max iterations (%d)", config.name, config.max_iterations)
    return AgentResult.fail(
        error=f"Max iterations ({config.max_iterations}) reached without a final answer.",
        context=ctx,
    )
