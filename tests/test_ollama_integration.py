"""
Integration test — makes a real HTTP call to Ollama.
Requires a running Ollama instance with phi4:latest pulled.

Run with:
    python -m pytest tests/test_ollama_integration.py -v -s
"""

import pytest

from agent_smith.llm.ollama import OllamaConfig, complete
from agent_smith.types import Message, Role


@pytest.fixture
def config():
    return OllamaConfig(model="phi4:latest", temperature=0.0)


def test_ollama_simple_completion(config):
    """Ollama responds with a non-empty string."""
    messages = [Message(role=Role.USER, content="Reply with the single word: pong")]

    text, tool_calls = complete(messages=messages, config=config)

    assert isinstance(text, str)
    assert len(text.strip()) > 0
    assert tool_calls == []
    print(f"\nModel response: {text.strip()}")


def test_ollama_system_prompt(config):
    """System prompt is respected."""
    messages = [Message(role=Role.USER, content="What are you?")]

    text, tool_calls = complete(
        messages=messages,
        config=config,
        system="You are a calculator. You only respond with numbers, nothing else.",
    )

    assert isinstance(text, str)
    assert len(text.strip()) > 0
    print(f"\nModel response: {text.strip()}")


def test_ollama_multi_turn(config):
    """Multi-turn conversation works correctly."""
    messages = [
        Message(role=Role.USER, content="My name is Ada."),
        Message(role=Role.ASSISTANT, content="Nice to meet you, Ada!"),
        Message(role=Role.USER, content="What is my name?"),
    ]

    text, _ = complete(messages=messages, config=config)

    assert "Ada" in text
    print(f"\nModel response: {text.strip()}")