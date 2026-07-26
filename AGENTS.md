# agent-smith — AGENTS.md

## Package

| Directory | Imports as | Test dir | Dependencies |
|---|---|---|---|
| `agent_smith/` | `agent_smith` | `tests/` | langchain>=1.0.0 |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

> Workaround: setuptools 82+ on Python 3.14 generates broken editable `.pth` files.
> Manually write the correct `.pth` file pointing to the repo root:
> ```bash
> echo "$(pwd)" > "$(dirname $(which python))/../lib/python3.14/site-packages/agent_smith.pth"
> ```

## Commands

| Command | Action |
|---|---|
| `python -m pytest tests/` | Run unit tests (mocked, no Ollama) |
| `python -m pytest tests/test_ollama_integration.py -v -s` | Integration tests (needs Ollama + `mistral:latest`) |
| `python -m pytest --cov=agent_smith` | Run with coverage |

## Architecture

Functional style — no agent classes, no inheritance.

- **Entrypoints:** `agent_smith.run()` or direct `run_web_search()`, `run_code()`, etc.
- **Agent runner:** `agents/runner.py` — agentic loop with LangChain tool binding
- **Built-in agents:** `agents/builtins.py` — 6 agents (WebSearch, Code, Document, API, Data, Orchestrator)
- **Tools:** `tools/builtins.py` — 10 tools (web_search, execute_python, read_file, list_files, http_get, http_post, read_csv, describe_data, query_data, delegate_to)
- **Workflows:** `workflows/engine.py` — `run_sequential`, `run_parallel`, `run_conditional`
- **Memory:** `memory/store.py` — sliding-window utilities
- **Types:** `types.py` — `AgentResult` (status/output/error/intermediate_steps)
- **Rules:** `rules/` — Markdown files with YAML frontmatter for agent configuration

## Key conventions

- LLM backend is **Ollama-only**. No OpenAI/Anthropic adapters.
- LangChain types live only in `llm.py` and `runner.py`. The rest of the codebase uses plain types.
- No formatter, linter, type checker, or pre-commit hook configured.
- Orchestrator agent delegates via `delegate_to` tool (max 20 iterations); all other agents default to 10.
- No generated code, no migrations, no build artifacts.
