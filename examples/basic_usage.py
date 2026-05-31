"""
Examples showing how to use Agent Smith.
Requires a running Ollama instance: https://ollama.com
"""

from agent_smith import (
    OllamaConfig,
    Step,
    run,
    run_orchestrator,
    run_sequential,
    run_web_search,
    run_code,
    run_parallel,
)


# ─── 1. Simplest possible usage ───────────────────────────────────────────────

def example_simple():
    result = run("What is optical interferometry?", agent="web_search")
    if result.success:
        print(result.output)
    else:
        print(f"Failed: {result.error}")


# ─── 2. Custom model ──────────────────────────────────────────────────────────

def example_custom_model():
    llm = OllamaConfig(model="mistral", temperature=0.3)
    result = run_web_search("Latest advances in VLBI interferometry", llm=llm)
    print(result.output)


# ─── 3. Code agent ────────────────────────────────────────────────────────────

def example_code():
    result = run_code(
        "Write a Python function that computes the Fourier transform of a signal "
        "and plots the frequency spectrum. Use numpy and matplotlib."
    )
    print(result.output)


# ─── 4. Sequential workflow ───────────────────────────────────────────────────

def example_sequential_workflow():
    llm = OllamaConfig(model="llama3.2")

    steps = [
        Step(
            name="research",
            agent=__import__("agent_smith.agents.builtins", fromlist=["web_search_agent"]).web_search_agent(llm),
            task_fn=lambda _: "Research the Michelson interferometer: how does it work?",
        ),
        Step(
            name="code",
            agent=__import__("agent_smith.agents.builtins", fromlist=["code_agent"]).code_agent(llm),
            task_fn=lambda r: (
                f"Based on this research:\n{r['research'].output}\n\n"
                "Write a Python simulation of a Michelson interferometer using numpy."
            ),
        ),
    ]

    workflow = run_sequential(steps)

    for name, result in workflow.steps.items():
        status = "✓" if result.success else "✗"
        print(f"\n[{status}] {name}")
        print(result.output or result.error)


# ─── 5. Parallel workflow ─────────────────────────────────────────────────────

def example_parallel():
    from agent_smith.agents.builtins import web_search_agent
    llm = OllamaConfig(model="llama3.2")

    steps = [
        Step(
            name="history",
            agent=web_search_agent(llm),
            task_fn=lambda _: "History of interferometry",
        ),
        Step(
            name="applications",
            agent=web_search_agent(llm),
            task_fn=lambda _: "Modern applications of interferometry",
        ),
        Step(
            name="ligo",
            agent=web_search_agent(llm),
            task_fn=lambda _: "How does LIGO use laser interferometry to detect gravitational waves?",
        ),
    ]

    workflow = run_parallel(steps, max_workers=3)

    for name, result in workflow.steps.items():
        print(f"\n=== {name} ===")
        print(result.output if result.success else f"Error: {result.error}")


# ─── 6. Orchestrator ─────────────────────────────────────────────────────────

def example_orchestrator():
    result = run_orchestrator(
        "Research optical coherence tomography, then write a Python simulation "
        "that demonstrates the basic principle of low-coherence interferometry."
    )
    print(result.output)


if __name__ == "__main__":
    import sys
    examples = {
        "simple": example_simple,
        "model": example_custom_model,
        "code": example_code,
        "sequential": example_sequential_workflow,
        "parallel": example_parallel,
        "orchestrator": example_orchestrator,
    }

    name = sys.argv[1] if len(sys.argv) > 1 else "simple"
    fn = examples.get(name)
    if fn is None:
        print(f"Unknown example. Choose from: {list(examples.keys())}")
        sys.exit(1)

    print(f"Running example: {name}\n{'─' * 40}")
    fn()
