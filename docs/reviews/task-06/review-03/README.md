# Task 6 第 3 次审查报告

审查日期：2026-07-11

审查范围：
- `backend/src/policymind/graph/{repository,search,path_ranker}.py`
- `backend/src/policymind/infrastructure/neo4j/repository.py`
- `backend/tests/graph/{test_repository,test_search}.py`

审查基线：
- [开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [审查报告目录规范](/D:/policymind/docs/reviews/README.md:1)
- 上一轮报告：[task-06/review-02](/D:/policymind/docs/reviews/task-06/review-02/README.md:1)

## 结论

这轮我判断 **Task 6 可以通过**，允许进入下一 Task。

上轮拦住的两件核心事，这次都已经补上了：

- `GraphSearchService.search()` 已接入 `rank_paths()`，并把来源信息拼进了 context。
- `Neo4jGraphRepository` 的写入和路径查询都显式带上了 `tenant_id` 约束，不再只是限制起点。

按你现在这套“简历项目、不过度卡小毛病”的标准，Task 6 已经达到了可以放心写成“实现了本地图谱检索与带来源的 GraphRAG 路径返回”的程度。

## 已关闭问题

### 1. Graph 搜索主链已接入排序与来源上下文

- 位置：
  - [backend/src/policymind/graph/search.py](/D:/policymind/backend/src/policymind/graph/search.py:22)
  - [backend/src/policymind/graph/path_ranker.py](/D:/policymind/backend/src/policymind/graph/path_ranker.py:6)

现在 `search()` 已经：

- 接收 `query`
- 调用 `rank_paths(paths, query=query)`
- 返回排序后的 `paths`
- 在 context 中输出 `relations` 和 `sources`

这说明上一轮“helper 在、主链没接上”的问题已经关掉了。

### 2. Neo4j 租户隔离已补到查询入口

- 位置：
  - [backend/src/policymind/infrastructure/neo4j/repository.py](/D:/policymind/backend/src/policymind/infrastructure/neo4j/repository.py:14)
  - [backend/src/policymind/infrastructure/neo4j/repository.py](/D:/policymind/backend/src/policymind/infrastructure/neo4j/repository.py:53)

当前实现已经做到：

- 节点 `MERGE` 按 `(id, tenant_id)` 建身份
- 关系创建按同租户端点匹配
- 路径查询要求整条路径上的节点和关系都满足 `tenant_id`

这已经越过了文档里关于 Cypher 租户边界的核心要求。

## 可改进但不阻塞

### 1. 内存仓储的实体键仍按 `id` 存储，和生产隔离模型还没完全对齐

- 严重性：低
- 位置：
  - [backend/src/policymind/graph/repository.py](/D:/policymind/backend/src/policymind/graph/repository.py:33)

`MemoryGraphRepository._entities` 现在仍是 `dict[str, dict[str, object]]`，`upsert()` 也是直接用 `id` 当 key。也就是说，如果两个租户用了相同实体 ID，后写入的实体会覆盖前一个。

这轮我不把它当阻塞项，原因是：

- 你现在真正的租户隔离风险点在 Neo4j 生产适配器，那里已经补上了。
- 这个问题更多是“测试适配器和生产模型的一致性”问题，不是当前简历演示链路的硬伤。

改进方向：
- 后面可把内存仓储键改成 `(tenant_id, id)`。
- 补一条相同实体 ID 跨租户的回归测试，让 memory 和 Neo4j 的行为更一致。

### 2. 搜索测试还可以更直接验证 service 层排序结果

- 严重性：低
- 位置：
  - [backend/tests/graph/test_search.py](/D:/policymind/backend/tests/graph/test_search.py:1)

当前测试已经覆盖了：

- `rank_paths()` 的 query 匹配
- `GraphSearchService` 会构建 context

但还没有一条测试直接断言：`GraphSearchService.search()` 返回的 `paths` 顺序确实受 `rank_paths()` 控制。

这也不阻塞当前通过，只是后面补上会更稳。

## 验证记录

实际执行：

1. `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\graph -q`
   - 结果：通过
   - 摘要：`19 passed`

2. `.\backend\.venv\Scripts\python.exe -m ruff check backend\src\policymind\graph backend\src\policymind\infrastructure\neo4j backend\tests\graph`
   - 结果：通过

## 是否允许进入下一 Task

**允许进入 Task 7。**

如果你想让 Task 6 再更漂亮一点，优先补内存仓储跨租户同 ID 的一致性测试；但不补也不会影响你现在继续推进主线。
