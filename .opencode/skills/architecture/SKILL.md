---
name: architecture
description: Architektur und Konventionen der LangChain Edition von agent-smith
metadata:
  edition: langchain
  version: 1.0.0
---

## Was ich bin

Dieser Skill enthält die vollständige Architektur-Dokumentation der LangChain Edition (`agent_smith/`) von agent-smith. Er wird von den spezialisierten Agenten (coder, tester, reviewer, architect) genutzt.

## Wann ich verwendet werden soll

- Wenn du Code für die LC Edition schreibst oder änderst
- Wenn du die Architektur der LC Edition verstehen möchtest
- Wenn du Refactoring oder Verbesserungen planst
- Wenn du Tests für die LC Edition schreibst

## Dateistruktur

```
agent_smith/
├── __init__.py              # Package-Eintritt: run(), _AGENT_MAP, run_interactive(), Public API
├── pyproject.toml           # Dependencies: langchain>=1.0.0, langchain-ollama
├── types.py                 # AgentResult, Status enum (LC-frei)
├── rules.py                 # Frontmatter-Parser: rules/*.md → AgentConfig
├── llm.py                   # LC-spezifisch: OllamaConfig, make_llm(), make_llm_with_tools()
├── approval.py              # HITL: Plan, Subtask, ApprovalDecision, _parse_subtask(), VALID_AGENTS
├── audit.py                 # AuditTrail, AuditEntry + Context-Vars für Observability
├── mcp_clients.py           # MCP-Dispatcher: call_mcp_tool(), list_servers() — silent-fail + Fallback-String
├── mcp_routing.py           # Routing Map: deterministisches Keyword-Matching für MCP-Subtasks
├── agents/
│   ├── __init__.py          # Re-exports
│   ├── runner.py            # Agentic Loop: AgentConfig, _trim(), run_agent(),
│   │                        #   run_agent_plan_phase(), run_agent_execute_phase(),
│   │                        #   _mcp_fallback_agent(), _mcp_fallback_task()
│   └── builtins.py          # 6 Agents: _agent_from_rule() + run_* convenience
├── tools/
│   ├── __init__.py          # Re-exports + delegate_to + security-tools + submit_plan Registrierung
│   ├── builtins.py          # 9 @tool-Funktionen + TOOL_MAP, get_tools()
│   ├── delegate.py          # delegate_to @tool (Orchestrator-Delegation)
│   ├── submit_plan.py       # submit_plan @tool + _coerce_subtasks() + parse_plan_from_args()
│   └── security.py          # bandit_scan, secret_scan, audit_dependencies, security_scan
├── memory/
│   ├── __init__.py
│   └── store.py             # window(), last_assistant_text()
└── workflows/
    ├── __init__.py
    └── engine.py            # Step, WorkflowResult, run_sequential, run_parallel, run_conditional
```

## Kern-Komponenten

### 1. Agentic Loop (`agents/runner.py`)

Das Herzstück der LC Edition. Rein funktional, keine Klasse.

```python
def run_agent(task: str, config: AgentConfig) -> AgentResult:
    """
    1. Tools holen (get_tools)
    2. LLM erzeugen (mit oder ohne bind_tools)
    3. Messages: [SystemMessage, HumanMessage]
    4. Loop (max_iterations):
       a. _trim(messages)
       b. llm.invoke(windowed) -> AIMessage
       c. Wenn keine tool_calls -> RETURN AgentResult.ok()
       d. Sonst: _execute_tool_calls() -> ToolMessages anhaengen
    5. RETURN AgentResult.fail("Max iterations reached")
    """
```

**Wichtige LC-Typen** (nur in `llm.py` und `runner.py`):
- `ChatOllama` (langchain_ollama)
- `AIMessage`, `HumanMessage`, `SystemMessage`, `ToolMessage` (langchain_core.messages)

### 2. Tool-System (`tools/builtins.py`)

9 Built-in Tools mit `@tool`-Dekorator:

| Tool | Funktion | Beschreibung |
|------|----------|--------------|
| `web_search` | DuckDuckGo-Suche | Gibt `[{title, url, snippet}]` zurück |
| `execute_python` | Subprocess | Gibt `{stdout, stderr, returncode}` zurück |
| `read_file` | Path.read_text() | Mit `max_chars` Trunkation |
| `list_files` | Path.glob(pattern) | Nur Dateien, keine Verzeichnisse |
| `http_get` | httpx.Client.get() | Body auf 5000 Zeichen begrenzt |
| `http_post` | httpx.Client.post() | JSON body |
| `read_csv` | csv.DictReader | Max `max_rows` Zeilen |
| `describe_data` | pandas.describe() | Shape, columns, dtypes, describe |
| `query_data` | pandas.DataFrame.query() | Max 100 Ergebnisse |

Plus `delegate_to` aus `tools/delegate.py`.

