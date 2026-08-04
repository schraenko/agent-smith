# agent-smith — AGENTS.md

## Package

| Directory | Imports as | Test dir | Dependencies |
|---|---|---|---|
| `agent_smith/` | `agent_smith` | `tests/` | langchain>=1.0.0, deepagents>=0.6.12, langgraph>=1.2.0 |

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
| `python -m pytest tests/test_ollama_integration.py -v -s` | Integration tests (needs Ollama + `gemma4:12b`) |
| `python -m pytest --cov=agent_smith` | Run with coverage |

## Architecture

Functional style — no agent classes, no inheritance.

- **Entrypoints:** `agent_smith.run()` or direct `run_web_search()`, `run_code()`, etc.
- **Agent runner:** `agents/runner.py` — agentic loop powered by `deepagents.create_deep_agent`, plan-phase (with `interrupt_on`) + execute-phase for HITL
- **Built-in agents:** `agents/builtins.py` — 6 agents (WebSearch, Code, Document, API, Data, Orchestrator) + `get_subagents()` for DeepAgents SubAgent configs
- **Tools:** `tools/builtins.py` — 7 domain tools (web_search, execute_python, http_get, http_post, read_csv, describe_data, query_data) + `submit_plan` + 4 security tools. Filesystem tools (read_file, ls, glob, grep, write_file, edit_file) provided by DeepAgents built-in
- **HITL:** `approval.py` (Plan/Subtask dataclasses) + `tools/submit_plan.py` (plan submission + validation) + runner's `interrupt_on` for plan-phase pause
- **MCP:** MCP servers connect via `langchain-mcp-adapters` `MultiServerMCPClient` (runtime concern, not bundled)
- **MCP Servers:** `mcp_servers/` — FastMCP servers (osm_router, weather, rain_sensor) with mock fallback
- **Workflows:** `workflows/engine.py` — `run_sequential`, `run_parallel`, `run_conditional`
- **Memory:** `memory/store.py` — sliding-window utilities (legacy, DeepAgents manages context internally)
- **Types:** `types.py` — `AgentResult` (status/output/error/intermediate_steps/audit_trail)
- **Audit Trail:** `audit.py` — `AuditEntry`, `AuditTrail` + Context-Vars for full observability
- **Rules:** `rules/` — Markdown files with YAML frontmatter for agent configuration
- **Security:** `tools/security.py` — bandit_scan, secret_scan, audit_dependencies, security_scan

## Key conventions

- LLM backend is **Ollama-only**. No OpenAI/Anthropic adapters.
- Agentic loop powered by **DeepAgents** (`create_deep_agent` on LangGraph). LangChain/LangGraph types confined to `llm.py` and `runner.py`.
- No formatter, linter, type checker, or pre-commit hook configured.
- Orchestrator delegates via built-in `task` tool with custom SubAgents (max 20 iterations); all other agents default to 10.
- No generated code, no migrations, no build artifacts.
- Tool calling uses native Ollama tool-calling API (no text fallback needed). Default model: `gemma4:12b`.
- DeepAgents provides built-in filesystem tools (read_file, ls, glob, grep, write_file, edit_file). Agent-smith domain tools (web_search, execute_python, http_get/post, read_csv, describe/query_data) are passed via `tools=`.
- HITL plan-phase uses DeepAgents `interrupt_on={"submit_plan": True}` to pause before plan submission.<tool_call>- **Entrypoints:** `agent_smith.run()` or direct `run_web_search()`, `run_code()`, etc.
- **Agent runner:** `agents/runner.py` — agentic loop powered by `deepagents.create_deep_agent`, plan-phase (with `interrupt_on`) + execute-phase for HITL
- **HITL:** `approval.py` (Plan/Subtask dataclasses) + `tools/submit_plan.py` (plan submission + validation) + runner's `interrupt_on` for plan-phase pause
- **MCP:** MCP servers connect via `langchain-mcp-adapters` `MultiServerMCPClient` (runtime concern, not bundled)
- **MCP Servers:** `mcp_servers/` — FastMCP servers (osm_router, weather, rain_sensor) with mock fallback
- **Workflows:** `workflows/engine.py` — `run_sequential`, `run_parallel`, `run_conditional`
- **Memory:** `memory/store.py` — sliding-window utilities (legacy, DeepAgents manages context internally)
- **Types:** `types.py` — `AgentResult` (status/output/error/intermediate_steps/audit_trail)
- **Audit Trail:** `audit.py` — `AuditEntry`, `AuditTrail` + Context-Vars for full observability
- **Rules:** `rules/` — Markdown files with YAML frontmatter for agent configuration
- **Security:** `tools/security.py` — bandit_scan, secret_scan, audit_dependencies, security_scan

## Key conventions

- LLM backend is **Ollama-only**. No OpenAI/Anthropic adapters.
- Agentic loop powered by **DeepAgents** (`create_deep_agent` on LangGraph). LangChain/LangGraph types confined to `llm.py` and `runner.py`.
- No formatter, linter, type checker, or pre-commit hook configured.
- Orchestrator delegates via built-in `task` tool with custom SubAgents (max 20 iterations); all other agents default to 10.
- No generated code, no migrations, no build artifacts.
- Tool calling uses native Ollama tool-calling API (no text fallback needed). Default model: `gemma4:12b`.
- DeepAgents provides built-in filesystem tools (read_file, ls, glob, grep, write_file, edit_file). Agent-smith domain tools (web_search, execute_python, http_get/post, read_csv, describe/query_data) are passed via `tools=`.
- HITL plan-phase uses DeepAgents `interrupt_on={"submit_plan": True}` to pause before plan submission.

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
