---
title: "Anforderungsdokument — agent-smith"
author: "Marco Schrank"
date: "2026-07-27"
tags:
  - anforderungen
  - requirements
  - arc42
  - ireb
abstract: "Arc42-basiertes Requirements-Dokument für agent-smith (LangChain Edition)."
---

# Anforderungsdokument — agent-smith

> Arc42-basiertes Requirements-Dokument für agent-smith (LangChain Edition).
> Formulierungen nach IREB-Konventionen (Soll-Aussagen, eindeutige IDs).

**Version:** 1.1
**Stand:** 2026-07-28
**Status:** Ist-Zustand (umgesetzte Anforderungen)

---

## 1. Einfuehrung und Ueberblick

### 1.1 Zielsetzung

agent-smith ist eine modulare Agenten-Engine, die auf lokalen LLMs (Ollama)
basiert. Das System soll es Entwicklern ermoeglichen, mit natuerlicher Sprache
Aufgaben zu definieren, die von spezialisierten Agenten unter Einsatz von
Werkzeugen (Tools) automatisiert bearbeitet werden.

### 1.2 Systemgrenzen

```
                  +---------------------------+
                  |      agent-smith          |
                  |                           |
 User-Aufgabe --> |  Agenten + Tools + Rules  | --> AgentResult
                  |                           |
                  +---------------------------+
                        |           |
                        v           v
                   +---------+  +---------+
                   | Ollama  |  | Externe |
                   | (LLM)  |  | APIs    |
                   +---------+  +---------+
```

### 1.3 Versionierung

| Version | Datum | Aenderung |
|---------|-------|-----------|
| 1.0 | 2026-07-27 | Erstfassung (Ist-Zustand) |
| 1.1 | 2026-07-28 | Human-in-the-Loop: `run_interactive()`, `submit_plan`-Tool, Plan/ApprovalDecision-Dataclasses |

---

## 2. Stakeholder

| Stakeholder | Rolle | Interesse |
|-------------|-------|-----------|
| Entwickler | Nutzer der Bibliothek | Einfache Integration, klare API |
| DevOps | Betrieb des Systems | Lokaler Betrieb, Ollama-Abhaengigkeit |
| Datenschutzbeauftragter | Compliance | Keine externen Datenfluesse, lokales LLM |

---

## 3. Funktionale Anforderungen

### 3.1 Agenten-System

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| FR-001 | Das System Soll einen Convenience-Einstiegspunkt `run()` bereitstellen, der eine Aufgabe in natuerlicher Sprache entgegennimmt und ein strukturiertes Ergebnis (`AgentResult`) zurueckgibt. | hoch |
| FR-002 | Das System Soll sechs vordefinierte Agenten bereitstellen: WebSearchAgent, CodeExecutionAgent, DocumentAgent, APIAgent, DataAgent, OrchestratorAgent. | hoch |
| FR-003 | Jeder Agent Soll ueber eine eigene Rule-Datei (Markdown mit YAML-Frontmatter) konfigurierbar sein. | hoch |
| FR-004 | Das System Soll einen generischen Agentic Loop (`run_agent`) bereitstellen, der LLM-Aufrufe und Tool-Ausfuehrungen iterativ ausfuehrt. | hoch |
| FR-005 | Der Agentic Loop Soll nach Erhalt einer Text-Antwort (ohne Tool-Calls) terminieren. | hoch |
| FR-006 | Der Agentic Loop Soll nach Erreichen der max_iterations-Konfiguration mit einem Fehler beenden. | hoch |
| FR-007 | Der Agentic Loop Soll einen Sliding-Window-Mechanismus (`_trim`) nutzen, um den Kontextfenster auf `context_window` Nachrichten zu beschraenken, wobei der System-Prompt immer erhalten bleiben Soll. | hoch |
| FR-008 | Das System Soll ein einheitliches Ergebnis-Protokoll (`AgentResult`) mit den Feldern status, output, error und intermediate_steps bereitstellen. | hoch |
| FR-009 | Jeder Agent Soll seinen Namen, System-Prompt, LLM-Konfiguration, erlaubte Tools, max_iterations und context_window ueber `AgentConfig` konfigurieren koennen. | hoch |

