"""
Memory utilities.
Thin functional wrappers around LangChain message history.
"""

from langchain_core.messages import BaseMessage, SystemMessage


def window(messages: list[BaseMessage], max_messages: int) -> list[BaseMessage]:
    """
    Sliding window over a message list.
    Always preserves a leading SystemMessage if present.
    """
    if not messages:
        return []
    if isinstance(messages[0], SystemMessage):
        return [messages[0]] + messages[1:][-max(0, max_messages - 1):]
    return messages[-max_messages:]


def last_assistant_text(messages: list[BaseMessage]) -> str | None:
    """Return the text content of the last AIMessage, or None."""
    from langchain_core.messages import AIMessage
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            return m.content
    return None
