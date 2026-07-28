---
title: "Architektur — agent-smith (LangChain Edition)"
author: "Marco Schrank"
date: "2026-07-28"
tags:
  - architektur
  - langchain
  - systemdesign
  - hitl
abstract: "Vollständige Architekturbeschreibung der LangChain-basierten Agenten-Engine inkl. Human-in-the-Loop-Flow."
---

# Architektur — agent-smith (LangChain Edition)

> Vollstaendige Architekturbeschreibung der LangChain-basierten Agenten-Engine.

---

## 1. Einfuehrung

agent-smith ist eine modulare Agenten-Engine fuer Ollama-basierte LLMs. Die Architektur
folgt einem streng funktionalen Paradigma — keine Agenten-Klassen, keine Vererbung,
keine Framework-Abstraktionen jenseits der LangChain-Nutzung in isolierten Modulen.

**Kernprinzipien:**

- **Funktionaler Stil** — Alles sind Funktionen und Dataclasses, keine Klassen hierarchien
- **LangChain-Isolation** — LangChain-Typen nur in `llm.py`, `runner.py`, `memory/store.py`, `tools/builtins.py`, `tools/delegate.py`
- **Ollama-only** — Keine OpenAI/Anthropic/andere Provider
- **Rule-basierte Agenten** — Agentenkonfiguration in Markdown-Dateien mit YAML-Frontmatter
- **Audit Trail** — Vollstaendige Nachverfolgung aller LLM-Aufrufe, Tool-Calls und Delegationen

---

## 2. Verzeichnisstruktur

```
agent-smith/
├── agent_smith/                 # Kernpaket
│   ├── __init__.py             # Oeffentliche API, run()/run_interactive()
│   ├── types.py                # Status, AgentResult
│   ├── llm.py                  # OllamaConfig, LLM-Factory
│   ├── rules.py                # Markdown-Frontmatter-Parser
│   ├── audit.py                # AuditTrail, AuditEntry + Context-Vars
│   ├── approval.py             # Subtask, Plan, ApprovalDecision (HITL)
│   ├── agents/
│   │   ├── __init__.py         # Re-exports
│   │   ├── runner.py           # Agentic-Loop + Plan/Execute-Phase
│   │   └── builtins.py         # 6 vordefinierte Agenten
│   ├── tools/
│   │   ├── __init__.py         # Re-exports + delegate_to/submit_plan Registrierung
│   │   ├── builtins.py         # 9 Standard-Tools + Registry
│   │   ├── delegate.py         # Orchestrator-Delegationstool (mit Audit)
│   │   └── submit_plan.py      # Plan-Submission-Tool (HITL)
│   ├── memory/
│   │   ├── __init__.py         # Re-exports
│   │   └── store.py            # Sliding-Window, last_assistant_text
│   └── workflows/
│       ├── __init__.py         # Re-exports
│       └── engine.py           # Sequential, Parallel, Conditional
├── mcp_servers/                # MCP-Server (extern)
│   └── rain_sensor/
│       └── server.py           # Rain Sensor Mock-Server (SSE)
├── rules/                      # Agenten-Definitionen (Markdown)
│   ├── web_search.md
│   ├── code.md
│   ├── document.md
│   ├── api.md
│   ├── data.md
│   └── orchestrator.md
├── tests/                      # Unit- und Integrationstests
│   ├── test_agent_smith.py
│   ├── test_hitl.py            # HITL-spezifische Tests
│   └── test_ollama_integration.py
├── docs/                       # Dokumentation
├── examples/                   # Beispielcode
├── pyproject.toml              # Build-Config + Abhaengigkeiten
└── AGENTS.md                   # Agenten-Infrastruktur-Doku
```

---

## 3. Abhaengigkeiten

### 3.1 Externe Pakete

| Paket | Version | Zweck |
|-------|---------|-------|
| `langchain` | >=1.0.0 | LLM-Framework (Message-Typen, Tool-Decorator) |
| `langchain-ollama` | >=0.3.0 | Ollama LLM-Provider (`ChatOllama`) |
| `langchain-community` | >=0.3.0 | Community-Integrationen |
| `langchain-core` | >=0.3.0 | Core-Typen (`AIMessage`, `ToolMessage`, etc.) |
| `httpx` | >=0.27.0 | HTTP-Client fuer `http_get`/`http_post` |
| `pandas` | >=2.0.0 | CSV-/Data-Analyse-Tools |
| `ddgs` | >=7.0.0 | DuckDuckGo-Suche (`web_search`) |
| `mcp[cli]` | >=1.27 | MCP-Server-SDK (fuer rain_sensor) |

### 3.2 Interne Abhaengigkeiten