### 3.2 Tool-System

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| FR-010 | Das System Soll elf Standard-Tools bereitstellen: `web_search`, `execute_python`, `read_file`, `list_files`, `http_get`, `http_post`, `read_csv`, `describe_data`, `query_data`, `delegate_to`, `submit_plan`. | hoch |
| FR-011 | Jedes Tool Soll als mit `@tool` dekorierte Funktion implementiert sein und ein Dict oder eine Liste zurueckgeben. | hoch |
| FR-012 | Jedes Tool Soll Fehler abfangen und als Dictionary (`{"error": "..."}`) zurueckgeben, ohne Exceptions an den Caller weiterzugeben. | hoch |
| FR-013 | Das System Soll eine globale Tool-Registry (`ALL_TOOLS`, `TOOL_MAP`) bereitstellen, die Tool-Namen auf Tool-Funktionen mapped. | hoch |
| FR-014 | Die Funktion `get_tools(names)` Soll Tools nach Name zurueckgeben oder alle Tools, wenn `names=None`. | mittel |
| FR-015 | Das `delegate_to`-Tool Soll dem OrchestratorAgent die Delegation von Subtasks an die fuenf Specialist-Agenten (WebSearch, Code, Document, API, Data) ermoeglichen. | hoch |
| FR-016 | Das `delegate_to`-Tool Soll Lazy-Imports nutzen, um zirkulare Abhaengigkeiten zu vermeiden. | mittel |
| FR-017 | Das `delegate_to`-Tool Soll den Dispatch ueber ein Dictionary realisieren, das Agent-Namen auf Runner-Funktionen mapped. | mittel |

### 3.3 Tool-Details

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| FR-018 | Das `web_search`-Tool Soll DuckDuckGo als Suchmaschine nutzen und Titel, URL sowie Snippet pro Treffer zurueckgeben. | hoch |
| FR-019 | Das `execute_python`-Tool Soll Python-Code in einem separaten Subprocess ausfuehren und stdout, stderr sowie returncode zurueckgeben. | hoch |
| FR-020 | Das `execute_python`-Tool Soll einen konfigurierbaren Timeout (Standard: 30 Sekunden) unterstützen. | mittel |
| FR-021 | Das `read_file`-Tool Soll eine Datei lesen und bei Ueberschreitung von max_chars (Standard: 10000) den Inhalt abschneiden. | mittel |
| FR-022 | Das `list_files`-Tool Soll Dateien anhand eines Glob-Patterns auflisten koennen. | mittel |
| FR-023 | Die HTTP-Tools (`http_get`, `http_post`) Sollten einen Timeout von 15 Sekunden und eine Body-Beschraenkung von 5000 Zeichen haben. | mittel |
| FR-024 | Das `read_csv`-Tool Soll CSV-Dateien mit DictReader lesen und max_rows (Standard: 100) Zeilen zurueckgeben. | mittel |
| FR-025 | Das `describe_data`-Tool Soll Pandas `describe()` fuer CSV-Dateien ausfuehren und shape, columns, dtypes sowie deskriptive Statistiken zurueckgeben. | mittel |
| FR-026 | Das `query_data`-Tool Soll einen Pandas query-String-Filter auf CSV-Dateien anwenden und max. 100 Zeilen zurueckgeben. | mittel |

### 3.4 Workflow-System

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| FR-027 | Das System Soll drei Workflow-Modi bereitstellen: `run_sequential`, `run_parallel`, `run_conditional`. | hoch |
| FR-028 | `run_sequential` Soll Schritte nacheinander ausfuehren und dabei die Ergebnisse vorheriger Schritte ueber eine `task_fn`-Funktion an naechste Schritte weitergeben. | hoch |
| FR-029 | `run_sequential` Soll beim ersten fehlgeschlagenen Step abbrechen und ein `WorkflowResult` mit den bisherigen Ergebnissen zurueckgeben. | hoch |
| FR-030 | `run_parallel` Soll alle Steps gleichzeitig ueber einen `ThreadPoolExecutor` ausfuehren. | mittel |
| FR-031 | `run_parallel` Soll jeden Step mit einem leeren `prior_results`-Dict aufrufen. | mittel |
| FR-032 | `run_conditional` Soll basierend auf einer Laufzeit-Bedingung zwischen zwei Step-Listen waehlen und den gewaehlten Ast sequential ausfuehren. | mittel |
| FR-033 | Jeder Workflow-Soll ein `WorkflowResult` mit den Feldern steps (Dict aller Ergebnisse) und final (letztes Ergebnis) zurueckgeben. | hoch |

