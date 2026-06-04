import csv
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import httpx


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo."""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        return results or [{"title": "No results", "url": "", "snippet": f"No results found for: {query}"}]
    except Exception as e:
        return [{"title": "Search error", "url": "", "snippet": str(e)}]


def execute_python(code: str, timeout: int = 30) -> dict:
    """Execute Python code in a subprocess and return stdout/stderr."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(textwrap.dedent(code))
        tmp_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True, timeout=timeout,
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Timeout after {timeout}s", "returncode": -1}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def read_file(path: str, max_chars: int = 10000) -> dict:
    """Read a text file and return its contents up to max_chars."""
    try:
        content = Path(path).read_text(encoding="utf-8")
        truncated = len(content) > max_chars
        return {"content": content[:max_chars], "truncated": truncated, "total_chars": len(content)}
    except Exception as e:
        return {"error": str(e)}


def list_files(path: str = ".", pattern: str = "*") -> list[str]:
    """List files matching a glob pattern in a directory."""
    try:
        return [str(p) for p in Path(path).glob(pattern) if p.is_file()]
    except Exception as e:
        return [f"Error: {e}"]


def http_get(url: str, headers: dict | None = None, params: dict | None = None) -> dict:
    """Send an HTTP GET request and return the response."""
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url, headers=headers or {}, params=params or {})
            return {"status_code": r.status_code, "body": r.text[:5000]}
    except Exception as e:
        return {"error": str(e)}


def http_post(url: str, body: dict, headers: dict | None = None) -> dict:
    """Send an HTTP POST request with a JSON body and return the response."""
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(url, json=body, headers=headers or {})
            return {"status_code": r.status_code, "body": r.text[:5000]}
    except Exception as e:
        return {"error": str(e)}


def read_csv(path: str, max_rows: int = 100) -> dict:
    """Read a CSV file and return rows as dicts."""
    try:
        rows = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(dict(row))
        return {"rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


def query_data(path: str, query: str, columns: list[str] | None = None) -> dict:
    """Query a CSV file using a pandas query expression."""
    try:
        import pandas as pd
        df = pd.read_csv(path)
        if columns:
            df = df[columns]
        result = df.query(query)
        return {"rows": result.head(100).to_dict(orient="records"), "count": len(result)}
    except Exception as e:
        return {"error": str(e)}


def describe_data(path: str) -> dict:
    """Return descriptive statistics for a CSV file."""
    try:
        import pandas as pd
        df = pd.read_csv(path)
        return {
            "shape": list(df.shape),
            "columns": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "describe": json.loads(df.describe(include="all").to_json()),
        }
    except Exception as e:
        return {"error": str(e)}


ALL_TOOLS = [
    web_search, execute_python,
    read_file, list_files,
    http_get, http_post,
    read_csv, query_data, describe_data,
]

TOOL_MAP: dict[str, Any] = {t.__name__: t for t in ALL_TOOLS}


def get_tools(names: list[str] | None = None) -> list:
    if names is None:
        return ALL_TOOLS
    return [TOOL_MAP[n] for n in names if n in TOOL_MAP]


def delegate_to(agent: str, task: str) -> str:
    from agent_smith_crewai.agents.builtins import (
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
        return f"Unknown agent: {agent}. Choose from: {list(dispatch.keys())}"
    result = runner(task)
    return result.output if result.success else f"Agent failed: {result.error}"
