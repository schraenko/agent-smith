"""
Ollama LLM backend.
Pure functions — take config + messages, return a string or tool calls.
"""

from dataclasses import dataclass, field
from typing import Any
import json
import logging
import httpx

from agent_smith.types import Message, Role, Tool, ToolCall

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OllamaConfig:
    model: str = "phi4:latest"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    options: dict[str, Any] = field(default_factory=dict)


def _messages_to_ollama(messages: list[Message]) -> list[dict]:
    result = []
    for m in messages:
        if m.role == Role.TOOL:
            result.append({"role": "tool", "content": str(m.content)})
        else:
            result.append({"role": m.role.value, "content": m.content})
    return result


def _tools_to_ollama(tools: list[Tool]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


def complete(
    messages: list[Message],
    config: OllamaConfig,
    tools: list[Tool] | None = None,
    system: str | None = None,
) -> tuple[str, list[ToolCall]]:
    """
    Call Ollama and return (text_response, tool_calls).
    One or the other will be empty depending on the model response.
    """
    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(_messages_to_ollama(messages))

    payload: dict[str, Any] = {
        "model": config.model,
        "messages": all_messages,
        "stream": False,
        "options": {
            "temperature": config.temperature,
            "num_predict": config.max_tokens,
            **config.options,
        },
    }

    if tools:
        payload["tools"] = _tools_to_ollama(tools)

    logger.debug("Ollama request: model=%s messages=%d", config.model, len(all_messages))

    with httpx.Client(timeout=config.timeout) as client:
        response = client.post(f"{config.base_url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

    message = data.get("message", {})
    text = message.get("content", "")
    raw_tool_calls = message.get("tool_calls", [])

    tool_calls = [
        ToolCall(
            id=str(i),
            name=tc["function"]["name"],
            arguments=tc["function"].get("arguments", {}),
        )
        for i, tc in enumerate(raw_tool_calls)
    ]

    logger.debug("Ollama response: text_len=%d tool_calls=%d", len(text), len(tool_calls))
    return text, tool_calls


def list_models(base_url: str = "http://localhost:11434") -> list[str]:
    """Return available model names from the local Ollama instance."""
    with httpx.Client(timeout=10) as client:
        response = client.get(f"{base_url}/api/tags")
        response.raise_for_status()
        return [m["name"] for m in response.json().get("models", [])]
