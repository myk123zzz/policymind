# Task 8 第 1 次审查报告

审查日期：2026-07-14

审查范围：
- `backend/src/policymind/main.py`
- `backend/src/policymind/api/v1/{chat,reviews,graph}.py`
- `backend/src/policymind/auth/router.py`
- `backend/src/policymind/documents/router.py`
- `backend/tests/api/test_security.py`
- `backend/tests/documents/test_router.py`

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- 上一轮阶段报告：[task-07/review-05](/D:/policymind/docs/reviews/task-07/review-05/README.md:1)

## 结论

这轮我判断 **Task 8 暂不通过**。

按简历项目口径看，Task 8 不需要一次性补成完整生产级 API，但现在还差几个会影响演示可信度的主入口：

1. Chat 的 `stream` 和 `resume` 没有共享同一个 Agent runtime/checkpointer，HITL 恢复 API 很容易找不到刚才中断的 thread。
2. Review API 现在返回的是空列表或临时状态，不是真正读取/驱动同一批 review task。
3. Graph API 还是空节点/占位实体，不能证明 API 层把 GraphRAG 结果暴露出来。
4. Task 8 要求的安全测试大多还没落到 API 行为上，尤其跨租户、超大文件、伪造 MIME、Prompt Injection 和限流。

所以当前更像是 **Task 8 的路由骨架已经开始搭建**，但还不能说“FastAPI 完整接口与安全”已经完成。

## 做得不错的部分

- `main.py` 已经挂载了 auth、documents、chat、reviews、graph 路由。
- `/health/live` 和 `/health/ready` 已经存在，`ready` 会检查数据库连接。
- 文档上传、列表、job 查询已有基本路由，并且文档路由使用 `tenant_id` 过滤。
- Chat SSE 只发送公开事件类型，没有直接转发隐藏推理 token。
- 当前 Task 8 相关测试在工作区临时目录下可以通过。

## Findings

### 1. Chat resume 与 stream 不共享状态，HITL API 闭环不成立

- 严重性：高
- 位置：
  - [backend/src/policymind/api/v1/chat.py](/D:/policymind/backend/src/policymind/api/v1/chat.py:52)
  - [backend/src/policymind/api/v1/chat.py](/D:/policymind/backend/src/policymind/api/v1/chat.py:116)
  - [backend/src/policymind/api/v1/chat.py](/D:/policymind/backend/src/policymind/api/v1/chat.py:124)

`chat_stream()` 内部每次请求都会 `build_policy_graph()`，`chat_resume()` 也重新 `build_policy_graph()`。这意味着 stream 中断时保存的状态和 resume 请求使用的状态不是同一个 checkpointer。

表现上会变成：

- `/chat/stream` 可以发出 `review_required`
- 但 `/chat/{thread_id}/resume` 很可能拿不到同一个 thread 的 checkpoint
- 前端演示“审批后恢复同一轮对话”时会断

改进方向：
- 把 runtime/checkpointer 放到 `app.state` 或依赖容器中，保证同一应用进程内共享。
- `chat_stream` 和 `chat_resume` 使用同一个 runtime 实例或同一个持久化 checkpointer。
- 补 API 级测试：stream 触发 review 后，用返回的 `thread_id` resume，结果必须完成并包含写工具执行结果。

### 2. Review API 没有读取真实 review 状态

- 严重性：高
- 位置：
  - [backend/src/policymind/api/v1/reviews.py](/D:/policymind/backend/src/policymind/api/v1/reviews.py:15)
  - [backend/src/policymind/api/v1/reviews.py](/D:/policymind/backend/src/policymind/api/v1/reviews.py:21)
  - [backend/src/policymind/api/v1/reviews.py](/D:/policymind/backend/src/policymind/api/v1/reviews.py:41)
  - [backend/src/policymind/api/v1/reviews.py](/D:/policymind/backend/src/policymind/api/v1/reviews.py:55)

当前 Review API 还是演示态：

- `list_reviews()` 固定返回 `[]`
- `get_review()` 固定返回一个 pending dict
- approve/reject 又新建一个 runtime，再操作它自己的内存 checkpointer

这和 Task 7 刚收口的 HITL 主链没有接上。对简历项目来说，这条要补，因为前端/面试演示通常会点“审核列表 -> 批准 -> 对话继续”。

