# agent-smith — AGENTS.md

## Package

| Directory | Imports as | Test dir | Dependencies |
|---|---|---|---|
| `agent_smith/` | `agent_smith` | `tests/` | langchain>=1.0.0 |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                    # installiert bandit + pip-audit automatisch
bash scripts/install-security-tools.sh     # installiert gitleaks (optional, Regex-Fallback vorhanden)
chmod +x .git/hooks/pre-push               # Pre-Push-Hook aktivieren
```

> **Hinweis:** `pyproject.toml` ist die Single Source of Truth für Dependencies.
> `requirements.txt` wird nicht mehr verwendet (gelöscht am 28. Juli 2026).

> Workaround: setuptools 82+ on Python 3.14 generates broken editable `.pth` files.
> Manually write the correct `.pth` file pointing to the repo root:
> ```bash
> echo "$(pwd)" > "$(dirname $(which python))/../lib/python3.14/site-packages/agent_smith.pth"
> ```

## Commands

| Command | Action |
|---|---|
| `python -m pytest tests/` | Run unit tests (mocked, no Ollama) |
| `python -m pytest tests/test_ollama_integration.py -v -s` | Integration tests (needs Ollama + `qwen3:8b`) |
| `python -m pytest --cov=agent_smith` | Run with coverage |

## Architecture

Functional style — no agent classes, no inheritance.

- **Entrypoints:** `agent_smith.run()` or direct `run_web_search()`, `run_code()`, etc.
- **Agent runner:** `agents/runner.py` — agentic loop with LangChain tool binding
- **Built-in agents:** `agents/builtins.py` — 6 agents (WebSearch, Code, Document, API, Data, Orchestrator)
- **Tools:** `tools/builtins.py` — 10 tools (web_search, execute_python, read_file, list_files, http_get, http_post, read_csv, describe_data, query_data, delegate_to)
- **Workflows:** `workflows/engine.py` — `run_sequential`, `run_parallel`, `run_conditional`
- **Memory:** `memory/store.py` — sliding-window utilities
- **Types:** `types.py` — `AgentResult` (status/output/error/intermediate_steps/audit_trail)
- **Audit Trail:** `audit.py` — `AuditEntry`, `AuditTrail` + Context-Vars for full observability
- **Rules:** `rules/` — Markdown files with YAML frontmatter for agent configuration
- **MCP Servers:** `mcp_servers/` — Mock data servers (rain_sensor)

## Key conventions

- LLM backend is **Ollama-only**. No OpenAI/Anthropic adapters.
- LangChain types live only in `llm.py` and `runner.py`. The rest of the codebase uses plain types.
- No formatter, linter, type checker, or pre-commit hook configured.
- Orchestrator agent delegates via `delegate_to` tool (max 20 iterations); all other agents default to 10.
- No generated code, no migrations, no build artifacts.
- Tool calling includes fallback parsing for models that output tool calls as text (e.g., Qwen3 with Ollama).
- Fallback parsing supports XML tags (`<tool_call>`) and raw JSON tool calls.

## OpenCode Agents & Skills

### Agents (`.opencode/agents/`)

| Agent | Type | Purpose |
|---|---|---|
| `coder.md` | subagent | Implementiert Features und Bugfixes in der LangChain Edition von agent-smith |
| `tester.md` | subagent | Schreibt und führt Unit-Tests für die LangChain Edition aus |
| `reviewer.md` | subagent | Führt Code-Review mit LC-spezifischen Checks durch |
| `architect.md` | subagent | Analysiert Architektur und schlägt Refactoring für die LC Edition vor |
| `dev-workflow.md` | subagent | Koordiniert den Entwicklungs-Workflow: Code → Review → Test |
| `requirements.md` | tab | Erstellt und aktualisiert Anforderungsdokumente basierend auf Code-Änderungen |
| `doku.md` | tab | Aktualisiert und pflegt die Projekt-Dokumentation |

### Skills (`.opencode/skills/`)

| Skill | Purpose |
|---|---|
| `architecture/` | Architektur und Konventionen der LangChain Edition von agent-smith |

## Conversation Transcript

### Pflicht
- Am Ende JEDER Antwort den Chat-Verlauf in `docs/chatlog.md` anhängen
- Die rohe Ausgabe erfassen wie sie erscheint — inklusive:
  - User-Nachrichten (vollständig)
  - Assistant-Antworten (vollständig)
  - Thinking-Blöcke mit Timings (`+ Thought: 4.5s`)
  - System-Reminders
  - UI-Marker (Context, LSP, Token-Counter)
  - Tool-Aufrufe und deren Ausgaben
  - Fehlermeldungen

### Format pro Eintrag
```markdown
### [Nr]. [Kurzbeschreibung des Themas]

**User:** [Vollständige User-Nachricht]

**Assistant:**
[Ausgabe wie sie auf dem Bildschirm erscheint]
```

### Trigger
- Nach JEDER User→Assistant-Interaktion
- Auch bei kurzen Fragen oder Erklärungen
- Datei am Ende der Session: Timestamp aktualisieren
- Falls Datei für aktuelles Datum noch nicht existiert: erstellen

### Spezielle Fälle
- Tool-Ergebnisse (tree, bash-Ausgaben) als Code-Block anhängen
- Längere Ausgaben: Vollständig kopieren, nicht kürzen
- Bei mehreren Tool-Aufrufen: Alle einzeln auflisten