**Tool-Registrierung**:
```python
# tools/__init__.py
ALL_TOOLS: list[Tool] = [...]  # Alle Tools
TOOL_MAP: dict[str, ToolFn] = {t.name: t.fn for t in ALL_TOOLS}
```

### 3. Rules (`rules.py`)

YAML-Frontmatter-Parser für Agent-Definitionen:

```yaml
---
name: WebSearchAgent
tools: web_search
max_iterations: 10
context_window: 20
---
System-Prompt hier
```

**Parser-Konvertierungen**:
- `int`: `"10"` → `10`
- `bool`: `"true"` → `True`
- `comma-separated list`: `"web_search, read_file"` → `["web_search", "read_file"]`

### 4. Built-in Agents (`agents/builtins.py`)

6 Agents mit Convenience-Funktionen:

```python
def _agent_from_rule(name: str) -> AgentConfig:
    """Lädt Rule und konstruiert AgentConfig"""
    rule = load_rule(name)  # aus rules.py
    return AgentConfig(
        name=rule["name"],
        system_prompt=rule["system_prompt"],
        llm=OllamaConfig(),
        tools=rule.get("tools"),
        max_iterations=rule.get("max_iterations", 10),
        context_window=rule.get("context_window", 20)
    )

def run_web_search(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    """Convenience: WebSearchAgent ausführen"""
    config = _agent_from_rule("web_search")
    if llm:
        config = replace(config, llm=llm)
    return run_agent(task, config)
```

**Agent-Registrierung** (`__init__.py`):
```python
_AGENT_MAP: dict[str, Callable] = {
    "WebSearchAgent": run_web_search,
    "CodeExecutionAgent": run_code,
    "DocumentAgent": run_document,
    "APIAgent": run_api,
    "DataAgent": run_data,
    "OrchestratorAgent": run_orchestrator,
}
```

### 5. Memory (`memory/store.py`)

```python
def window(messages: list[Message], max_messages: int = 20) -> list[Message]:
    """Sliding Window: SystemMessage wird immer beibehalten"""
    ...

def last_assistant_text(messages: list[Message]) -> str | None:
    """Findet den letzten AIMessage.content"""
    ...
```

**Problem**: `window()` ist identisch mit `runner._trim()`.

### 6. Workflows (`workflows/engine.py`)

```python
def run_sequential(steps: list[Step]) -> WorkflowResult:
    """Seqentiell, bricht bei Fehler ab"""
    ...

def run_parallel(steps: list[Step], max_workers: int = 4) -> WorkflowResult:
    """Alle Steps parallel via ThreadPoolExecutor"""
    ...

def run_conditional(
    condition: Callable[[dict[str, AgentResult]], bool],
    if_true: list[Step],
    if_false: list[Step]
) -> WorkflowResult:
    """Branch basierend auf Condition-Funktion"""
    ...
```

### 7. Human-in-the-Loop + MCP-Integration (`approval.py`, `submit_plan.py`, `runner.py`)

Zweiphasiger HITL-Flow:

**Phase 1 — Planung** (`run_agent_plan_phase`):
- Orchestrator hat nur `submit_plan` als Tool
- LLM erzeugt strukturierten Plan mit `submit_plan(reasoning=..., subtasks=[...])`
- Jeder Subtask ist entweder ein Agent-Subtask (`agent`/`task`) oder MCP-Subtask (`mcp_server`/`tool_name`/`args`)
- Validierung via `_coerce_subtasks()` in `submit_plan.py`

**Phase 2 — Ausführung** (`run_agent_execute_phase`):
- MCP-Subtasks werden via `call_mcp_tool()` ausgeführt (synchron, deterministisch)
- Bei MCP-Fehler → transparenter Fallback auf `WebSearchAgent` via `_mcp_fallback_agent()` + `_mcp_fallback_task()`
- Agent-Subtasks werden via `_delegate_sync()` an spezialisierte Agents delegiert
- Finaler LLM-Call kombiniert alle Ergebnisse

### 8. MCP-Routing (`mcp_routing.py`)

Deterministisches Keyword-Matching für Task→MCP-Server-Routing:

- `RoutingEntry`: task_type, mcp_server, tool_name, keywords, description
- `find_routing(task)` → erster Match oder `None`
- `render_routes_for_prompt()` → Markdown-Tabelle für System-Prompt
- Kein LLM involviert, rein deterministisch

**Aktuelle Einträge:**
| Task Type | MCP Server | Tool | Keywords |
|---|---|---|---|
| `route_distance` | `osm_router` | `get_route_distance` | entfernung, distanz |
| `route_info` | `osm_router` | `get_route_info` | route, wegbeschreibung |
| `weather` | `weather` | `get_weather` | wetter, temperatur |
| `weather_forecast` | `weather` | `get_forecast` | vorhersage, forecast, wetter |

