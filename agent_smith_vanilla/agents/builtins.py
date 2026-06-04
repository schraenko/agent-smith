"""
Built-in agents.
Each agent is a pre-configured AgentConfig + a convenience run_* function.
"""

from dataclasses import dataclass, field

from agent_smith_vanilla.agents.runner import AgentConfig, run_agent
from agent_smith_vanilla.llm.ollama import OllamaConfig
from agent_smith_vanilla.types import AgentContext, AgentResult


# ─── Web Search Agent ────────────────────────────────────────────────────────

WEB_SEARCH_SYSTEM = """\
You are a web research assistant. Use the web_search tool to find relevant,
up-to-date information. Always cite your sources. Be concise and factual.
"""

def web_search_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="WebSearchAgent",
        system_prompt=WEB_SEARCH_SYSTEM,
        llm=llm or OllamaConfig(),
        tools=["web_search"],
    )

def run_web_search(task: str, llm: OllamaConfig | None = None, context: AgentContext | None = None) -> AgentResult:
    return run_agent(task, web_search_agent(llm), context)


# ─── Code Execution Agent ─────────────────────────────────────────────────────

CODE_SYSTEM = """\
You are an expert software engineer. Write clean, correct Python code to solve
the given task. Use the execute_python tool to run code and verify results.
Always explain what the code does and show the output.
"""

def code_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="CodeExecutionAgent",
        system_prompt=CODE_SYSTEM,
        llm=llm or OllamaConfig(),
        tools=["execute_python"],
    )

def run_code(task: str, llm: OllamaConfig | None = None, context: AgentContext | None = None) -> AgentResult:
    return run_agent(task, code_agent(llm), context)


# ─── Document Agent ───────────────────────────────────────────────────────────

DOCUMENT_SYSTEM = """\
You are a document analysis expert. Use the read_file tool to read documents.
Extract key information, summarize content, and answer questions accurately.
"""

def document_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="DocumentAgent",
        system_prompt=DOCUMENT_SYSTEM,
        llm=llm or OllamaConfig(),
        tools=["read_file", "list_files"],
    )

def run_document(task: str, llm: OllamaConfig | None = None, context: AgentContext | None = None) -> AgentResult:
    return run_agent(task, document_agent(llm), context)


# ─── API Agent ────────────────────────────────────────────────────────────────

API_SYSTEM = """\
You are an API integration specialist. Use the http_get and http_post tools to
interact with REST APIs. Handle errors gracefully and return structured results.
"""

def api_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="APIAgent",
        system_prompt=API_SYSTEM,
        llm=llm or OllamaConfig(),
        tools=["http_get", "http_post"],
    )

def run_api(task: str, llm: OllamaConfig | None = None, context: AgentContext | None = None) -> AgentResult:
    return run_agent(task, api_agent(llm), context)


# ─── Data Agent ───────────────────────────────────────────────────────────────

DATA_SYSTEM = """\
You are a data analyst. Use the read_csv, query_data, and describe_data tools
to analyze structured data. Provide clear insights and statistical summaries.
"""

def data_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="DataAgent",
        system_prompt=DATA_SYSTEM,
        llm=llm or OllamaConfig(),
        tools=["read_csv", "query_data", "describe_data"],
    )

def run_data(task: str, llm: OllamaConfig | None = None, context: AgentContext | None = None) -> AgentResult:
    return run_agent(task, data_agent(llm), context)


# ─── Orchestrator Agent ───────────────────────────────────────────────────────

ORCHESTRATOR_SYSTEM = """\
You are an orchestrator agent. Break down complex tasks into subtasks and
delegate them to the appropriate specialist agents using the delegate_to tool.
Think step by step. Be explicit about your reasoning and delegation decisions.
Available agents: WebSearchAgent, CodeExecutionAgent, DocumentAgent, APIAgent, DataAgent.
"""

def orchestrator_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="OrchestratorAgent",
        system_prompt=ORCHESTRATOR_SYSTEM,
        llm=llm or OllamaConfig(),
        tools=["delegate_to"],
        max_iterations=20,
    )

def run_orchestrator(task: str, llm: OllamaConfig | None = None, context: AgentContext | None = None) -> AgentResult:
    return run_agent(task, orchestrator_agent(llm), context)
