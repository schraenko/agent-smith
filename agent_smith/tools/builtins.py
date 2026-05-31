"""
Built-in tool implementations.
Each tool is a plain function registered via the @tool decorator.
"""

import io
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import httpx

from agent_smith.tools.registry import tool


# ─── Web Search ───────────────────────────────────────────────────────────────

@tool(
    name="web_search",
    description="Search the web for information. Returns a list of results with titles, URLs, and snippets.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "description": "Max results to return (default 5)", "default": 5},
        },
        "required": ["query"],
    },
)
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Uses DuckDuckGo Instant Answer API (no key required).
    For production, replace with a proper Search API.
    """
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            )
            response.raise_for_status()
            data = response.json()

        results = []

        # Abstract
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", ""),
                "url": data.get("AbstractURL", ""),
                "snippet": data["Abstract"],
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if "Text" in topic:
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", ""),
                })

        return results[:max_results] or [{"title": "No results", "url": "", "snippet": f"No results found for: {query}"}]
    except Exception as e:
        return [{"title": "Search error", "url": "", "snippet": str(e)}]


# ─── Code Execution ───────────────────────────────────────────────────────────

@tool(
    name="execute_python",
    description="Execute Python code in a sandboxed subprocess and return stdout/stderr.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)", "default": 30},
        },
        "required": ["code"],
    },
)
def execute_python(code: str, timeout: int = 30) -> dict:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(textwrap.dedent(code))
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Timeout after {timeout}s", "returncode": -1}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ─── File Operations ──────────────────────────────────────────────────────────

@tool(
    name="read_file",
    description="Read the contents of a file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
            "max_chars": {"type": "integer", "description": "Max characters to read (default 10000)", "default": 10000},
        },
        "required": ["path"],
    },
)
def read_file(path: str, max_chars: int = 10000) -> dict:
    try:
        content = Path(path).read_text(encoding="utf-8")
        truncated = len(content) > max_chars
        return {
            "content": content[:max_chars],
            "truncated": truncated,
            "total_chars": len(content),
        }
    except Exception as e:
        return {"error": str(e)}


@tool(
    name="list_files",
    description="List files in a directory.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (default: current dir)", "default": "."},
            "pattern": {"type": "string", "description": "Glob pattern (default: *)", "default": "*"},
        },
    },
)
def list_files(path: str = ".", pattern: str = "*") -> list[str]:
    try:
        return [str(p) for p in Path(path).glob(pattern) if p.is_file()]
    except Exception as e:
        return [f"Error: {e}"]


# ─── HTTP ─────────────────────────────────────────────────────────────────────

@tool(
    name="http_get",
    description="Perform an HTTP GET request and return the response.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to request"},
            "headers": {"type": "object", "description": "Optional request headers", "default": {}},
            "params": {"type": "object", "description": "Optional query parameters", "default": {}},
        },
        "required": ["url"],
    },
)
def http_get(url: str, headers: dict | None = None, params: dict | None = None) -> dict:
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url, headers=headers or {}, params=params or {})
            return {
                "status_code": r.status_code,
                "headers": dict(r.headers),
                "body": r.text[:5000],
            }
    except Exception as e:
        return {"error": str(e)}


@tool(
    name="http_post",
    description="Perform an HTTP POST request and return the response.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to post to"},
            "body": {"type": "object", "description": "JSON body to send"},
            "headers": {"type": "object", "description": "Optional request headers", "default": {}},
        },
        "required": ["url", "body"],
    },
)
def http_post(url: str, body: dict, headers: dict | None = None) -> dict:
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(url, json=body, headers=headers or {})
            return {
                "status_code": r.status_code,
                "headers": dict(r.headers),
                "body": r.text[:5000],
            }
    except Exception as e:
        return {"error": str(e)}


# ─── Data ─────────────────────────────────────────────────────────────────────

@tool(
    name="read_csv",
    description="Read a CSV file and return its contents as a list of dicts.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the CSV file"},
            "max_rows": {"type": "integer", "description": "Max rows to return (default 100)", "default": 100},
        },
        "required": ["path"],
    },
)
def read_csv(path: str, max_rows: int = 100) -> dict:
    try:
        import csv
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


@tool(
    name="query_data",
    description="Run a simple filter/aggregation query on a CSV file using pandas.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the CSV file"},
            "query": {"type": "string", "description": "Pandas query string (e.g. 'age > 30')"},
            "columns": {"type": "array", "items": {"type": "string"}, "description": "Columns to include"},
        },
        "required": ["path", "query"],
    },
)
def query_data(path: str, query: str, columns: list[str] | None = None) -> dict:
    try:
        import pandas as pd
        df = pd.read_csv(path)
        if columns:
            df = df[columns]
        result = df.query(query)
        return {"rows": result.head(100).to_dict(orient="records"), "count": len(result)}
    except Exception as e:
        return {"error": str(e)}


@tool(
    name="describe_data",
    description="Return summary statistics for a CSV file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the CSV file"},
        },
        "required": ["path"],
    },
)
def describe_data(path: str) -> dict:
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


# ─── Delegation (for Orchestrator) ────────────────────────────────────────────

@tool(
    name="delegate_to",
    description="Delegate a subtask to a specialist agent. Returns the agent's output.",
    parameters={
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "description": "Agent to delegate to",
                "enum": ["WebSearchAgent", "CodeExecutionAgent", "DocumentAgent", "APIAgent", "DataAgent"],
            },
            "task": {"type": "string", "description": "The subtask description"},
        },
        "required": ["agent", "task"],
    },
)
def delegate_to(agent: str, task: str) -> str:
    # Import here to avoid circular imports
    from agent_smith.agents.builtins import (
        run_api,
        run_code,
        run_data,
        run_document,
        run_web_search,
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

    result = runner(task)
    if result.success:
        return str(result.output)
    return f"Agent failed: {result.error}"
