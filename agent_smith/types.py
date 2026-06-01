"""
Core types for Agent Smith (LangChain edition).
Plain dataclasses — no LangChain types leak into the domain model.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class AgentResult:
    status: Status
    output: Any
    error: str | None = None
    intermediate_steps: list = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status == Status.SUCCESS

    @classmethod
    def ok(cls, output: Any, steps: list | None = None) -> "AgentResult":
        return cls(status=Status.SUCCESS, output=output, intermediate_steps=steps or [])

    @classmethod
    def fail(cls, error: str) -> "AgentResult":
        return cls(status=Status.FAILED, output=None, error=error)