### 9. MCP-Client-Dispatcher (`mcp_clients.py`)

`call_mcp_tool(server, tool, args)` → dispatcht synchron an registrierte Python-Clients:
- `osm_router` → `OSMRouterClient` (OSRM live API + deterministischer Mock)
- `weather` → `WeatherClient` (deterministischer Mock)
- Unbekannte Server → `"MCP_ERROR: Unknown server '{server}'"` → löst Fallback aus

### 10. MCP-Server (`mcp_servers/`)

Separate Top-Level-Pakete (nicht in `agent_smith/`), pro Server:
- `mcp_servers/osm_router/` — FastMCP-Server + synchroner Python-Client
- `mcp_servers/weather/` — FastMCP-Server + synchroner Python-Client
- `mcp_servers/rain_sensor/` — Mock-Daten für Tests

**Wichtig:** `mcp_servers` muss via `.pth`-Datei im venv auf `sys.path` sein (siehe AGENTS.md Setup).

## Import-Abhängigkeiten

```
__init__.py
  ├── mcp_routing.py         ← standalone, keine Abhängigkeiten
  ├── mcp_clients.py         → mcp_servers.*.client (lazy import)
  ├── approval.py            ← standalone: Plan, Subtask, ApprovalDecision
  ├── audit.py               ← standalone: AuditTrail, AuditEntry
  ├── tools/submit_plan.py   → approval.py (VALID_AGENTS, Plan, Subtask)
  ├── agents/runner.py       → llm.py (make_llm, make_llm_with_tools)
  │                           → tools/builtins.py (TOOL_MAP, get_tools)
  │                           → tools/submit_plan.py (PLAN_SUBMITTED_MARKER, parse_plan_from_args)
  │                           → mcp_clients.py (call_mcp_tool, lazy import)
  │                           → approval.py (Plan)
  │                           → audit.py (AuditTrail, set_audit_context, reset_audit_context)
  │                           → types.py (AgentResult)
  ├── agents/builtins.py     → rules.py (load_rule) → runner.py
  └── tools/delegate.py      → agents/builtins.py (lazy import)
  └── tools/__init__.py      → builtins.py + delegate.py + submit_plan.py + security.py
```

## Konventionen

### Code-Style
- **Funktionaler Stil**: Keine Klassen, keine Vererbung. Alles Funktionen und Dataclasses.
- **LC-Isolation**: LC-Typen nur in `llm.py` und `runner.py`. Domain-Typen in `types.py` sind LC-frei.
- **Immutable State**: `AgentConfig` ist ein frozen dataclass.
- **Keine Kommentare**: Außer bei komplexer Logik.
- **Type Hints**: Für alle Funktionen.

### Testing
- **Mocking**: `make_llm` und `make_llm_with_tools` mocken
- **Naming**: `test_{funktion}_{szenario}`
- **Structure**: Arrange-Act-Assert

### Tool-System
- **Registrierung**: In `ALL_TOOLS` und `TOOL_MAP` in `tools/__init__.py`
- **Dekorator**: `@tool` mit klarem Docstring (wird LLM als Tool-Beschreibung angezeigt)

### Agent-System
- **Registrierung**: In `_AGENT_MAP` in `__init__.py`
- **Convenience**: `run_{name}(task, llm)` Funktionen
- **Delegation**: Orchestrator nutzt `delegate_to` mit lazy-import

## Bekannte Probleme und geplante Änderungen

### Kurzfristig (Quick Wins)
1. **`_trim()` entfernen**: `runner.py` nutzt `memory.store.window()` (dupliziert)
2. **Tool-Warnung**: `get_tools()` warnt bei unbekannten Tools
3. **Strukturierte Fehler**: `delegate_to` gibt `{"status": "error", ...}` zurück
4. **MCP-Fallback ausgebaut**: Fallback unterstützt aktuell nur `osm_router` + `weather` — erweiterbar

### Mittelfristig
5. **Zentrale Agent-Registry**: Dynamische Dispatch-Map statt Hardcoding
6. **`__all__` definieren**: In allen `__init__.py` Dateien
7. **Testabdeckung erhöhen**: Fehlende Tests implementieren
8. **DeepAgents-Migration evaluieren**: Siehe `docs/features_and_ideas.md#deepagents-migration`

### Langfristig
9. **Prompt-Engineering**: Detailliertere System-Prompts mit Output-Format
10. **Dynamisches Context-Window**: Basierend auf Modell-Kontextgröße
11. **Sandbox für `execute_python`**: Thread-sichere Temp-Verzeichnisse

## Befehle

```bash
# LC Tests ausführen
python -m pytest tests/ -v

# Mit Coverage
python -m pytest tests/ --cov=agent_smith

# Integrationstests (braucht Ollama)
python -m pytest tests/test_ollama_integration.py -v -s
```
