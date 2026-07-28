"""
Audit trail for agent execution.
Tracks all LLM calls, tool calls, and delegations.
"""

import contextvars
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# Context variables for passing audit trail and level through tool calls
_current_audit_trail: contextvars.ContextVar[AuditTrail | None] = contextvars.ContextVar("audit_trail", default=None)
_current_level: contextvars.ContextVar[int] = contextvars.ContextVar("audit_level", default=0)


def set_audit_context(trail: AuditTrail | None, level: int = 0) -> contextvars.Token | None:
    """Set the current audit context. Returns tokens to restore later."""
    t = _current_audit_trail.set(trail)
    l = _current_level.set(level)
    return (t, l)


def reset_audit_context(tokens) -> None:
    """Reset the audit context to previous values."""
    if tokens:
        t, l = tokens
        _current_audit_trail.reset(t)
        _current_level.reset(l)


def get_current_trail() -> AuditTrail | None:
    return _current_audit_trail.get()


def get_current_level() -> int:
    return _current_level.get()


@dataclass
class AuditEntry:
    timestamp: str
    level: int
    agent: str
    action: str  # "llm_call" | "tool_call" | "tool_result" | "delegate" | "delegate_result" | "plan_submitted" | "plan_approved" | "plan_rejected"
    task: str | None = None
    tool_name: str | None = None
    args: dict | None = None
    result: str | None = None
    success: bool = True
    iteration: int | None = None


@dataclass
class AuditTrail:
    entries: list[AuditEntry] = field(default_factory=list)

    def log(self, **kwargs: Any) -> None:
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            **kwargs,
        )
        self.entries.append(entry)
        self._print(entry)

    def _print(self, entry: AuditEntry) -> None:
        indent = "  " * entry.level
        prefix = f"[{entry.level}]"

        if entry.action == "llm_call":
            print(f"{indent}{prefix} LLM Call (iteration {entry.iteration})", file=sys.stderr)
        elif entry.action == "delegate":
            print(f"{indent}{prefix} DELEGATE -> {entry.agent}", file=sys.stderr)
            print(f"{indent}    Task: {entry.task}", file=sys.stderr)
        elif entry.action == "delegate_result":
            status = "OK" if entry.success else "FAILED"
            print(f"{indent}{prefix} RESULT [{status}] from {entry.agent}", file=sys.stderr)
            result_preview = (entry.result or "")[:80]
            print(f"{indent}    Output: {result_preview}...", file=sys.stderr)
        elif entry.action == "tool_call":
            print(f"{indent}{prefix} TOOL: {entry.tool_name}({entry.args})", file=sys.stderr)
        elif entry.action == "tool_result":
            result_preview = (entry.result or "")[:80]
            print(f"{indent}{prefix} RESULT: {result_preview}", file=sys.stderr)
        elif entry.action == "plan_submitted":
            print(f"{indent}{prefix} PLAN SUBMITTED by {entry.agent}", file=sys.stderr)
            if entry.task:
                print(f"{indent}    Plan: {entry.task}", file=sys.stderr)
        elif entry.action == "plan_approved":
            print(f"{indent}{prefix} PLAN APPROVED", file=sys.stderr)
        elif entry.action == "plan_rejected":
            print(f"{indent}{prefix} PLAN REJECTED", file=sys.stderr)
            if entry.task:
                print(f"{indent}    Feedback: {entry.task}", file=sys.stderr)

    def format(self) -> str:
        lines = []
        for i, e in enumerate(self.entries, 1):
            indent = "  " * e.level
            lines.append(f"{indent}[{i}] {e.timestamp} | {e.action.upper()}")
            if e.action == "llm_call":
                lines.append(f"{indent}    Agent: {e.agent}, Iteration: {e.iteration}")
            elif e.action == "delegate":
                lines.append(f"{indent}    Agent: {e.agent}")
                lines.append(f"{indent}    Task: {e.task}")
            elif e.action == "delegate_result":
                status = "OK" if e.success else "FAILED"
                lines.append(f"{indent}    Status: {status}")
                lines.append(f"{indent}    Output: {(e.result or '')[:100]}")
            elif e.action == "tool_call":
                lines.append(f"{indent}    Tool: {e.tool_name}")
                lines.append(f"{indent}    Args: {e.args}")
            elif e.action == "tool_result":
                lines.append(f"{indent}    Result: {(e.result or '')[:100]}")
            elif e.action == "plan_submitted":
                lines.append(f"{indent}    Agent: {e.agent}")
                lines.append(f"{indent}    Plan: {e.task}")
            elif e.action == "plan_approved":
                lines.append(f"{indent}    Plan approved by user")
            elif e.action == "plan_rejected":
                lines.append(f"{indent}    Plan rejected by user")
                lines.append(f"{indent}    Feedback: {e.task or ''}")
            lines.append("")
        return "\n".join(lines)
