---
title: "Features & Ideen"
author: "Marco Schrank"
date: "2026-07-30"
tags:
  - features
  - ideen
  - roadmap
abstract: "Lebendes Dokument zur Verfolgung aller Features, Ideen und geplanter Verbesserungen."
---

# Features & Ideen

> Lebendes Dokument zur Verfolgung aller Features, Ideen und geplanter Verbesserungen.
> Wird waehrend Code-Reviews, Refactorings und Planungssessions aktualisiert.

---

## Legende

| Status | Bedeutung |
|--------|-----------|
| `umgesetzt` | Implementiert und getestet |
| `geplant` | Aktuell in Arbeit oder naechster Sprint |
| `idee` | Bewertungswuerdig, noch nicht priorisiert |

---

## Umgesetzte Features

| Feature | Kategorie | Beschreibung |
|---------|-----------|-------------|
| Agentic Loop | Kern | `run_agent` mit Tool-Calling, Sliding-Window und Max-Iterationen |
| 6 vordefinierte Agenten | Agenten | WebSearch, Code, Document, API, Data, Orchestrator |
| 7 Domain-Tools | Tools | `web_search`, `execute_python`, `http_get`, `http_post`, `read_csv`, `describe_data`, `query_data`. Dateisystem-Tools via DeepAgents built-in |
| Rule-basierte Konfiguration | Konfiguration | Markdown+YAML-Frontmatter fuer Agenten-Definitionen in `rules/` |
| Workflow-Engine | Workflows | `run_sequential`, `run_parallel`, `run_conditional` |
| Memory-Utilities | Memory | `window()` (Sliding-Window), `last_assistant_text()` |
| Ollama-LLM-Backend | Infrastruktur | `OllamaConfig` + `make_llm`/`make_llm_with_tools` Factory |
| Docker-Setup | Infrastruktur | `Dockerfile.lc` + `docker-compose.yml` mit 3 Services |
| Unit-Tests | Testing | 16 gemockte Tests, 3 Integrationstests (Ollama noetig) |
| Orchestrator-Delegation | Agenten | SubAgents via DeepAgents' built-in `task`-Tool, generiert aus Rule-Dateien via `get_subagents()` |
| Convenience-API | Kern | `agent_smith.run()` als top-level Einstiegspunkt mit Agent-Dispatch |
| Human-in-the-Loop | Agenten | `run_interactive(task, approval_callback)` — Orchestrator plant zuerst, holt User-Bestaetigung, fuehrt dann aus. Strukturierter JSON-Plan via `submit_plan`-Tool, Callback-basierte Approval-Schnittstelle. Audit-Actions: `plan_submitted`, `plan_approved`, `plan_rejected`. |
| 4 Security-Tools | Sicherheit | `bandit_scan`, `secret_scan`, `audit_dependencies`, `security_scan` — Defense-in-Depth mit gitleaks/Regex-Fallback, bandit, pip-audit |

---

## Ideen & Verbesserungen

