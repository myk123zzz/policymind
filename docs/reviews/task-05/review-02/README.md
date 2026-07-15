# Task 5 第 2 次审查报告

审查日期：2026-07-10

审查目的：

- 复审 [Task 5 第 1 次审查报告](/D:/policymind/docs/reviews/task-05/review-01/README.md:1) 中提出的问题。
- 判断 Task 5 是否已经达到可收口状态。

审查范围：

- `backend/src/policymind/retrieval/{ports,service,parent_expansion}.py`
- `backend/src/policymind/infrastructure/milvus/store.py`
- `backend/tests/retrieval/{test_store,test_parent_expansion}.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 5 第 1 次审查报告](/D:/policymind/docs/reviews/task-05/review-01/README.md:1)

## 结论

上一次审查里的 4 个核心问题，这次已经修掉了大半：

1. `VectorStore.hybrid_search()` 契约和 `RetrievalService.retrieve()` 都补回了 `at` 时间参数。
2. `MemoryVectorStore` 现在已经实现租户、权限和时间过滤。
3. `RetrievalService` 不再默认偷偷使用测试用 embedder，而是要求显式传入。
4. `expand_parents()` 不再是纯空实现，并补了对应测试。

本次在当前受限环境下，我用仓库内 `.venv` 复核了：

- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\python.exe -m ruff check src tests`
- `.\\.venv\\Scripts\\python.exe -m mypy src`

结论判断：

- Task 5 还**不能收口**。
- 剩下最关键的阻塞点是：`MilvusStore` 依然没有真正完成 `upsert / hybrid_search / delete_document_version` 的行为实现。

## 已关闭的问题

### 1. 缺少 `at` 时间参数

- 状态：已关闭
- 证据：
  - [backend/src/policymind/retrieval/ports.py](/D:/policymind/backend/src/policymind/retrieval/ports.py:37)
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:40)

### 2. `MemoryVectorStore` 未做租户/权限/时间过滤

- 状态：已关闭
- 证据：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:21)
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:35)
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:49)
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:63)

### 3. `RetrievalService` 默认偷偷用测试 embedder

- 状态：已关闭
- 证据：
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:29)
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:33)

### 4. `expand_parents()` 为空实现

- 状态：已关闭
- 证据：
  - [backend/src/policymind/retrieval/parent_expansion.py](/D:/policymind/backend/src/policymind/retrieval/parent_expansion.py:6)
  - [backend/tests/retrieval/test_parent_expansion.py](/D:/policymind/backend/tests/retrieval/test_parent_expansion.py:5)

## Findings

### 1. `MilvusStore` 仍然不是真正可工作的检索适配器，只是从“抛错壳子”变成了“连通性壳子”

- 严重性：高
- 位置：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:98)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:118)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:125)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:139)

当前 `MilvusStore` 的状态是：

- 能尝试连接 Milvus
- `upsert()` 只保证“已连接”，没有写入逻辑
- `hybrid_search()` 直接返回空 `dense=[] / bm25=[]`
- `delete_document_version()` 直接返回 `0`

这比上次的 `NotImplementedError` 强了一点，但从 reviewer 视角仍然不能算“Milvus 适配器已完成”。

影响：

- Task 5 最核心的“真实生产向量适配器”仍然缺失。
- 现在所有有意义的检索语义仍然只存在于 `MemoryVectorStore`。

改进方向：

- 把 `MilvusStore` 做成真正可写、可查、可删的最小实现。
- 给 `MilvusStore` 单独补至少一组行为测试，哪怕是 integration marker 下跑。

### 2. 仍然缺少 `RetrievalService` 主链测试，当前测试主要停留在组件级

- 严重性：中
- 位置：
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:29)
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:1)

现在这轮测试已经覆盖了：

- store 过滤语义
- RRF
- citations
- parent expansion

但还没有直接测试 `RetrievalService.retrieve()` 主链，比如：

- embed query
- hybrid_search
- RRF
- rerank 降级
- parent expansion
- citation/context 产出

影响：

- 组件测试都绿，并不等于主链拼装就一定正确。

改进方向：

- 补一个 `RetrievalService` 层测试，至少覆盖正常路径和 rerank 降级路径。

## Remaining Risk

### 1. `MilvusStore._ensure_connected()` 捕获所有异常后统一转成 `RuntimeError`，诊断信息偏少

- 严重性：低
- 位置：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:106)

说明：

这次不是阻塞点，因为真正阻塞的是它还没做完行为实现。  
但等你把 Milvus 逻辑补齐后，最好把底层异常上下文也保留下来，不然排查连接问题会有点闷。

## Change Summary

这轮修复已经让 Task 5 从“retrieval 骨架”进化成了“retrieval 语义开始落地”的状态：

- 时间过滤回来了
- 安全过滤回来了
- parent expansion 不再是空壳
- 服务层模式边界比上次清楚了

但只要 `MilvusStore` 还没真正工作，我这边就不会把 Task 5 判成完成态。

## 验证记录

实际执行结果：

1. `.\\.venv\\Scripts\\python.exe -m ruff check src tests`
   - 结果：通过

2. `.\\.venv\\Scripts\\python.exe -m mypy src`
   - 结果：通过

3. `.\\.venv\\Scripts\\python.exe -m pytest`
   - 结果：通过
   - 摘要：`77 passed`

补充说明：

- 为绕开当前受限环境里系统临时目录权限问题，本次仍使用仓库内 `.venv`，并将 `TEMP/TMP` 指向工作区内目录后完成了测试复核。

