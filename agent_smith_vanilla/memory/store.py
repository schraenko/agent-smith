"""
Memory abstractions.
Two flavors: short-term (conversation window) and long-term (key-value store).
Both are pure functions operating on immutable data.
"""

from dataclasses import dataclass, field
from typing import Any

from agent_smith.types import Message, Role


@dataclass(frozen=True)
class MemoryStore:
    """Immutable key-value store for long-term agent memory."""
    data: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> "MemoryStore":
        return MemoryStore(data={**self.data, key: value})

    def delete(self, key: str) -> "MemoryStore":
        return MemoryStore(data={k: v for k, v in self.data.items() if k != key})

    def keys(self) -> list[str]:
        return list(self.data.keys())


def empty_store() -> MemoryStore:
    return MemoryStore()


def window(messages: list[Message], max_messages: int) -> list[Message]:
    """
    Return a sliding window of the last N messages,
    always preserving any leading system message.
    """
    if not messages:
        return []

    if messages[0].role == Role.SYSTEM:
        system = [messages[0]]
        rest = messages[1:]
        return system + rest[-max(0, max_messages - 1):]

    return messages[-max_messages:]


def summarize_to_memory(
    messages: list[Message],
    store: MemoryStore,
    key: str = "conversation_summary",
) -> MemoryStore:
    """
    Naive summary: store the last assistant message as a memory entry.
    Replace with an LLM-powered summarizer for production use.
    """
    assistant_messages = [m for m in messages if m.role == Role.ASSISTANT]
    if not assistant_messages:
        return store
    return store.set(key, assistant_messages[-1].content)
