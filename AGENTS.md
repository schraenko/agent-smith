# agent-smith — AGENTS.md

## Quick start

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

Requires Python >=3.11 and a running Ollama instance (default: `phi4:latest` at `http://localhost:11434`).

## Two editions

| Edition | Directory | Imports as | Test dir |
|---|---|---|---|
| **LangChain** | `agent_smith_lc/` | `agent_smith_lc` | `tests_lc/` |
| **Vanilla** | `agent_smith_vanilla/` | `agent_smith` | `tests_vanilla/` |

Both are installed as editable packages from the same `pyproject.toml`. The vanilla edition has no LangChain dependency — it calls the Ollama API directly via httpx.

## Commands

| Command | Action |
|---|---|
| `python -m pytest tests_lc/` | Run LC edition unit tests (mocked, no Ollama) |
| `python -m pytest tests_vanilla/` | Run vanilla edition unit tests (mocked, no Ollama) |
| `python -m pytest tests_lc/ tests_vanilla/` | Run all unit tests |
| `python -m pytest tests_lc/test_ollama_integration.py -v -s` | Integration tests (needs Ollama + `mistral:latest`) |
| `python -m pytest --cov=agent_smith` | Run with coverage |

`pyproject.toml` `testpaths` is stale — always pass the test dir explicitly.

## Architecture (both editions)

Functional style — no agent classes, no inheritance. Both editions share the same structure:

- **Entrypoints:** `{pkg}.run()` or direct `run_web_search()`, `run_code()`, etc.
- **Agent runner:** `agents/runner.py` — imperative agentic loop (no LangGraph)
- **Built-in agents:** `agents/builtins.py` — 6 agents (WebSearch, Code, Document, API, Data, Orchestrator)
- **Tools:** `tools/builtins.py` — 10 tools (web_search, execute_python, read_file, list_files, http_get, http_post, read_csv, describe_data, query_data, delegate_to)
- **Workflows:** `workflows/engine.py` — `run_sequential`, `run_parallel`, `run_conditional`
- **Memory:** `memory/store.py` — sliding-window + (in vanilla) immutable `MemoryStore` KV
- **Types:** `types.py` — `AgentResult` (status/output/error/intermediate_steps); vanilla adds `AgentContext`, `Message`, `MemoryStore`

## Key conventions

- LLM backend is **Ollama-only**. No OpenAI/Anthropic adapters.
- LangChain types live only in `llm.py` and `runner.py` of the LC edition. The vanilla edition uses plain types throughout.
- No formatter, linter, type checker, or pre-commit hook configured.
- Orchestrator agent delegates via `delegate_to` tool (max 20 iterations); all other agents default to 10.
- Vanilla edition uses immutable state (`AgentContext`, `MemoryStore`). LC edition uses mutable lists.
- No generated code, no migrations, no build artifacts.