```mermaid
graph TD
    subgraph "agent_smith/__init__.py"
        INIT["__init__.py<br/>(run, _AGENT_MAP)"]
    end

    subgraph "Kernmodule"
        TYPES["types.py<br/>(Status, AgentResult)"]
        LLM["llm.py<br/>(OllamaConfig, make_llm)"]
        RULES["rules.py<br/>(load_rule)"]
        AUDIT["audit.py<br/>(AuditTrail, AuditEntry, Context-Vars)"]
    end

    subgraph "agents/"
        RUNNER["runner.py<br/>(AgentConfig, run_agent)"]
        BUILTINS_A["builtins.py<br/>(6 Agent-Factorys)"]
    end

    subgraph "tools/"
        TOOLS_B["builtins.py<br/>(9 Tools, TOOL_MAP)"]
        DELEGATE["delegate.py<br/>(delegate_to, Audit-Logging)"]
        SUBMIT_PLAN["submit_plan.py<br/>(submit_plan, HITL)"]
        TOOLS_INIT["__init__.py<br/>(Registrierung)"]
    end

    subgraph "workflows/"
        ENGINE["engine.py<br/>(Step, WorkflowResult)"]
    end

    subgraph "memory/"
        STORE["store.py<br/>(window, last_assistant_text)"]
    end

    subgraph "mcp_servers/"
        MCP["rain_sensor/server.py<br/>(Mock Regensensoren)"]
    end

    RUNNER --> LLM
    RUNNER --> TOOLS_B
    RUNNER --> TYPES
    RUNNER --> AUDIT
    BUILTINS_A --> RUNNER
    BUILTINS_A --> LLM
    BUILTINS_A --> RULES
    BUILTINS_A --> TYPES
    BUILTINS_A --> AUDIT
    TOOLS_INIT --> TOOLS_B
    TOOLS_INIT --> DELEGATE
    TOOLS_INIT --> SUBMIT_PLAN
    DELEGATE --> AUDIT
    SUBMIT_PLAN --> AUDIT
    ENGINE --> RUNNER
    ENGINE --> TYPES
    INIT --> RUNNER
    INIT --> BUILTINS_A
    INIT --> LLM
    INIT --> TYPES
    INIT --> ENGINE
```

---

## 4. Kernkomponenten

### 4.1 [`types.py`](../agent_smith/types.py) — Domaintypen

Keine externen Abhaengigkeiten. Reine stdlib-Typen.

```python
class Status(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class AgentResult:
    status: Status
    output: Any
    error: str | None = None
    intermediate_steps: list = field(default_factory=list)
    audit_trail: AuditTrail = field(default_factory=AuditTrail)

    @property
    def success(self) -> bool: ...
    @classmethod
    def ok(cls, output, steps=None, audit_trail=None) -> AgentResult: ...
    @classmethod
    def fail(cls, error, audit_trail=None) -> AgentResult: ...
```

`AgentResult` ist das einheitliche Rueckgabeprotokoll aller Agenten-Aufrufe.
Das `audit_trail`-Feld enthaelt die vollstaendige Protokollierung aller Schritte.

### 4.2 [`llm.py`](../agent_smith/llm.py) — LLM-Factory

Einziges Modul (neben `runner.py`), das `ChatOllama` importiert.

```python
@dataclass(frozen=True)
class OllamaConfig:
    model: str = "qwen3:8b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    options: dict[str, Any] = field(default_factory=dict)

def make_llm(config: OllamaConfig) -> ChatOllama: ...
def make_llm_with_tools(config: OllamaConfig, tools: list) -> ChatOllama: ...
```

`make_llm_with_tools` ruft `make_llm(config).bind_tools(tools)` — so wird das
LangChain-Tool-Calling-Protocol verknuepft.

### 4.3 [`rules.py`](../agent_smith/rules.py) — Frontmatter-Parser

Liest Markdown-Dateien aus `rules/`, parst YAML-Frontmatter (hand-rolled, kein
yaml-Dependency) und liefert ein Konfigurationsdict.

```python
def load_rule(name: str) -> dict:
    """Laedt rules/{name}.md, parsed Frontmatter, liefert config-dict mit 'system_prompt'."""
```

**Parser-Logik:**
- Werte werden automatisch in int, bool oder komma-separierte Liste konvertiert
- Der Markdown-Body wird als `system_prompt` zurueckgegeben
- Einzelne Tool-Strings werden zu Listen normalisiert

### 4.4 [`agents/runner.py`](../agent_smith/agents/runner.py) — Agentic-Loop

Das Herzstueck. Eine einzige Funktion `run_agent` fuer den agentic loop,
plus zwei HITL-spezifische Phasen-Funktionen.

```python
MAX_ITERATIONS = 10

@dataclass(frozen=True)
class AgentConfig:
    name: str
    system_prompt: str
    llm: OllamaConfig = field(default_factory=OllamaConfig)
    tools: list[str] | None = None
    max_iterations: int = MAX_ITERATIONS
    context_window: int = 20

def run_agent(
    task: str,
    config: AgentConfig,
    audit_trail: AuditTrail | None = None,
    level: int = 0,
) -> AgentResult: ...

def run_agent_plan_phase(
    task: str,
    config: AgentConfig,
    audit_trail: AuditTrail | None = None,
    level: int = 0,
) -> tuple[Plan | None, AgentResult]:
    """HITL Phase 1: fuehrt Agentic-Loop aus, bis submit_plan aufgerufen wird."""

def run_agent_execute_phase(
    task: str,
    plan: Plan,
    config: AgentConfig,
    audit_trail: AuditTrail | None = None,
    level: int = 0,
) -> AgentResult:
    """HITL Phase 2: fuehrt genehmigten Plan via delegate_to aus."""

def _trim(messages: list, max_messages: int) -> list: ...

def _execute_tool_calls(
    tool_calls: list,
    audit_trail: AuditTrail | None = None,
    level: int = 0,
    agent_name: str = "",
) -> list[ToolMessage]: ...
```

