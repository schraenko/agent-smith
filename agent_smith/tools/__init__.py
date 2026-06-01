from agent_smith.tools.builtins import ALL_TOOLS, TOOL_MAP, get_tools
from agent_smith.tools.delegate import delegate_to

# Register delegate_to so the orchestrator can find it
ALL_TOOLS.append(delegate_to)
TOOL_MAP["delegate_to"] = delegate_to
