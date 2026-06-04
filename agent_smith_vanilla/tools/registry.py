"""
Tool registry and execution.
Tools are plain functions decorated with @tool — no classes, no inheritance.
"""

import inspect
import json
import logging
from typing import Any, Callable

from agent_smith_vanilla.types import Tool, ToolCall, ToolResult

logger = logging.getLogger(__name__)

# Global registry: name -> Tool
_registry: dict[str, Tool] = {}


def tool(name: str, description: str, parameters: dict[str, Any]) -> Callable:
    """Decorator to register a function as a tool."""
    def decorator(fn: Callable) -> Callable:
        _registry[name] = Tool(
            name=name,
            description=description,
            parameters=parameters,
            fn=fn,
        )
        logger.debug("Registered tool: %s", name)
        return fn
    return decorator


def get_tool(name: str) -> Tool | None:
    return _registry.get(name)


def get_tools(names: list[str] | None = None) -> list[Tool]:
    if names is None:
        return list(_registry.values())
    return [_registry[n] for n in names if n in _registry]


def execute_tool_call(call: ToolCall) -> ToolResult:
    """Execute a single tool call and return its result."""
    t = get_tool(call.name)
    if t is None:
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            result=None,
            error=f"Unknown tool: {call.name}",
        )

    try:
        logger.info("Executing tool: %s args=%s", call.name, call.arguments)
        result = t.fn(**call.arguments)
        return ToolResult(tool_call_id=call.id, name=call.name, result=result)
    except Exception as e:
        logger.error("Tool %s failed: %s", call.name, e)
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            result=None,
            error=str(e),
        )


def execute_tool_calls(calls: list[ToolCall]) -> list[ToolResult]:
    return [execute_tool_call(c) for c in calls]
