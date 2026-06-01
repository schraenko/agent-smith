"""
Examples for Agent Smith (LangChain edition).
Requires a running Ollama instance: https://ollama.com
"""

import sys

from agent_smith import OllamaConfig, Step, run, run_code, run_sequential, run_web_search, run_parallel
from agent_smith.agents.builtins import web_search_agent


def example_simple():
    result = run("What is optical interferometry?", agent="web_search")
    print(result.output if result.success else f"Failed: {result.error}")


def example_code():
    result = run_code(
        "Write a Python function that computes the Fourier transform of a signal "
        "and plots its frequency spectrum using numpy."
    )
    print(result.output)


def example_sequential():
    llm = OllamaConfig(model="mistral:latest", temperature=0.3)
    steps = [
        Step(
            name="research",
            agent=web_search_agent(llm),
            task_fn=lambda _: "How does a Michelson interferometer work?",
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
    wf = run_sequential(steps)
    for name, result in wf.steps.items():
        print(f"\n{'✓' if result.success else '✗'} {name}")
        print(result.output or result.error)


def example_parallel():
    llm = OllamaConfig(model="mistral:latest")
    steps = [
        Step("history",      web_search_agent(llm), lambda _: "History of interferometry"),
        Step("applications", web_search_agent(llm), lambda _: "Modern applications of interferometry"),
        Step("ligo",         web_search_agent(llm), lambda _: "How does LIGO detect gravitational waves?"),
    ]
    wf = run_parallel(steps, max_workers=3)
    for name, result in wf.steps.items():
        print(f"\n=== {name} ===")
        print(result.output if result.success else f"Error: {result.error}")


if __name__ == "__main__":
    examples = {
        "simple": example_simple,
        "code": example_code,
        "sequential": example_sequential,
        "parallel": example_parallel,
    }
    name = sys.argv[1] if len(sys.argv) > 1 else "simple"
    fn = examples.get(name)
    if fn is None:
        print(f"Choose from: {list(examples.keys())}")
        sys.exit(1)
    print(f"Running: {name}\n{'─' * 40}")
    fn()
