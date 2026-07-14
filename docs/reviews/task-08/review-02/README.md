# Task 8 第 2 次审查报告

审查日期：2026-07-14

审查范围：
- `backend/src/policymind/main.py`
- `backend/src/policymind/api/v1/{chat,reviews,graph}.py`
- `backend/src/policymind/documents/router.py`
- `backend/tests/api/test_security.py`
- `backend/tests/documents/test_router.py`

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- 上一轮报告：[task-08/review-01](/D:/policymind/docs/reviews/task-08/review-01/README.md:1)

## 结论

这轮我判断 **Task 8 可以收口，并允许进入 Task 9**。

按简历项目的验收口径，上一轮卡住演示闭环的主要问题已经补齐：

1. Chat API 和 Review API 已经共享 `app.state.agent_runtime`。
2. `/chat/stream -> /reviews -> /chat/{thread_id}/resume` 这条 HITL API 主线可以跑通。
3. Review API 不再固定返回空列表，可以读取共享 checkpointer 里的 pending review。
4. Graph API 不再固定返回空 nodes/Unknown，占用共享 `graph_repo`，有数据时能返回真实节点和边。

剩下的安全测试深度、限流、Prompt Injection 等问题仍建议后续补，但不再阻塞 Task 8 以简历项目标准收尾。

## 已关闭的问题

### 1. Chat resume 与 stream 不共享状态

上一轮阻塞项已关闭。

当前实现：

- [main.py](/D:/policymind/backend/src/policymind/main.py:36) 初始化 `app.state.agent_runtime = PolicyAgentRuntime()`。
- [chat.py](/D:/policymind/backend/src/policymind/api/v1/chat.py:25) 通过 `_get_runtime()` 从 `app.state` 获取共享 runtime。
- [chat.py](/D:/policymind/backend/src/policymind/api/v1/chat.py:41) 的 stream 和 [chat.py](/D:/policymind/backend/src/policymind/api/v1/chat.py:91) 的 resume 使用同一个 runtime 来源。

实测 API 链路：

- `POST /api/v1/chat/stream` 对审批类请求返回 `review_required`。
- `GET /api/v1/reviews` 能看到同一个 thread 的 pending review。
- `POST /api/v1/chat/{thread_id}/resume` 能返回 completed，并且 `draft_answer` 包含 `ticket-... created`。

### 2. Review API 没有读取真实 review 状态

上一轮阻塞项已关闭到 demo 可用标准。

当前实现：

- [reviews.py](/D:/policymind/backend/src/policymind/api/v1/reviews.py:16) 从 `app.state.agent_runtime` 获取共享 runtime。
- [reviews.py](/D:/policymind/backend/src/policymind/api/v1/reviews.py:20) 遍历共享 checkpointer 的 pending review。
- [reviews.py](/D:/policymind/backend/src/policymind/api/v1/reviews.py:42) 可以按 review id 读取状态。
- approve/reject 写回同一个 checkpointer。

这还不是生产级 repository/API 设计，但对“审核列表能展示刚刚触发的 HITL 任务”已经足够。

### 3. Graph API 仍是占位返回

上一轮阻塞项已关闭到 demo 可用标准。

当前实现：

- [main.py](/D:/policymind/backend/src/policymind/main.py:38) 初始化共享 `MemoryGraphRepository`。
- [graph.py](/D:/policymind/backend/src/policymind/api/v1/graph.py:15) 从 `app.state.graph_repo` 获取 repo。
- [graph.py](/D:/policymind/backend/src/policymind/api/v1/graph.py:21) 调用 `repo.search_paths()` 返回真实节点和边。
- [graph.py](/D:/policymind/backend/src/policymind/api/v1/graph.py:51) 可以从 repo 读取实体。

手动探针中预置 `p1 -> d1` 后，`/graph/subgraph?seed_ids=p1` 能返回 `Policy`、`Department` 和 `OWNED_BY` 边。

## 保留但不阻塞的问题

### 1. 安全测试还偏薄

- 位置：
  - [backend/tests/api/test_security.py](/D:/policymind/backend/tests/api/test_security.py:29)
  - [backend/tests/api/test_security.py](/D:/policymind/backend/tests/api/test_security.py:32)
  - [backend/tests/documents/test_router.py](/D:/policymind/backend/tests/documents/test_router.py:38)

当前仍然存在：

- 跨租户 API 测试还是空 `pass`。
- 无效上传测试还是 `pytest.raises(ValueError)`，不是断言 API 返回 4xx。
- Prompt Injection 和限流还没有 API 级测试。

这些对生产级安全不够，但考虑到当前是简历项目，并且匿名访问、JWT、租户过滤、上传校验的底层模块已有覆盖，这轮不继续卡 Task 8。

建议在 Task 9 或 Task 10 前顺手补：

- 一个跨租户文档列表/API 访问测试。
- 一个伪造 MIME 上传返回 4xx 的测试。
- 一个轻量 prompt injection 标记/拒绝测试。
- 一个内存限流测试。

### 2. Review API 仍直接访问内存 checkpointer 私有字段

当前 `reviews.py` 直接读取 `runtime._checkpointer._reviews`。这对 demo 可以接受，但后续最好给 `MemoryCheckpointer` 补 `list_reviews()` / `get_review()` 方法，避免 API 层依赖内部结构。

### 3. Evaluation API 仍未暴露

Task 8 实施计划里列了 `evaluations` 路由，但从整体任务分工看，评测核心在 Task 10。这里不阻塞 Task 8。

## 验证记录

实际执行：

1. `$env:TEMP='D:\policymind\.tmp_pytest'; $env:TMP='D:\policymind\.tmp_pytest'; .\backend\.venv\Scripts\python.exe -m pytest backend\tests\api backend\tests\documents\test_router.py backend\tests\test_smoke.py -q`
   - 结果：通过
   - 摘要：`14 passed`

2. `.\backend\.venv\Scripts\python.exe -m ruff check backend\src\policymind\api backend\src\policymind\documents\router.py backend\src\policymind\main.py backend\tests\api backend\tests\documents\test_router.py`
   - 结果：通过
   - 摘要：`All checks passed!`

补充 API 探针：

- `POST /api/v1/chat/stream`
  - 结果：`200 OK`
  - 事件包含：`routing`、`review_required`、`done`
- `GET /api/v1/reviews`
  - 结果：`200 OK`
  - 返回 pending review，包含 `thread_id=api-thread-1`
- `POST /api/v1/chat/api-thread-1/resume`
  - 结果：`200 OK`
  - 返回 `status=completed`
  - `draft_answer` 包含 `Write op executed` 和 `ticket-...`
- 预置图谱数据后访问 `/api/v1/graph/subgraph?seed_ids=p1`
  - 结果：`200 OK`
  - 返回真实 nodes 和 `OWNED_BY` edge

## 是否允许进入下一 Task

**允许进入 Task 9。**

Task 8 的主要 API 演示闭环已经成立：登录保护、文档接口、Chat SSE、HITL review 列表、resume 恢复、Graph API 都有可运行入口。剩余安全测试深度可以作为后续增强项继续补。
