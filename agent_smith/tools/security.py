"""
Security scanning tools.

Wraps external scanners (bandit, gitleaks, pip-audit) and adds a regex-based
fallback for environments where these binaries are not installed.

Severity model:
- critical: secrets, hardcoded credentials, dangerous functions
- warning:  medium-severity code issues, outdated dependencies
- info:     low-severity hints

All tools are plain functions decorated with LangChain's @tool.
"""

import json
import re
import subprocess
from pathlib import Path

from langchain_core.tools import tool


SECRET_PATTERNS: dict[str, str] = {
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret_key": r"(?i)aws[_-]?secret[_-]?access[_-]?key[^\n]{0,40}['\"][0-9a-zA-Z/+]{40}['\"]",
    "openai_key": r"sk-[A-Za-z0-9]{20,}",
    "anthropic_key": r"sk-ant-[A-Za-z0-9\-]{20,}",
    "github_token": r"gh[pousr]_[A-Za-z0-9]{36,}",
    "private_key": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
    "slack_token": r"xox[abprs]-[0-9a-zA-Z-]{10,72}",
    "stripe_key": r"sk_(test|live)_[0-9a-zA-Z]{24,}",
    "generic_password": r"(?i)\b(password|passwd|pwd)\s*=\s*['\"][^'\"\\\s]{3,}['\"]",
    "generic_api_key": r"(?i)\b(api[_-]?key|apikey|secret[_-]?key|auth[_-]?token|access[_-]?token)\s*=\s*['\"][^'\"\\\s]{8,}['\"]",
}

DANGEROUS_FUNCTIONS: dict[str, str] = {
    "eval": "Use of eval() allows arbitrary code execution. Avoid with untrusted input.",
    "exec": "Use of exec() allows arbitrary code execution. Avoid with untrusted input.",
    "os.system": "os.system() passes string to shell. Prefer subprocess with shell=False.",
    "subprocess_shell": "subprocess with shell=True is vulnerable to shell injection. Use shell=False and pass args as list.",
    "pickle_loads": "pickle.load(s) executes arbitrary code. Use json or a safe deserializer for untrusted data.",
    "yaml_load": "yaml.load() without Loader=SafeLoader executes arbitrary code. Use yaml.safe_load().",
    "sql_string_format": "SQL query built via string formatting/concatenation. Use parameterized queries.",
    "assert_statement": "assert is removed with python -O. Do not use for security or validation logic.",
    "hardcoded_secret": "Hardcoded credential or token detected.",
    "weak_hash": "Weak hash algorithm (md5/sha1). Use sha256 or stronger for security purposes.",
}

DANGEROUS_FUNCTION_REGEX: list[tuple[str, str]] = [
    ("eval", r"\beval\s*\("),
    ("exec", r"\bexec\s*\("),
    ("os.system", r"\bos\.system\s*\("),
    ("subprocess_shell", r"subprocess\.[A-Za-z_]+\([^)]*shell\s*=\s*True"),
    ("pickle_loads", r"\bpickle\.loads?\s*\("),
    ("yaml_load", r"\byaml\.load\s*\("),
    ("sql_string_format", r'(?:execute|executemany)\s*\(\s*["\'].*?%[sd]|f["\'].*?(?:SELECT|INSERT|UPDATE|DELETE)'),
    ("assert_statement", r"^\s*assert\s+"),
    ("weak_hash", r"\bhashlib\.(?:md5|sha1)\s*\("),
]

SKIP_DIRS = {".venv", "venv", ".git", "__pycache__", "node_modules", ".opencode", "htmlcov", ".pytest_cache"}


def _is_excluded(path: Path, repo_root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return True
    return any(part in SKIP_DIRS for part in rel.parts)


def _classify_bandit_severity(severity: str) -> str:
    return {"HIGH": "critical", "MEDIUM": "warning", "LOW": "info"}.get(severity.upper(), "info")


def _classify_pipaudit_severity(fix_versions: list[str] | None) -> str:
    return "warning"


def _format_finding(tool_name: str, severity: str, file: str, line: int, message: str, snippet: str = "") -> str:
    loc = f"{file}:{line}" if line else file
    return f"[{tool_name}|{severity}] {loc} — {message}\n    {snippet}".rstrip()


def _run_subprocess(cmd: list[str], cwd: str | None = None, timeout: int = 60) -> dict:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return {"ok": True, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except FileNotFoundError as e:
        return {"ok": False, "error": f"Tool not installed: {e.filename}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool
def bandit_scan(path: str = ".") -> dict:
    """Run bandit Python security linter on the given path. Returns findings classified by severity."""
    cmd_result = _run_subprocess(["bandit", "-r", path, "-f", "json", "-q"], cwd=path)
    if not cmd_result["ok"]:
        return {"scanner": "bandit", "available": False, "error": cmd_result["error"], "findings": []}

    try:
        data = json.loads(cmd_result["stdout"])
    except json.JSONDecodeError as e:
        return {"scanner": "bandit", "available": True, "error": f"JSON parse error: {e}", "findings": []}

    findings: list[dict] = []
    for r in data.get("results", []):
        findings.append({
            "severity": _classify_bandit_severity(r.get("issue_severity", "LOW")),
            "file": r.get("filename", ""),
            "line": r.get("line_number", 0),
            "test_id": r.get("test_id", ""),
            "test_name": r.get("test_name", ""),
            "message": r.get("issue_text", ""),
        })

    return {
        "scanner": "bandit",
        "available": True,
        "metrics": data.get("metrics", {}),
        "findings": findings,
        "summary": {
            "critical": sum(1 for f in findings if f["severity"] == "critical"),
            "warning": sum(1 for f in findings if f["severity"] == "warning"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
    }


@tool
def secret_scan(path: str = ".") -> dict:
    """Scan for hardcoded secrets (API keys, passwords, tokens). Uses gitleaks if available, otherwise regex fallback."""
    cmd_result = _run_subprocess(
        ["gitleaks", "detect", "--source", path, "-f", "json", "--no-banner", "--redact"],
        cwd=path,
    )

    if cmd_result["ok"]:
        findings: list[dict] = []
        if cmd_result["stdout"].strip():
            try:
                raw = json.loads(cmd_result["stdout"])
            except json.JSONDecodeError:
                raw = []
            for entry in raw if isinstance(raw, list) else []:
                findings.append({
                    "severity": "critical",
                    "file": entry.get("File", ""),
                    "line": entry.get("StartLine", 0),
                    "rule": entry.get("RuleID", ""),
                    "message": entry.get("Description", "Secret detected by gitleaks"),
                    "match": entry.get("Match", ""),
                })
        return {
            "scanner": "gitleaks",
            "available": True,
            "findings": findings,
            "summary": {
                "critical": len(findings),
                "warning": 0,
                "info": 0,
            },
        }

    findings = []
    repo_root = Path(path)
    for py_file in repo_root.rglob("*.py"):
        if _is_excluded(py_file, repo_root):
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern_name, pattern in SECRET_PATTERNS.items():
                if re.search(pattern, line):
                    findings.append({
                        "severity": "critical",
                        "file": str(py_file.relative_to(repo_root)),
                        "line": lineno,
                        "rule": pattern_name,
                        "message": f"Potential secret detected ({pattern_name})",
                        "match": line.strip()[:120],
                    })

    return {
        "scanner": "regex-fallback",
        "available": True,
        "note": "gitleaks not installed; using regex fallback",
        "findings": findings,
        "summary": {
            "critical": len(findings),
            "warning": 0,
            "info": 0,
        },
    }


@tool
def audit_dependencies() -> dict:
    """Audit Python dependencies for known vulnerabilities using pip-audit."""
    cmd_result = _run_subprocess(["pip-audit", "-f", "json", "--strict"], timeout=120)
    if not cmd_result["ok"]:
        return {
            "scanner": "pip-audit",
            "available": False,
            "error": cmd_result["error"],
            "findings": [],
        }

    try:
        data = json.loads(cmd_result["stdout"])
    except json.JSONDecodeError as e:
        return {"scanner": "pip-audit", "available": True, "error": f"JSON parse error: {e}", "findings": []}

    findings: list[dict] = []
    for dep in data.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            findings.append({
                "severity": _classify_pipaudit_severity(vuln.get("fix_versions")),
                "package": dep.get("name", ""),
                "version": dep.get("version", ""),
                "vuln_id": vuln.get("id", ""),
                "description": vuln.get("description", ""),
                "fix_versions": vuln.get("fix_versions", []),
            })

    return {
        "scanner": "pip-audit",
        "available": True,
        "findings": findings,
        "summary": {
            "critical": sum(1 for f in findings if f["severity"] == "critical"),
            "warning": sum(1 for f in findings if f["severity"] == "warning"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
    }


@tool
def security_scan(path: str = ".") -> dict:
    """Run all security scanners (bandit, secret_scan, audit_dependencies) and return a combined report."""
    bandit_result = bandit_scan.func(path) if hasattr(bandit_scan, "func") else bandit_scan.invoke({"path": path})
    secret_result = secret_scan.func(path) if hasattr(secret_scan, "func") else secret_scan.invoke({"path": path})
    audit_result = audit_dependencies.func() if hasattr(audit_dependencies, "func") else audit_dependencies.invoke({})

    total_critical = (
        bandit_result.get("summary", {}).get("critical", 0)
        + secret_result.get("summary", {}).get("critical", 0)
        + audit_result.get("summary", {}).get("critical", 0)
    )
    total_warnings = (
        bandit_result.get("summary", {}).get("warning", 0)
        + secret_result.get("summary", {}).get("warning", 0)
        + audit_result.get("summary", {}).get("warning", 0)
    )
    total_info = (
        bandit_result.get("summary", {}).get("info", 0)
        + secret_result.get("summary", {}).get("info", 0)
        + audit_result.get("summary", {}).get("info", 0)
    )

    recommendation = "BESTANDEN" if total_critical == 0 else "NICHT BESTANDEN"

    report_lines = [
        "## Security Scan Report",
        f"Path: {path}",
        f"Recommendation: **{recommendation}**",
        "",
        "### Summary",
        f"- Critical: {total_critical}",
        f"- Warnings: {total_warnings}",
        f"- Info:     {total_info}",
        "",
    ]

    for label, result in [
        ("Bandit (Python Code)", bandit_result),
        ("Secret Scan", secret_result),
        ("Dependency Audit (pip-audit)", audit_result),
    ]:
        if not result.get("available", False):
            report_lines.append(f"### {label}: NOT AVAILABLE")
            report_lines.append(f"Error: {result.get('error', 'unknown')}")
            report_lines.append("")
            continue
        summary = result.get("summary", {})
        report_lines.append(
            f"### {label}: {summary.get('critical', 0)} critical, {summary.get('warning', 0)} warnings, {summary.get('info', 0)} info"
        )
        for f in result.get("findings", []):
            if f.get("severity") == "critical":
                loc = f.get("file", "")
                if f.get("line"):
                    loc += f":{f['line']}"
                msg = f.get("message") or f.get("description") or f.get("rule") or "issue"
                report_lines.append(f"- **[critical]** `{loc}` — {msg}")
        report_lines.append("")

    return {
        "recommendation": recommendation,
        "summary": {
            "critical": total_critical,
            "warnings": total_warnings,
            "info": total_info,
        },
        "scanners": {
            "bandit": bandit_result,
            "secrets": secret_result,
            "dependencies": audit_result,
        },
        "report": "\n".join(report_lines),
    }
