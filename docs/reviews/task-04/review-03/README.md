# Task 4 第 3 次审查报告

审查日期：2026-07-05

审查目的：

- 复审 [Task 4 第 2 次审查报告](/D:/policymind/docs/reviews/task-04/review-02/README.md:1) 中剩余的问题。
- 判断 Task 4 是否可以正式收口。

审查范围：

- `backend/src/policymind/documents/{router,pipeline}.py`
- `backend/tests/documents/test_pipeline.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 4 第 2 次审查报告](/D:/policymind/docs/reviews/task-04/review-02/README.md:1)

## 结论

Task 4 第 2 次审查中剩余的两个高优先级问题已经修复：

1. pipeline 不再把 `tenant_id` 硬编码成 `1`，而是通过 `DocumentVersion -> Document` 解析真实租户。
2. router 和 pipeline 都已经支持注入 `ObjectStorage`，不再直接把业务链路硬绑死在 `LocalObjectStorage("./data/")` 上。

本次在你的真实环境里实际跑通了：

- `conda run -n policymind uv run pytest`
- `conda run -n policymind uv run ruff check src tests`
- `conda run -n policymind uv run mypy src`

结论判断：

- Task 4 可以收口。
- 可以进入下一任务。

## 已关闭的问题

### 1. pipeline 硬编码 `tenant_id = 1`

- 状态：已关闭
- 证据：
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:106)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:132)

说明：

当前 pipeline 通过 `_get_tenant_id()` 从 `DocumentVersion` 关联的 `Document` 查询真实租户，再写入 `ChunkContext`。

### 2. router / pipeline 硬绑定本地存储实现

- 状态：已关闭
- 证据：
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:19)
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:38)
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:85)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:44)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:47)

说明：

现在 router 通过 `_get_storage()` 从 `app.state` 解析存储适配器，pipeline 也接受显式 `storage` 注入。虽然默认值仍然是本地存储，但链路已经不再被写死。

## Findings

本次复审未发现新的阻塞问题。

## Remaining Risk

### 1. `_get_tenant_id()` 在查不到 `Document` 时回退到 `1`，这个兜底偏宽松

- 严重性：低
- 位置：
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:106)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:111)

说明：

当前实现里，如果按 `document_id` 没查到 `Document`，会返回 `1`。  
在现有正常链路里这不太会发生，因为 `DocumentVersion` 是刚由路由层创建的；所以这次我不把它算成 Task 4 阻塞项。  
但从洁癖一点的角度说，更稳妥的做法是直接抛错，而不是回退到默认租户。

## Change Summary

这轮修复把 Task 4 最后两段基础设施接线补齐了：

- 多租户信息从路由真正传到 pipeline / chunk 层
- 存储从“本地实现硬绑定”推进到“可替换适配器注入”

从 reviewer 视角，Task 4 到这里已经可以判定收口。

## 验证记录

实际执行结果：

1. `conda run -n policymind uv run pytest`
   - 结果：通过
   - 摘要：`62 passed`

2. `conda run -n policymind uv run ruff check src tests`
   - 结果：通过

3. `conda run -n policymind uv run mypy src`
   - 结果：通过

补充说明：

- 并发执行 `conda run` 仍可能出现临时文件竞争错误；顺序重跑后门禁通过。
