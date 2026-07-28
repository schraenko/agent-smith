"""
Delegation tool for the OrchestratorAgent.
Registered separately to avoid circular imports.
"""

from langchain_core.tools import tool

from agent_smith.audit import get_current_trail, get_current_level


@tool
def delegate_to(agent: str, task: str) -> str:
    """
    Delegate a subtask to a specialist agent.
    Available agents: WebSearchAgent, CodeExecutionAgent, DocumentAgent, APIAgent, DataAgent.
    """
    from agent_smith.agents.builtins import (
        run_api, run_code, run_data, run_document, run_web_search,
    )

    trail = get_current_trail()
    level = get_current_level()

    if trail:
        trail.log(level=level, agent=agent, action="delegate", task=task)

    dispatch = {
        "WebSearchAgent": run_web_search,
        "CodeExecutionAgent": run_code,
        "DocumentAgent": run_document,
        "APIAgent": run_api,
        "DataAgent": run_data,
    }

    runner = dispatch.get(agent)
    if runner is None:
        if trail:
            trail.log(level=level, agent=agent, action="delegate_result", result=f"Unknown agent: {agent}", success=False)
        return f"Unknown agent: {agent}. Choose from: {list(dispatch.keys())}"

    result = runner(task, audit_trail=trail, level=level + 1) if trail else runner(task)

    if trail:
        output = result.output if result.success else (result.error or "unknown error")
        trail.log(level=level, agent=agent, action="delegate_result", result=str(output), success=result.success)

    return result.output if result.success else f"Agent failed: {result.error}"