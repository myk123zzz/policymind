# Task 7 第 4 次审查报告

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
- 上一轮报告：[task-07/review-03](/D:/policymind/docs/reviews/task-07/review-03/README.md:1)

## 结论

这轮我仍然判断 **Task 7 暂不通过**，但现在只剩 1 个我认为值得继续拦的核心问题。

好消息是，上轮里更硬的那个 bug 已经修掉了：

- `approval_token` 现在会从 MCP server 注入到工具参数里，`transport` 这条链不再是假通的。

现在真正还差的，是 **HITL 恢复后没有把被拦下的写操作真实补执行**。这会直接影响你演示“审批后继续完成写工具调用”这条主线。

## 已修复

- `StdioMCPClient.call_tool()` 支持传 `approval_token`。
- `run_stdio_server()` 在 `tools/call` 中会把 `approval_token` 注入工具参数。
- `approval_node()` 不再写死 `pending_review_id=1`，已经会创建 `ReviewTask`。
- `resume()` 已经会按 `review_id` 调用 `approve_review()` / `reject_review()`。

## Findings

### 1. HITL 恢复后并没有真实补执行那次被拦下的写操作

- 严重性：高
- 位置：
  - [backend/src/policymind/agents/graph.py](/D:/policymind/backend/src/policymind/agents/graph.py:100)
  - [backend/src/policymind/agents/graph.py](/D:/policymind/backend/src/policymind/agents/graph.py:201)
  - [backend/src/policymind/conversations/checkpoint.py](/D:/policymind/backend/src/policymind/conversations/checkpoint.py:39)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:641)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:785)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:216)

这轮最关键的问题已经从“token 没传到工具”收缩成了“恢复后做了什么”。

当前链路是：

- `approval_node()` 会创建 review，并把 `review_id` 存进状态。
- `resume()` 也会把这条 review 标记为 approved/rejected。

但批准后的实际行为还是偏“演示态”：

- `approval_node()` 保存的 payload 只有 `{"tool_name": "create_review_ticket"}`，没有那次待执行调用的完整参数。
- `resume()` 批准后并没有重新调用 `create_review_ticket()` 或任何 MCP 写工具。
- 它只是修改 `state`，塞一个 `draft_answer`，再从 `executor` 继续跑。
- `executor_node()` 本身也只是 `tool_call_count + 1`，并没有真实工具执行。

所以现在可以说：

- 有 review
- 有 approve/reject
- 有 resume

但还不能说：

- “那次被 HITL 拦下的写操作，在批准后被真正补执行了一次”

对 Task 7 来说，这仍然是主链问题，因为文档把“写工具 HITL 批准后只执行一次”写得非常明确。对简历项目来说，这也是面试里很容易被追问的地方。

改进方向：
- 在 interrupt 时把待执行工具名和参数完整保存进 review payload。
- `resume()` 批准后，基于 payload 真正补执行那次写工具调用。
- 补一条测试，验证批准前不会创建 ticket，批准后会创建且只创建一次。

## 可先忽略的问题

这轮我不把下面这些当阻塞项：

- 现在还不是严格意义上的官方 `LangGraph` 编译对象。
- 还没切到 PostgreSQL checkpointer。
- `executor`、`planner`、`critic` 还是轻量逻辑。
- 还没有完整的 SSE 公开事件链路。

这些对“简历项目的最小可演示闭环”影响都没有上面那一项大。

## 验证记录

实际执行：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\mcp backend\tests\agents backend\tests\conversations -q`
   - 结果：通过
   - 摘要：`19 passed`

2. `.\backend\.venv\Scripts\python.exe -m ruff check backend\src\policymind\mcp backend\src\policymind\agents backend\src\policymind\conversations backend\tests\mcp backend\tests\agents backend\tests\conversations`
   - 结果：通过

补充说明：

- 当前测试证明：transport 传 token、创建 review、invoke/resume 这些局部能力都能跑。
- 当前测试还没有证明：批准后那次具体写操作真的被补执行，而且只执行一次。

## 是否允许进入下一 Task

我建议 **再补这一轮，不要急着进 Task 8**。

现在已经不是“大框架没立住”的阶段了，就差把 HITL 写操作闭环钉死。修完这一处，我会很倾向于放行 Task 7。