| Idee | Kategorie | Status | Prioritaet | Beschreibung |
|------|-----------|--------|------------|-------------|
| `execute_python` Sandboxing | Sicherheit | idee | hoch | Code-Ausfuehrung in Sandbox/Container mit Ressourcen-Limits, Network-Restrictions |
| Test-Abdeckung erhoebern | Testing | geplant | hoch | Tests fuer Rules-Parser, SubAgent-Konfiguration, Security-Tools, parallel/conditional Workflows |
| Bessere System-Prompts | Qualitaet | geplant | mittel | Ausgabeformat-Spezifikation, strukturierte Antworten, konkretere Anweisungen |
| Formatter/Linter | Tooling | idee | mittel | ruff, mypy, pre-commit hooks einrichten |
| `_trim`/`window` Deduplizierung | Refactoring | idee | niedrig | `runner._trim()` und `memory.store.window()` sind funktionsgleich — eine Loesung behalten |
| Strukturierte Fehler in SubAgent-Ergebnissen | Qualitaet | idee | niedrig | Fehler als Dict statt String zurueckgeben (aktuell nur String aus DeepAgents) |
| Dynamische Tool-Registrierung | Architektur | idee | niedrig | Kein Import-Seiteneffekt in `tools/__init__.py`, stattdessen explizite Registrierung |
| `get_tools()` Warning bei unbekannten Namen | Qualitaet | idee | niedrig | Aktuell werden unbekannte Tool-Namen still ignoriert |
| DeepAgents-Migration | Refactoring | umgesetzt | mittel | Siehe Abschnitt [DeepAgents-Migration](#deepagents-migration) unten — migriert auf deepagents 0.6.12 |
| Gradio Web-Client (Client-Server) | UI | idee | hoch | Siehe Abschnitt [Gradio Web-Client](#gradio-web-client) unten |

---

## DeepAgents-Migration

> Evaluierung: Lassen sich Teile von agent-smith durch `deepagents` (LangChains neues Agent-Harness) ersetzen oder vereinfachen?

`deepagents` ist ein Batterien-inklusive-Framework auf Basis von LangChain + LangGraph. Es liefert out-of-the-box: Agentic Loop, Subagent-Delegation, HITL-Interrupts, Context-Management, MCP-Integration, Dateisystem-Tools und Sandboxing.

### Betroffene Komponenten

| Datei | Heute (Zeilen) | Mit DeepAgents | Ersparnis |
|-------|----------------|----------------|-----------|
| `runner.py` | ~544 | ~50 (nur noch Config + Execute-Rest) | ~90% |
| `approval.py` | ~120 | 0 (komplett entfallen) | 100% |
| `submit_plan.py` | ~91 | 0 | 100% |
| `tools/__init__.py` | ~19 | ~5 (nur Tool-Liste) | ~75% |
| `memory/store.py` | ~35 | 0 | 100% |
| `audit.py` | ~80 | 0 (LangSmith-Tracing) | 100% |
| **Gesamt** | **~890** | **~55** | **~94%** |

### Im Detail

#### 1. Agentic Loop → `create_deep_agent`

**Heute:** `run_agent()` in `runner.py` — ~60 Zeilen:
- LLM-Call mit `make_llm_with_tools` / `make_llm`
- Message-Aufbau: `[SystemMessage, HumanMessage]`
- Loop mit Sliding-Window (`_trim`)
- Tool-Call-Execution via `_execute_tool_calls` (native `tool_calls`)
- Ergebnis-Rückgabe

**Mit DeepAgents:**
```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="ollama:gemma4:12b",
    tools=[web_search, execute_python, read_file, http_get, http_post, read_csv, query_data, describe_data],
)
result = agent.invoke({"messages": [{"role": "user", "content": task}]})
```

**Entfällt:**
- Message-Management (`SystemMessage`, `HumanMessage`, `ToolMessage`)
- Sliding-Window (`_trim`, `memory.store.window`)
- `make_llm_with_tools` / `bind_tools`
- `_execute_tool_calls`
- `AgentConfig`-Dataclass
- `AgentConfig.max_iterations`-Loop

#### 2. HITL-Planungs-Flow → `human_in_the_loop=True`

**Heute:** 4 Dateien + ~250 Zeilen:
- `approval.py` — `Plan`, `Subtask`, `ApprovalDecision`, `_parse_subtask`, `VALID_AGENTS`
- `submit_plan.py` — `submit_plan`-Tool, `_coerce_subtasks`, `parse_plan_from_args`
- `runner.py:334-425` — `run_agent_plan_phase` (eigener Loop nur für `submit_plan`)
- `runner.py:428-525` — `run_agent_execute_phase` (deterministische Ausführung)
- `__init__.py:61-105` — `run_interactive` (verbindet Plan + Approval + Execute)

**Mit DeepAgents:**
```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="ollama:gemma4:12b",
    tools=ALL_TOOLS,
    human_in_the_loop=True,  # LangGraph-Interrupts
)
```

**Entfällt:**
- `Plan` / `Subtask` / `ApprovalDecision` — Dataclasses
- `submit_plan` — Spezial-Tool
- `_coerce_subtasks` — Validierung
- Zwei-Phasen-Flow (plan → execute)
- Approval-Callback-Interface

#### 3. Subagent-Delegation → built-in `task`-Tool

**Heute:** `delegate_to`-Tool + `_delegate_sync`-Wrapper in `runner.py:528-544`:
```python
def _delegate_sync(agent: str, task: str, ...) -> str:
    dispatch = {
        "WebSearchAgent": run_web_search,
        "CodeExecutionAgent": run_code,
        ...
    }
    runner = dispatch.get(agent)
    return runner(task)
```

**Mit DeepAgents:** Subagent-Spawning ist built-in. Der Agent ruft selbstständig `task` auf. Context-Isolation erfolgt automatisch — der Subagent sieht nur das Ergebnis, nicht den gesamten Verlauf.

**Entfällt:**
- `tools/delegate.py`
- `_delegate_sync`
- Manuelle Dispatch-Map
- Lazy-Import-Pattern (Arbeitaround für Zirkularimporte)

#### 4. Tool-Registrierung → `tools=[...]`

**Heute:**
```python
# tools/builtins.py
ALL_TOOLS = [web_search, execute_python, ...]
TOOL_MAP = {t.name: t for t in ALL_TOOLS}

# tools/__init__.py (manuelles Nachregistrieren)
for _t in (bandit_scan, secret_scan, ...):
    ALL_TOOLS.append(_t)
    TOOL_MAP[_t.name] = _t
```

**Mit DeepAgents:** `create_deep_agent(tools=[...])` — keine globale Registry nötig.

#### 5. Audit-Trail → LangSmith

**Heute:** Eigenes `AuditTrail` mit Context-Vars in `audit.py`:
```python
class AuditTrail:
    entries: list[AuditEntry]
    def log(self, level, agent, action, ...): ...
    def format(self): ...
```

**Mit DeepAgents:** LangSmith-Tracing ist integriert. Projektspezifische Audit-Events können als Custom-Spans hinzugefügt werden, aber das Grundgerüst entfällt.

### Nicht betroffen / bleibt

| Komponente | Begründung |
|------------|-----------|
| `mcp_routing.py` | Applikationslogik (Keyword-Matching), kein Framework-Thema |
| `mcp_servers/` | Eigene Datenquellen (osm_router, weather) — bleiben unverändert |
| `mcp_clients.py` | Kann durch DeepAgents' MCP-Middleware ersetzt werden (optional) |
| `rules/` + `rules.py` | Markdown-Frontmatter könnte durch DeepAgents-Profile ersetzt werden, aber optional |
| `types.py` | `AgentResult` bleibt als Domain-Dataclass erhalten |
| `llm.py` | `OllamaConfig` bleibt — DeepAgents nutzt `init_chat_model` aus LangChain |
| Security-Tools | Unabhängig (`security_scan`, `bandit_scan`, etc.) |
| `workflows/engine.py` | Kann durch LangGraph-Graphen ersetzt werden, aber bestehende API ist schlanker |

### Risiken / Offene Punkte

| Punkt | Beschreibung | Status |
|-------|-------------|--------|
| ~~**Ollama + Fallback-Parsing**~~ | ~~Text-Fallback-Parser könnte fehlen~~ — **gelöst**: `gemma4:12b` liefert native `tool_calls`, Fallback entfernt | ✅ gelöst |
| **MCP-Routing-Fallback** | Aktuell implementiert `runner.py` einen expliziten Fallback (MCP-Fehler → WebSearchAgent). Mit DeepAgents' MCP-Middleware müsste das anders gelöst werden. | offen |
| **Abhängigkeit** | `deepagents` ist ein zusätzliches Dependency. Aktuell hat agent-smith nur `langchain>=1.0.0`. | offen |
| **LangGraph-Runtime** | DeepAgents setzt LangGraph voraus. Das bedeutet State-Graphen statt einfacher Funktionen — mächtiger, aber komplexer. | offen |

---

## Gradio Web-Client

> Konzept für eine grafische Web-Oberfläche für agent-smith als Client-Server-System.

### Motivation

agent-smith ist aktuell eine reine Bibliothek (`python -c "import agent_smith; ..."` oder
Skripte in `examples/`). Für Demos, nicht-technische Nutzer und schnelle Experimente fehlt
eine grafische Oberfläche. Der Web-Client soll die bestehende API nutzen, ohne die Core-Logik
zu verändern.

### Architektur-Überblick

```
┌─────────────────┐     HTTP/WS      ┌──────────────────┐     Funktional     ┌─────────────────┐     HTTP      ┌────────┐
│  Gradio Web-UI  │ ◄──────────────► │  FastAPI Server  │ ◄─────────────────► │  agent-smith     │ ◄──────────► │ Ollama │
│  (Client)       │                  │  (API-Gateway)    │                    │  (Core)          │              └────────┘
└─────────────────┘                  └──────────────────┘                    └─────────────────┘
                                             │
                                             │ HTTP/SSE
                                             ▼
                                     ┌──────────────────┐
                                     │  MCP-Server       │
                                     │  (osm, weather)   │
                                     └──────────────────┘
```

Die Trennung in API-Server und Gradio-Client hat mehrere Vorteile:

- **Wiederverwendbarkeit** — Die API ist unabhängig vom Client. Spätere Clients (CLI-Rich,
  Mobile, Third-Party) können dieselben Endpunkte nutzen.
- **Streaming** — WebSocket/SSE ermöglicht Live-Anzeige von Agent-Schritten, Tool-Calls und
  Audit-Einträgen, während der Agent läuft.
- **HITL-Approval** — Interaktive Plan-Freigabe über asynchrone Callbacks, ohne den Agent zu
  blockieren.
- **Sicherheit** — Der Server kapselt Ollama-/MCP-Zugriff. Der Client braucht keine direkte
  Netzwerkverbindung zu Ollama.

### Komponenten

#### 1. API-Server (`server/api.py`) — FastAPI

Wrapt die agent-smith Core-API als REST- + WebSocket-Endpunkte. Neu hinzuzufügen, keine
Änderungen an bestehendem Core-Code.

| Endpunkt | Methode | Zweck |
|----------|---------|-------|
| `/api/agents` | GET | Verfügbare Agenten auflisten (`_AGENT_MAP.keys()`) |
| `/api/models` | GET | Verfügbare Ollama-Modelle auflisten (`ollama list`) |
| `/api/run` | POST | Agent-Task starten — `agent_smith.run(task, agent, model)` |
| `/ws/chat` | WS | Streaming-Chat: Agent-Schritte live, Token-Streaming, Tool-Call-Events |
| `/ws/hitl` | WS | HITL-Flow: Plan einsehen → genehmigen/ablehnen → Ausführung fortsetzen |
| `/api/audit/{run_id}` | GET | Audit-Trail einer spezifischen Run abrufen |

**Streaming-Events über WebSocket (JSON pro Zeile):**

```json
{"event": "llm_call", "agent": "WebSearchAgent", "iteration": 1}
{"event": "tool_call", "tool": "web_search", "args": {"query": "..."}}
{"event": "tool_result", "tool": "web_search", "result": "..."}
{"event": "delegate", "agent": "WebSearchAgent", "task": "..."}
{"event": "delegate_result", "agent": "WebSearchAgent", "result": "..."}
{"event": "done", "output": "...", "success": true}
```

**HITL-Flow über WebSocket:**

```
Client ──► POST /api/run (mode=interactive) ──► Server
Client ◄── {"event": "plan_submitted", "plan": {...}} ── Server
Client ──► {"action": "approve"} oder {"action": "reject", "feedback": "..."} ──► Server
Client ◄── {"event": "done", "output": "..."} ── Server
```

#### 2. Gradio Web-UI (`client/app.py`)

Die Gradio-App läuft als eigenständiger Prozess und kommuniziert ausschließlich über die
API-Endpunkte. Gradio's `launch()` startet einen eingebetteten Webserver.

**UI-Komponenten:**

| Komponente | Gradio-Element | Beschreibung |
|------------|-----------------|--------------|
| Chat-Verlauf | `gr.ChatInterface` oder `gr.Chatbot` | Streaming-Nachrichten, Agent-Antworten |
| Agent-Auswahl | `gr.Dropdown` | Wählt aus `_AGENT_MAP` (web_search, code, …, orchestrator) |
| Modell-Auswahl | `gr.Dropdown` | Wählt Ollama-Modell (Default: `gemma4:12b`) |
| HITL-Plan-Dialog | `gr.Accordion` + `gr.Button` | Plan einsehen → Genehmigen/Ablehnen |
| Audit-Trail-Viewer | `gr.JSON` oder `gr.Markdown` | Live-Audit-Events formatiert |
| Tool-Call-Anzeige | `gr.Accordion` (kollabierbar) | Zeigt jeden Tool-Call + Ergebnis |
| Status-Indikator | `gr.Markdown` od. `gr.Progress` | "Läuft…", "Warte auf Freigabe", "Fertig" |

**Chat-Modi:**

1. **Direct Mode** — `run(task, agent)` → Ergebnis anzeigen (kein Streaming nötig)
2. **Streaming Mode** — WebSocket `/ws/chat` → Live-Schritte anzeigen
3. **HITL Mode** — WebSocket `/ws/hitl` → Plan-Freigabe interaktiv

#### 3. Run-Manager (`server/run_manager.py`)

Verwaltet asynchrone Agent-Runs mit eindeutigen IDs. Da agent-smith synchron ist
(`run_agent()` blockiert), läuft jeder Run in einem Thread/Task.

```python
@dataclass
class RunHandle:
    run_id: str
    status: Literal["running", "awaiting_approval", "done", "failed"]
    result: AgentResult | None
    audit_trail: AuditTrail
    approval_event: threading.Event  # HITL-Synchronisation
```

### Verzeichnisstruktur (vorgeschlagen)

```
agent-smith/
├── agent_smith/              # Core (unverändert)
├── server/                   # Neu: API-Server
│   ├── __init__.py
│   ├── api.py                # FastAPI-App + Endpunkte
│   ├── run_manager.py        # Async Run-Verwaltung
│   └── ws_handlers.py        # WebSocket-Handler (chat, hitl)
├── client/                   # Neu: Gradio Web-UI
│   ├── __init__.py
│   ├── app.py                # Gradio-App-Einstieg
│   ├── components.py         # UI-Komponenten (Chat, Audit, HITL)
│   └── api_client.py         # HTTP/WS-Client für server/
├── mcp_servers/              # Bestehend (unverändert)
└── ...
```

### Neue Dependencies

| Paket | Zweck |
|-------|-------|
| `fastapi` | API-Server (REST + WebSocket) |
| `uvicorn` | ASGI-Server für FastAPI |
| `gradio` (≥4.0) | Web-UI mit Streaming-Chat, HITL-Dialogen |
| `httpx` |bereits vorhanden — Client nutzt es für API-Calls |

### Deployment-Varianten

| Variante | Server | Client | Einsatz |
|----------|--------|--------|---------|
| **Single-Process** | FastAPI + Gradio in einem Prozess (`gr.mount_gradio_app`) | Eingebettet | Lokale Demo, Single-User |
| **Two-Process** | FastAPI separat (`uvicorn server.api:app`) | Gradio separat (`python client/app.py`) | Remote-Server, Multi-User |
| **Docker** | `docker-compose` mit 3 Services (api, gradio, ollama) | Eigener Container | Produktion |

### Integration mit bestehender Architektur

- **Keine Core-Änderungen** — Server nutzt ausschließlich die öffentliche API (`run()`,
  `run_interactive()`, `AuditTrail`, `AgentResult`).
- **HITL-Brücke** — `run_interactive()` erwartet einen `approval_callback`. Der Server
  implementiert einen asynchronen Callback, der über WebSocket auf die Client-Antwort wartet.
- **Audit-Streaming** — `AuditTrail` wird um einen optionalen Callback erweitert (oder per
  Context-Var-Polling ausgelesen), um Events live an den WebSocket zu pushen.
- **MCP-Server** — Bleiben unverändert. Der Server greift über `mcp_clients.py` zu.

### Risiken / Offene Punkte

| Punkt | Beschreibung |
|-------|-------------|
| **Synchroner Core** | `run_agent()` blockiert. Run muss in Thread/Task ausgelagert werden. Streaming erfordert Polling oder Refactoring auf Generator/Async. |
| **HITL-Timeout** | Wenn der Client nicht antwortet, muss der Server den Run nach Timeout abbrechen. |
| **Streaming-Architektur** | Aktuell gibt `run_agent()` erst am Ende ein `AgentResult`. Für Live-Streaming müsste entweder der Audit-Trail gepollt oder `run_agent()` als Generator refactored werden. |
| **Sicherheit** | API-Server sollte Auth/CORS konfigurieren, wenn er im Netzwerk暴露iert wird. |
| **Gradio-Version** | Gradio ≥4.0 für `gr.ChatInterface`-Streaming. API kann sich zwischen Versionen ändern. |
| **State-Management** | Multi-User-Betrieb erfordert Session-Tracking und Run-Isolierung. |

### MVP-Scope (erster Schritt)

1. FastAPI-Server mit `POST /api/run` (blocking, kein Streaming)
2. Gradio-Client mit Agent-Dropdown + Chat-Ausgabe
3. Audit-Trail als послеgelagertes `gr.JSON` (nicht live)
4. Single-Process-Deployment (`gr.mount_gradio_app`)

Streaming und HITL folgen in Phase 2.
