# Task 3 第 1 次审查报告

审查日期：2026-07-02

审查范围：

- `backend/src/policymind/documents/{models,orm,validation,storage,chunking}.py`
- `backend/src/policymind/documents/parsers/{registry,markdown}.py`
- `backend/migrations/versions/cc8cc4ae3f94_documents.py`
- `backend/tests/documents/{test_validation,test_storage,test_parsers,test_chunking}.py`
- `backend/pyproject.toml`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)

## Findings

### 1. Task 3 计划要求的 PDF / DOCX / XLSX parser 和 `S3ObjectStorage` 还没实现，当前只完成了 Markdown parser 与本地存储

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/parsers/markdown.py](/D:/policymind/backend/src/policymind/documents/parsers/markdown.py:6)
  - [backend/src/policymind/documents/storage.py](/D:/policymind/backend/src/policymind/documents/storage.py:11)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:136)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:137)

Task 3 的计划写得很明确：要实现 `PDF / DOCX / XLSX / Markdown Parser`，并提供 `LocalObjectStorage` 与 `S3ObjectStorage`。当前仓库里只有 `MarkdownParser` 和 `LocalObjectStorage`，没有看到其余 parser，也没有 `S3ObjectStorage`。

影响：

- 现在的交付范围还不足以支撑“versioned multimodal documents”这个 Task 标题。
- 你在 `pyproject.toml` 里已经引入了 `pymupdf`、`python-docx`、`openpyxl`，但实现还没真正接上，容易造成“依赖在、能力已交付”的错觉。

改进方向：

- 至少补齐 PDF / DOCX / XLSX 的最小 parser，实现并测试 registry 能按 MIME 解析。
- 补 `S3ObjectStorage` 的实现或明确标注它还未完成，别让 Task 3 在接口层假装已经闭环。

### 2. `ObjectStorage` 协议定义为异步，但 `LocalObjectStorage` 实现成了同步方法，接口契约已经分叉

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/storage.py](/D:/policymind/backend/src/policymind/documents/storage.py:5)
  - [backend/src/policymind/documents/storage.py](/D:/policymind/backend/src/policymind/documents/storage.py:23)
  - [backend/src/policymind/documents/storage.py](/D:/policymind/backend/src/policymind/documents/storage.py:28)
  - [backend/src/policymind/documents/storage.py](/D:/policymind/backend/src/policymind/documents/storage.py:34)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:349)

`ObjectStorage` protocol 约定的是：

```python
async def put(...)
async def get(...)
async def delete(...)
```

但 `LocalObjectStorage` 实际实现成了普通同步方法。现在测试当然能过，因为测试直接按同步方法调用；可一旦后续服务代码按 protocol 期待 `await storage.put(...)`，这里就会直接错位。

影响：

- 接口契约和实现不一致，后续接 `DocumentService` 或 ingestion pipeline 时很容易出运行时错误。
- 这属于典型的“测试通过但集成会炸”的类型。

改进方向：

- 统一成真正的异步接口，哪怕内部只是线程池或同步封装，也要在外部契约上保持一致。
- 测试也改成按异步接口调用，别继续放大这个分叉。

### 3. `Chunk` 模型缺少文档要求的 `effective_from` / `effective_to`，后续检索时间过滤无法落地

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/models.py](/D:/policymind/backend/src/policymind/documents/models.py:24)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:174)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:186)

开发手册定义的 `Chunk` 明确包含：

- `effective_from: datetime`
- `effective_to: datetime | None`

当前 dataclass 里没有这两个字段。

影响：

- Task 5 的检索过滤会直接依赖文档生效时间，这里不补，后面只能再返工改 chunk 契约。
- 这也让 Task 3 里“多版本生效区间”的能力只停留在 ORM 层，没有进入 chunk 领域模型。

改进方向：

- 把时间范围字段补到 `Chunk` 模型，并在 chunking / 测试里传递下去。
- 如果暂时还拿不到值，也应该在 chunk 创建入口明确要求传入，避免以后到处补默认值。

### 4. `HierarchicalChunker` 的输入输出契约仍然偏实现方便，不符合文档约定的 `ChunkContext` / 来源信息要求

- 严重性：中
- 位置：
  - [backend/src/policymind/documents/chunking.py](/D:/policymind/backend/src/policymind/documents/chunking.py:18)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:392)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:146)

文档里 `chunk()` 预期接收 `ChunkContext`，并强调 leaf chunk 要保留 parent、页码、bbox 和来源版本。当前实现是把 `document_version_id`、`tenant_id`、`document_id` 散着传，而且 `Chunk` 模型里也没有文档计划示例里提到的 `source_version_id` 一类显式来源字段。

影响：

- 现在的 API 还能工作，但可扩展性一般，后面一旦再塞生效时间、权限、文档元数据，参数会继续散开。
- 和文档约定已经出现偏差，后面很容易形成“测试和真实服务各走一套输入”的局面。

改进方向：

- 尽早收敛到一个 context 对象，把版本、租户、文档、权限和时间范围打包。
- 测试也改成围绕这个 context 验证，不要继续用零散参数撑着。

### 5. 上传校验对 Office 文件的 ZIP 内部结构还没有做验证，未满足文档里的安全要求

- 严重性：中
- 位置：
  - [backend/src/policymind/documents/validation.py](/D:/policymind/backend/src/policymind/documents/validation.py:78)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:341)

开发手册明确写了：Office 文件要进一步检查 ZIP 内部结构，不能只看到 `PK` 就认定合法。当前 `validate_upload()` 只靠扩展名、声明 MIME 和 `filetype.guess()`，没有检查 DOCX/XLSX 容器内部是否真符合 Office 结构。

影响：

- 对 Office 文件的校验仍然偏弱，和文档安全要求不一致。
- 后续 parser 一旦接上，这个弱校验会直接成为入口风险。

改进方向：

- 在校验层补最小结构检查，例如 DOCX 要求 `[Content_Types].xml`、`word/`，XLSX 要求 `xl/` 等。
- 为这些结构校验补对应测试。

## Open Questions / Assumptions

- 我把这次的重点放在“Task 3 是否已按文档完成”，不是单纯看当前测试是否为绿。
- 这批代码质量并不差，尤其 Markdown parser、随机 storage key、基础 chunk provenance 都做了，但范围还不足以判定 Task 3 已收口。

## Change Summary

当前 Task 3 已完成的部分：

- `documents` 领域模型和 ORM 雏形
- 文档版本迁移
- Markdown parser 与 parser registry
- 本地对象存储
- 基础上传校验
- 基础 parent/leaf chunking

但从 reviewer 视角看，它更像是 “Task 3 的第一段纵切”，还不是文档所要求的完整 Task 3 交付。

## 验证记录

实际执行结果：

1. `conda run -n policymind uv run pytest`
   - 结果：通过
   - 摘要：`49 passed`

2. `conda run -n policymind uv run ruff check src tests`
   - 结果：通过

3. `conda run -n policymind uv run mypy src`
   - 结果：通过

补充说明：

- 并发执行 `conda run` 时出现了临时文件竞争错误；顺序重跑后 `ruff` 和 `mypy` 均通过。
