# Task 5 第 3 次审查报告

审查日期：2026-07-10

审查目的：

- 复审 [Task 5 第 2 次审查报告](/D:/policymind/docs/reviews/task-05/review-02/README.md:1) 中剩余的问题。
- 判断 Task 5 是否已经达到可收口状态。

审查范围：

- `backend/src/policymind/infrastructure/milvus/store.py`
- `backend/tests/retrieval/test_service.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 5 第 2 次审查报告](/D:/policymind/docs/reviews/task-05/review-02/README.md:1)

## 结论

这轮确实把上次的两个重点往前推了：

1. `MilvusStore` 不再只是空壳，已经有连接初始化和基本 `upsert/search/delete` 路径。
2. `RetrievalService` 主链测试已经补上。

本次在当前受限环境下，我用仓库内 `.venv` 复核了：

- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\python.exe -m ruff check src tests`
- `.\\.venv\\Scripts\\python.exe -m mypy src`

结论判断：

- Task 5 仍然**不能收口**。
- 原因很集中：`MilvusStore` 现在虽然“不再空”，但它的行为语义还没有达到文档要求，也没有和 `MemoryVectorStore` 对齐。

## 已关闭的问题

### 1. 缺少 `RetrievalService` 主链测试

- 状态：已关闭
- 证据：
  - [backend/tests/retrieval/test_service.py](/D:/policymind/backend/tests/retrieval/test_service.py:31)
  - [backend/tests/retrieval/test_service.py](/D:/policymind/backend/tests/retrieval/test_service.py:54)

说明：

现在已经覆盖：

- 正常主链
- rerank 失败降级

## Findings

### 1. `MilvusStore.hybrid_search()` 只按 `tenant_id` 过滤，仍然没有实现文档要求的权限与时间过滤

- 严重性：高
- 位置：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:159)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:175)

虽然 `hybrid_search()` 现在不再返回空列表了，但实际 filter 只有：

```python
tenant_id == ...
```

它并没有使用：

- `access_level`
- `at`

而这些正是 Task 5 文档要求的核心安全约束。

影响：

- `MemoryVectorStore` 和 `MilvusStore` 的检索语义现在并不一致。
- 真切 Milvus 后，越权召回和过期文档召回的风险没有被守住。

改进方向：

- 在 Milvus schema / filter expression 里补权限和时间过滤字段。
- 至少让 Milvus 适配器和 Memory store 在 contract 语义上对齐。

### 2. `MilvusStore.delete_document_version()` 根本没有按 `version_id` 删除

- 严重性：高
- 位置：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:200)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:207)

现在 delete 用的表达式只有：

```python
tenant_id == {tenant_id}
```

然后把查到的所有 `id` 都删掉。  
这意味着它不是“删除一个 document version”，而是“删除这个租户下查到的所有记录”。

影响：

- 这是实打实的数据删除风险。
- 一旦接到真实 Milvus，删除一个版本可能把整租户的数据都清空。

改进方向：

- schema 里至少要有 `document_version_id` 字段。
- 删除表达式必须同时按 `tenant_id` 和 `version_id` 过滤。

### 3. `MilvusStore.upsert()` 和 schema 仍然过于简化，没为 BM25 / 权限 / 时间 / 删除语义准备必要字段

- 严重性：高
- 位置：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:125)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:151)

当前 schema 只有：

- `id`
- `tenant_id`
- `text`
- `dense_vector`

缺少 Task 5 真正要用到的关键元数据，比如：

- `document_version_id`
- `access_level`
- `effective_from / effective_to`
- 任何 BM25 / sparse 相关字段

影响：

- 即使现在 search 能返回点东西，也离文档要求的 Hybrid RAG 还有本质差距。
- 你后面一旦补 filter 或 delete，很快就会发现 schema 本身不够用。

改进方向：

- 先把 Task 5 文档要求的过滤和删除字段补进 schema。
- 再考虑 BM25 / sparse 的实现路径。

## Remaining Risk

### 1. `MilvusStore` 还没有配套测试，无法证明它和 `MemoryVectorStore` 的契约一致

- 严重性：中
- 位置：
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:24)

说明：

现在 `test_store.py` 只在测 `MemoryVectorStore`。  
这次虽然把 `MilvusStore` 从空壳推进到了有代码路径，但没有任何行为测试兜底。

## Change Summary

这轮让 Task 5 从“store 只有 Memory 实现有行为”推进到了“Milvus 适配器开始长骨头”的阶段。  
但它现在还没长到能承受文档要求的那种程度，尤其在：

- 权限过滤
- 时间过滤
- 精确删除
- schema 完整性

这四点上还不够。

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
