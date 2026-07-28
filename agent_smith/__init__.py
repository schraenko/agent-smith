from typing import Callable

from agent_smith.agents.builtins import (
    run_api, run_code, run_data, run_document,
    run_orchestrator, run_web_search,
)
from agent_smith.agents.runner import (
    AgentConfig, run_agent_execute_phase, run_agent_plan_phase,
)
from agent_smith.approval import ApprovalDecision, Plan
from agent_smith.llm import OllamaConfig
from agent_smith.rules import load_rule
from agent_smith.types import AgentResult
from agent_smith.workflows.engine import Step, WorkflowResult, run_sequential, run_parallel


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
    model: str = "qwen3:8b",
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


def _load_orchestrator_config(model: str, base_url: str) -> AgentConfig:
    cfg = load_rule("orchestrator")
    return AgentConfig(
        name=cfg["name"],
        system_prompt=cfg["system_prompt"],
        llm=OllamaConfig(model=model, base_url=base_url),
        tools=cfg.get("tools"),
        max_iterations=cfg.get("max_iterations", 20),
        context_window=cfg.get("context_window", 20),
    )


def run_interactive(
    task: str,
    approval_callback: Callable[[Plan], ApprovalDecision],
    model: str = "qwen3:8b",
    base_url: str = "http://localhost:11434",
) -> AgentResult:
    """
    Run the orchestrator in human-in-the-loop mode.

    The orchestrator first produces a structured delegation plan via
    `submit_plan`. The plan is passed to `approval_callback`, which returns
    an `ApprovalDecision`. If approved, the orchestrator then executes the
    plan via `delegate_to`. If rejected, the run is aborted and a failed
    `AgentResult` is returned.

    Args:
        task:              Natural language task description.
        approval_callback: Callable receiving a `Plan` and returning
                           an `ApprovalDecision`.
        model:             Ollama model name.
        base_url:          Ollama API base URL.

    Returns:
        AgentResult from the execution phase (or a failed result on reject).
    """
    config = _load_orchestrator_config(model, base_url)

    plan, phase1_result = run_agent_plan_phase(task, config)
    if plan is None:
        return phase1_result

    decision = approval_callback(plan)
    if not decision.approved:
        phase1_result.audit_trail.log(
            level=0,
            agent=config.name,
            action="plan_rejected",
            task=decision.feedback,
        )
        return AgentResult.fail(
            f"Plan rejected by user: {decision.feedback or 'no feedback'}",
            audit_trail=phase1_result.audit_trail,
        )

    return run_agent_execute_phase(task, plan, config, audit_trail=phase1_result.audit_trail)


__all__ = [
    "run", "run_interactive", "run_agent",
    "run_web_search", "run_code", "run_document",
    "run_api", "run_data", "run_orchestrator",
    "run_sequential", "run_parallel",
    "AgentConfig", "AgentResult", "OllamaConfig",
    "Plan", "ApprovalDecision",
    "Step", "WorkflowResult",
]
