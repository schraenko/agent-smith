"""
Integration test — makes a real HTTP call to Ollama.
Requires a running Ollama instance with phi4:latest pulled.

Run with:
    python -m pytest tests/test_ollama_integration.py -v -s
"""

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from agent_smith_lc.llm import OllamaConfig, make_llm


@pytest.fixture
def llm():
    return make_llm(OllamaConfig(model="mistral:latest", temperature=0.0))


def test_simple_completion(llm):
    """LLM responds with a non-empty string."""
    response = llm.invoke([HumanMessage(content="Reply with the single word: pong")])
    assert isinstance(response.content, str)
    assert len(response.content.strip()) > 0
    print(f"\nModel response: {response.content.strip()}")


def test_system_prompt(llm):
    """System prompt is passed and respected."""
    messages = [
        SystemMessage(content="You are a calculator. Only respond with numbers."),
        HumanMessage(content="What is 6 multiplied by 7?"),
    ]
    response = llm.invoke(messages)
    assert "42" in response.content
    print(f"\nModel response: {response.content.strip()}")


def test_multi_turn(llm):
    """Conversation history is preserved across turns."""
    from langchain_core.messages import AIMessage
    messages = [
        HumanMessage(content="My name is Ada."),
        AIMessage(content="Nice to meet you, Ada!"),
        HumanMessage(content="What is my name?"),
    ]
    response = llm.invoke(messages)
    assert "Ada" in response.content
    print(f"\nModel response: {response.content.strip()}")
