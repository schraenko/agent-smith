# agent-smith — AGENTS.md

## Three editions (each with its own `pyproject.toml`)

| Edition | Directory | Imports as | Test dir | Dependencies |
|---|---|---|---|---|
| **Vanilla** | `agent_smith_vanilla/` | `agent_smith_vanilla` | `tests_vanilla/` | httpx, pandas, ddgs |
| **LangChain** | `agent_smith_lc/` | `agent_smith_lc` | `tests_lc/` | langchain>=1.0.0 |
| **CrewAI** | `agent_smith_crewai/` | `agent_smith_crewai` | `tests_crewai/` | crewai>=0.11.0 |

CrewAI requires `langchain>=0.1.0,<0.2.0` which conflicts with the LC edition's `langchain>=1.0.0` — they cannot share a venv.

## Setup per edition

```bash
# Vanilla (zero LangChain)
python -m venv .venv-vanilla && source .venv-vanilla/bin/activate
pip install -e "./agent_smith_vanilla[dev]"
# Workaround: setuptools 82+ generates broken editable .pth files on Python 3.14.
# Manually write the correct .pth file pointing to the repo root.
echo "$(cd .. && pwd)" > "$(dirname $(which python))/../lib/python3.14/site-packages/agent_smith_vanilla.pth"

# LangChain
python -m venv .venv-lc && source .venv-lc/bin/activate
pip install -e "./agent_smith_lc[dev]"
echo "$(pwd)" > ".venv-lc/lib/python3.14/site-packages/agent_smith_lc.pth"

# CrewAI (separate venv, uses crewai's built-in Ollama support)
python -m venv .venv-crewai && source .venv-crewai/bin/activate
pip install crewai --no-deps
pip install tiktoken  # latest (0.13+) has a binary wheel for Python 3.14 arm64
pip install "setuptools<82"  # pkg_resources removed in setuptools 82+
pip install "langchain>=0.1.0,<0.2.0" "langchain-openai>=0.0.5,<0.0.6" --no-deps
pip install "langchain-core>=0.1.52,<0.2.0" "langsmith>=0.1.17,<0.2.0"
pip install "langchain-community>=0.0.38,<0.1" "langchain-text-splitters>=0.0.1,<0.1"
pip install "numpy>=1,<2" "SQLAlchemy>=1.4,<3" "docstring-parser>=0.16"
pip install "openai>=1.7.1,<2.0.0" "instructor>=0.5.2,<0.6.0" "regex>=2023.12.25,<2024.0.0" "pydantic>=2.4.2,<3.0.0"
pip install -e "./agent_smith_crewai[dev]" --no-deps
echo "$(pwd)" > ".venv-crewai/lib/python3.14/site-packages/agent_smith_crewai.pth"

# Note: setuptools 82+ on Python 3.14 generates __editable__ .pth files that point
# to the package directory (e.g. agent_smith_lc/) instead of the repo root.
# The manual .pth files above override this by adding the repo root to sys.path.
```

## Commands

| Command | Action |
|---|---|
| `python -m pytest tests_lc/` | Run LC edition unit tests (mocked, no Ollama) |
| `python -m pytest tests_vanilla/` | Run vanilla edition unit tests (mocked, no Ollama) |
| `python -m pytest tests_crewai/` | Run CrewAI edition unit tests (mocked, no Ollama) |
| `python -m pytest tests_lc/ tests_vanilla/ tests_crewai/` | Run all unit tests |
| `python -m pytest tests_lc/test_ollama_integration.py -v -s` | Integration tests (needs Ollama + `mistral:latest`) |
| `python -m pytest --cov=agent_smith_vanilla --cov=agent_smith_lc --cov=agent_smith_crewai` | Run with coverage |

## Architecture (all three editions)

Functional style — no agent classes, no inheritance.

- **Entrypoints:** `{pkg}.run()` or direct `run_web_search()`, `run_code()`, etc.
- **Agent runner:** `agents/runner.py` — agentic loop (LC: imperative with langchain tool binding, Vanilla: imperative with custom tool dispatch, CrewAI: wraps CrewAI Agent/Task/Crew)
- **Built-in agents:** `agents/builtins.py` — 6 agents (WebSearch, Code, Document, API, Data, Orchestrator)
- **Tools:** `tools/builtins.py` — 10 tools (web_search, execute_python, read_file, list_files, http_get, http_post, read_csv, describe_data, query_data, delegate_to)
- **Workflows:** `workflows/engine.py` — `run_sequential`, `run_parallel`, `run_conditional`
- **Memory:** `memory/store.py` — sliding-window + (in vanilla) immutable `MemoryStore` KV
- **Types:** `types.py` — `AgentResult` (status/output/error/intermediate_steps); vanilla adds `AgentContext`, `Message`, `MemoryStore`

## Key conventions

- LLM backend is **Ollama-only**. No OpenAI/Anthropic adapters.
- LangChain types live only in `llm.py` and `runner.py` of the LC edition. Vanilla uses plain types throughout. CrewAI uses crewai's built-in Ollama support.
- No formatter, linter, type checker, or pre-commit hook configured.
- Orchestrator agent delegates via `delegate_to` tool (max 20 iterations); all other agents default to 10.
- Vanilla edition uses immutable state (`AgentContext`, `MemoryStore`). LC edition uses mutable lists.
- No generated code, no migrations, no build artifacts.
