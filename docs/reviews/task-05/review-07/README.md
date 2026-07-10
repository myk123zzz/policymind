# Task 5 第 7 次审查报告
审查日期：2026-07-10

审查目的：
- 复审 Task 5 最新修复。
- 判断 Task 5 是否已经达到可收口、可进入下一 Task 的状态。

审查范围：
- `backend/src/policymind/retrieval/{parent_expansion,service,citations,ports}.py`
- `backend/src/policymind/infrastructure/milvus/store.py`
- `backend/tests/retrieval/{test_parent_expansion,test_service,test_citations,test_store}.py`

审查基线：
- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10 实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 5 第 6 次审查报告](/D:/policymind/docs/reviews/task-05/review-06/README.md:1)

## 结论

这轮我认为 **Task 5 可以收口，并允许进入下一 Task**。

上轮卡住的主问题已经修复：

- `expand_parents()` 现在在追加 parent 文本时，能够保留 `document_name`、`document_version`、`page_number`、`bbox` 等引用元数据。
- 对应的回归测试已经补上，能直接证明 parent expansion 不再破坏 citation 所需信息。

从“是否能作为简历项目成立”的标准看，Task 5 的核心叙事已经闭环：

- 有租户/权限/时间过滤；
- 有 Dense + BM25 + RRF + Rerank 降级；
- 有 Parent Expansion；
- 有可验证 Citation；
- 相关 retrieval 测试与静态检查通过。

剩余内容更多是“完善度继续提升会更好”，不是我建议继续卡住 Task 5 的问题。

## 已关闭的问题

### 1. `expand_parents()` 丢失 citation 元数据

- 状态：已关闭
- 证据：
  - [backend/src/policymind/retrieval/parent_expansion.py](/D:/policymind/backend/src/policymind/retrieval/parent_expansion.py:21)
  - [backend/tests/retrieval/test_parent_expansion.py](/D:/policymind/backend/tests/retrieval/test_parent_expansion.py:23)

说明：

当前实现会在 parent expansion 时保留原始命中的元数据，并额外写入 `parent_text`，后续 `build_citations()` 读取到的字段不再退化。

## Findings

本轮未发现新的阻塞性问题。

## 可忽略的尾项

### 1. “共享 Contract Test 同时约束 Memory 与 Milvus” 还不算完全成型

- 严重性：低
- 位置：
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:178)
  - [backend/tests/retrieval/test_store.py](/D:/policymind/backend/tests/retrieval/test_store.py:1)

说明：

按文档的理想形态，最好把同一套 store contract tests 同时跑在 `MemoryVectorStore` 和 `MilvusStore` 上。  
现在更多还是以内存实现作为主覆盖对象。

但从你当前目标看，这已经属于可以接受的尾项：

- 它不会直接破坏 Task 5 当前主链路；
- 它更偏“测试组织方式还可更工程化”；
- 在简历表述里不会成为明显短板。

如果后面你还有精力，可以在统一 contract test 上再补一层；如果没有，我建议直接继续 Task 6。

## 验证记录

实际执行结果：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\retrieval -q`
   - 结果：通过
   - 摘要：`19 passed`

2. `.\backend\.venv\Scripts\python.exe -m ruff check backend\src backend\tests`
   - 结果：通过

补充说明：

- 测试输出里仍有若干第三方依赖 warning，但目前没有看到会影响 Task 5 主功能验收的错误。
- 因此这轮审查结论是：**Task 5 通过，可以进入下一 Task。**
