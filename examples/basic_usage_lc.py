"""
Examples for Agent Smith (LangChain edition).
Requires a running Ollama instance: https://ollama.com
"""

import sys

from agent_smith_lc import run_code, run_web_search
from agent_smith_lc.agents.builtins import web_search_agent, code_agent
from agent_smith_lc.llm import OllamaConfig
from agent_smith_lc.workflows.engine import run_sequential, run_parallel


def example_web_search():
    result = run_web_search("What is optical interferometry?")
    if result.success:
        print(result.output)
    else:
        print(f"Failed: {result.error}")


def example_code():
    result = run_code(
        "Write a Python function that computes the Fourier transform of a signal "
        "and plots its frequency spectrum using numpy."
    )
    print(result.output)


def example_sequential():
    llm = OllamaConfig(model="mistral:latest", temperature=0.3)
    steps = [
        {
            "name": "research",
            "agent": web_search_agent(llm),
            "task_fn": lambda _: "How does a Michelson interferometer work?",
        },
        {
            "name": "code",
            "agent": code_agent(llm),
            "task_fn": lambda r: (
                f"Based on this research:\n{r['research'].output}\n\n"
                "Write a Python simulation of a Michelson interferometer using numpy."
            ),
        },
    ]
    wf = run_sequential(steps)
    for name, result in wf.items():
        print(f"\n{'OK' if result.success else 'FAIL'} {name}")
        print(result.output or result.error)


def example_parallel():
    llm = OllamaConfig(model="mistral:latest")
    steps = [
        {"name": "history",      "agent": web_search_agent(llm), "task_fn": lambda _: "History of interferometry"},
        {"name": "applications", "agent": web_search_agent(llm), "task_fn": lambda _: "Modern applications of interferometry"},
    ]
    wf = run_parallel(steps, max_workers=2)
    for name, result in wf.items():
        print(f"\n=== {name} ===")
        print(result.output if result.success else f"Error: {result.error}")


if __name__ == "__main__":
    examples = {
        "web_search": example_web_search,
        "code": example_code,
        "sequential": example_sequential,
        "parallel": example_parallel,
    }
    name = sys.argv[1] if len(sys.argv) > 1 else None
    fn = examples.get(name)
    if fn:
        print(f"Running: {name}\n{'─' * 40}")
        fn()
    elif name:
        print("Unknown example:", name)