### 3.5 Rules-System

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| FR-034 | Das System Soll Agenten-Konfigurationen in Markdown-Dateien mit YAML-Frontmatter ermoeglichen. | hoch |
| FR-035 | Der Frontmatter-Parser Soll ganzzahlige, boolesche, komma-separierte und String-Werte automatisch erkennen und konvertieren. | hoch |
| FR-036 | Der Markdown-Body Soll als `system_prompt` zur Verfuegung stehen. | hoch |
| FR-037 | Einzelne Tool-Strings in der Rule Sollten zu Listen normalisiert werden. | mittel |

### 3.6 LLM-Integration

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| FR-038 | Das System Soll ausschliesslich Ollama als LLM-Backend nutzen (kein OpenAI, kein Anthropic). | hoch |
| FR-039 | Die `OllamaConfig` Soll folgende Parameter unterstuetzen: model, base_url, temperature, max_tokens, timeout, options. | hoch |
| FR-040 | Die Funktion `make_llm(config)` Soll eine `ChatOllama`-Instanz aus einer `OllamaConfig` erzeugen. | hoch |
| FR-041 | Die Funktion `make_llm_with_tools(config, tools)` Soll eine `ChatOllama`-Instanz mit gebundenen Tools zurueckgeben. | hoch |
| FR-042 | Das Standard-Modell Soll `gemma4:12b` sein. | mittel |

### 3.7 Oeffentliche API

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| FR-043 | Die Funktion `run()` Soll einen `agent`-Parameter akzeptieren, der den zu verwendenden Agenten auswaehlt (Standard: "orchestrator"). | hoch |
| FR-044 | Die Funktion `run()` Soll bei unbekanntem Agent-Namen einen `ValueError` ausloesen. | mittel |
| FR-045 | Das System Soll ein `__all__`-Export mit den oeffentlichen Symbolen bereitstellen. | mittel |
| FR-046 | Das System Soll Convenience-Funktionen (`run_web_search`, `run_code`, `run_document`, `run_api`, `run_data`, `run_orchestrator`) bereitstellen. | hoch |

### 3.8 Human-in-the-Loop (HITL)

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| FR-047 | Das System Soll eine `run_interactive(task, approval_callback)`-Funktion bereitstellen, die den Orchestrator in einem zweiphasigen Flow ausfuehrt: zuerst Plan-Generierung, dann User-Approval, dann Execution. | hoch |
| FR-048 | Die Plan-Phase Soll ausschliesslich das `submit_plan`-Tool bereitstellen, die Execution-Phase ausschliesslich das `delegate_to`-Tool. | hoch |
| FR-049 | Das `submit_plan`-Tool Soll einen strukturierten Plan mit Feldern `subtasks` (Liste aus `{agent, task}`) und optional `reasoning` (string) entgegennehmen. | hoch |
| FR-050 | Das System Soll eine `Plan`-Dataclass mit `subtasks: list[Subtask]` und `reasoning: str` sowie `to_json()`/`from_json()`/`format()`-Methoden bereitstellen. | hoch |
| FR-051 | Das System Soll eine `ApprovalDecision`-Dataclass mit `approved: bool` und optional `feedback: str` bereitstellen. | hoch |
| FR-052 | Der Approval-Callback Soll einen `Plan` erhalten und eine `ApprovalDecision` zurueckgeben (kein `True/False` direkt). | hoch |
| FR-053 | Bei `approved=False` Soll das System den Lauf abbrechen und `AgentResult.fail("Plan rejected by user: ...")` zurueckgeben. | hoch |
| FR-054 | Bei `approved=True` Soll das System den genehmigten Plan via `delegate_to` ausfuehren und das Ergebnis der Subagents kombiniert zurueckgeben. | hoch |
| FR-055 | Der Plan-Audit-Trail Soll die Actions `plan_submitted`, `plan_approved` und `plan_rejected` enthalten. | mittel |

### 3.8 Memory

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| FR-047 | Die Funktion `window(messages, max_messages)` Soll einen Sliding-Window ueber Nachrichtenlisten bereitstellen, wobei ein fuehrender System-Prompt immer erhalten bleiben Soll. | mittel |
| FR-048 | Die Funktion `last_assistant_text(messages)` Soll den Text der letzten AIMessage zurueckgeben oder None. | niedrig |

---

## 4. Nicht-funktionale Anforderungen

### 4.1 Performance

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| NFR-001 | Der Agentic Loop Soll waehrend der LLM-Aufrufe nicht blockieren, sondern asynchron mit dem Ollama-Server kommunizieren koennen. | mittel |
| NFR-002 | `run_parallel` Soll bis zu `max_workers` (Standard: 4) gleichzeitige Agenten-Ausfuehrungen unterstuetzen. | mittel |