**Ablauf (siehe Abschnitt 6).**

### 4.5 [`agents/builtins.py`](../agent_smith/agents/builtins.py) — Vordefinierte Agenten

6 Agenten, jeweils als Factory-Funktion + Convenience-`run_*`-Funktion:

| Agent | Rule-Datei | Tools | max_iterations |
|-------|-----------|-------|----------------|
| WebSearchAgent | `web_search.md` | `web_search` | 10 |
| CodeExecutionAgent | `code.md` | `execute_python` | 10 |
| DocumentAgent | `document.md` | `read_file`, `list_files` | 10 |
| APIAgent | `api.md` | `http_get`, `http_post` | 10 |
| DataAgent | `data.md` | `read_csv`, `query_data`, `describe_data` | 10 |
| OrchestratorAgent | `orchestrator.md` | `submit_plan`, `delegate_to` | 20 |

Der Orchestrator erhaelt 20 Iterationen (doppelte Anzahl), da jede Delegation
als eine Iteration zaehlt.

**Pattern:**

```python
def _agent_from_rule(name, llm=None) -> AgentConfig:
    cfg = load_rule(name)
    return AgentConfig(
        name=cfg["name"],
        system_prompt=cfg["system_prompt"],
        llm=llm or OllamaConfig(),
        tools=cfg["tools"],
        max_iterations=cfg.get("max_iterations", 10),
        context_window=cfg.get("context_window", 20),
    )

def web_search_agent(llm=None) -> AgentConfig:
    return _agent_from_rule("web_search", llm)

def run_web_search(task, llm=None, audit_trail=None, level=0) -> AgentResult:
    return run_agent(task, web_search_agent(llm), audit_trail=audit_trail, level=level)
```

Alle `run_*`-Funktionen akzeptieren optionale `audit_trail`- und `level`-Parameter
fuer die vollstaendige Nachverfolgung.

### 4.6 [`tools/builtins.py`](../agent_smith/tools/builtins.py) — Standard-Tools

9 Tools, dekoriert mit LangChain `@tool`. Jedes Tool faengt Fehler ab und
liefert ein Dict statt Exceptions.

| Tool | Signatur | Beschreibung |
|------|----------|-------------|
| `web_search` | `(query: str, max_results: int = 5)` | DuckDuckGo-Suche |
| `execute_python` | `(code: str, timeout: int = 30)` | Python-Code in Subprocess |
| `read_file` | `(path: str, max_chars: int = 10000)` | Datei lesen |
| `list_files` | `(path: str = ".", pattern: str = "*")` | Dateien auflisten |
| `http_get` | `(url: str, headers?, params?)` | HTTP GET |
| `http_post` | `(url: str, body: dict, headers?)` | HTTP POST |
| `read_csv` | `(path: str, max_rows: int = 100)` | CSV lesen |
| `describe_data` | `(path: str)` | Pandas describe |
| `query_data` | `(path: str, query: str, columns?)` | Pandas query-Filter |

**Globale Registry:**

```python
ALL_TOOLS = [web_search, execute_python, read_file, list_files,
             http_get, http_post, read_csv, describe_data, query_data]

TOOL_MAP: dict[str, object] = {t.name: t for t in ALL_TOOLS}

def get_tools(names=None) -> list:
    """Tools nach Name zurueckgeben, oder alle wenn names=None."""
```

### 4.7 [`tools/delegate.py`](../agent_smith/tools/delegate.py) — Orchestrator-Tool

Wird exklusiv vom OrchestratorAgent genutzt. Verwendet lazy imports um
Zirkular-Abhaengigkeiten zu vermeiden. Nutzt Context-Variablen fuer
die Audit-Trail-Weitergabe.

```python
from agent_smith.audit import get_current_trail, get_current_level

@tool
def delegate_to(agent: str, task: str) -> str:
    """Delegiert Subtask an einen Specialist-Agenten."""
    trail = get_current_trail()
    level = get_current_level()

    if trail:
        trail.log(level=level, agent=agent, action="delegate", task=task)

    # Lazy import innerhalb der Funktion
    from agent_smith.agents.builtins import (
        run_api, run_code, run_data, run_document, run_web_search,
    )
    dispatch = {
        "WebSearchAgent": run_web_search,
        "CodeExecutionAgent": run_code,
        "DocumentAgent": run_document,
        "APIAgent": run_api,
        "DataAgent": run_data,
    }
    runner = dispatch.get(agent)
    if runner is None:
        return f"Unknown agent: {agent}"
    result = runner(task, audit_trail=trail, level=level + 1) if trail else runner(task)

    if trail:
        output = result.output if result.success else (result.error or "unknown error")
        trail.log(level=level, agent=agent, action="delegate_result",
                  result=str(output), success=result.success)

    return result.output if result.success else f"Agent failed: {result.error}"
```

