"""
Workflow engine.
Workflows are compositions of agent runs — sequential, parallel, or conditional.
All functions are pure: given the same inputs, produce the same outputs.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from agent_smith.agents.runner import AgentConfig, run_agent
from agent_smith.types import AgentContext, AgentResult, Status

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Step:
    """A single step in a workflow."""
    name: str
    agent: AgentConfig
    task_fn: Callable[[dict[str, Any]], str]  # builds task string from prior results


@dataclass
class WorkflowResult:
    steps: dict[str, AgentResult] = field(default_factory=dict)
    final: AgentResult | None = None

    @property
    def success(self) -> bool:
        return all(r.success for r in self.steps.values())


def run_sequential(
    steps: list[Step],
    initial_context: AgentContext | None = None,
) -> WorkflowResult:
    """
    Run steps one after another.
    Each step receives the accumulated results of all prior steps.
    """
    results: dict[str, AgentResult] = {}
    context = initial_context or AgentContext()

    for step in steps:
        task = step.task_fn(results)
        logger.info("[workflow] running step: %s", step.name)

        result = run_agent(task, step.agent, context)
        results[step.name] = result

        if not result.success:
            logger.warning("[workflow] step %s failed: %s", step.name, result.error)
            return WorkflowResult(steps=results, final=result)

        # Pass context forward so agents share conversation history
        context = result.context

    return WorkflowResult(steps=results, final=results[steps[-1].name] if steps else None)


def run_parallel(
    steps: list[Step],
    initial_context: AgentContext | None = None,
    max_workers: int = 4,
) -> WorkflowResult:
    """
    Run all steps concurrently. Each step gets the same initial context.
    Results are collected as steps complete.
    """
    context = initial_context or AgentContext()
    results: dict[str, AgentResult] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_agent, step.task_fn({}), step.agent, context): step.name
            for step in steps
        }

        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
                logger.info("[workflow] parallel step done: %s", name)
            except Exception as e:
                logger.error("[workflow] parallel step %s raised: %s", name, e)
                results[name] = AgentResult.fail(str(e), context)

    # Synthesize a final result: last successful or last failed
    successful = [r for r in results.values() if r.success]
    final = successful[-1] if successful else list(results.values())[-1]

    return WorkflowResult(steps=results, final=final)


def run_conditional(
    condition: Callable[[dict[str, Any]], bool],
    if_true: list[Step],
    if_false: list[Step],
    context: AgentContext | None = None,
    prior_results: dict[str, Any] | None = None,
) -> WorkflowResult:
    """Branch to a different set of steps based on a condition."""
    chosen = if_true if condition(prior_results or {}) else if_false
    return run_sequential(chosen, context)
