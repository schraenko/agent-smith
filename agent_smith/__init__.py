"""
Agent Smith — modular agentic workflows for Ollama.

Quick start:

    from agent_smith import run, run_orchestrator, OllamaConfig

    result = run("Explain the Michelson-Morley experiment", agent="web_search")
    print(result.output)
"""

# Trigger tool registration
import agent_smith.tools.builtins  # noqa: F401

from agent_smith.agents.builtins import (
    run_api,
    run_code,
    run_data,
    run_document,
    run_orchestrator,
    run_web_search,
)
from agent_smith.agents.runner import AgentConfig, run_agent
from agent_smith.llm.ollama import OllamaConfig, list_models
from agent_smith.memory.store import MemoryStore, empty_store
from agent_smith.tools.registry import get_tools, tool
from agent_smith.types import AgentContext, AgentResult, Message, Role, Status
from agent_smith.workflows.engine import Step, WorkflowResult, run_parallel, run_sequential

_AGENT_MAP = {
    "web_search": run_web_search,
    "code": run_code,
    "document": run_document,
    "api": run_api,
    "data": run_data,
    "orchestrator": run_orchestrator,
}


def run(
    task: str,
    agent: str = "orchestrator",
    model: str = "phi4:latest",
    base_url: str = "http://localhost:11434",
) -> AgentResult:
    """
    Convenience entry point.

    Args:
        task:     Natural language task description.
        agent:    One of: web_search, code, document, api, data, orchestrator.
        model:    Ollama model name.
        base_url: Ollama API base URL.
    """
    llm = OllamaConfig(model=model, base_url=base_url)
    runner = _AGENT_MAP.get(agent)
    if runner is None:
        raise ValueError(f"Unknown agent '{agent}'. Choose from: {list(_AGENT_MAP.keys())}")
    return runner(task, llm=llm)


__all__ = [
    "run",
    "run_agent",
    "run_web_search",
    "run_code",
    "run_document",
    "run_api",
    "run_data",
    "run_orchestrator",
    "run_sequential",
    "run_parallel",
    "AgentConfig",
    "AgentContext",
    "AgentResult",
    "OllamaConfig",
    "MemoryStore",
    "Message",
    "Role",
    "Status",
    "Step",
    "WorkflowResult",
    "tool",
    "get_tools",
    "list_models",
    "empty_store",
]
