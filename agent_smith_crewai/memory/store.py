def window(messages: list, max_messages: int) -> list:
    if not messages:
        return []
    if max_messages <= 0:
        return []
    return messages[-max_messages:]


def last_assistant_text(messages: list) -> str | None:
    for m in reversed(messages):
        if hasattr(m, "role") and m.role == "assistant":
            return m.content
        if isinstance(m, dict) and m.get("role") == "assistant":
            return m.get("content", "")
    return None
