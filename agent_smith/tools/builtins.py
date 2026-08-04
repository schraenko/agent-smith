"""
Built-in tools.
Each tool is a plain function decorated with LangChain's @tool.
No classes, no inheritance — just functions.
"""

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import httpx
from langchain_core.tools import tool


# ─── Web Search ───────────────────────────────────────────────────────────────

@tool
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo. Returns titles, URLs, and snippets."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in ddgs.text(query, max_results=max_results)
            ]
        return results or [{"title": "No results", "url": "", "snippet": f"No results for: {query}"}]
    except Exception as e:
        return [{"title": "Search error", "url": "", "snippet": str(e)}]


# ─── Code Execution ───────────────────────────────────────────────────────────

@tool
def execute_python(code: str, timeout: int = 30) -> dict:
    """Execute Python code in a subprocess. Returns stdout, stderr, and returncode."""
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


# ─── HTTP ─────────────────────────────────────────────────────────────────────

@tool
def http_get(url: str, headers: dict | None = None, params: dict | None = None) -> dict:
    """Perform an HTTP GET request and return status, headers, and body."""
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url, headers=headers or {}, params=params or {})
            return {"status_code": r.status_code, "body": r.text[:5000]}
    except Exception as e:
        return {"error": str(e)}


@tool
def http_post(url: str, body: dict, headers: dict | None = None) -> dict:
    """Perform an HTTP POST request with a JSON body."""
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(url, json=body, headers=headers or {})
            return {"status_code": r.status_code, "body": r.text[:5000]}
    except Exception as e:
        return {"error": str(e)}


# ─── Data ─────────────────────────────────────────────────────────────────────

@tool
def read_csv(path: str, max_rows: int = 100) -> dict:
    """Read a CSV file and return its contents as a list of row dicts."""
    try:
        import csv
        rows = []
        with open(path, newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f)):
                if i >= max_rows:
                    break
                rows.append(dict(row))
        return {"rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


@tool
def describe_data(path: str) -> dict:
    """Return summary statistics and schema for a CSV file."""
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


@tool
def query_data(path: str, query: str, columns: list[str] | None = None) -> dict:
    """Run a pandas query string filter on a CSV file."""
    try:
        import pandas as pd
        df = pd.read_csv(path)
        if columns:
            df = df[columns]
        result = df.query(query)
        return {"rows": result.head(100).to_dict(orient="records"), "count": len(result)}
    except Exception as e:
        return {"error": str(e)}


# ─── Tool collections ─────────────────────────────────────────────────────────

ALL_TOOLS = [
    web_search, execute_python,
    http_get, http_post,
    read_csv, describe_data, query_data,
]

TOOL_MAP: dict[str, object] = {t.name: t for t in ALL_TOOLS}


def get_tools(names: list[str] | None = None) -> list:
    """Return tools by name, or all tools if names is None."""
    if names is None:
        return ALL_TOOLS
    return [TOOL_MAP[n] for n in names if n in TOOL_MAP]