**Context-Variablen:** Da `delegate_to` als LangChain-Tool von LLMs aufgerufen wird,
kann der Audit-Trail nicht als Parameter uebergeben werden. Stattdessen werden
`contextvars` verwendet, um den Trail implizit durch die Tool-Aufrufe zu leiten.

### 4.8 [`tools/__init__.py`](../agent_smith/tools/__init__.py) — Registrierung

```python
from agent_smith.tools.builtins import ALL_TOOLS, TOOL_MAP, get_tools
from agent_smith.tools.delegate import delegate_to
from agent_smith.tools.submit_plan import submit_plan

ALL_TOOLS.append(delegate_to)
TOOL_MAP["delegate_to"] = delegate_to
ALL_TOOLS.append(submit_plan)
TOOL_MAP["submit_plan"] = submit_plan
```

Mutiert `ALL_TOOLS` und `TOOL_MAP` zur Import-Zeit — `delegate_to` und
`submit_plan` sind danach im globalen Tool-Registry verfuegbar.

### 4.9 [`tools/submit_plan.py`](../agent_smith/tools/submit_plan.py) — Plan-Submission (HITL)

Wird vom OrchestratorAgent in der Plan-Phase des Human-in-the-Loop-Flows
genutzt. Nimmt strukturierte Argumente entgegen und validiert den Plan.

```python
@tool
def submit_plan(
    subtasks: list[dict],
    reasoning: str = "",
) -> str:
    """
    Args:
        subtasks: List of {agent, task} objects
        reasoning: Optional explanation
    """
    Plan(subtasks=_coerce_subtasks(subtasks), reasoning=reasoning)
    return PLAN_SUBMITTED_MARKER  # "PLAN_SUBMITTED"
```

**Validierung in `_coerce_subtasks`:**
- Agent muss aus `VALID_AGENTS` stammen
- Task darf nicht leer sein
- Subtasks-Liste darf nicht leer sein

**Zwei akzeptierte Eingabeformate via `parse_plan_from_args`:**
- `{"subtasks": [...], "reasoning": "..."}` — bevorzugtes Format (Qwen3)
- `{"plan_json": "<json string>"}` — Backward-Compat

### 4.10 [`approval.py`](../agent_smith/approval.py) — HITL-Datentypen

Reine Domain-Dataclasses fuer den Human-in-the-Loop-Flow. Keine
externen Abhaengigkeiten.

```python
@dataclass(frozen=True)
class Subtask:
    agent: str
    task: str

@dataclass
class Plan:
    subtasks: list[Subtask] = field(default_factory=list)
    reasoning: str = ""
    # to_json() / from_json() / format() Methoden

@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    feedback: str | None = None

VALID_AGENTS = (
    "WebSearchAgent", "CodeExecutionAgent", "DocumentAgent",
    "APIAgent", "DataAgent",
)
```

`Plan.from_json()` validiert strikt: leerer Subtasks-Liste, unbekannte Agenten
und leere Tasks werden abgelehnt.

### 4.11 [`memory/store.py`](../agent_smith/memory/store.py) — Memory-Utilities

Funktionale Wrapper fuer Nachrichtenlisten.

```python
def window(messages: list[BaseMessage], max_messages: int) -> list[BaseMessage]:
    """Sliding Window, bewahrt fuehrenden SystemMessage auf."""

def last_assistant_text(messages: list[BaseMessage]) -> str | None:
    """Letzten AIMessage-Text zurueckgeben."""
```

> **Bekanntes Problem:** `window()` ist funktionsgleich mit `runner._trim()`
> (Code-Duplizierung).

### 4.12 [`workflows/engine.py`](../agent_smith/workflows/engine.py) — Workflow-Engine

Drei Ausfuehrungsmodi fuer mehrstufige Agenten-Pipelines.

```python
@dataclass(frozen=True)
class Step:
    name: str
    agent: AgentConfig
    task_fn: Callable[[dict[str, AgentResult]], str]

@dataclass
class WorkflowResult:
    steps: dict[str, AgentResult]
    final: AgentResult | None = None

    @property
    def success(self) -> bool: ...

def run_sequential(steps: list[Step]) -> WorkflowResult: ...
def run_parallel(steps: list[Step], max_workers: int = 4) -> WorkflowResult: ...
def run_conditional(condition, if_true, if_false, prior_results=None) -> WorkflowResult: ...
```

| Modus | Beschreibung |
|-------|-------------|
| `run_sequential` | Schrittweise Ausfuehrung, Ergebnisse werden weitergegeben, Abbruch bei Fehler |
| `run_parallel` | ThreadPoolExecutor, alle Steps gleichzeitig, jeder bekommt leeres prior_results |
| `run_conditional` | Laufzeit-Bedingung waehlt Branch, dann sequential-Ausfuehrung |

### 4.13 [`__init__.py`](../agent_smith/__init__.py) — Oeffentliche API

