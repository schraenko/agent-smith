"""
Tests for the security scanning tools:
- secret_scan (regex-based fallback for gitleaks)
- bandit_scan (with mocked subprocess)
- audit_dependencies (with mocked subprocess)
- security_scan (combined report)
- severity classification
"""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from agent_smith.tools import security as sec
from agent_smith.tools.security import (
    DANGEROUS_FUNCTIONS,
    SECRET_PATTERNS,
    audit_dependencies,
    bandit_scan,
    secret_scan,
    security_scan,
)


# ─── Pattern constants ────────────────────────────────────────────────────────

def test_secret_patterns_defined():
    expected_keys = {
        "aws_access_key", "openai_key", "anthropic_key",
        "github_token", "private_key", "generic_password", "generic_api_key",
    }
    assert expected_keys.issubset(SECRET_PATTERNS.keys())


def test_dangerous_functions_defined():
    expected = {"eval", "exec", "os.system", "subprocess_shell", "pickle_loads", "yaml_load"}
    assert expected.issubset(DANGEROUS_FUNCTIONS.keys())


# ─── bandit_scan ──────────────────────────────────────────────────────────────

def _bandit_subprocess_mock(*, high: int = 0, medium: int = 0, low: int = 0):
    results = []
    for i in range(high):
        results.append({"issue_severity": "HIGH", "filename": f"src/mod{i}.py",
                        "line_number": 10 + i, "test_id": "B102", "test_name": "exec_used",
                        "issue_text": "Use of exec detected"})
    for i in range(medium):
        results.append({"issue_severity": "MEDIUM", "filename": f"src/m{i}.py",
                        "line_number": 20 + i, "test_id": "B602", "test_name": "shell_true",
                        "issue_text": "subprocess with shell=True"})
    for i in range(low):
        results.append({"issue_severity": "LOW", "filename": f"src/l{i}.py",
                        "line_number": 30 + i, "test_id": "B303", "test_name": "md5",
                        "issue_text": "Use of weak hash"})

    payload = json.dumps({"results": results, "metrics": {"_totals": {"loc": 1000}}})
    mock_result = MagicMock()
    mock_result.stdout = payload
    mock_result.returncode = 0
    return mock_result


def test_bandit_scan_classifies_severity():
    mock_proc = _bandit_subprocess_mock(high=1, medium=2, low=1)
    with patch.object(sec.subprocess, "run", return_value=mock_proc):
        result = bandit_scan.func(".")

    assert result["available"] is True
    assert result["summary"]["critical"] == 1
    assert result["summary"]["warning"] == 2
    assert result["summary"]["info"] == 1
    assert result["findings"][0]["severity"] == "critical"
    assert result["findings"][0]["test_id"] == "B102"


def test_bandit_scan_handles_tool_not_installed():
    err = FileNotFoundError(2, "No such file", "bandit")
    with patch.object(sec.subprocess, "run", side_effect=err):
        result = bandit_scan.func(".")

    assert result["available"] is False
    assert "error" in result
    assert result["findings"] == []


def test_bandit_scan_handles_invalid_json():
    mock_result = MagicMock()
    mock_result.stdout = "not json"
    mock_result.returncode = 0
    with patch.object(sec.subprocess, "run", return_value=mock_result):
        result = bandit_scan.func(".")

    assert result["available"] is True
    assert "JSON parse error" in result["error"]


# ─── secret_scan ──────────────────────────────────────────────────────────────

def _write_py_with_secret(tmp_path, content: str):
    py_file = tmp_path / "config.py"
    py_file.write_text(content)
    return tmp_path


def test_secret_scan_detects_aws_key(tmp_path):
    _write_py_with_secret(
        tmp_path,
        'aws_key = "AKIAIOSFODNN7EXAMPLE"\n',
    )
    with patch.object(sec.subprocess, "run", side_effect=FileNotFoundError(2, "no", "gitleaks")):
        result = secret_scan.func(str(tmp_path))

    assert result["available"] is True
    assert result["scanner"] == "regex-fallback"
    assert result["summary"]["critical"] >= 1
    rules = {f["rule"] for f in result["findings"]}
    assert "aws_access_key" in rules


def test_secret_scan_detects_openai_key(tmp_path):
    _write_py_with_secret(
        tmp_path,
        'api = "sk-abcdefghijklmnopqrstuv1234567890ABCDEFGH"\n',
    )
    with patch.object(sec.subprocess, "run", side_effect=FileNotFoundError(2, "no", "gitleaks")):
        result = secret_scan.func(str(tmp_path))

    rules = {f["rule"] for f in result["findings"]}
    assert "openai_key" in rules


def test_secret_scan_detects_github_token(tmp_path):
    _write_py_with_secret(
        tmp_path,
        'token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789AB"\n',
    )
    with patch.object(sec.subprocess, "run", side_effect=FileNotFoundError(2, "no", "gitleaks")):
        result = secret_scan.func(str(tmp_path))

    rules = {f["rule"] for f in result["findings"]}
    assert "github_token" in rules


def test_secret_scan_detects_generic_password(tmp_path):
    _write_py_with_secret(
        tmp_path,
        'password = "super_secret_123"\n',
    )
    with patch.object(sec.subprocess, "run", side_effect=FileNotFoundError(2, "no", "gitleaks")):
        result = secret_scan.func(str(tmp_path))

    rules = {f["rule"] for f in result["findings"]}
    assert "generic_password" in rules


