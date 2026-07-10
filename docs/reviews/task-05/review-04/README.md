# Task 5 第 4 次审查报告

审查日期：2026-07-10

审查目的：

- 复审 [Task 5 第 3 次审查报告](/D:/policymind/docs/reviews/task-05/review-03/README.md:1) 中剩余的问题。
- 再次判断 Task 5 是否已经达到可收口状态。

审查范围：

- `backend/src/policymind/infrastructure/milvus/store.py`
- `backend/tests/retrieval/{test_store,test_service}.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 5 第 3 次审查报告](/D:/policymind/docs/reviews/task-05/review-03/README.md:1)

## 结论

这轮把 `MilvusStore` 往前推了一截：

- schema 已补齐版本、权限、时间字段
- 过滤表达式已经覆盖 `tenant_id / access_level / effective_from / effective_to`
- `delete_document_version()` 也改成了按 `tenant_id + document_version_id` 删除

本次在当前受限环境下，我继续用仓库内 `.venv` 复核了：

- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\python.exe -m ruff check src tests`
- `.\\.venv\\Scripts\\python.exe -m mypy src`

但结论仍然是：

- Task 5 还**不能收口**。

原因不再是“权限/时间/删除字段缺失”，而是更本质的一点：

- 现在的 `MilvusStore` 依然不是真正的 **Hybrid Search** 实现。

## 已关闭的问题

### 1. `MilvusStore` 缺少权限和时间过滤字段

- 状态：已关闭
- 证据：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:123)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:199)

### 2. `delete_document_version()` 没按版本精确删除

- 状态：已关闭
- 证据：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:230)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:237)

## Findings

### 1. `MilvusStore.hybrid_search()` 仍然不是“dense + BM25”双通道检索，而是把同一套 dense 结果同时塞进 `dense` 和 `bm25`

- 严重性：高
- 位置：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:177)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:228)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:180)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:448)

当前实现里只做了一次向量搜索：

- `anns_field="dense_vector"`

然后把这一次搜索得到的 `hits` 同时返回成：

- `dense=hits`
- `bm25=hits`

这意味着：

- 现在没有真正的 BM25 / sparse 通道
- RRF 融合实际上是在融合两份相同结果

影响：

- 这还不符合 Task 5 文档写的 “Dense Top30 + BM25 Top30 -> RRF”。
- 当前 `Hybrid RAG` 名义上成立，语义上还没有成立。

改进方向：

- 接上真实 BM25 / sparse 通道。
- 如果当前阶段只能做 dense，应明确返回单通道能力，而不是伪造第二通道。

### 2. `MilvusStore` 仍然缺少行为级测试，无法证明它与 `MemoryVectorStore` 的契约一致

- 严重性：中
- 位置：
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:24)

这轮虽然把 `MilvusStore` 代码补了不少，但测试仍然只覆盖 `MemoryVectorStore`。  
没有任何一条测试证明：

- Milvus 过滤语义正确
- 版本删除正确
- 返回的 dense/bm25 通道符合预期

影响：

- `MilvusStore` 的关键行为没有测试兜底。
- 你现在看到的“全绿”，并不能说明 Milvus 这一层真的可用。

改进方向：

- 至少加一组 integration 测试，专门验证 MilvusStore 的过滤和删除行为。
- 或者补 contract test，让 memory/milvus 共用同一批语义测试。

## Remaining Risk

### 1. `delete_document_version()` 捕获异常后直接返回 `0`，失败与“本来就没删到东西”不可区分

- 严重性：低
- 位置：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:238)

说明：

这个点不阻塞 Task 5 主线，但会让后续排查删除失败变得很闷。  
如果 Milvus 删除操作异常，最好保留失败信号，而不是默默吞掉。

## Change Summary

这轮修复把 Task 5 从“Milvus schema 不够用”推进到了“Milvus schema 基本能承载过滤和删除语义”的状态。  
但当前最大的剩余问题已经从“字段不够”切换成了“检索通道不对”：

- 现在仍然没有真实 BM25 / sparse 通道
- 所以还不能算真正的 Hybrid RAG 完成态

## 验证记录

实际执行结果：

1. `.\\.venv\\Scripts\\python.exe -m ruff check src tests`
   - 结果：通过

2. `.\\.venv\\Scripts\\python.exe -m mypy src`
   - 结果：通过

3. `.\\.venv\\Scripts\\python.exe -m pytest`
   - 结果：通过
   - 摘要：`79 passed`

补充说明：

- 为绕开当前受限环境里的系统临时目录限制，本次仍使用仓库内 `.venv`，并将 `TEMP/TMP` 指向工作区内目录后完成了测试复核。
