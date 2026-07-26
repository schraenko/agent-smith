"""
LLM factory.
Pure functions — take config, return a LangChain chat model.
LangChain types are isolated here and don't leak into the rest of the codebase.
"""

from dataclasses import dataclass, field
from typing import Any

from langchain_ollama import ChatOllama


@dataclass(frozen=True)
class OllamaConfig:
    model: str = "phi4:latest"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    options: dict[str, Any] = field(default_factory=dict)


def make_llm(config: OllamaConfig) -> ChatOllama:
    """Return a ChatOllama instance for the given config."""
    return ChatOllama(
        model=config.model,
        base_url=config.base_url,
        temperature=config.temperature,
        num_predict=config.max_tokens,
        timeout=config.timeout,
        **config.options,
    )


def make_llm_with_tools(config: OllamaConfig, tools: list) -> ChatOllama:
    """Return a ChatOllama instance with tools bound."""
    return make_llm(config).bind_tools(tools)
