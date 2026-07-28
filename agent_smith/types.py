"""
Core types for Agent Smith (LangChain edition).
Plain dataclasses — no LangChain types leak into the domain model.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent_smith.audit import AuditTrail


class Status(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class AgentResult:
    status: Status
    output: Any
    error: str | None = None
    intermediate_steps: list = field(default_factory=list)
    audit_trail: AuditTrail = field(default_factory=AuditTrail)

    @property
    def success(self) -> bool:
        return self.status == Status.SUCCESS

    @classmethod
    def ok(cls, output: Any, steps: list | None = None, audit_trail: AuditTrail | None = None) -> "AgentResult":
        return cls(status=Status.SUCCESS, output=output, intermediate_steps=steps or [], audit_trail=audit_trail or AuditTrail())

    @classmethod
    def fail(cls, error: str, audit_trail: AuditTrail | None = None) -> "AgentResult":
        return cls(status=Status.FAILED, output=None, error=error, audit_trail=audit_trail or AuditTrail())
