---
title: "Features & Ideen"
author: "Marco Schrank"
date: "2026-07-28"
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
| 10 Tools | Tools | `web_search`, `execute_python`, `read_file`, `list_files`, `http_get`, `http_post`, `read_csv`, `describe_data`, `query_data`, `delegate_to` |
| Rule-basierte Konfiguration | Konfiguration | Markdown+YAML-Frontmatter fuer Agenten-Definitionen in `rules/` |
| Workflow-Engine | Workflows | `run_sequential`, `run_parallel`, `run_conditional` |
| Memory-Utilities | Memory | `window()` (Sliding-Window), `last_assistant_text()` |
| Ollama-LLM-Backend | Infrastruktur | `OllamaConfig` + `make_llm`/`make_llm_with_tools` Factory |
| Docker-Setup | Infrastruktur | `Dockerfile.lc` + `docker-compose.yml` mit 3 Services |
| Unit-Tests | Testing | 16 gemockte Tests, 3 Integrationstests (Ollama noetig) |
| Orchestrator-Delegation | Agenten | `delegate_to`-Tool mit lazy-import Pattern fuer zirkularfreie Architektur |
| Convenience-API | Kern | `agent_smith.run()` als top-level Einstiegspunkt mit Agent-Dispatch |
| Human-in-the-Loop | Agenten | `run_interactive(task, approval_callback)` — Orchestrator plant zuerst, holt User-Bestaetigung, fuehrt dann aus. Strukturierter JSON-Plan via `submit_plan`-Tool, Callback-basierte Approval-Schnittstelle. Audit-Actions: `plan_submitted`, `plan_approved`, `plan_rejected`. |

---

## Ideen & Verbesserungen

| Idee | Kategorie | Status | Prioritaet | Beschreibung |
|------|-----------|--------|------------|-------------|
| `execute_python` Sandboxing | Sicherheit | idee | hoch | Code-Ausfuehrung in Sandbox/Container mit Ressourcen-Limits, Network-Restrictions |
| Test-Abdeckung erhoebern | Testing | geplant | hoch | Tests fuer Rules-Parser, `delegate_to`, builtins convenience functions, parallel/conditional Workflows |
| Bessere System-Prompts | Qualitaet | geplant | mittel | Ausgabeformat-Spezifikation, strukturierte Antworten, konkretere Anweisungen |
| Formatter/Linter | Tooling | idee | mittel | ruff, mypy, pre-commit hooks einrichten |
| `_trim`/`window` Deduplizierung | Refactoring | idee | niedrig | `runner._trim()` und `memory.store.window()` sind funktionsgleich — eine Loesung behalten |
| Strukturierte Fehler in `delegate_to` | Qualitaet | idee | niedrig | Fehler als Dict statt String zurueckgeben |
| Dynamische Tool-Registrierung | Architektur | idee | niedrig | Kein Import-Seiteneffekt in `tools/__init__.py`, stattdessen explizite Registrierung |
| `get_tools()` Warning bei unbekannten Namen | Qualitaet | idee | niedrig | Aktuell werden unbekannte Tool-Namen still ignoriert |