改进方向：
- Review API 使用和 Chat API 同一个 checkpointer。
- `list_reviews()` 返回真实 pending review。
- approve/reject 后能驱动对应 thread resume，或至少把 review 状态写回同一个 store。

### 3. Graph API 仍是占位返回，不能展示 GraphRAG API 成果

- 严重性：中
- 位置：
  - [backend/src/policymind/api/v1/graph.py](/D:/policymind/backend/src/policymind/api/v1/graph.py:15)
  - [backend/src/policymind/api/v1/graph.py](/D:/policymind/backend/src/policymind/api/v1/graph.py:24)

`/graph/subgraph` 固定返回空 nodes/edges，`/graph/entities/{entity_id}` 返回 `Unknown`。这对“完整 API”来说不够，但按简历项目口径，它不必马上接 Neo4j，只要能返回 Task 6 已有 GraphRAG service 的真实 demo 数据或内存结果即可。

改进方向：
- 最小可接受：接入已有 graph search/repository 的内存实现，返回真实节点、边、来源和租户字段。
- 补一条 API 测试：当前租户只能看到自己的 graph entity/path。

### 4. Task 8 安全测试覆盖不足，部分测试不是 API 行为

- 严重性：中
- 位置：
  - [backend/tests/api/test_security.py](/D:/policymind/backend/tests/api/test_security.py:29)
  - [backend/tests/api/test_security.py](/D:/policymind/backend/tests/api/test_security.py:32)
  - [backend/tests/documents/test_router.py](/D:/policymind/backend/tests/documents/test_router.py:38)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:242)

实施计划明确要求先测匿名访问、跨租户资源、超大文件、伪造 MIME、Prompt Injection 和限流。现在：

- 匿名访问有测试。
- 跨租户测试是空 `pass`。
- 无效上传测试使用 `pytest.raises(ValueError)`，不是断言 API 返回 4xx。
- 没看到 Prompt Injection 和限流测试。

改进方向：
- 把 invalid upload 改成 API 层 400/422 响应测试。
- 增加两个租户数据隔离测试。
- 增加一个 prompt injection 被标记/拒绝/降权的 API 测试。
- 简历项目可以先做轻量内存限流，但要有可验证行为。

## 可先忽略的问题

这轮我不把下面这些当阻塞项：

- `api/v1/auth.py`、`api/v1/documents.py` 没有按实施计划路径拆分，目前分别在 `auth/router.py` 和 `documents/router.py`；只要路由契约稳定，简历项目可以接受。
- Evaluation API 暂缺可以放到 Task 10 一起补，不必在 Task 8 第一轮硬卡。
- `/health/ready` 目前只检查 database，没有检查 Milvus/Neo4j/Redis/MCP；简历项目可先保留，但后续发布前最好补依赖列表。

## 验证记录

实际执行：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\api backend\tests\documents\test_router.py backend\tests\test_smoke.py -q`
   - 首次结果：受 Windows 默认临时目录权限影响失败
   - 失败原因：`PermissionError: [WinError 5]`，发生在 pytest 创建 `tmp_path`

2. 使用工作区临时目录重跑：
   - 命令：`$env:TEMP='D:\policymind\.tmp_pytest'; $env:TMP='D:\policymind\.tmp_pytest'; .\backend\.venv\Scripts\python.exe -m pytest backend\tests\api backend\tests\documents\test_router.py backend\tests\test_smoke.py -q`
   - 结果：通过
   - 摘要：`14 passed`

3. `.\backend\.venv\Scripts\python.exe -m ruff check backend\src\policymind\api backend\src\policymind\documents\router.py backend\src\policymind\main.py backend\tests\api backend\tests\documents\test_router.py`
   - 结果：通过
   - 摘要：`All checks passed!`

## 是否允许进入下一 Task

**暂不建议进入 Task 9。**

建议先补一个小闭环：

1. 让 Chat API 和 Review API 共享同一个 checkpointer。
2. 补 API 级 HITL resume 测试。
3. Review 列表返回真实 pending review。
4. Graph API 至少接一个真实 demo/内存结果。
5. 把跨租户和 invalid upload 测试改成真正 API 断言。

这几项补完后，Task 8 就可以按简历项目标准收口。
