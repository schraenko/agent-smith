---
title: Security Policy
author: agent-smith
date: 2026-07-28
tags: [security, scanning, workflow]
abstract: Dokumentation der Security-Scanner, ihrer Konfiguration und Integration in den Coding-Workflow.
---

# Security Policy

Diese Dokumentation beschreibt die Security-Scanner im agent-smith-Projekt, ihre Installation und Integration in den Entwicklungs-Workflow.

## Übersicht

Drei Defense-in-Depth-Schichten schützen den Code:

| Schicht | Tool | Trigger | Aktion |
|---|---|---|---|
| **LLM-Security-Agent** | Ollama via `security` Subagent | Während `dev-workflow` Schritt 1.5 | Semantische Analyse, Report |
| **Pattern-Scanner** | `bandit`, `gitleaks`, `pip-audit` | Vor `git push` (Pre-Push Hook) | Blockiert bei kritischen Funden |
| **Regex-Fallback** | Built-in Python Regex | Immer (im Tool) | Erkennt Standard-Secrets |

## Security-Tools

### `bandit_scan`

Python-Security-Linter. Erkennt:

- `eval()`, `exec()` — arbitrary code execution
- `os.system()` — shell command injection
- `subprocess` mit `shell=True` — shell injection
- `pickle.load(s)` — arbitrary code execution
- `yaml.load()` ohne SafeLoader — arbitrary code execution
- SQL-String-Konkatenation — SQL-Injection
- Schwaches Hashing (md5, sha1)

**Severity-Mapping:**

| bandit-Severity | agent_smith-Severity | Blockiert Push? |
|---|---|---|
| HIGH | critical | ✅ Ja |
| MEDIUM | warning | ❌ Nein (nur Report) |
| LOW | info | ❌ Nein |

### `secret_scan`

Secret-Detection. Nutzt `gitleaks` falls installiert, sonst Regex-Fallback.

**Erkannte Patterns:**

| Provider | Regex |
|---|---|
| AWS Access Key | `AKIA[0-9A-Z]{16}` |
| OpenAI | `sk-[A-Za-z0-9]{20,}` |
| Anthropic | `sk-ant-[A-Za-z0-9\-]{20,}` |
| GitHub | `gh[pousr]_[A-Za-z0-9]{36,}` |
| Stripe | `sk_(test\|live)_[0-9a-zA-Z]{24,}` |
| Slack | `xox[abprs]-[0-9a-zA-Z-]{10,72}` |
| Private Key | `-----BEGIN (RSA \|EC \|DSA \|OPENSSH )?PRIVATE KEY-----` |
| Generic Password | `password\s*=\s*['"][^'"\s]{3,}['"]` |
| Generic API Key | `api[_-]?key\s*=\s*['"][^'"\s]{8,}['"]` |

**Jeder Fund = critical → blockiert Push.**

### `audit_dependencies`

Scannt `pip` Dependencies auf bekannte CVEs via `pip-audit`.

**Severity:** Aktuell immer `warning` (kein CVSS-Score-Parsing, kann erweitert werden).

### `security_scan`

Kombiniert alle drei Scans zu einem aggregierten Report:

```python
{
    "recommendation": "BESTANDEN" | "NICHT BESTANDEN",
    "summary": {"critical": 0, "warnings": 0, "info": 0},
    "scanners": {"bandit": {...}, "secrets": {...}, "dependencies": {...}},
    "report": "## Security Scan Report\n..."
}
```

**Entscheidungslogik:**

- `critical > 0` → `NICHT BESTANDEN` → Push blockiert
- `critical == 0` und `warning > 0` → `BESTANDEN` mit Warnungen
- `critical == 0` und `warning == 0` → `BESTANDEN`

## Integration in den Workflow

### Im dev-workflow (OpenCode)

```
Schritt 1: coder
   ↓
Schritt 1.5: security (NEU) ← Scannt Code-Änderungen
   ↓
Schritt 2: reviewer
   ↓
Schritt 3: tester
```