```python
_Agent_MAP = {
    "web_search": run_web_search,
    "code": run_code,
    "document": run_document,
    "api": run_api,
    "data": run_data,
    "orchestrator": run_orchestrator,
}

def run(
    task: str,
    agent: str = "orchestrator",
    model: str = "qwen3:8b",
    base_url: str = "http://localhost:11434",
) -> AgentResult:
    """Convenience-Einstiegspunkt."""
    llm = OllamaConfig(model=model, base_url=base_url)
    runner = _AGENT_MAP.get(agent)
    if runner is None:
        raise ValueError(f"Unknown agent '{agent}'")
    return runner(task, llm=llm)


def run_interactive(
    task: str,
    approval_callback: Callable[[Plan], ApprovalDecision],
    model: str = "qwen3:8b",
    base_url: str = "http://localhost:11434",
) -> AgentResult:
    """
    Human-in-the-Loop: Orchestrator plant zuerst, holt User-Bestaetigung,
    fuehrt dann aus.
    """
    config = _load_orchestrator_config(model, base_url)
    plan, phase1_result = run_agent_plan_phase(task, config)
    if plan is None:
        return phase1_result
    decision = approval_callback(plan)
    if not decision.approved:
        phase1_result.audit_trail.log(
            level=0, agent=config.name, action="plan_rejected",
            task=decision.feedback,
        )
        return AgentResult.fail(
            f"Plan rejected by user: {decision.feedback or 'no feedback'}",
            audit_trail=phase1_result.audit_trail,
        )
    return run_agent_execute_phase(task, plan, config, audit_trail=phase1_result.audit_trail)
```

### 4.14 [`audit.py`](../agent_smith/audit.py) — Audit-Trail

Protokolliert alle LLM-Aufrufe, Tool-Calls und Delegationen.
Bietet strukturierte Konsolenausgabe und formatierte Berichte.

**Context-Variablen (fuer Tool-Delegation):**

```python
import contextvars

_current_audit_trail: contextvars.ContextVar[AuditTrail | None] = contextvars.ContextVar("audit_trail", default=None)
_current_level: contextvars.ContextVar[int] = contextvars.ContextVar("audit_level", default=0)

def set_audit_context(trail: AuditTrail | None, level: int = 0) -> tuple:
    """Setzt den aktuellen Audit-Kontext. Gibt Token zur Wiederherstellung zurueck."""
    t = _current_audit_trail.set(trail)
    l = _current_level.set(level)
    return (t, l)

def reset_audit_context(tokens) -> None:
    """Setzt den Audit-Kontext auf vorherige Werte zurueck."""
    if tokens:
        t, l = tokens
        _current_audit_trail.reset(t)
        _current_level.reset(l)

def get_current_trail() -> AuditTrail | None:
    return _current_audit_trail.get()

def get_current_level() -> int:
    return _current_level.get()
```

**AuditEntry:**

```python
@dataclass
class AuditEntry:
    timestamp: str
    level: int          # 0 = Orchestrator, 1 = Subagent, 2 = ...
    agent: str          # Name des Agenten
    action: str         # "llm_call" | "tool_call" | "tool_result" | "delegate" | "delegate_result" | "plan_submitted" | "plan_approved" | "plan_rejected"
    task: str | None = None
    tool_name: str | None = None
    args: dict | None = None
    result: str | None = None
    success: bool = True
    iteration: int | None = None
```

**AuditTrail:**

```python
@dataclass
class AuditTrail:
    entries: list[AuditEntry] = field(default_factory=list)

    def log(self, **kwargs) -> None:
        """Erstellt einen neuen Audit-Eintrag und gibt ihn auf stderr aus."""
        ...

    def format(self) -> str:
        """Formatierte Ausgabe aller Eintraege."""
        ...
```

**Beispiel-Ausgabe:**

```
[0] LLM Call (iteration 1)
[0] TOOL: delegate_to({'agent': 'WebSearchAgent', 'task': '...'})
[0] DELEGATE -> WebSearchAgent
    Task: What is the capital of France?
  [1] LLM Call (iteration 1)
  [1] TOOL: web_search({'query': 'capital of France'})
  [1] RESULT: [{'title': 'Paris', ...}]
  [1] LLM Call (iteration 2)
[0] RESULT [OK] from WebSearchAgent
    Output: Paris ist die Hauptstadt von Frankreich...
[0] LLM Call (iteration 2)
```

---

## 5. Rules-System

Jeder Agent wird durch eine Markdown-Datei in `rules/` definiert.

### Format

```markdown
---
name: AgentName
tools: tool1, tool2
max_iterations: 10
context_window: 20
---

System-Prompt als Fliesstext.
Beschreibt die Rolle und Grenzen des Agenten.
```

### Uebersicht aller Rules

