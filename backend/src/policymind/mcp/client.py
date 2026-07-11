import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MCPTool:
    name: str
    description: str = ""
    parameters: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ToolObservation:
    tool_name: str
    result: dict[str, object]
    error: str = ""


class EnterpriseMCPClient:
    """MCP Client：通过工具注册表调用 MCP 工具。"""

    def __init__(self) -> None:
        self._tools: dict[str, object] = {}

    def register_tool(self, name: str, func: object) -> None:
        self._tools[name] = func

    async def list_tools(self) -> list[MCPTool]:
        return [
            MCPTool(
                name="get_employee_profile",
                description="Get employee profile by ID",
            ),
            MCPTool(
                name="get_approval_chain",
                description="Get approval chain for a process",
            ),
            MCPTool(
                name="list_required_materials",
                description="List required materials for a process",
            ),
            MCPTool(
                name="get_policy_version",
                description="Get current effective policy version",
            ),
            MCPTool(
                name="create_review_ticket",
                description="Create a human review ticket (requires approval)",
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> ToolObservation:
        try:
            func = self._tools.get(name)
            if not func:
                return ToolObservation(
                    tool_name=name, result={}, error=f"Tool {name} not found"
                )
            result = func(**arguments)  # type: ignore[operator]
            out = result if isinstance(result, dict) else {"value": result}
            return ToolObservation(tool_name=name, result=out)
        except Exception as e:
            return ToolObservation(tool_name=name, result={}, error=str(e))