**Verhalten bei Schritt 1.5:**

| Security-Status | Aktion |
|---|---|
| BESTANDEN | WEITERLEITEN an Review |
| WARNUNGEN | WEITERLEITEN mit Hinweis an Tester |
| KRITISCH | ZURÜCK ZUM CODER mit Security-Report |

### Im Pre-Push Hook

Bei jedem `git push` läuft automatisch `.git/hooks/pre-push`:

1. `gitleaks protect --staged` (falls installiert)
2. `bandit -r .` (falls installiert)
3. `pip-audit --strict` (falls installiert)

**Bei critical findings:** Push blockiert mit Anweisungen.

**Bypass (nicht empfohlen):** `git push --no-verify`

## Installation

### bandit (Python)

Wird automatisch via `pip install -e ".[dev]"` installiert (siehe `pyproject.toml`).

Manuelle Installation (nicht empfohlen):

```bash
pip install bandit
```

### pip-audit (Python)

Wird automatisch via `pip install -e ".[dev]"` installiert (siehe `pyproject.toml`).

Manuelle Installation (nicht empfohlen):

```bash
pip install pip-audit
```

### gitleaks (Go-Binary)

**Empfohlen (automatisch, OS-Erkennung):**

```bash
bash scripts/install-security-tools.sh
```

Unterstützt macOS (Homebrew) und Linux (Binary-Download via wget/curl).

**Manuell (falls Script fehlschlägt):**

```bash
# macOS
brew install gitleaks

# Linux (amd64)
VERSION=8.18.4
wget https://github.com/gitleaks/gitleaks/releases/download/v${VERSION}/gitleaks_${VERSION}_linux_amd64.tar.gz
tar -xzf gitleaks_${VERSION}_linux_amd64.tar.gz
sudo mv gitleaks /usr/local/bin/

# Windows
scoop install gitleaks
```

**Hinweis:** Ohne gitleaks funktioniert `secret_scan` mit Regex-Fallback (10 Patterns, weniger umfassend als gitleaks).

### Optional: pre-commit Framework

Falls das `pre-commit` Framework bevorzugt wird, kann eine `.pre-commit-config.yaml` ergänzt werden:

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.8
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
```

## Bypass-Optionen

Falls ein False-Positive gefunden wird:

| Bypass | Wie | Risiko |
|---|---|---|
| Push | `git push --no-verify` | Hoch — Secrets gelangen ins Repo |
| Workflow | User-bestätigtes Überspringen | Mittel — manueller Review nötig |
| Inline | `# nosec` Kommentar (bandit-spezifisch) | Niedrig — nur Code, nicht Hook |

## Tests

Security-Tests in `tests/test_security.py`:

```bash
python -m pytest tests/test_security.py -v
```

**18 Tests** decken ab:

- Pattern-Definitionen
- Bandit JSON-Parsing und Severity-Mapping
- Secret-Scanning (gitleaks + Regex-Fallback)
- Dependency-Audit
- Aggregierte Reports
- Tool-Registrierung
- Skip-Verhalten (`.venv`)

## Best Practices

1. **Keine Secrets im Code** — Nutze Environment-Variablen oder `.env` (in `.gitignore`)
2. **Dependencies aktuell halten** — Regelmäßig `pip-audit` laufen lassen
3. **Keine `eval()`/`exec()`** — Nutze sichere Alternativen (`ast.literal_eval`, `json.loads`)
4. **Parameterisierte Queries** — Verwende SQLAlchemy oder `?`-Platzhalter
5. **`shell=False`** — Bei `subprocess` immer `shell=False` und args als Liste

## Bekannte Limitierungen

- **pip-audit CVSS-Score** wird nicht geparst (alle findings = warning)
- **Regex-Fallback** kann False-Positives haben bei Base64-Strings
- **Kein Semgrep** integriert (für komplexere Multi-Language-Analyse)
- **Kein GitHub Actions CI** (nur lokale Hooks)
