"""MCP Server — 独立进程运行，通过 stdio/HTTP transport 对外暴露工具。"""

import json
import sys
from collections.abc import Callable

from policymind.mcp.tools import (
    create_review_ticket,
    get_approval_chain,
    get_employee_profile,
    get_policy_version,
    list_required_materials,
)

TOOLS: dict[str, Callable[..., dict[str, object]]] = {
    "get_employee_profile": get_employee_profile,
    "get_approval_chain": get_approval_chain,
    "list_required_materials": list_required_materials,
    "get_policy_version": get_policy_version,
    "create_review_ticket": create_review_ticket,
}


def run_stdio_server() -> None:
    """运行 stdio 模式的 MCP server。读取 JSON-RPC 请求，返回 JSON-RPC 响应。"""
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            method = request.get("method", "")
            req_id = request.get("id")

            if method == "tools/list":
                tools_list = [
                    {"name": n, "description": f.__doc__ or ""}
                    for n, f in TOOLS.items()
                ]
                response = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}

            elif method == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name", "")
                arguments = dict(params.get("arguments", {}))
                # 将 approval_token 注入写工具参数
                if "approval_token" in params:
                    arguments["approval_token"] = params["approval_token"]
                func = TOOLS.get(tool_name)
                if func:
                    try:
                        result = func(**arguments)
                        response = {
                            "jsonrpc": "2.0", "id": req_id,
                            "result": {"content": [{"type": "text", "text": json.dumps(result)}]},
                        }
                    except Exception as e:
                        code = -32001 if "Approval" in type(e).__name__ else -1
                        response = {
                            "jsonrpc": "2.0", "id": req_id,
                            "error": {
                                "code": code,
                                "message": str(e),
                                "data": {
                                    "type": type(e).__name__,
                                    "requires_review": code == -32001,
                                },
                            },
                        }
                else:
                    response = {
                        "jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                    }
            else:
                response = {
                    "jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown method: {method}"},
                }

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            continue
