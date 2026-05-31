"""
Core types for Agent Smith.
All domain objects are plain dataclasses — no hidden state, no magic.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Status(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class Message:
    role: Role
    content: str
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    result: Any
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class AgentContext:
    """Carries all state through an agent run — passed explicitly, never mutated in place."""
    messages: list[Message] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_message(self, message: Message) -> "AgentContext":
        return AgentContext(
            messages=[*self.messages, message],
            memory=self.memory,
            metadata=self.metadata,
        )

    def with_memory(self, key: str, value: Any) -> "AgentContext":
        return AgentContext(
            messages=self.messages,
            memory={**self.memory, key: value},
            metadata=self.metadata,
        )


@dataclass
class AgentResult:
    status: Status
    output: Any
    context: AgentContext
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.status == Status.SUCCESS

    @classmethod
    def ok(cls, output: Any, context: AgentContext) -> "AgentResult":
        return cls(status=Status.SUCCESS, output=output, context=context)

    @classmethod
    def fail(cls, error: str, context: AgentContext) -> "AgentResult":
        return cls(status=Status.FAILED, output=None, context=context, error=error)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    fn: Any  # callable — not typed to keep frozen=True simple
