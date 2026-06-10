"""
Examples for Agent Smith (CrewAI edition).
Requires a running Ollama instance: https://ollama.com

Build:
    podman build -f Dockerfile.crewai -t agent-smith-crewai .

Usage (from repo root, uses $PWD for absolute volume path):
    podman run --rm -v $PWD:/workspace -e PYTHONPATH=/workspace agent-smith-crewai examples/basic_usage_crewai.py web_search
    podman run --rm -v $PWD:/workspace -e PYTHONPATH=/workspace agent-smith-crewai examples/basic_usage_crewai.py code
"""

import sys

from agent_smith_crewai import run_code, run_web_search
from agent_smith_crewai.llm import OllamaConfig


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


if __name__ == "__main__":
    examples = {
        "web_search": example_web_search,
        "code": example_code,
    }
    name = sys.argv[1] if len(sys.argv) > 1 else None
    fn = examples.get(name)
    if fn:
        print(f"Running: {name}\n{'─' * 40}")
        fn()
    elif name:
        print("Unknown example:", name)
