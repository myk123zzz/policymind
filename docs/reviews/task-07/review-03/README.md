# Task 7 第 3 次审查报告

审查日期：2026-07-11

审查范围：
- `backend/src/policymind/mcp/{client,server,tools}.py`
- `backend/src/policymind/agents/graph.py`
- `backend/src/policymind/conversations/checkpoint.py`
- `backend/tests/{mcp,agents,conversations}/`

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [审查报告目录规范](/D:/policymind/docs/reviews/README.md:1)
- 上一轮报告：[task-07/review-02](/D:/policymind/docs/reviews/task-07/review-02/README.md:1)

## 结论

这轮我仍然判断 **Task 7 暂不通过**，但已经很接近了。

和上一轮比，主线已经明显成形：

- `stdio` MCP transport 能用了。
- Agent runtime 已经不是纯拓扑说明，而是能实际 `invoke/resume`。
- HITL 中断和恢复也有了最小执行链。

在你“简历项目、不要卡太死”的标准下，我这次只保留 2 个阻塞项，而且都是真会影响演示可信度的点：

1. 审批 token 实际没有从 MCP server 传进写工具，导致“批准后再调写工具”这条 transport 链路并没有真的打通。
2. `resume()` 现在还没有绑定到具体待审批操作和 review 记录，更像是通用状态跳转，不是“批准后把刚才那次写操作真正补执行一次”。

## 已修复

- `StdioMCPClient` 已支持 `approval_token` 参数。
- `run_stdio_server()` 已能把 `ApprovalRequired` 转成结构化错误响应，并标记 `requires_review`。
- `build_policy_graph()` 已经返回可执行 runtime，不再只是节点/边的静态描述。
- `PolicyAgentRuntime.invoke()` / `resume()` 已经跑得起来，相关测试也补上了。

## Findings

### 1. MCP transport 里的审批 token 没有真正传到写工具函数

- 严重性：高
- 位置：
  - [backend/src/policymind/mcp/client.py](/D:/policymind/backend/src/policymind/mcp/client.py:74)
  - [backend/src/policymind/mcp/server.py](/D:/policymind/backend/src/policymind/mcp/server.py:39)
  - [backend/src/policymind/mcp/tools.py](/D:/policymind/backend/src/policymind/mcp/tools.py:57)

这条链现在表面上看是通的，但实际上还差最后一脚：

- client 会把 `approval_token` 放到请求 `params` 里。
- server 取到了 `params`，但调用工具时仍然是 `func(**arguments)`。
- `approval_token` 没有并入 `arguments`，所以 `create_review_ticket()` 根本拿不到它。

这意味着什么：

- “未审批 -> review_required” 这半段是成立的。
- 但“审批后带 token 重试 -> 写工具成功” 这半段，其实还没有通过 MCP transport 真正打通。

这个问题不是风格问题，而是实打实的行为 bug。面试时如果你演示“批准后继续创建 review ticket”，现在这条链会露馅。

改进方向：
- 在 `tools/call` 分支里，把 `approval_token` 正确注入到写工具调用参数。
- 最好补一条 transport 级测试：未带 token 返回 `review_required`，带 token 后真正返回 `status=created`。

### 2. `resume()` 还没有绑定具体 review / 待执行写操作，恢复流程偏“演示态”

- 严重性：高
- 位置：
  - [backend/src/policymind/agents/graph.py](/D:/policymind/backend/src/policymind/agents/graph.py:185)
  - [backend/src/policymind/agents/graph.py](/D:/policymind/backend/src/policymind/agents/graph.py:100)
  - [backend/src/policymind/conversations/checkpoint.py](/D:/policymind/backend/src/policymind/conversations/checkpoint.py:39)
  - [backend/tests/agents/test_graph.py](/D:/policymind/backend/tests/agents/test_graph.py:64)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:773)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:785)

这轮最大的进步是 runtime 确实有 `resume()` 了，但它现在的恢复逻辑还是比较“泛”：

- `approval_node()` 仍然把 `pending_review_id` 写死成 `1`。
- `MemoryCheckpointer.create_review()` 存在，但 runtime 并没有在 interrupt 时真正创建/关联 review。
- `resume()` 没有读取某个 pending review 的 payload、待调用工具、参数摘要。
- 批准后也不是“补执行刚才被拦住的写工具一次”，而是直接改 state，再从 `executor` 继续跑。

也就是说，现在更接近：

- 有中断
- 有恢复
- 但还不是“恢复那次被审批拦下的具体操作”

对 Task 7 来说，这仍然是主链问题，因为文档最看重的就是“写工具 HITL 批准后只执行一次”。

改进方向：
- 在 interrupt 时真实创建 review，并把 tool 名、arguments 摘要、必要的 payload 关联进去。
- `approval_node()` 使用真实 `review_id`，不要写死 `1`。
- `resume()` 根据 review 决策恢复那次待执行操作，而不是只改一份通用 state。
- 补一条测试，证明同一 review 批准后只会把目标写操作执行一次。

## 可先忽略的问题

这轮我不把下面这些当阻塞项：

- 现在还不是严格意义上的 `CompiledStateGraph`。
- 还没切到 PostgreSQL checkpointer。
- `critic`、`planner`、`executor` 里的业务逻辑还是轻量 stub。

这些对“简历项目的最小可演示闭环”影响没前两项大。

## 验证记录

实际执行：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\mcp backend\tests\agents backend\tests\conversations -q`
   - 结果：通过
   - 摘要：`19 passed`

2. `.\backend\.venv\Scripts\python.exe -m ruff check backend\src\policymind\mcp backend\src\policymind\agents backend\src\policymind\conversations backend\tests\mcp backend\tests\agents backend\tests\conversations`
   - 结果：通过

补充说明：

- 当前测试证明：runtime 的中断/恢复雏形能跑，MCP 错误分支也能表达 review_required。
- 当前测试还没有证明：批准 token 通过 transport 后，写工具真的成功执行；也没有证明：resume 会精确恢复那次待审批写操作。

## 是否允许进入下一 Task

我建议 **再补这一轮，不要急着进 Task 8**。

好消息是，这次已经不是“大框架没起来”的问题了，基本就差把 HITL 写操作闭环钉牢。把这两处修完，Task 7 很有机会过。
