"""
Built-in agents.
Each agent is a pre-configured AgentConfig + a convenience run_* function.
"""

from agent_smith_lc.agents.runner import AgentConfig, run_agent
from agent_smith_lc.llm import OllamaConfig
from agent_smith_lc.rules import load_rule
from agent_smith_lc.types import AgentResult


def _agent_from_rule(name: str, llm: OllamaConfig | None = None) -> AgentConfig:
    cfg = load_rule(name)
    return AgentConfig(
        name=cfg["name"],
        system_prompt=cfg["system_prompt"],
        llm=llm or OllamaConfig(),
        tools=cfg["tools"],
        max_iterations=cfg.get("max_iterations", 10),
        context_window=cfg.get("context_window", 20),
    )


# ─── Web Search Agent ─────────────────────────────────────────────────────────

def web_search_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return _agent_from_rule("web_search", llm)

def run_web_search(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, web_search_agent(llm))


# ─── Code Execution Agent ─────────────────────────────────────────────────────

def code_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return _agent_from_rule("code", llm)

def run_code(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, code_agent(llm))


# ─── Document Agent ───────────────────────────────────────────────────────────

def document_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return _agent_from_rule("document", llm)

def run_document(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, document_agent(llm))


# ─── API Agent ────────────────────────────────────────────────────────────────

def api_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return _agent_from_rule("api", llm)

def run_api(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, api_agent(llm))


# ─── Data Agent ───────────────────────────────────────────────────────────────

def data_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return _agent_from_rule("data", llm)

def run_data(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, data_agent(llm))


# ─── Orchestrator Agent ───────────────────────────────────────────────────────

def orchestrator_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return _agent_from_rule("orchestrator", llm)

def run_orchestrator(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, orchestrator_agent(llm))