| Datei | Agent | Tools | max_iter | context_window |
|-------|-------|-------|----------|----------------|
| `web_search.md` | WebSearchAgent | `web_search` | 10 | 20 |
| `code.md` | CodeExecutionAgent | `execute_python` | 10 | 20 |
| `document.md` | DocumentAgent | `read_file`, `list_files` | 10 | 20 |
| `api.md` | APIAgent | `http_get`, `http_post` | 10 | 20 |
| `data.md` | DataAgent | `read_csv`, `query_data`, `describe_data` | 10 | 20 |
| `orchestrator.md` | OrchestratorAgent | `submit_plan`, `delegate_to` | 20 | 20 |

---

## 6. Agentic-Loop

```mermaid
flowchart TD
    START(["run_agent(task, config)"]) --> INIT["tools = get_tools(config.tools)<br/>llm = make_llm_with_tools(config.llm, tools)<br/>messages = [SystemMessage, HumanMessage]"]
    INIT --> LOOP{"iteration < max_iterations?"}

    LOOP -- Ja --> AUDIT_LOG["audit_trail.log(action='llm_call', level=level)"]
    AUDIT_LOG --> TRIM["windowed = _trim(messages, context_window)"]
    TRIM --> INVOKE["response = llm.invoke(windowed)"]

    INVOKE -- Exception --> FAIL["return AgentResult.fail(error)"]

    INVOKE -- OK --> APPEND["messages.append(response)"]
    APPEND --> HAS_TOOLS{"response.tool_calls?"}

    HAS_TOOLS -- Nein --> DONE["return AgentResult.ok(response.content)"]
    HAS_TOOLS -- Ja --> EXEC["_execute_tool_calls(tool_calls, audit_trail, level)"]
    EXEC --> EXTEND["messages.extend(tool_messages)<br/>intermediate_steps.extend(...)"]
    EXTEND --> LOOP

    LOOP -- Nein --> MAX["return AgentResult.fail('Max iterations reached')"]

    style START fill:#4CAF50,color:#fff
    style DONE fill:#4CAF50,color:#fff
    style FAIL fill:#f44336,color:#fff
    style MAX fill:#f44336,color:#fff
```

**Schluessel-Details:**

1. **Sliding Window** — `_trim()` bewahrt immer den fuehrenden `SystemMessage` auf
2. **Tool-Ausfuehrung** — Jeder Tool-Call wird einzeln ausgefuehrt, Fehler werden als JSON-String in `ToolMessage` zurueckgegeben
3. **Audit-Trail** — Jeder LLM-Aufruf und Tool-Call wird protokolliert
4. **Abbruchbedingungen:** Text-Antwort (Erfolg), LLM-Ausnahme (Fehler), Max-Iterationen (Fehler)

---

## 7. Tool-Registry

```mermaid
flowchart LR
    subgraph "tools/builtins.py"
        T1[web_search]
        T2[execute_python]
        T3[read_file]
        T4[list_files]
        T5[http_get]
        T6[http_post]
        T7[read_csv]
        T8[describe_data]
        T9[query_data]
        ALL["ALL_TOOLS (Liste)"]
        MAP["TOOL_MAP (Dict)"]
    end

    subgraph "tools/__init__.py"
        REG["Registrierung"]
        D[delegate_to]
        SP[submit_plan]
    end

    T1 --> ALL
    T2 --> ALL
    T3 --> ALL
    T4 --> ALL
    T5 --> ALL
    T6 --> ALL
    T7 --> ALL
    T8 --> ALL
    T9 --> ALL
    ALL --> MAP
    D --> REG
    SP --> REG
    REG -->|append| ALL
    REG -->|TOOL_MAP['delegate_to']| MAP
    REG -->|TOOL_MAP['submit_plan']| MAP

    subgraph "agents/runner.py"
        GET["get_tools(names)"]
        LOOKUP["TOOL_MAP[name]"]
    end

    MAP --> GET
    MAP --> LOOKUP
```

**`get_tools(names)`** — Liefert Tools nach Name, oder alle Tools wenn `names=None`.

---

## 8. Orchestrator-Delegation

```mermaid
sequenceDiagram
    participant U as User
    participant O as OrchestratorAgent
    participant D as delegate_to
    participant S as Specialist (z.B. WebSearchAgent)
    participant A as AuditTrail

    U->>O: task
    Note over O: audit_trail.log(level=0, action="llm_call")
    O->>O: LLM entscheidet: delegate_to(agent, task)
    Note over O: audit_trail.log(level=0, action="tool_call")
    O->>D: delegate_to("WebSearchAgent", "Finde Info X")
    Note over D: get_current_trail() via contextvars
    Note over D: audit_trail.log(level=0, action="delegate")
    D->>S: run_web_search("Finde Info X", audit_trail, level=1)
    Note over S: audit_trail.log(level=1, action="llm_call")
    S->>S: agentic loop (web_search tool)
    Note over S: audit_trail.log(level=1, action="tool_call")
    Note over S: audit_trail.log(level=1, action="tool_result")
    S-->>D: AgentResult (mit audit_trail)
    Note over D: audit_trail.log(level=0, action="delegate_result")
    D-->>O: result.output
    O->>O: LLM verarbeitet Ergebnis
    Note over O: audit_trail.log(level=0, action="llm_call")
    O-->>U: AgentResult (finaler Output + audit_trail)
```