### 4.2 Zuverlaessigkeit

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| NFR-003 | LLM-Ausnahmen Sollten im Agentic Loop abgefangen und als `AgentResult.fail()` zurueckgegeben werden. | hoch |
| NFR-004 | Tool-Ausnahmen Sollten pro Tool einzeln abgefangen und als JSON-Fehler in ToolMessages zurueckgegeben werden. | hoch |
| NFR-005 | Das System Soll bei Erreichen der maximalen Iterationsanzahl fehlerfrei terminieren. | hoch |

### 4.3 Portabilitaet

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| NFR-006 | Das System Soll Python >=3.11 erfordern und auf macOS, Linux sowie Windows lauffaehig sein. | hoch |
| NFR-007 | Das System Soll als Docker-Container betrieben werden koennen (Dockerfile und docker-compose.yml vorhanden). | mittel |

### 4.4 Wartbarkeit

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| NFR-008 | Die Architektur Soll funktionalen Stil folgen — keine Klassen, keine Vererbung, nur Funktionen und Dataclasses. | hoch |
| NFR-009 | LangChain-Typen Sollten nur in `llm.py`, `runner.py`, `memory/store.py`, `tools/builtins.py` und `tools/delegate.py` importiert werden. | hoch |
| NFR-010 | Das System Soll keine externen Abhaengigkeiten jenseits der in `pyproject.toml` definierten Pakete erzeugen. | mittel |

### 4.5 Testbarkeit

| ID | Anforderung | Prioritaet |
|----|-------------|------------|
| NFR-011 | Unit-Tests Sollten ohne laufenden Ollama-Server ausfuehrbar sein (Mocking des LLM). | hoch |
| NFR-012 | Integrationstests Sollten optional mit laufendem Ollama-Server ausfuehrbar sein. | mittel |
| NFR-013 | Das System Soll einen Coverage-Bericht ueber `pytest-cov` unterstuetzen. | mittel |

---

## 5. Einschraenkungen (Constraints)

### 5.1 Technische Constraints

| ID | Einschraenkung | Begründung |
|----|---------------|------------|
| C-001 | Das System Soll ausschliesslich Ollama als LLM-Backend nutzen. | Datenschutz: Keine externen Datenfluesse |
| C-002 | Das System Soll LangChain als Framework fuer LLM-Kommunikation und Tool-Calling nutzen. | Architektur-Entscheidung |
| C-003 | Das System Soll `ddgs` (DuckDuckGo) als einzige Suchmaschine nutzen. | Keine API-Keys noetig |
| C-004 | Das System Soll `httpx` als HTTP-Client nutzen. | Konsistenz mit LangChain |
| C-005 | Das System Soll `pandas` fuer CSV-Analyse nutzen. | Funktionsumfang |

### 5.2 Organisatorische Constraints

| ID | Einschraenkung | Begründung |
|----|---------------|------------|
| C-006 | Das Projekt Soll unter Apache-2.0-Lizenz stehen. | Open Source |
| C-007 | Kein Formatter, Linter oder Type-Checker Soll konfiguriert sein (aktuell). | Provisorisch |

---

## 6. Qualitaetsanforderungen

### 6.1 Qualitaetsbaum (nach arc42)

```
Qualitaetsziel
├── Funktionale Eignung
│   ├── Korrektheit: Agenten liefern zutreffende Ergebnisse
│   ├── Vollstaendigkeit: Alle 6 Agenten und 10 Tools sind implementiert
│   └── Angemessenheit: Tools sind auf ihre Domäne beschraenkt
├── Zuverlaessigkeit
│   ├── Reife: Fehler werden abgefangen und strukturiert zurueckgegeben
│   ├── Verfuegbarkeit: Lokaler Betrieb, keine Cloud-Abhaengigkeit
│   └── Fehlertoleranz: LLM- und Tool-Fehler brechen den Loop nicht ab
├── Bedienbarkeit
│   ├── Verstaendlichkeit: Einfache API (`run()`, `run_*()` Funktionen)
│   ├── Erlernbarkeit: Rule-System fuer Agenten-Konfiguration
│   └── Bedienbarkeit: Natuerliche Sprache als Eingabe
├── Effizienz
│   ├── Zeitverhalten: Asynchrone LLM-Kommunikation (geplant)
│   └── Ressourcennutzung: Lokales LLM, kein Cloud-Traffic
├── Wartbarkeit
│   ├── Modularitaet: Klare Trennung (types, llm, agents, tools, workflows)
│   ├── Testbarkeit: Mocking des LLM in Unit-Tests
│   └── Analysierbarkeit: Logging in `runner.py` und `engine.py`
├── Portabilitaet
│   ├── Austauschbarkeit: Ollama als einziges Backend
│   ├── Installation: pip-installierbar
│   └── Betriebssystem: Python-basiert (plattformuebergreifend)
└── Sicherheit
    ├── Vertraulichkeit: Keine externen Datenfluesse
    └── Integritaet: Tool-Fehler werden nicht weitergegeben
```