def test_secret_scan_no_false_positive_on_short_value(tmp_path):
    _write_py_with_secret(
        tmp_path,
        'x = "hi"\n',
    )
    with patch.object(sec.subprocess, "run", side_effect=FileNotFoundError(2, "no", "gitleaks")):
        result = secret_scan.func(str(tmp_path))

    assert result["summary"]["critical"] == 0


def test_secret_scan_uses_gitleaks_when_available(tmp_path):
    gitleaks_output = json.dumps([
        {
            "File": "src/secret.py",
            "StartLine": 5,
            "RuleID": "aws-access-token",
            "Description": "AWS access token",
            "Match": "AKIA...EXAMPLE",
        }
    ])
    mock_result = MagicMock()
    mock_result.stdout = gitleaks_output
    mock_result.returncode = 1
    with patch.object(sec.subprocess, "run", return_value=mock_result):
        result = secret_scan.func(str(tmp_path))

    assert result["scanner"] == "gitleaks"
    assert result["summary"]["critical"] == 1
    assert result["findings"][0]["rule"] == "aws-access-token"


def test_secret_scan_skips_venv_directory(tmp_path):
    venv_dir = tmp_path / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "secret.py").write_text('password = "super_secret_123"\n')

    with patch.object(sec.subprocess, "run", side_effect=FileNotFoundError(2, "no", "gitleaks")):
        result = secret_scan.func(str(tmp_path))

    assert result["summary"]["critical"] == 0


# ─── audit_dependencies ───────────────────────────────────────────────────────

def test_audit_dependencies_returns_findings():
    payload = json.dumps({
        "dependencies": [
            {
                "name": "vuln-pkg",
                "version": "1.0.0",
                "vulns": [
                    {
                        "id": "PYSEC-2023-001",
                        "description": "Critical RCE",
                        "fix_versions": ["1.0.1"],
                    }
                ],
            }
        ]
    })
    mock_result = MagicMock()
    mock_result.stdout = payload
    mock_result.returncode = 0
    with patch.object(sec.subprocess, "run", return_value=mock_result):
        result = audit_dependencies.func()

    assert result["available"] is True
    assert len(result["findings"]) == 1
    assert result["findings"][0]["package"] == "vuln-pkg"
    assert result["findings"][0]["vuln_id"] == "PYSEC-2023-001"


def test_audit_dependencies_handles_missing_tool():
    with patch.object(sec.subprocess, "run", side_effect=FileNotFoundError(2, "no", "pip-audit")):
        result = audit_dependencies.func()

    assert result["available"] is False
    assert "error" in result


# ─── security_scan (combined) ────────────────────────────────────────────────

def test_security_scan_aggregates_critical_findings():
    bandit_payload = json.dumps({
        "results": [
            {"issue_severity": "HIGH", "filename": "x.py", "line_number": 1,
             "test_id": "B102", "test_name": "exec", "issue_text": "exec used"}
        ],
        "metrics": {},
    })
    bandit_proc = MagicMock(stdout=bandit_payload, returncode=0)

    gitleaks_payload = json.dumps([
        {"File": "x.py", "StartLine": 2, "RuleID": "aws",
         "Description": "AWS key", "Match": "AKIA..."}
    ])
    gitleaks_proc = MagicMock(stdout=gitleaks_payload, returncode=1)

    pip_payload = json.dumps({"dependencies": []})
    pip_proc = MagicMock(stdout=pip_payload, returncode=0)

    def subprocess_side_effect(cmd, **kwargs):
        if "bandit" in cmd[0]:
            return bandit_proc
        if "gitleaks" in cmd[0]:
            return gitleaks_proc
        if "pip-audit" in cmd[0]:
            return pip_proc
        raise RuntimeError(f"unexpected command: {cmd}")

    with patch.object(sec.subprocess, "run", side_effect=subprocess_side_effect):
        result = security_scan.func(".")

    assert result["recommendation"] == "NICHT BESTANDEN"
    assert result["summary"]["critical"] == 2
    assert "Security Scan Report" in result["report"]
    assert "NICHT BESTANDEN" in result["report"]


def test_security_scan_bestanden_when_clean():
    bandit_payload = json.dumps({"results": [], "metrics": {}})
    bandit_proc = MagicMock(stdout=bandit_payload, returncode=0)

    gitleaks_payload = json.dumps([])
    gitleaks_proc = MagicMock(stdout=gitleaks_payload, returncode=0)

    pip_payload = json.dumps({"dependencies": []})
    pip_proc = MagicMock(stdout=pip_payload, returncode=0)

    def subprocess_side_effect(cmd, **kwargs):
        if "bandit" in cmd[0]:
            return bandit_proc
        if "gitleaks" in cmd[0]:
            return gitleaks_proc
        if "pip-audit" in cmd[0]:
            return pip_proc
        raise RuntimeError(f"unexpected command: {cmd}")

    with patch.object(sec.subprocess, "run", side_effect=subprocess_side_effect):
        result = security_scan.func(".")

    assert result["recommendation"] == "BESTANDEN"
    assert result["summary"]["critical"] == 0
    assert "BESTANDEN" in result["report"]


# ─── Tool registration ───────────────────────────────────────────────────────

def test_security_tools_registered_in_tool_map():
    from agent_smith.tools import TOOL_MAP
    assert "bandit_scan" in TOOL_MAP
    assert "secret_scan" in TOOL_MAP
    assert "audit_dependencies" in TOOL_MAP
    assert "security_scan" in TOOL_MAP


def test_security_tools_in_all_tools_list():
    from agent_smith.tools import ALL_TOOLS
    tool_names = {t.name for t in ALL_TOOLS}
    assert {"bandit_scan", "secret_scan", "audit_dependencies", "security_scan"}.issubset(tool_names)
