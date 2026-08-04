---
title: "HowTo — agent-smith"
author: "Marco Schrank"
date: "2026-08-01"
tags:
  - howto
  - konsolenbefehle
  - venv
  - tests
  - jupyter
abstract: "Alle wichtigen Konsolenbefehle für agent-smith: Setup, Venv, Tests, Jupyter, Beispiele, Security."
---

# HowTo — Konsolenbefehle für agent-smith

> Alle Konsolenbefehle im Überblick: von der Einrichtung über Tests und
> Jupyter-Notebooks bis zu den Beispielen und Security-Tools.
> Zielgruppe: Entwickler, die mit der Codebasis arbeiten.

---

## 1. Voraussetzungen & Setup

### 1.1 Ollama installieren

agent-smith benoetigt einen laufenden Ollama-Server
(`http://localhost:11434`). Ohne Ollama laufen die Agents nicht.

```bash
# macOS/Linux: Ollama installieren
curl -fsSL https://ollama.com/install.sh | sh

# Ollama-Server starten (daemon)
ollama serve

# Modell herunterladen (Standardmodell von agent-smith)
ollama pull gemma4:12b

# Installierte Modelle anzeigen
ollama list
```

> **Hinweis:** Das Standardmodell ist `gemma4:12b`. Weitere Modelle
> (z. B. `mistral:latest`) koennen mit `ollama pull mistral:latest`
> heruntergeladen und per `OllamaConfig(model=...)` gewaehlt werden
> (siehe [Kapitel 6](#6-direkte-agent-aufrufe-aus-python)).

### 1.2 Virtuelle Umgebung anlegen

```bash
# In das Projektverzeichnis wechseln
cd /Users/marco.schrank/projects/agent-smith

# Venv erstellen
python -m venv .venv

# Venv aktivieren
source .venv/bin/activate
```

### 1.3 Pakete installieren

```bash
# Alle Abhaengigkeiten + Dev-Tools (pytest, bandit, pip-audit, jupyterlab, ipykernel)
pip install -e ".[dev]"
```

> **Hinweis:** `pyproject.toml` ist die **Single Source of Truth** fuer
> Dependencies. `requirements.txt` wird nicht mehr verwendet.

### 1.4 Sicherheits-Tools & Pre-Push-Hook (optional)

```bash
# gitleaks installieren (optional; Regex-Fallback ist vorhanden)
bash scripts/install-security-tools.sh

# Pre-Push-Hook aktivieren (fuehrt Security-Checks vor dem Push aus)
chmod +x .git/hooks/pre-push
```

### 1.5 Setup-Workaround (nur bei setuptools 82+ auf Python 3.14)

Falls das editable Install fehlerhafte `.pth`-Dateien erzeugt, manuell
korrigieren:

```bash
echo "$(pwd)" > "$(dirname $(which python))/../lib/python3.14/site-packages/agent_smith.pth"
```

---

## 2. Venv verwalten

| Aktion | Befehl |
|---|---|
| Venv aktivieren | `source .venv/bin/activate` |
| Venv beenden | `deactivate` |
| Python im Venv (ohne Aktivierung) | `.venv/bin/python3` |
| Pip im Venv (ohne Aktivierung) | `.venv/bin/pip` |
| Interpreter-Pfad anzeigen | `which python` |

> **Wichtig:** Das System-Python hat **kein** `deepagents` und **kein**
> `agent-smith` installiert. Immer das Venv nutzen — entweder nach
> `source .venv/bin/activate` das bare `python`, oder explizit
> `.venv/bin/python3`.

```bash
# Beispiel: aktivieren, Befehl ausfuehren, beenden
source .venv/bin/activate
python -c "import agent_smith; print(agent_smith.__version__ if hasattr(agent_smith, '__version__') else 'ok')"
deactivate
```

---

## 3. Tests ausfuehren

### 3.1 Unit-Tests (mocked, ohne Ollama)

```bash
# Alle Tests
python -m pytest tests/

# Einzelne Testdatei
python -m pytest tests/test_agent_smith.py

# Einzelner Test mit Namen
python -m pytest tests/test_agent_smith.py -k "retry"

# Ausfuehrliche Ausgabe
python -m pytest tests/ -v
```

### 3.2 Integrationstests (benoetigt Ollama + `gemma4:12b`)

```bash
python -m pytest tests/test_ollama_integration.py -v -s
```

### 3.3 Test-Coverage

```bash
python -m pytest --cov=agent_smith
```

---

## 4. Jupyter-Notebooks

JupyterLab ist im Venv installiert (Kernel `python3` zeigt auf das Venv).

### 4.1 JupyterLab starten

```bash
source .venv/bin/activate
jupyter lab
```

Dann im Browser das Notebook `hands_on.ipynb` oeffnen und mit dem Kernel
`python3` ausfuehren.

### 4.2 Notebook headless ausfuehren

```bash
# Ergebnisse werden ins Notebook geschrieben (--inplace ist wichtig!)
jupyter execute --inplace hands_on.ipynb

# Ohne --inplace wird das Eingabe-Notebook NICHT ueberschrieben
```

> **Stolperstein:** Ohne `--inplace` schreibt `jupyter execute` die
> Ergebnisse nicht zurueck in die Quelldatei.

### 4.3 Jupyter-Version pruefen

```bash
jupyter --version
jupyter kernelspec list   # python3 -> .venv/share/jupyter/kernels/python3
```

---

## 5. Beispiele: `examples/basic_usage.py`

Alle Beispiele benoetigen einen laufenden Ollama-Server.

```bash
python examples/basic_usage.py <name>
```

| Name | Funktion | Beschreibung |
|---|---|---|
| `run` | `example_run()` | Orchestrator: Entfernung Nussloch → Bruchsal |
| `simple` | `example_simple()` | Direkter Agent `web_search`: optische Interferometrie |
| `code` | `example_code()` | Code-Agent: Fourier-Transformation mit numpy |
| `sequential` | `example_sequential()` | Sequenzieller Workflow: Recherche → Code |
| `parallel` | `example_parallel()` | Paralleler Workflow: 3 Web-Suchen gleichzeitig |
| `hitl` | `example_hitl()` | HITL mit CLI-Genehmigung (y/n) |
| `hitl-auto-reject` | `example_hitl_auto_reject()` | HITL: Plan wird automatisch abgelehnt (Error-Pfad) |
| `hitl-edit` | `example_hitl_edit()` | HITL: User streicht einzelne Subtasks |
| `hitl-audit` | `example_hitl_audit()` | HITL: zeigt nach Ausfuehrung den Audit-Trail |

Beispiele:

```bash
python examples/basic_usage.py run
python examples/basic_usage.py simple
python examples/basic_usage.py code
python examples/basic_usage.py hitl
```

> **Hinweis:** Unbekannte Namen ergeben `Error: Unknown example: <name>`.

---

## 6. Direkte Agent-Aufrufe aus Python

Die Kernfunktionen von agent-smith lassen sich direkt in einem
Python-Skript oder in einer interaktiven Session nutzen.

```python
from agent_smith import run, run_code, run_web_search, run_interactive

# Orchestrator (delegiert an SubAgents)
result = run("Was ist die Entfernung von Nussloch nach Bruchsal?")

# Direkter Web-Search-Agent
result = run_web_search("What is optical interferometry?")

# Code-Agent
result = run_code("Schreibe eine Python-Funktion fuer die Fourier-Transformation.")

# Human-in-the-Loop (Plan-Genehmigung)
result = run_interactive("Aufgabe", lambda plan: ApprovalDecision(approved=True))

print(result.output if result.success else result.error)
```

### 6.1 Modell waehlen

```python
from agent_smith import OllamaConfig, run

result = run(
    "Was ist 2+2?",
    config=OllamaConfig(model="mistral:latest", temperature=0.3),
)
```

> Detaillierte Erklaerungen aller APIs: [docs/tutorial.md](tutorial.md).

---

## 7. Security-Tools

| Tool | Befehl | Zweck |
|---|---|---|
| Bandit | `bandit -r agent_smith` | Statische Sicherheitsanalyse des Python-Codes |
| pip-audit | `pip-audit` | Prueft installierte Pakete auf bekannte Schwachstellen |
| gitleaks | `gitleaks detect` | Findet Secrets/API-Keys im Repo (Go-Binary, optional) |
| Pre-Push-Hook | (automatisch bei `git push`) | Fuehrt Security-Checks vor dem Push aus |

---

## 8. MCP-Server (optional)

Die MCP-Server liegen in `mcp_servers/` (FastMCP: `osm_router`, `weather`,
`rain_sensor` — mit Mock-Fallback). Die Server werden zur Laufzeit ueber
`langchain-mcp-adapters` (`MultiServerMCPClient`) angebunden und sind nicht
Teil der Kern-Installation.

```bash
# Beispiel: Wetter-Server starten (SSE auf Port 8082, Mock-Fallback ohne API-Key)
python -m mcp_servers.weather.server
```

> Details zur MCP-Anbindung: [docs/mcp_routing.md](mcp_routing.md).

---

## 9. Bekannte Stolpersteine

| Problem | Empfehlung |
|---|---|
| Orchestrator delegiert nicht (gemma4:12b antwortet direkt) | HITL (`run_interactive()`) oder direkten Agent (`run_web_search`, `run_code`) nutzen — die `task`-Delegation ist mit gemma4:12b unzuverlaessig |
| `jupyter execute` ohne `--inplace` speichert keine Ergebnisse | Immer `--inplace` angeben |
| `python` findet `agent-smith` nicht | Venv aktivieren (`source .venv/bin/activate`) oder `.venv/bin/python3` nutzen |
| setuptools 82+ bricht editable Install | `.pth`-Workaround aus [1.5](#15-setup-workaround-nur-bei-setuptools-82-auf-python-314) |

---

## 10. Weitere Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/architektur.md](architektur.md) | Vollstaendige Architekturbeschreibung |
| [docs/tutorial.md](tutorial.md) | Schritt-fuer-Schritt-Einfuehrung |
| [docs/anforderungen.md](anforderungen.md) | Anforderungsdokument |
| [docs/features_and_ideas.md](features_and_ideas.md) | Feature-Tracking |
| [docs/security.md](security.md) | Sicherheitskonzept |
| [docs/mcp_routing.md](mcp_routing.md) | MCP-Anbindung |
| [docs/chatlog.md](chatlog.md) | Chat-Verlauf der Entwicklungssessions |
