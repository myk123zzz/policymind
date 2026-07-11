# Task 6 第 2 次审查报告

审查日期：2026-07-11

审查范围：
- `backend/src/policymind/graph/{extraction,path_ranker,repository,search}.py`
- `backend/src/policymind/infrastructure/neo4j/repository.py`
- `backend/tests/graph/{test_extraction,test_repository,test_search}.py`

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [审查报告目录规范](/D:/policymind/docs/reviews/README.md:1)
- 上一轮报告：[task-06/review-01](/D:/policymind/docs/reviews/task-06/review-01/README.md:1)

## 结论

这轮我仍然判断 **Task 6 暂不通过**。

和上一轮相比，Task 6 已经明显更完整了：现在有了可用的 `GraphExtractor`、基础的 `GraphSearchService`、`rank_paths()` 原型，以及对应的单测，说明你不是停留在“只有仓储层”的状态了。

但还剩 2 个值得拦住的点，它们都不是小瑕疵，而是会直接影响“GraphRAG 已完成”的说法是否站得住：

1. Graph 搜索主链还没有真正把“路径评分 + 带来源上下文”接起来。
2. Neo4j 适配器的租户隔离仍然不安全。

在你目前这个“简历项目、酌情放松”的标准下，我会放过 `context.py` 还没独立拆文件、也放过 Neo4j 集成测试暂时没补齐；但上面这两个点我还是建议修掉再算 Task 6 过。

## 已修复

- `GraphExtractor.extract()` 已经存在，不再是只有 JSON helper 的状态。
- 图谱搜索与路径排序模块已经落文件，不再完全缺失。
- `backend/tests/graph` 当前测试全部通过，说明现有内存实现和辅助逻辑基本可运行。

## Findings

### 1. GraphSearchService 还没有真正完成“路径评分 + 带来源上下文”这条主链

- 严重性：高
- 位置：
  - [backend/src/policymind/graph/search.py](/D:/policymind/backend/src/policymind/graph/search.py:22)
  - [backend/src/policymind/graph/path_ranker.py](/D:/policymind/backend/src/policymind/graph/path_ranker.py:6)
  - [backend/src/policymind/graph/search.py](/D:/policymind/backend/src/policymind/graph/search.py:58)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:603)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:203)

当前 `GraphSearchService.search()` 直接把 repository 返回的 `paths` 原样交给 `_build_context()`，没有调用 `rank_paths()`，而且接口里也没有 `query` 参与评分逻辑。所以现在的“路径排序”仍然是孤立 helper，不是实际 GraphRAG 查询链的一部分。

另外，`_build_context()` 现在只输出：

- 实体类型/名称
- 关系类型

但没有把来源信息写进上下文，例如：

- `source_chunk_id`
- `source_document_version_id`

这和文档里要求的“Chunk -> 种子实体 -> 路径 -> 评分 -> 带关系/来源的上下文”还差最后一段。对简历项目来说，这会直接影响你是否能稳妥地说“GraphRAG 返回带关系和来源的路径”。

改进方向：
- 让 `GraphSearchService.search()` 真正接入 `rank_paths()`。
- 把 `query` 纳入 `search()` 入参，并参与排名。
- 在 context 中显式展示每条路径的来源信息，至少包含关系类型和可追溯引用字段。
- 补一条测试，验证 `search()` 返回结果的顺序确实受 `rank_paths()` 控制，而不是只测试 helper 本身。

### 2. Neo4jGraphRepository 的租户隔离仍然会串租户

- 严重性：高
- 位置：
  - [backend/src/policymind/infrastructure/neo4j/repository.py](/D:/policymind/backend/src/policymind/infrastructure/neo4j/repository.py:24)
  - [backend/src/policymind/infrastructure/neo4j/repository.py](/D:/policymind/backend/src/policymind/infrastructure/neo4j/repository.py:33)
  - [backend/src/policymind/infrastructure/neo4j/repository.py](/D:/policymind/backend/src/policymind/infrastructure/neo4j/repository.py:66)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:590)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:202)

这里的问题还是实质性的：

- 节点写入使用 `MERGE (n:{etype} {id: $id})`，没有把 `tenant_id` 放进 identity。
- 关系写入时用 `MATCH (a {id: $src}), (b {id: $tgt})`，同样没有按租户匹配端点。
- 搜索时只限制了 `start {id: $sid, tenant_id: $tid}`，但可变长路径 `[*1..N]` 里的中间节点、终点节点、关系本身都没有被限制为同租户。

这意味着：

- 两个租户若碰巧使用同一个实体 ID，节点可能互相覆盖或共享。
- 图搜索可能从当前租户起点走进别的租户节点/边。

这不是“理想设计”问题，而是多租户正确性问题，也正好踩中文档里“Cypher 必须在查询入口限定 tenant_id”的红线。

改进方向：
- 节点 `MERGE` 至少按 `(id, tenant_id)` 建唯一身份。
- 关系创建时，端点匹配也必须同时带 `tenant_id`。
- 路径查询应保证整条路径上的节点和关系都属于当前租户，而不是只限制起点。
- 最好补一条回归测试：两个租户使用相同实体 ID，验证写入不互相覆盖、查询也不会穿透。

## 可先忽略的问题

下面这些我这轮不当阻塞项：

- `graph/context.py` 还没单独拆文件。
- Neo4j 适配器暂时没有 integration test。
- Neo4j driver 目前是同步调用包在 async 方法里。

这些更像“工程完整度”问题，不是当前 Task 6 是否能体面收口的核心风险。

## 验证记录

实际执行：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\graph -q`
   - 结果：通过
   - 摘要：`18 passed`

2. `.\backend\.venv\Scripts\python.exe -m ruff check backend\src\policymind\graph backend\tests\graph`
   - 结果：通过

补充说明：

- 当前测试证明：图谱提取、内存仓储、基础搜索和路径排序 helper 已可运行。
- 当前测试还不能证明：Neo4j 适配器满足租户隔离，也不能证明 Graph 搜索主链已经产出“带来源的已排序上下文”。

## 是否允许进入下一 Task

我建议 **先不要进入 Task 7**。

原因不是吹毛求疵，而是 Task 6 的对外说法现在还差最后两块硬骨头。把这两处补掉后，Task 6 就会从“已经有原型”变成“可以放心写进简历并演示”。
