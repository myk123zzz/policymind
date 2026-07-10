# Task 5 第 5 次审查报告

审查日期：2026-07-10

审查目的：

- 继续复审 Task 5 最新修复。
- 判断 Task 5 是否已经达到可收口状态。

审查范围：

- `backend/src/policymind/infrastructure/milvus/store.py`
- `backend/src/policymind/retrieval/{service,citations}.py`
- `backend/tests/retrieval/{test_store,test_service}.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 5 第 4 次审查报告](/D:/policymind/docs/reviews/task-05/review-04/README.md:1)

## 结论

这轮 `MilvusStore` 已经从“伪双通道”推进到了真正尝试 dense + BM25 双通道的实现方向，门禁也继续全绿：

- `.\\.venv\\Scripts\\python.exe -m pytest` -> `79 passed`
- `.\\.venv\\Scripts\\python.exe -m ruff check src tests` -> 通过
- `.\\.venv\\Scripts\\python.exe -m mypy src` -> 通过

但我这轮仍然不建议直接把 Task 5 判定收口。  
现在剩下的问题已经不是“大框架没做”，而是契约和结果质量上的真实缺口。

## 已关闭的问题

### 1. `MilvusStore` 伪装双通道，只返回两份 dense 结果

- 状态：已关闭
- 证据：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:145)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:242)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:253)

说明：

现在 schema 已经引入 `sparse_vector`，并通过 BM25 Function 生成 sparse 通道；检索也拆成了 dense 与 sparse/BM25 两次搜索，不再是“把同一套 dense 结果复制两份”。

## Findings

### 1. `MemoryVectorStore.delete_document_version()` 仍然忽略 `tenant_id`，删除语义和文档契约不一致

- 严重性：高
- 位置：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:72)
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:84)

当前内存实现删除逻辑只按：

```python
document_version_id != version_id
```

来过滤，没有同时检查 `tenant_id`。  
如果两个租户恰好存在相同的 `document_version_id`，调用一个租户的删除可能会误删另一个租户的数据。

影响：

- `MemoryVectorStore` 和 `MilvusStore` 的删除语义不一致。
- 这违背了 Task 5 文档要求的租户安全边界。
- 测试当前也没有覆盖“相同 version_id 跨租户删除”的场景。

改进方向：

- 把内存实现也改成按 `tenant_id + version_id` 删除。
- 补一条跨租户删除测试，防止回归。

### 2. `RetrievalService` 仍然没有真正接上 parent expansion 所需的父级上下文源，服务层这一步实际上还是 noop

- 严重性：中
- 位置：
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:79)
  - [backend/src/policymind/retrieval/parent_expansion.py](/D:/policymind/backend/src/policymind/retrieval/parent_expansion.py:6)

虽然 `expand_parents()` 这个 helper 已经支持 `parent_map`，但 `RetrievalService.retrieve()` 调它时并没有提供任何 `parent_map` 或父级 chunk 来源。

这意味着在真实主链里：

- parent expansion 这一步名义上存在
- 实际上仍然不会扩出任何父级上下文

影响：

- 跟文档要求的 “Rerank -> Parent扩展 -> Citation” 还有一段距离。
- 当前 `context` 仍然只是 reranked hits 的文本拼接。

改进方向：

- 给 `RetrievalService` 增加获取父级文本的依赖来源。
- 再补一条服务层测试，验证 `retrieve()` 之后的 `context` 确实包含父级内容。

### 3. `RetrievalService` 产出的 `Citation` 仍然缺失文档名、版本、页码、bbox 等关键元数据

- 严重性：中
- 位置：
  - [backend/src/policymind/retrieval/citations.py](/D:/policymind/backend/src/policymind/retrieval/citations.py:27)
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:83)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:202)

`build_citations()` 的默认参数还是：

- `document_name=""`
- `version=""`
- `page=1`
- `bbox=None`

而 `RetrievalService` 调用时没有传任何真实元数据。

影响：

- 当前 citation 虽然“有 id 和 quote”，但还不符合文档要求的可追溯引用质量。
- 后续前端如果要跳页、定位、展示版本信息，这一层信息还不够。

改进方向：

- 让 `SearchHit` 或 retrieval 结果携带必要的文档元数据。
- `build_citations()` 用真实 document/version/page/bbox 构建引用，而不是默认值。

## Remaining Risk

### 1. `MilvusStore` 仍然没有行为级测试，当前绿色门禁并不证明它真实可用

- 严重性：中
- 位置：
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:24)

说明：

这次 `MilvusStore` 代码明显进步了，但测试仍然主要覆盖 `MemoryVectorStore`。  
在没有 integration / contract 测试的情况下，Milvus 这一层仍然缺少“真跑过”的证据。

## Change Summary

这轮把 Task 5 从“Milvus 只有 dense 壳”进一步推进到了“Milvus 开始具备真实 hybrid 形状”的状态。  
但 reviewer 视角下，真正的收口还差三块：

- 内存实现和 Milvus 实现的删除契约对齐
- 服务层 parent expansion 真接线
- citation 元数据完整性

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
