"""
Delegation tool for the OrchestratorAgent.
Registered separately to avoid circular imports.
"""

from langchain_core.tools import tool


@tool
def delegate_to(agent: str, task: str) -> str:
    """
    Delegate a subtask to a specialist agent.
    Available agents: WebSearchAgent, CodeExecutionAgent, DocumentAgent, APIAgent, DataAgent.
    """
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

    result = runner(task)
    return result.output if result.success else f"Agent failed: {result.error}"
