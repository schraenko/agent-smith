from agent_smith.tools.builtins import ALL_TOOLS, TOOL_MAP, get_tools
from agent_smith.tools.submit_plan import submit_plan
from agent_smith.tools.security import (
    audit_dependencies,
    bandit_scan,
    secret_scan,
    security_scan,
)

for _t in (bandit_scan, secret_scan, audit_dependencies, security_scan):
    ALL_TOOLS.append(_t)
    TOOL_MAP[_t.name] = _t

ALL_TOOLS.append(submit_plan)
TOOL_MAP["submit_plan"] = submit_plan
