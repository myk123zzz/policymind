# Task 5 第 6 次审查报告
审查日期：2026-07-10

审查目的：
- 复审 Task 5 最新修复。
- 判断 Task 5 是否已经达到可收口状态。

审查范围：
- `backend/src/policymind/retrieval/{service,parent_expansion,citations,ports}.py`
- `backend/src/policymind/infrastructure/milvus/store.py`
- `backend/tests/retrieval/{test_service,test_parent_expansion,test_citations,test_store}.py`

审查基线：
- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10 实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 5 第 5 次审查报告](/D:/policymind/docs/reviews/task-05/review-05/README.md:1)

## 结论

这轮修复把上次的一个关键问题关掉了：

- `MemoryVectorStore.delete_document_version()` 现在已经按 `tenant_id + version_id` 共同删除，跨租户误删问题已关闭。

但我仍然**不建议现在收口 Task 5**。当前还存在 1 个中严重度问题：

- `Parent Expansion` 在拼接父级文本时重新构造了 `SearchHit`，但没有保留 `document_name`、`document_version`、`page_number`、`bbox` 等引用元数据，导致后续 `build_citations()` 拿到的是被“洗掉元数据”的命中结果。

这意味着链路名义上已经是 `Embedding -> Dense/BM25 -> RRF -> Rerank -> Parent Expansion -> Citation`，但一旦真的发生 parent expansion，citation 质量会倒退，不符合文档对“页码、bbox 和来源不得丢失”的要求。

## 已关闭的问题

### 1. `MemoryVectorStore.delete_document_version()` 跨租户误删

- 状态：已关闭
- 证据：
  - [backend/src/policymind/infrastructure/milvus/store.py](/D:/policymind/backend/src/policymind/infrastructure/milvus/store.py:72)
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:95)

说明：

内存实现现在已经和 `MilvusStore` 一样，按 `tenant_id` 与 `document_version_id` 共同约束删除条件，并且补上了跨租户删除测试。

## Findings

### 1. `expand_parents()` 会丢失 citation 所需元数据，导致 parent expansion 与可验证引用目标相冲突

- 严重性：中
- 位置：
  - [backend/src/policymind/retrieval/parent_expansion.py](/D:/policymind/backend/src/policymind/retrieval/parent_expansion.py:21)
  - [backend/src/policymind/retrieval/ports.py](/D:/policymind/backend/src/policymind/retrieval/ports.py:13)
  - [backend/src/policymind/retrieval/service.py](/D:/policymind/backend/src/policymind/retrieval/service.py:82)
  - [backend/src/policymind/retrieval/citations.py](/D:/policymind/backend/src/policymind/retrieval/citations.py:34)
  - [backend/tests/retrieval/test_parent_expansion.py](/D:/policymind/backend/tests/retrieval/test_parent_expansion.py:5)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:399)

当前 `expand_parents()` 在命中存在父级文本时，会重新 new 一个 `SearchHit`，但只保留：

- `chunk_id`
- `score`
- `channel`
- `rank`
- `text`

而 `SearchHit` 本身已经定义了：

- `parent_text`
- `document_name`
- `document_version`
- `page_number`
- `bbox`

这些字段在重新构造时全部被丢掉了。随后 `RetrievalService.retrieve()` 会把这个被重建后的结果直接送入 `build_citations()`，而 `build_citations()` 正是从 `SearchHit` 读取 `document_name`、`document_version`、`page_number`、`bbox` 来生成引用。

所以当前行为会变成：

1. 不触发 parent expansion 时，citation 元数据正常。
2. 一旦触发 parent expansion，citation 会退化成默认值或空值。

这和文档中“表头、标题、页码、bbox 和来源不得丢失”的要求不一致，也会让 Task 5 的“可验证引用”在真实命中父级上下文时失真。

当前测试没有覆盖这个回归点：`test_expand_parents_appends_parent_text()` 只验证文本被追加，没有验证元数据是否被完整保留，因此现有绿灯没有挡住这个问题。

改进方向：

- `expand_parents()` 不要手工重建一个只带少数字段的 `SearchHit`；应保留原命中的全部元数据，只更新扩展后的文本字段。
- 如果希望区分 leaf 文本和 parent 文本，优先把父级内容放入 `parent_text` 或显式字段，再由 `RetrievalService` 统一组装 `context`。
- 增加一条服务级或单元测试，验证触发 parent expansion 后，`document_name`、`document_version`、`page_number`、`bbox` 仍能原样进入 citation。

## Remaining Risk

### 1. Task 5 要求的“共享 Contract Test，内存和 Milvus 适配器通过同一组过滤测试”仍未完全落地

- 严重性：低
- 位置：
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:178)
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:1)

说明：

当前过滤与删除测试仍然只跑 `MemoryVectorStore`，我没有看到“同一组 contract tests 同时约束内存实现和 Milvus 实现”的测试组织方式。  
这不一定马上阻塞你继续修上面的主问题，但在 Task 5 收口前，最好把这条文档要求补齐，不然 Milvus 适配器仍然缺少和内存实现对齐的行为证据。

## 验证记录

实际执行结果：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\retrieval -q`
   - 结果：通过
   - 摘要：`18 passed`

补充说明：

- 这次结论主要来自代码复核 + 针对 retrieval 测试复跑。
- 虽然测试全绿，但现有用例没有覆盖“parent expansion 后 citation 元数据仍完整保留”的场景，所以不能据此判定 Task 5 已收口。