---

## 9. Human-in-the-Loop (HITL)

Erweitert den Orchestrator um eine zusaetzliche Plan-Phase mit User-Bestaetigung
vor der Ausfuehrung. Implementiert ueber `run_interactive(task, approval_callback)`.

### 9.1 Ablauf

```mermaid
sequenceDiagram
    participant U as User
    participant I as run_interactive
    participant P as Plan-Phase (submit_plan)
    participant E as Execute-Phase (delegate_to)
    participant S as Specialist

    U->>I: task
    I->>P: run_agent_plan_phase(task, config)
    Note over P: tools = [submit_plan]
    P->>P: LLM ruft submit_plan(subtasks, reasoning)
    Note over P: audit: plan_submitted
    P-->>I: (Plan, AgentResult)
    I->>U: approval_callback(plan)
    U-->>I: ApprovalDecision(approved, feedback)

    alt approved = true
        I->>E: run_agent_execute_phase(task, plan, config)
        Note over E: tools = [delegate_to]
        Note over E: audit: plan_approved
        loop fuer jeden Subtask
            E->>S: delegate_to(agent, task)
            S-->>E: result
        end
        E-->>I: AgentResult (final)
        I-->>U: AgentResult
    else approved = false
        Note over I: audit: plan_rejected
        I-->>U: AgentResult.fail("Plan rejected by user: ...")
    end
```

### 9.2 Zwei-Phasen-Architektur

| Phase | Funktion | Verfuegbare Tools | Zweck |
|-------|----------|-------------------|-------|
| Plan | `run_agent_plan_phase` | nur `submit_plan` | Orchestrator generiert strukturierten Plan |
| Execute | `run_agent_execute_phase` | nur `delegate_to` | Genehmigter Plan wird Subtask fuer Subtask ausgefuehrt |

Diese harte Trennung wird durch `tools=["submit_plan"]` bzw. `tools=["delegate_to"]`
in den jeweiligen Phasen-Konfigurationen erzwungen. Der LLM kann die Phasen
nicht mischen.

### 9.3 Approval-Callback

```python
def approval_callback(plan: Plan) -> ApprovalDecision:
    # Anzeige, Validierung, Logging, ...
    return ApprovalDecision(approved=True, feedback="ok")
```

Der Callback ist zustandslos — er bekommt nur den Plan und gibt eine
Entscheidung zurueck. Das macht die Schnittstelle einfach testbar und
in verschiedenen UIs wiederverwendbar (CLI, Web-UI, automatisiert).

### 9.4 Plan-Schema

```python
@dataclass(frozen=True)
class Subtask:
    agent: str   # WebSearchAgent, CodeExecutionAgent, ...
    task: str

@dataclass
class Plan:
    subtasks: list[Subtask]
    reasoning: str = ""
```

`Plan.from_json()` validiert strikt:
- Subtasks-Liste darf nicht leer sein
- Agent muss aus `VALID_AGENTS` stammen
- Task darf nicht leer sein

### 9.5 Audit-Trail-Actions

| Action | Wann |
|--------|------|
| `plan_submitted` | Orchestrator hat `submit_plan` aufgerufen |
| `plan_approved` | User hat Plan via Callback genehmigt |
| `plan_rejected` | User hat Plan abgelehnt (mit optionalem Feedback) |

### 9.6 Beispiel

```python
from agent_smith import run_interactive, ApprovalDecision

def my_callback(plan):
    print(plan.format())  # Plan:, Reasoning:, 1. [Agent] task, ...
    return ApprovalDecision(
        approved=input("OK? (y/n): ") == "y",
        feedback=None,
    )

result = run_interactive("Recherchiere X", my_callback)
```

Weitere Beispiele: `python examples/basic_usage.py hitl`,
`hitl-auto-reject`, `hitl-edit`, `hitl-audit`.

---

## 10. Workflows

### 10.1 Sequential

```mermaid
flowchart LR
    S1["Step 1: web_search"] -->|Ergebnis| S2["Step 2: code"]
    S2 -->|Ergebnis| S3["Step 3: document"]

    style S1 fill:#2196F3,color:#fff
    style S2 fill:#2196F3,color:#fff
    style S3 fill:#2196F3,color:#fff
```

- Jeder Step erhaelt alle vorherigen Ergebnisse ueber `task_fn(prior_results)`
- Abbruch beim ersten Fehler

### 10.2 Parallel

```mermaid
flowchart TD
    START(["run_parallel"]) --> S1["Step 1: web_search"]
    START --> S2["Step 2: code"]
    START --> S3["Step 3: document"]
    S1 --> COLLECT["Ergebnisse sammeln"]
    S2 --> COLLECT
    S3 --> COLLECT

    style START fill:#FF9800,color:#fff
    style S1 fill:#4CAF50,color:#fff
    style S2 fill:#4CAF50,color:#fff
    style S3 fill:#4CAF50,color:#fff
```

- Alle Steps laufen gleichzeitig (`ThreadPoolExecutor`)
- Jeder bekommt leeres `prior_results`-Dict

### 10.3 Conditional

