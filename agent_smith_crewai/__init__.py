from agent_smith_crewai.agents.runner import AgentConfig, run_agent
from agent_smith_crewai.agents.builtins import (
    run_web_search, run_code, run_document,
    run_api, run_data, run_orchestrator,
)
from agent_smith_crewai.llm import OllamaConfig
from agent_smith_crewai.types import AgentResult
from agent_smith_crewai.workflows.engine import Step, WorkflowResult, run_sequential, run_parallel

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
) -> AgentResult:
    llm = OllamaConfig(model=model)
    runner = _AGENT_MAP.get(agent)
    if runner is None:
        raise ValueError(f"Unknown agent '{agent}'. Choose from: {list(_AGENT_MAP.keys())}")
    return runner(task, llm=llm)


__all__ = [
    "run", "run_agent",
    "run_web_search", "run_code", "run_document",
    "run_api", "run_data", "run_orchestrator",
    "run_sequential", "run_parallel",
    "AgentConfig", "AgentResult", "OllamaConfig",
    "Step", "WorkflowResult",
]