### 6.2 Qualitaets-Szenarien

| ID | Szenario | Qualitaetsziel |
|----|----------|----------------|
| QS-001 | Ein Entwickler integriert `agent_smith.run()` in eine bestehende Anwendung mit 3 Codezeilen. | Bedienbarkeit |
| QS-002 | Ein Administrator deployt das System als Docker-Container und verbindet es mit einem lokalen Ollama-Server. | Portabilitaet |
| QS-003 | Ein Tester fuehrt Unit-Tests ohne Internetverbindung und ohne laufenden Ollama-Server aus. | Testbarkeit |
| QS-004 | Das LLM ist kurzzeitig nicht verfuegbar — das System gibt einen strukturierten Fehler zurueck, ohne zu crashen. | Zuverlaessigkeit |

---

## 7. Risiken

| ID | Risiko | Auswirkung | Massnahme |
|----|--------|------------|-----------|
| R-001 | Code-Duplizierung zwischen `runner._trim()` und `memory.store.window()` | Erhoehter Wartungsaufwand | Deduplizierung geplant (siehe features_and_ideas.md) |
| R-002 | Kein Sandboxing fuer `execute_python` | Sicherheitsrisiko | Idee in features_and_ideas.md dokumentiert |
| R-003 | Test-Abdeckung unvollstaendig | Regressionsrisiko | Erhoehung geplant (siehe features_and_ideas.md) |
| R-004 | Import-Seiteneffekte in `tools/__init__.py` | Versteckte Abhaengigkeiten | Idee in features_and_ideas.md dokumentiert |
| R-005 | Generische System-Prompts | Suboptimale Agenten-Leistung | Verbesserung geplant (siehe features_and_ideas.md) |

---

## 8. Glossar

| Begriff | Definition |
|---------|------------|
| **Agent** | Ein spezialisierter Task-Verarbeiter bestehend aus LLM, Tools und System-Prompt |
| **Agentic Loop** | Der iterative Ablauf: LLM-Aufruf, Tool-Ausfuehrung, Wiederholung bis Text-Antwort |
| **Tool** | Eine Funktion, die ein LLM aufrufen kann, um mit der Aussenwelt zu interagieren |
| **Rule** | Eine Markdown-Datei mit YAML-Frontmatter, die einen Agenten konfiguriert |
| **Workflow** | Eine Verkettung mehrerer Agenten-Aufrufe (sequential, parallel, conditional) |
| **Orchestrator** | Ein Agent, der Aufgaben an Specialist-Agenten delegiert |
| **Sliding-Window** | Mechanismus zur Beschraenkung der Nachrichtenlaenge im LLM-Kontext |
| **AgentResult** | Das einheitliche Rueckgabeprotokoll aller Agenten-Aufrufe |
| **Ollama** | Ein lokaler LLM-Server fuer Open-Source-Modelle |
| **LangChain** | Ein Framework fuer LLM-Anwendungen, das Tool-Calling und Message-Typen bereitstellt |
| **Human-in-the-Loop (HITL)** | Flow, bei dem der Orchestrator zuerst einen Plan generiert und der User die Ausfuehrung explizit genehmigen muss, bevor Subtasks via `delegate_to` ausgefuehrt werden |
| **Plan** | Strukturierte Beschreibung der geplanten Subtasks (Liste aus `{agent, task}` plus optional `reasoning`) |
| **ApprovalDecision** | Ergebnis der User-Bewertung eines Plans (`approved: bool`, optionales `feedback: str`) |

---

## 9. Referenzen

| Dokument | Pfad |
|----------|------|
| Architekturbeschreibung | `docs/architektur.md` |
| Tutorial | `docs/tutorial.md` |
| Feature-Tracking | `docs/features_and_ideas.md` |
| Agenten-Infrastruktur | `AGENTS.md` |
| Projekt-Konfiguration | `pyproject.toml` |
