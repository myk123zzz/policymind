# Task 4 第 1 次审查报告

审查日期：2026-07-04

审查范围：

- `backend/src/policymind/documents/{pipeline,jobs,router,orm}.py`
- `backend/migrations/versions/8e99a887d676_ingestion_jobs.py`
- `backend/tests/documents/{test_pipeline,test_router}.py`
- `backend/src/policymind/main.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)

## Findings

### 1. 上传接口并没有真正接收文件、做校验、写对象存储或调用解析器，当前只是“写几条元数据然后跑空 pipeline”

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:15)
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:31)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:362)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:159)

文档要求的 Task 4 是“上传到可检索链路”，核心应该是：

- 接收上传文件
- 校验上传
- 写对象存储
- 写文档版本记录
- 创建摄取任务
- 跑解析/分块/后续索引链路

但当前 `/api/v1/documents` 接口只接收一个 JSON body：

- `content_hash`
- `storage_key`
- `mime_type`

然后直接把这些字段写进 `DocumentVersion`，并同步调用 pipeline。  
这里没有真实文件输入，也没有调用 `validate_upload()`、`ObjectStorage.put()`、`ParserRegistry.parse()`。

影响：

- 这还不是“上传链路接通”，而是“手动提供已知元数据，绕过上传过程”。
- 文档里强调的上传安全、对象存储、解析入口都还没真正接进来。

改进方向：

- 把接口改成真正接收上传文件，至少支持 multipart 上传。
- 在接口或服务层串起 `validate_upload()`、对象存储写入和版本记录创建。
- 后续 pipeline 只消费已经真实落库的 `document_version`，而不是消费调用方手工拼出的元数据。

### 2. `IngestionPipeline` 的阶段函数几乎全部是 `pass`，状态机会前进，但没有真实副作用

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:87)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:97)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:101)
  - [backend/src/policymind/documents/pipeline.py](/D:/policymind/backend/src/policymind/documents/pipeline.py:104)

`IngestionPipeline.run()` 现在确实会把状态从：

`queued -> stored -> parsed -> chunked -> embedded -> vector_indexed -> graph_indexed -> ready`

一路推进到 `ready`。  
但 `_execute_stage()` 里的逻辑几乎全是 `pass`，包括最该在 Task 4 完成的：

- `stored`
- `parsed`
- `chunked`

影响：

- 这是典型的“状态真走了，事情没做”的假闭环。
- 测试现在只验证“状态机会前进”，并没有验证“内容真的被解析/分块/可检索”。
- 这和开发手册里禁止的“上传接口只返回预览、没写入知识库”和“假完成”是同一类风险。

改进方向：

- 至少把 Task 4 范围内的 `stored / parsed / chunked` 做成真实逻辑。
- `embedded / vector_indexed / graph_indexed` 可以继续留给 Task 5/6，但应明确降级为未执行而不是假装完成。
- 测试需要断言实际产物，而不只是 `processing_status == ready`。

### 3. `ArqJobRunner` 仍然是 `NotImplementedError`，`ingest_document_job()` 也没有正确拿到 session

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/jobs.py](/D:/policymind/backend/src/policymind/documents/jobs.py:23)
  - [backend/src/policymind/documents/jobs.py](/D:/policymind/backend/src/policymind/documents/jobs.py:32)
  - [backend/src/policymind/documents/jobs.py](/D:/policymind/backend/src/policymind/documents/jobs.py:36)

Task 4 文档要求测试可用 inline runner，生产用 ARQ，共享同一 pipeline。  
当前状态是：

- `InlineJobRunner` 能跑
- `ArqJobRunner.enqueue()` 直接 `NotImplementedError`
- `ingest_document_job()` 把 `session_factory: object` 直接传给 `IngestionPipeline(session_factory)`，类型和实际依赖都不对

影响：

- 目前只存在“测试/开发模式同步调用”。
- 生产异步任务入口还没真正形成。
- 一旦后面切 ARQ，这里会立刻露馅。

改进方向：

- 把 `ArqJobRunner` 至少做成最小可工作的 enqueue 壳。
- `ingest_document_job()` 要从 `session_factory` 正确创建 `AsyncSession`，而不是把 factory 当 session 传进去。

### 4. 文档接口仍然把 `tenant_id` 固定写成 1，没有接上认证上下文

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:36)
  - [backend/src/policymind/documents/router.py](/D:/policymind/backend/src/policymind/documents/router.py:53)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:137)

当前文档路由里：

- `Document.tenant_id = 1`
- `IngestionJob.tenant_id = 1`

这直接绕过了 Task 2 刚做好的认证/租户边界。

影响：

- 文档主链还没有进入真正的多租户语义。
- 后续你很容易在“认证是多租户的，文档却是固定 tenant=1”的分裂状态里继续堆代码。

改进方向：

- 文档接口接入 `RequestContext` / `get_current_context`。
- 所有文档和任务记录都从上下文拿 `tenant_id`，不要再写死。

### 5. 测试覆盖的是“状态推进”和“202 返回”，还没有覆盖 Task 4 最重要的真实闭环

- 严重性：中
- 位置：
  - [backend/tests/documents/test_pipeline.py](/D:/policymind/backend/tests/documents/test_pipeline.py:31)
  - [backend/tests/documents/test_router.py](/D:/policymind/backend/tests/documents/test_router.py:4)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:159)

文档里写的 Task 4 关键 E2E 是：

- 上传 Markdown
- 等待任务完成
- 随后检索必须命中其内容

当前测试只验证：

- status code 是 202
- pipeline 最后能走到 `ready`
- job 状态会更新

没有验证：

- 文件真实存储
- parser 真实执行
- chunk 真实产出
- 后续检索路径能看到内容

影响：

- 测试对“假闭环”几乎没有辨识力。

改进方向：

- 至少补一个集成测试，证明上传内容经过解析和分块后，能在持久层或下游可见。
- 如果 Task 5 还没接检索，也可以先验证解析/分块产物真实存在，而不是只看状态字段。

## Open Questions / Assumptions

- 我把 Task 4 的目标理解为“真实接通上传→解析→分块主链”，不是仅仅建立状态机和 jobs 表。
- 允许 `embedded / vector_indexed / graph_indexed` 在 Task 4 暂时不做完，但不应伪装成已执行。

## Change Summary

这轮已经做出来的东西：

- `ingestion_jobs` 迁移
- 文档路由和 job 查询入口
- pipeline / jobs 基础骨架
- 与主 app 的路由集成

这些是有价值的，但更像“Task 4 的框架搭起来了”，还不是文档要求的真实闭环。

## 验证记录

实际执行结果：

1. `conda run -n policymind python -m pytest`
   - 结果：通过
   - 摘要：`61 passed`

2. `conda run -n policymind python -m ruff check src tests`
   - 结果：通过

3. `conda run -n policymind python -m mypy src`
   - 结果：通过

补充观察：

- `pytest` 通过并不代表 Task 4 已按文档完成；当前测试对“真实副作用”覆盖明显不足。

