"""
Workflow engine.
Workflows are plain functions composing agent runs.
No classes — just sequential, parallel, and conditional execution.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from agent_smith.agents.runner import AgentConfig, run_agent
from agent_smith.types import AgentResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Step:
    name: str
    agent: AgentConfig
    task_fn: Callable[[dict[str, AgentResult]], str]


@dataclass
class WorkflowResult:
    steps: dict[str, AgentResult] = field(default_factory=dict)
    final: AgentResult | None = None

    @property
    def success(self) -> bool:
        return all(r.success for r in self.steps.values())


def run_sequential(steps: list[Step]) -> WorkflowResult:
    """Run steps one after another, passing prior results to each task_fn."""
    results: dict[str, AgentResult] = {}

    for step in steps:
        task = step.task_fn(results)
        logger.info("[workflow:sequential] step: %s", step.name)

        result = run_agent(task, step.agent)
        results[step.name] = result

        if not result.success:
            logger.warning("[workflow:sequential] step %s failed — stopping", step.name)
            return WorkflowResult(steps=results, final=result)

    return WorkflowResult(
        steps=results,
        final=results[steps[-1].name] if steps else None,
    )


def run_parallel(steps: list[Step], max_workers: int = 4) -> WorkflowResult:
    """Run all steps concurrently. Each step gets an empty prior-results dict."""
    results: dict[str, AgentResult] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_agent, step.task_fn({}), step.agent): step.name
            for step in steps
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
                logger.info("[workflow:parallel] done: %s", name)
            except Exception as e:
                logger.error("[workflow:parallel] %s raised: %s", name, e)
                results[name] = AgentResult.fail(str(e))

    successful = [r for r in results.values() if r.success]
    final = successful[-1] if successful else list(results.values())[-1]
    return WorkflowResult(steps=results, final=final)


def run_conditional(
    condition: Callable[[dict[str, Any]], bool],
    if_true: list[Step],
    if_false: list[Step],
    prior_results: dict[str, Any] | None = None,
) -> WorkflowResult:
    """Branch to a different set of steps based on a runtime condition."""
    chosen = if_true if condition(prior_results or {}) else if_false
    return run_sequential(chosen)
