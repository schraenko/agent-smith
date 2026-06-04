from agent_smith_crewai.agents.runner import AgentConfig, run_agent
from agent_smith_crewai.llm import OllamaConfig
from agent_smith_crewai.types import AgentResult


def web_search_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="WebSearchAgent",
        system_prompt=(
            "You are a web research assistant. Use the web_search tool to find "
            "relevant, up-to-date information. Always cite your sources. Be concise and factual."
        ),
        llm=llm or OllamaConfig(),
        tools=["web_search"],
    )


def run_web_search(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, web_search_agent(llm))


def code_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="CodeExecutionAgent",
        system_prompt=(
            "You are an expert software engineer. Write clean, correct Python code. "
            "Use the execute_python tool to run and verify your code. "
            "Always explain what the code does and show the output."
        ),
        llm=llm or OllamaConfig(),
        tools=["execute_python"],
    )


def run_code(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, code_agent(llm))


def document_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="DocumentAgent",
        system_prompt=(
            "You are a document analysis expert. Use the read_file tool to read documents. "
            "Extract key information and answer questions accurately."
        ),
        llm=llm or OllamaConfig(),
        tools=["read_file", "list_files"],
    )


def run_document(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, document_agent(llm))


def api_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="APIAgent",
        system_prompt=(
            "You are an API integration specialist. Use the http_get and http_post tools "
            "to interact with REST APIs. Handle errors gracefully."
        ),
        llm=llm or OllamaConfig(),
        tools=["http_get", "http_post"],
    )


def run_api(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, api_agent(llm))


def data_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="DataAgent",
        system_prompt=(
            "You are a data analyst. Use read_csv, query_data, and describe_data "
            "to analyze structured data. Provide clear insights and statistics."
        ),
        llm=llm or OllamaConfig(),
        tools=["read_csv", "query_data", "describe_data"],
    )


def run_data(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, data_agent(llm))


def orchestrator_agent(llm: OllamaConfig | None = None) -> AgentConfig:
    return AgentConfig(
        name="OrchestratorAgent",
        system_prompt=(
            "You are an orchestrator. Break down complex tasks and delegate subtasks "
            "to specialist agents.\n"
            "Available agents: WebSearchAgent, CodeExecutionAgent, DocumentAgent, APIAgent, DataAgent."
        ),
        llm=llm or OllamaConfig(),
        tools=["web_search", "execute_python", "read_file", "list_files",
               "http_get", "http_post", "read_csv", "query_data", "describe_data"],
        max_iterations=20,
    )


def run_orchestrator(task: str, llm: OllamaConfig | None = None) -> AgentResult:
    return run_agent(task, orchestrator_agent(llm))
