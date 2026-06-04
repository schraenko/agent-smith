from dataclasses import dataclass, field


@dataclass(frozen=True)
class OllamaConfig:
    model: str = "phi4:latest"
