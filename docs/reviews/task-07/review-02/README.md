# Task 7 第 2 次审查报告

审查日期：2026-07-11

审查范围：
- `backend/src/policymind/mcp/{client,server,tools}.py`
- `backend/src/policymind/agents/{state,critic,graph}.py`
- `backend/src/policymind/conversations/checkpoint.py`
- `backend/tests/{mcp,agents,conversations}/`

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [审查报告目录规范](/D:/policymind/docs/reviews/README.md:1)
- 上一轮报告：[task-07/review-01](/D:/policymind/docs/reviews/task-07/review-01/README.md:1)

## 结论

这轮我仍然判断 **Task 7 暂不通过**。

比上一轮好很多：

- 已经有了独立的 `stdio` MCP server/client。
- 已经有了 agent graph 雏形。
- `ApprovalRequired` 也开始进入领域错误层了。

但 Task 7 文档里最关键的“真闭环”还是没完成：

1. 写工具审批没有真正形成可恢复的 HITL 链路。
2. Agent 拓扑仍是元数据描述，不是可执行的 LangGraph 闭环。

## 已修复

- `MCP` 不再只是同进程函数注册表，已经有了 `StdioMCPClient` 和独立 `run_stdio_server()`。
- `create_review_ticket()` 不再接受裸 `approved=True/False`，而是开始要求审批令牌。
- `build_policy_graph()`、`supervisor_node()`、`critic_node()` 等基础节点已经落地。

## Findings

### 1. 写工具审批还没有接成真正可恢复的 `ApprovalRequired -> interrupt -> resume`

- 严重性：高
- 位置：
  - [backend/src/policymind/mcp/tools.py](/D:/policymind/backend/src/policymind/mcp/tools.py:57)
  - [backend/src/policymind/mcp/server.py](/D:/policymind/backend/src/policymind/mcp/server.py:39)
  - [backend/src/policymind/conversations/checkpoint.py](/D:/policymind/backend/src/policymind/conversations/checkpoint.py:39)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:641)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:216)

现在 `create_review_ticket()` 没有审批令牌时会抛 `ApprovalRequired`，这方向是对的；但 server 侧还没把它接成文档要求的 HITL 流程：

- `run_stdio_server()` 只捕获了 `ValueError`
- `ApprovalRequired` 不会被这个分支接住
- `MCPClient.call_tool()` 也没有审批令牌通道

结果就是：写工具一旦没批，现状更像是异常冒泡，而不是“进入 interrupt，保存 review，再 resume”。

改进方向：
- 在 server 边界把 `ApprovalRequired` 转成结构化 review 事件。
- client/tool 调用要支持 approval token 或 pending review 分支。
- 把 review 持久化和 resume 路径真正串起来，不要只停留在内存 dict。

### 2. Agent graph 还是“拓扑说明”，不是可执行的 LangGraph 闭环

- 严重性：高
- 位置：
  - [backend/src/policymind/agents/graph.py](/D:/policymind/backend/src/policymind/agents/graph.py:158)
  - [backend/src/policymind/agents/graph.py](/D:/policymind/backend/src/policymind/agents/graph.py:112)
  - [backend/src/policymind/agents/graph.py](/D:/policymind/backend/src/policymind/agents/graph.py:151)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:699)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:758)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:218)

`build_policy_graph()` 目前返回的是一个普通 `dict`，里面放了节点名和 edge 回调；它还不是文档要求的 `CompiledStateGraph`，也没有真正的 `Command(resume=...)` 恢复入口。

更关键的是，`approval_node()` 和 `route_after_approval()` 现在只是“等一个 pending id / 返回 executor or end”的 stub：

- `approval_node()` 直接把 `pending_review_id` 写死成 `1`
- `route_after_approval()` 也没有和 checkpointer 的 approve/reject 结果联动
- 没有 `resume` 的真实接入点，审批完成后也无法证明会回到正确节点

这意味着现在虽然有了“图的形状”，但还没有 Task 7 要求的那条真正能跑的多 agent 闭环。

改进方向：
- 把 `build_policy_graph()` 真正做成可执行图。
- 补 `resume(thread_id, decision)` 的入口。
- 让 approval 节点和 checkpointer 的 review 状态联动，而不是写死 `pending_review_id = 1`。

## 可先忽略的问题

这轮我不把下面这些当阻塞项：

- `AgentState` 还没完全补齐文档里的全部字段。
- `critic` 规则还比较朴素。
- MCP 工具数据目前仍偏 demo 化。

这些都可以后面慢慢补，但前提还是先把 HITL 和图执行闭环立住。

## 验证记录

实际执行：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\mcp backend\tests\agents backend\tests\conversations -q`
   - 结果：通过
   - 摘要：`18 passed`

2. `.\backend\.venv\Scripts\python.exe -m ruff check backend\src\policymind\mcp backend\src\policymind\agents backend\src\policymind\conversations backend\tests\mcp backend\tests\agents backend\tests\conversations`
   - 结果：通过

补充说明：

- 当前测试证明：MCP server/client helper、agent 节点 helper、checkpoint helper 能运行。
- 当前测试不能证明：审批中断恢复、LangGraph 真实执行图、resume 后继续执行的闭环已经完成。

## 是否允许进入下一 Task

我建议 **先不要进入 Task 8**。

Task 8 是完整 API 出口；如果 Task 7 这条主链还没真正闭环，继续往上搭接口很容易变成“壳子先有了，里面还是断的”。先把审批恢复和图执行补实，再往下推进会更稳。
