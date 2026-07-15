# Task 4 第 2 次审查报告

审查日期：2026-07-04

审查目的：

- 复审 [Task 4 第 1 次审查报告](/D:/policymind/docs/reviews/task-04/review-01/README.md:1) 中提出的问题。
- 判断 Task 4 是否已经达到可收口状态。

审查范围：

- `backend/src/policymind/documents/{router,pipeline,jobs}.py`
- `backend/tests/documents/{test_router,test_pipeline}.py`
- `backend/tests/conftest.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 4 第 1 次审查报告](/D:/policymind/docs/reviews/task-04/review-01/README.md:1)

## 结论

上一次审查里的几个大问题，这次已经明显向前推进：

1. 文档接口已经改成真实文件上传，不再只是接 JSON 元数据。
2. 上传链路已经调用上传校验、本地对象存储和 pipeline。
3. 路由层已经接上 `RequestContext`，文档与 job 记录不再固定 `tenant_id = 1`。
4. pipeline 已经在 `stored / parsed / chunked` 阶段执行真实副作用，而不是全 `pass`。
5. 测试也从“只看状态字段”推进到了“上传 Markdown 文件并走完整主链”的方向。

本次在你的真实环境里实际跑通了：

- `conda run -n policymind python -m pytest`
- `conda run -n policymind python -m ruff check src tests`
- `conda run -n policymind python -m mypy src`

但是，这一轮我仍然不建议直接把 Task 4 判定为完全收口。  
主要还剩 2 个比较实在的问题：

1. pipeline 内部仍有硬编码 `tenant_id=1`。
2. router / pipeline 仍直接硬绑定 `LocalObjectStorage("./data/")`，没有真正走可替换的存储适配器。

## 已关闭的问题

### 1. 上传接口不是实际上传文件

- 状态：已关闭
- 证据：
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:24)
  - [backend/tests/documents/test_router.py](/D:/policymind/backend/tests/documents/test_router.py:17)

说明：

接口现在接收 `UploadFile`，并通过 `files=...` 走 multipart 上传路径，不再依赖调用方手工提供 `content_hash / storage_key / mime_type`。

### 2. pipeline 阶段全是 `pass`

- 状态：大体关闭
- 证据：
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:124)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:131)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:142)

说明：

`stored / parsed / chunked` 三个 Task 4 范围内最关键的阶段，现在已经开始做真实动作：

- 校验对象存储存在
- 调用 parser
- 调用 chunker

### 3. 文档链路固定 `tenant_id = 1`

- 状态：部分关闭
- 证据：
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:27)
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:55)
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:75)

说明：

路由层已经不再固定写死 tenant，而是从 `RequestContext` 取值。  
但 pipeline 内部在 `ChunkContext` 里仍有 `tenant_id=1`，所以这里只能算“部分关闭”。

## Findings

### 1. pipeline 在 chunk 阶段仍把 `tenant_id` 硬编码为 `1`

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:150)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:152)

虽然路由已经接上 `RequestContext`，但 pipeline 在构造 `ChunkContext` 时仍然写的是：

```python
tenant_id=1
```

影响：

- 文档主链依然没有完全进入真实多租户语义。
- 现在如果两个租户都上传文档，chunk 层的 tenant 信息会失真。

改进方向：

- 从 `DocumentVersion -> Document` 或任务上下文里拿真实 `tenant_id`。
- 补一条测试，验证不同租户上传后 chunk context 的 tenant 值不会串。

### 2. router 和 pipeline 都直接绑定 `LocalObjectStorage("./data/")`，没有真正使用可替换适配器

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:44)
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:46)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:55)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:127)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:168)

当前实现虽然把文件真的写进了对象存储，但写死了：

- 存储实现：`LocalObjectStorage`
- 路径：`./data/`

影响：

- 这和 Task 3 刚做好的 `S3ObjectStorage`、抽象 `ObjectStorage` 没有真正接起来。
- 后续你切 S3/MinIO 时，还得回头改 router 和 pipeline，而不是只换配置/适配器。

改进方向：

- 把 storage 作为依赖注入到 router / pipeline，至少通过 app state 或 container 传递。
- 测试里再 override 为本地存储，生产再接本地或 S3。

## Remaining Risk

### 1. `test_upload_rejects_invalid` 仍然通过 `pytest.raises(ValueError)` 验证接口行为，不是标准 API 响应测试

- 严重性：低
- 位置：
  - [backend/tests/documents/test_router.py](/D:/policymind/backend/tests/documents/test_router.py:38)

说明：

这个测试现在还是在断言接口调用直接抛 Python 异常，而不是断言一个明确的 HTTP 4xx 响应。  
它不一定会立刻出错，但会让接口契约测试看起来有点“半服务层、半路由层”。

## Change Summary

这轮修复已经让 Task 4 从“骨架版状态机”推进到“真实上传 + 真实 parse/chunk 主链初步打通”的状态。

但从 reviewer 角度看，还差最后一段基础设施接线：

- 把 tenant 真正传到 pipeline/chunk
- 把 storage 真正抽象成可替换依赖

## 验证记录

实际执行结果：

1. `conda run -n policymind python -m pytest`
   - 结果：通过
   - 摘要：`62 passed`

2. `conda run -n policymind python -m ruff check src tests`
   - 结果：通过

3. `conda run -n policymind python -m mypy src`
   - 结果：通过

补充说明：

- 并发执行 `conda run` 仍可能出现临时文件竞争错误；顺序重跑后门禁通过。

