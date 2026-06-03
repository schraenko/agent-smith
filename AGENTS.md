# agent-smith — AGENTS.md

## Quick start

```bash
pip install -r requirements.txt
pip install -e .
```

Requires Python >=3.11 and a running Ollama instance (default: `mistral:latest` at `http://localhost:11434`).  
All tests use `mistral:latest`.

## Commands

| Command | Action |
|---|---|
| `python -m pytest` | Run all unit tests (no external deps) |
| `python -m pytest -v -s tests/test_ollama_integration.py` | Integration tests (needs running Ollama) |
| `python -m pytest --cov=agent_smith` | Run with coverage |
| `python examples/basic_usage.py {simple,code,sequential,parallel}` | Run example (needs Ollama) |
| `pip install -e ".[dev]"` | Install with dev extras (pytest, pytest-cov) |

Tests are in `tests/`. Unit tests mock the LLM — they should pass without Ollama.

## Architecture

Single package at `agent_smith/`. Functional style — no agent classes, no inheritance.

- **Entrypoints:** `agent_smith.run()` for convenience, or direct `run_web_search()`, `run_code()` etc.
- **Agent runner:** `agent_smith/agents/runner.py` — imperative agentic loop, no LangGraph
- **Built-in agents:** `agent_smith/agents/builtins.py` — 6 agents (WebSearch, Code, Document, API, Data, Orchestrator)
- **Tools:** `agent_smith/tools/builtins.py` — 9 tools (web_search, execute_python, read_file, list_files, http_get, http_post, read_csv, describe_data, query_data) + delegation tool in `delegate.py`
- **Workflows:** `agent_smith/workflows/engine.py` — `run_sequential`, `run_parallel`, `run_conditional`
- **LLM layer:** `agent_smith/llm.py` — isolates LangChain `ChatOllama` behind simple config+factory
- **Memory:** `agent_smith/memory/store.py` — sliding-window trim, no persistent storage
- **Types:** `agent_smith/types.py` — `AgentResult` (status/output/error/intermediate_steps)

## Key conventions

- LLM backend is **Ollama-only**. No OpenAI/Anthropic adapters.
- LangChain types live only in `llm.py` and `runner.py` — domain model uses plain dataclasses.
- No formatter, linter, type checker, or pre-commit hook configured.
- Orchestrator agent delegates via `delegate_to` tool (max 20 iterations); all other agents default to 10.
- No generated code, no migrations, no build artifacts.