```mermaid
flowchart TD
    COND{"condition(prior_results)"} -->|True| T1["Step A"] --> T2["Step B"]
    COND -->|False| F1["Step X"] --> F2["Step Y"]

    style COND fill:#9C27B0,color:#fff
```

---

## 11. Konventionen

| Regel | Beschreibung |
|-------|-------------|
| Funktionales Paradigma | Keine Klassen, keine Vererbung — nur Funktionen und Dataclasses |
| LangChain-Isolation | LangChain-Typen nur in `llm.py`, `runner.py`, `memory/store.py`, `tools/` |
| Ollama-only | Kein OpenAI/Anthropic/anderer Provider |
| Tool-Fehlerbehandlung | Tools liefern Fehler-Dicts, nie Exceptions an den Caller |
| Rule-basiert | Agentenkonfiguration in Markdown-Dateien, nicht im Code |
| Audit-Trail | Vollstaendige Nachverfolgung aller Interaktionen mit dem LLM |
| Keine Formatter/Linter | Kein ruff, black, mypy oder pre-commit hooks konfiguriert |
| Naming | `test_{function}_{scenario}` fuer Tests |
| Python >=3.11 | Type-Annotationen mit `str | None`, `list[str]`, etc. |

---

## 12. Bekannte Probleme

| Problem | Beschreibung |
|---------|-------------|
| Code-Duplizierung | `memory/store.py::window()` ist funktionsgleich mit `runner.py::_trim()` |
| Stille Fehler | `get_tools()` ueberspringt unbekannte Tool-Namen ohne Warnung |
| Unstrukturierte Fehler | `delegate_to` liefert Strings statt strukturierter Dicts zurueck |
| Hardcoded Dispatch | Agent-Dispatch in `delegate.py` manuell gepflegt |
| Import-Seiteneffekte | `tools/__init__.py` mutiert `ALL_TOOLS` und `TOOL_MAP` zur Import-Zeit |
| Test-Luecken | Fehlende Tests fuer: Rules-Parser, parallel/conditional workflows |
| Generische System-Prompts | Nur 2-3 Saetze, kein Ausgabeformat spezifiziert |
| Kein Sandboxing | `execute_python` fuehrt Code ohne Sicherheitsbeschraenkungen aus |

---

## 13. Infrastruktur

### 12.1 Docker

- **Dockerfile.lc** — Python 3.14-slim mit allen Abhaengigkeiten
- **docker-compose.yml** — 3 Services (`vanilla`, `lc`, `crewai`), verbinden sich zu host-Ollama via `host.containers.internal:11434`

### 12.2 LLM-Backend

- Ollama auf `localhost:11434`
- Default-Modell: `qwen3:8b`
- Integrationstests: `qwen3:8b`

### 12.3 Test-Befehle

```bash
# Unit-Tests (gemockt, kein Ollama noetig)
python -m pytest tests/

# HITL-Tests isoliert ausfuehren
python -m pytest tests/test_hitl.py -v

# Integrationstests (benoetigt laufenden Ollama)
python -m pytest tests/test_ollama_integration.py -v -s

# Mit Coverage
python -m pytest --cov=agent_smith
```

---

## 14. MCP Server (rain_sensor)

### 13.1 Ueberblick

Mock-MCP-Server fuer ein gefaktes Regensensor-Netzwerk.
Werte werden mit Zufallszahlen generiert. Nuetzt fuer Tests und Prototyping.

### 13.2 Starten

```bash
python mcp_servers/rain_sensor/server.py
# Server laeuft auf http://localhost:8080/sse
```

### 13.3 Tools

| Tool | Beschreibung | Parameter |
|------|--------------|-----------|
| `get_all_sensors()` | Alle 6 Sensoren mit Zufallsdaten | - |
| `get_sensor(sensor_id)` | Einzelner Sensor nach ID | `sensor_id: str` |
| `get_rain_level()` | Durchschnitt/Min/Max aller Sensoren | - |
| `get_alerts(threshold)` | Sensoren ueber Schwellenwert | `threshold: float = 5.0` |

### 13.4 Sensor-Struktur

```json
{
  "id": "sensor_01",
  "name": "Berlin-Mitte",
  "location": {"lat": 52.52, "lon": 13.40},
  "rain_mm": 12.5,
  "humidity": 72,
  "temperature": 15.3,
  "status": "online",
  "last_update": "2026-07-27T14:30:00Z"
}
```

### 13.5 Sensoren

| ID | Name | Standort |
|----|------|----------|
| sensor_01 | Berlin-Mitte | Berlin |
| sensor_02 | Hamburg-Sued | Hamburg |
| sensor_03 | Muenchen-Zentrum | Muenchen |
| sensor_04 | Koeln-Innenstadt | Koeln |
| sensor_05 | Frankfurt-West | Frankfurt |
| sensor_06 | Stuttgart-Nord | Stuttgart |

### 13.6 Konfiguration in OpenCode

```json
{
  "mcpServers": {
    "rain-sensor": {
      "command": "python",
      "args": ["mcp_servers/rain_sensor/server.py"]
    }
  }
}
```
