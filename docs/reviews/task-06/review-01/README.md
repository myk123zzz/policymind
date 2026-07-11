# Task 6 第 1 次审查报告
审查日期：2026-07-10

审查目的：
- 审查 Task 6：Neo4j GraphRAG 当前实现是否达到可继续推进或可收口状态。
- 按“简历项目可讲、主链路不翻车”的标准判断当前缺口。

审查范围：
- `backend/src/policymind/graph/{ontology,extraction,repository}.py`
- `backend/src/policymind/infrastructure/neo4j/repository.py`
- `backend/tests/graph/{test_ontology,test_extraction,test_repository}.py`

审查基线：
- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10 实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [审查报告目录规范](/D:/policymind/docs/reviews/README.md:1)

## 结论

这轮我认为 **Task 6 还不能算通过**，但不是因为小毛刺，而是因为还缺 2 个主件：

- 图谱抽取链只做了 `extract_json_object()`，还没有把“Chunk -> 结构化抽取 -> 校验 -> upsert Neo4j”真正接起来。
- GraphRAG 目前只有 repository 层，没有看到查询组装、路径排序、上下文拼接这些面向问答链路的模块，离文档要求的“给出带关系和来源的路径”还差一段。

换句话说，现在更像是 **Task 6 的地基已经起了**，但还没到“我可以把 GraphRAG 这条能力写进简历并放心演示”的程度。

## 做得不错的部分

这轮有几块是成立的：

- ontology 白名单已经有了基本形状；
- 内存图谱仓库支持租户过滤和多跳路径；
- Neo4j 适配器已经起了端口/适配器分层；
- graph 相关单元测试是绿的，说明当前这层基础代码不是空壳。

## Findings

### 1. 图谱抽取主链还没实现，当前并不存在真正可用的 `GraphExtractor`

- 严重性：高
- 位置：
  - [backend/src/policymind/graph/extraction.py](/D:/policymind/backend/src/policymind/graph/extraction.py:5)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:123)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:569)

当前 `extraction.py` 只有一个 `extract_json_object()`，它解决的是“从文本里抠出 JSON 对象”的小步骤，但文档要求的主链是：

- `GraphExtractor.extract(chunk)`
- 抽取并校验实体/关系
- 拒绝无来源或端点不存在的关系
- 再进入 `GraphRepository.upsert`

也就是说，**现在还没有真正的图谱抽取器**。  
如果停在这个状态，Task 6 在能力描述上只能说“有图谱存储和 JSON 提取辅助函数”，还不能说“实现了 GraphRAG 抽取链”。

改进方向：

- 在 `graph/extraction.py` 中补上 `parse_llm_json()` 与 `GraphExtractor.extract()`。
- 让抽取结果显式包含实体、关系、来源信息，并做 ontology 白名单校验。
- 至少补一条从 chunk 文本到 extraction 结果的测试，证明不是只有 JSON helper。

### 2. GraphRAG 查询链还没成型，只有 repository 没有检索/排序/上下文层

- 严重性：中
- 位置：
  - [backend/src/policymind/graph/repository.py](/D:/policymind/backend/src/policymind/graph/repository.py:13)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:196)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:315)

文档里 Task 6 要求创建：

- `graph/search.py`
- `graph/path_ranker.py`
- `graph/context.py`

但当前 `graph/` 下只有 `ontology.py`、`extraction.py`、`repository.py`。  
这说明现在已经有“图存哪里、怎么查几跳路径”的底层能力，但还没有“如何把 query 变成 GraphRAG 可消费结果”的中间层。

对简历项目来说，这不是吹毛求疵，而是会直接影响你怎么讲这条线：

- 现在可以讲“图谱存储原型和路径查询原型”；
- 还不太适合讲“GraphRAG 路径检索与上下文增强已经完成”。

改进方向：

- 补 `search/path_ranker/context` 三层里最小可用的一版，不必一上来做很重。
- 先做到：给定 seed entity ids -> 取 paths -> 排序 -> 生成可拼到回答里的 graph context。
- 只要这条链闭环，Task 6 就会从“原型层”跨到“可演示层”。

## 可先忽略的尾项

### 1. Neo4j 适配器还没有集成测试

- 严重性：低
- 位置：
  - [backend/src/policymind/infrastructure/neo4j/repository.py](/D:/policymind/backend/src/policymind/infrastructure/neo4j/repository.py:1)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:933)

说明：

这项最好后面补，但我这次没有把它当阻塞项。  
原因很简单：当前 Task 6 先要解决的是“主链有没有”，不是“集成验证够不够完整”。

## 验证记录

实际执行结果：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\graph -q`
   - 结果：通过
   - 摘要：`11 passed`

补充说明：

- 现有 graph 测试能证明基础 helper 与内存仓库可用。
- 但它们还不能证明 Task 6 的完整目标已经实现，因为抽取器和 GraphRAG 查询链主体仍未闭环。
