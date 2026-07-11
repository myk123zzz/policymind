# Task 7 第 1 次审查报告

审查日期：2026-07-11

审查范围：
- `backend/src/policymind/mcp/{client,tools}.py`
- `backend/src/policymind/agents/{state,critic}.py`
- `backend/src/policymind/conversations/checkpoint.py`
- `backend/tests/{mcp,agents,conversations}/`

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [审查报告目录规范](/D:/policymind/docs/reviews/README.md:1)

## 结论

这轮我判断 **Task 7 暂不通过**。

原因不是小问题，而是 Task 7 文档要求的三件核心事目前都还没有真正闭环：

1. 现在不是“真实 MCP Transport”，而是同进程工具注册表调用。
2. 现在没有 LangGraph 多 agent 拓扑，也没有 resume 闭环。
3. 写工具审批和 HITL 仍然只是普通布尔参数/内存保存，不是文档要求的 `ApprovalRequired -> interrupt -> resume` 流程。

换句话说，现在代码更像是 **Task 7 的若干前置 helper**，还不能算“多 Agent + MCP + HITL 已完成”。

## 做得不错的部分

- 已经有 MCP 工具雏形，五个工具名基本对上文档要求。
- `critic`、`AgentState`、`MemoryCheckpointer` 都起了最小骨架。
- 当前相关测试与 lint 全部通过，说明这些基础模块不是空壳。

## Findings

### 1. MCP Client 仍然是同进程函数调用，不是真实 MCP Transport

- 严重性：高
- 位置：
  - [backend/src/policymind/mcp/client.py](/D:/policymind/backend/src/policymind/mcp/client.py:21)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:625)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:216)

当前 `EnterpriseMCPClient` 的本质是：

- `register_tool()` 把函数塞进 `_tools`
- `call_tool()` 直接 `func(**arguments)`

这正好踩中了开发手册里明确禁止的那种“直接 import/同进程调用工具函数”，和“真实 MCP Transport”不是一回事。对简历项目来说，这个差异是实质性的，因为你后面如果说“实现了 MCP 工具调用”，面试里一追问 transport/鉴权/隔离，就会露出层次差。

改进方向：
- 至少补出真正的 server/client 边界，不要让 client 直接执行本地 Python 函数。
- `list_tools()` 和 `call_tool()` 应来自 transport 层，而不是硬编码工具清单。
- 最低限度也要做到“client 调 server”，哪怕先是本机进程间 transport。

### 2. 写工具审批没有走 `ApprovalRequired -> interrupt -> resume` 主链

- 严重性：高
- 位置：
  - [backend/src/policymind/mcp/tools.py](/D:/policymind/backend/src/policymind/mcp/tools.py:57)
  - [backend/src/policymind/mcp/client.py](/D:/policymind/backend/src/policymind/mcp/client.py:54)
  - [backend/src/policymind/conversations/checkpoint.py](/D:/policymind/backend/src/policymind/conversations/checkpoint.py:30)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:641)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:216)

`create_review_ticket()` 现在只是通过 `approved: bool` 决定是否抛 `ValueError`。这和文档要求的行为差很多：

- 没有 `ApprovalRequired`
- 没有 approval token
- 没有绑定 `thread/tool/arguments hash`
- 没有 idempotency key
- 没有真正从 agent 图里 `interrupt`
- 没有恢复后“只执行一次”的保证

`interrupt_for_review()` 也只是把状态存进内存，并返回一个 dict；它还不是 LangGraph 的中断恢复契约。

这条是 Task 7 最核心的演示点之一，所以我会继续把它当阻塞项。

改进方向：
- 写工具未获批时，抛出领域错误 `ApprovalRequired`，不要用普通 `ValueError`。
- Agent 执行写工具时走 `interrupt(...)` 语义，而不是在工具函数里塞一个 `approved=True/False` 参数。
- 恢复时用同一 `thread_id` 和明确的 resume 命令，保证审批后只执行一次。

### 3. LangGraph 多 agent 主体和固定拓扑还没有落地

- 严重性：高
- 位置：
  - [backend/src/policymind/agents/state.py](/D:/policymind/backend/src/policymind/agents/state.py:4)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:684)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:699)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:218)

目前 `agents/` 下只有：

- `state.py`
- `critic.py`

还没有文档要求的：

- `supervisor / planner / executor / synthesizer / graph / retrieval / approval`
- `build_policy_graph()`
- 固定拓扑与节点跳转

这意味着现在还不能称为“多 agent 执行完整计划”，最多只能说已经起了 agent 状态和 critic 雏形。

改进方向：
- 先把最小可运行拓扑搭起来，哪怕每个节点先用轻量 stub。
- 至少跑通一条：`supervisor -> retrieval/graph/planner -> synthesizer -> critic -> END|interrupt`
- 把 `critic` 的输出接入图，而不是停留在独立 helper。

### 4. Checkpointer 与会话恢复仍然不是文档要求的持久化恢复模型

- 严重性：中
- 位置：
  - [backend/src/policymind/conversations/checkpoint.py](/D:/policymind/backend/src/policymind/conversations/checkpoint.py:8)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:758)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:229)

当前只有 `MemoryCheckpointer`，没有 PostgreSQL checkpointer，也没有 `resume` 服务链路。对 Task 7 来说，这还不是小差异，因为文档把“同一 thread_id 恢复”写成了明确要求。

不过我把它排在前三项后面，因为它更像“闭环缺后半截”，不是最开始就能独立成立的 blocker。

改进方向：
- 先定义 conversations 层的 thread/review 持久化模型。
- 提供最小的 `resume(thread_id, decision)` 调用面。
- 再把 checkpointer 从内存换成 PostgreSQL 适配器。

## 可先忽略的问题

这轮我不把下面这些当阻塞项：

- `AgentState` 还没完全补齐文档里的全部字段。
- `critic` 规则目前比较朴素。
- MCP 工具数据先用 demo 数据，而不是完整 repository。

这些都能后面继续补，但前提是 Task 7 的主闭环得先站起来。

## 验证记录

实际执行：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\mcp backend\tests\agents backend\tests\conversations -q`
   - 结果：通过
   - 摘要：`10 passed`

2. `.\backend\.venv\Scripts\python.exe -m ruff check backend\src\policymind\mcp backend\src\policymind\agents backend\src\policymind\conversations backend\tests\mcp backend\tests\agents backend\tests\conversations`
   - 结果：通过

补充说明：

- 当前测试证明：MCP 工具 helper、critic helper、内存 checkpoint helper 可以运行。
- 当前测试不能证明：真实 MCP transport、LangGraph 拓扑、审批中断恢复、SSE 公开事件链路已经实现。

## 是否允许进入下一 Task

我建议 **先不要进入 Task 8**。

Task 8 是 API 与完整对话出口，如果 Task 7 现在这条主链还没闭环，继续往上包 API 很容易变成“接口先搭起来，里面还是假动作”。先把 Task 7 至少补到一个最小可演示闭环，会顺很多。
