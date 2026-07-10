# Task 5 第 1 次审查报告

审查日期：2026-07-10

审查范围：

- `backend/src/policymind/retrieval/{ports,embeddings,fusion,rerank,parent_expansion,citations,service}.py`
- `backend/src/policymind/infrastructure/milvus/store.py`
- `backend/tests/retrieval/{test_fusion,test_embeddings,test_citations}.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)

## Findings

### 1. `MilvusStore` 仍然完全是占位实现，Task 5 最核心的生产适配器还没接通

- 严重性：高
- 位置：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:94)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:103)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:108)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:174)

当前 `MilvusStore` 的 `upsert / hybrid_search / delete_document_version` 全部还是 `NotImplementedError`。  
也就是说，这轮真正能工作的只有 `MemoryVectorStore`，还不能算“Milvus Hybrid RAG”已经落地。

影响：

- Task 5 文档要求的生产向量适配器和 contract 测试目标都还没有达到。
- 现在更像是“retrieval 领域代码和测试先写好了”，而不是“secure hybrid rag 已真正接通”。

改进方向：

- 至少补齐 Milvus 适配器的最小可运行实现。
- 再加一组 memory/milvus 共享 contract 测试，去证明两个实现遵守同一语义。

### 2. `VectorStore.hybrid_search()` 契约缺少文档要求的时间参数 `at`

- 严重性：高
- 位置：
  - [backend/src/policymind/retrieval/ports.py](/D:/policymind/backend/src/policymind/retrieval/ports.py:36)
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:39)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:462)

开发手册对检索接口明确要求基于查询时间做有效期过滤。当前 `VectorStore.hybrid_search()` 没有 `at` 参数，`RetrievalService.retrieve()` 也没有 `at` 参数。

影响：

- 这会让 Task 3 里刚加上的 `effective_from / effective_to` 在检索层根本用不上。
- 后续你为了补时间过滤，得重新改 protocol、service 和所有实现。

改进方向：

- 把 `at: datetime` 补回 `VectorStore` 契约和 `RetrievalService.retrieve()`。
- 测试补上“过期版本不应被召回”的用例。

### 3. `MemoryVectorStore` 没有做租户、权限和时间过滤，当前测试也没有覆盖这些约束

- 严重性：高
- 位置：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:22)
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:31)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:177)

当前内存检索实现只是对所有已存 chunk 做余弦排序，没有真正使用：

- `tenant_id`
- `access_level`
- 文档时间范围

而 Task 5 文档明确要求 contract test 覆盖租户、权限和时间过滤。

影响：

- 现在的测试绿，并不能证明你的 hybrid search 满足最关键的安全语义。
- 如果后续 agent 直接接这套检索，跨租户或越权召回的风险没有被测试网住。

改进方向：

- 让 `MemoryVectorStore` 也遵守和未来 Milvus 一样的过滤语义。
- 补共享 contract test，不要只测 RRF / Citation 这些“后半段逻辑”。

### 4. `RetrievalService` 仍然默认使用 `MemoryEmbeddingProvider` 和 `NoopReranker`，但没有显式降级标记或错误策略

- 严重性：中
- 位置：
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:28)
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:36)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:452)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:490)

默认测试替身本身没问题，但现在服务层没有明确区分：

- 这是测试模式
- 这是降级模式
- 这是生产模式

文档里要求 embedding 失败要抛 `EmbeddingUnavailable`，rerank 超时要保留 RRF 顺序并记录降级。现在这些策略在服务层没有明确表达。

影响：

- 运行时模式边界不清晰，容易把测试替身一路带进实际链路。

改进方向：

- 至少把测试替身只留给测试 wiring。
- 在正式服务构造路径中强制显式传入真实 embedder / reranker，或在缺失时直接报错。

### 5. `expand_parents()` 仍然是空实现，Task 5 文档要求的 parent expansion 还没有真正发生

- 严重性：中
- 位置：
  - [backend/src/policymind/retrieval/parent_expansion.py](/D:/policymind/backend/src/policymind/retrieval/parent_expansion.py:6)
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:65)

现在 `expand_parents()` 只是原样返回 hits，没有把 leaf 命中扩成父级上下文。

影响：

- 当前 `context` 实际上仍然是 leaf 文本拼接，不是文档要求的 parent expansion 结果。

改进方向：

- 至少接入一个 `parent_map` 或 chunk repository，把父级文本真正扩进来。
- 给 retrieval service 补测试，验证 parent expansion 改变了上下文结果。

## Open Questions / Assumptions

- 我把这轮定位为“Task 5 的第一段实现”，而不是完成态。
- `pytest` 在当前受限环境里需要把 `TEMP/TMP` 指向工作区内目录才能稳定运行；我据此复核了测试结果。

## Change Summary

这轮已经有价值的部分：

- retrieval 基础协议和服务骨架
- RRF 融合
- Citation 构建与验证
- 内存 embedding / vector store
- 最小测试集

但从 reviewer 视角看，这还明显没到“secure hybrid rag”可收口的程度，更像是 Task 5 的基础模型和单元测试阶段。

## 验证记录

实际执行结果：

1. `.\\.venv\\Scripts\\python.exe -m ruff check src tests`
   - 结果：通过

2. `.\\.venv\\Scripts\\python.exe -m mypy src`
   - 结果：通过

3. `.\\.venv\\Scripts\\python.exe -m pytest`
   - 结果：通过
   - 摘要：`71 passed`

补充说明：

- 直接使用 `conda run -n policymind uv run pytest` 在当前受限环境中会因为 `uv` 缓存目录权限失败。
- 我改用仓库内 `.venv` 运行，并把 `TEMP/TMP` 指向工作区内目录后完成了测试复核。
