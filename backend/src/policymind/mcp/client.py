import asyncio
import json
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


class StdioMCPClient:
    """通过 stdio transport 与独立 MCP server 进程通信。"""

    def __init__(self, server_command: list[str]) -> None:
        self._cmd = server_command
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0

    async def connect(self) -> None:
        self._process = await asyncio.create_subprocess_exec(
            *self._cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def disconnect(self) -> None:
        if self._process and self._process.stdin:
            self._process.stdin.close()
            await self._process.wait()
            self._process = None

    async def _send_request(
        self, method: str, params: dict[str, object] | None = None
    ) -> dict[str, object]:
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise RuntimeError("MCP client not connected")

        self._request_id += 1
        req = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params or {}}
        line = json.dumps(req) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

        resp_line = await self._process.stdout.readline()
        return json.loads(resp_line.decode())  # type: ignore[no-any-return]

    async def list_tools(self) -> list[MCPTool]:
        resp = await self._send_request("tools/list")
        result = resp.get("result", {})
        if not isinstance(result, dict):
            return []
        tools_data = result.get("tools", [])
        result_list: list[MCPTool] = []
        for t in tools_data:
            if isinstance(t, dict):
                result_list.append(
                    MCPTool(name=str(t.get("name", "")), description=str(t.get("description", "")))
                )
        return result_list

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
        approval_token: str | None = None,
    ) -> ToolObservation:
        params: dict[str, object] = {"name": name, "arguments": arguments}
        if approval_token:
            params["approval_token"] = approval_token

        try:
            resp = await self._send_request("tools/call", params)
            if "error" in resp:
                err = resp["error"]
                err_data = err.get("data", {}) if isinstance(err, dict) else {}
                requires_review = isinstance(err_data, dict) and err_data.get("requires_review")
                err_msg = str(err.get("message", "")) if isinstance(err, dict) else str(err)
                if requires_review:
                    return ToolObservation(
                        tool_name=name,
                        result={"status": "review_required"},
                        error=err_msg,
                    )
                return ToolObservation(tool_name=name, result={}, error=err_msg)
            result = resp.get("result", {})
            if not isinstance(result, dict):
                return ToolObservation(tool_name=name, result={}, error="invalid result")
            content_list = result.get("content", [])
            if isinstance(content_list, list) and content_list:
                first = content_list[0]
                if isinstance(first, dict):
                    text = first.get("text", "{}")
                    return ToolObservation(tool_name=name, result=json.loads(str(text)))
            return ToolObservation(tool_name=name, result={})
        except Exception as e:
            return ToolObservation(tool_name=name, result={}, error=str(e))
        except Exception as e:
            return ToolObservation(tool_name=name, result={}, error=str(e))
