# Task 3 第 2 次审查报告

审查日期：2026-07-02

审查目的：

- 复审 [Task 3 第 1 次审查报告](/D:/policymind/docs/reviews/task-03/review-01/README.md:1) 中提出的问题。
- 判断 Task 3 是否可以收口并进入下一任务。

审查范围：

- `backend/src/policymind/documents/{models,storage,validation,chunking}.py`
- `backend/src/policymind/documents/parsers/{pdf,docx,xlsx,registry}.py`
- `backend/tests/documents/{test_storage,test_validation,test_chunking,test_parsers}.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 3 第 1 次审查报告](/D:/policymind/docs/reviews/task-03/review-01/README.md:1)

## 结论

上一次审查提出的主要结构性问题，大部分已经正面修复：

1. 已补 `PDF / DOCX / XLSX` parser。
2. `ObjectStorage` 与 `LocalObjectStorage` 已统一为异步接口。
3. 已引入 `ChunkContext`，并把生效时间字段传递到 `Chunk`。
4. Office 文件校验已增加 ZIP 内部结构检查。

本次在你的真实环境里实际跑通了：

- `conda run -n policymind uv run pytest`
- `conda run -n policymind uv run ruff check src tests`
- `conda run -n policymind uv run mypy src`

但我这次仍然不建议直接把 Task 3 判为完全收口。还剩 2 个比较实在的问题：

1. `S3ObjectStorage` 只有类壳子，方法全部 `NotImplementedError`。
2. 新增的 `PDF / DOCX / XLSX` parser 几乎没有对应测试，当前测试仍主要覆盖 Markdown parser。

## 已关闭的问题

### 1. 仅有 Markdown parser / 本地存储

- 状态：部分关闭
- 证据：
  - [backend/src/policymind/documents/parsers/pdf.py](/D:/policymind/backend/src/policymind/documents/parsers/pdf.py:9)
  - [backend/src/policymind/documents/parsers/docx.py](/D:/policymind/backend/src/policymind/documents/parsers/docx.py:9)
  - [backend/src/policymind/documents/parsers/xlsx.py](/D:/policymind/backend/src/policymind/documents/parsers/xlsx.py:9)
  - [backend/src/policymind/documents/storage.py](/D:/policymind/backend/src/policymind/documents/storage.py:47)

说明：

Parser 维度已经不再只有 Markdown，这一点算明显进步。  
但 `S3ObjectStorage` 仍然只是占位定义，没有真正可运行的实现，所以这里我标记为“部分关闭”。

### 2. `ObjectStorage` 协议和实现分叉

- 状态：已关闭
- 证据：
  - [backend/src/policymind/documents/storage.py](/D:/policymind/backend/src/policymind/documents/storage.py:6)
  - [backend/src/policymind/documents/storage.py](/D:/policymind/backend/src/policymind/documents/storage.py:23)
  - [backend/tests/documents/test_storage.py](/D:/policymind/backend/tests/documents/test_storage.py:20)

### 3. `Chunk` 缺少生效时间字段

- 状态：已关闭
- 证据：
  - [backend/src/policymind/documents/models.py](/D:/policymind/backend/src/policymind/documents/models.py:25)
  - [backend/tests/documents/test_chunking.py](/D:/policymind/backend/tests/documents/test_chunking.py:111)

### 4. `HierarchicalChunker` 没有收敛到 context 输入

- 状态：已关闭
- 证据：
  - [backend/src/policymind/documents/chunking.py](/D:/policymind/backend/src/policymind/documents/chunking.py:18)
  - [backend/src/policymind/documents/models.py](/D:/policymind/backend/src/policymind/documents/models.py:25)

### 5. Office ZIP 结构未检查

- 状态：已关闭
- 证据：
  - [backend/src/policymind/documents/validation.py](/D:/policymind/backend/src/policymind/documents/validation.py:89)

## Findings

### 1. `S3ObjectStorage` 仍然只是占位类，不是可工作的适配器

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/storage.py](/D:/policymind/backend/src/policymind/documents/storage.py:47)
  - [backend/src/policymind/documents/storage.py](/D:/policymind/backend/src/policymind/documents/storage.py:62)
  - [docs/policymind/2026-07-01-policymind-implementation.md](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:137)

当前 `S3ObjectStorage` 虽然已经定义出来了，但 `put/get/delete` 全部直接抛 `NotImplementedError`。  
从 reviewer 视角，这仍然不能算“已提供 `S3ObjectStorage`”，只能算“预留了类名和构造参数”。

影响：

- 只要后续服务切到 S3/MinIO 路径，就会立刻失败。
- 这和 Task 3 文档中的“提供 `LocalObjectStorage` 与 `S3ObjectStorage`”还有差距。

改进方向：

- 实现最小可运行的 S3/MinIO 适配器。
- 如果你想把真正连云端的事情推到后面，也至少要在文档或任务边界里明确说明“Task 3 仅完成接口壳，Task 4 才完成生产适配器”。

### 2. 新增 parser 缺少对应测试，当前测试并不能证明 PDF / DOCX / XLSX 路径真的可用

- 严重性：高
- 位置：
  - [backend/src/policymind/documents/parsers/pdf.py](/D:/policymind/backend/src/policymind/documents/parsers/pdf.py:1)
  - [backend/src/policymind/documents/parsers/docx.py](/D:/policymind/backend/src/policymind/documents/parsers/docx.py:1)
  - [backend/src/policymind/documents/parsers/xlsx.py](/D:/policymind/backend/src/policymind/documents/parsers/xlsx.py:1)
  - [backend/tests/documents/test_parsers.py](/D:/policymind/backend/tests/documents/test_parsers.py:1)

`test_parsers.py` 现在仍然只覆盖：

- Markdown parser
- ParserRegistry 对 Markdown 的解析

并没有真正测试：

- PDF 是否能提取文本
- DOCX 是否能提取段落/标题
- XLSX 是否能提取表格
- registry 是否能正确注册并解析这些 MIME

影响：

- 新 parser 代码虽然存在，但目前没有可靠测试来证明它们可用。
- 例如 `pdf.py` 里直接用了 `# mypy: ignore-errors`，这更说明它需要行为测试兜底。

改进方向：

- 为 PDF / DOCX / XLSX 分别补最小样本测试。
- 至少补一条 registry 集成测试，覆盖 4 类 MIME 的解析路径。

## Remaining Risk

### 1. Office ZIP 校验目前仍然偏弱，只检查了 `[Content_Types].xml`

- 严重性：低
- 位置：
  - [backend/src/policymind/documents/validation.py](/D:/policymind/backend/src/policymind/documents/validation.py:101)

这次已经不再是“完全没做”，但现在对 `.docx` 和 `.xlsx` 都只要求 `[Content_Types].xml`。  
如果想更贴近文档里的“结构校验”，还可以再补：

- DOCX 要求 `word/`
- XLSX 要求 `xl/`

这次我不把它当阻塞项，因为你已经从“没有内部结构检查”推进到了“有最小内部结构检查”。

## Change Summary

这次修复把 Task 3 从“只有 Markdown 路径可用”拉到了“多格式骨架基本齐全”的状态：

- parser 种类补齐了
- 存储接口契约对齐了
- chunk 上下文和生效时间打通了
- Office 校验也不再完全裸奔

但如果按 reviewer 的较严标准，Task 3 还差最后一口气：把 `S3ObjectStorage` 做成真适配器，并给新增 parser 补上测试证明。

## 验证记录

实际执行结果：

1. `conda run -n policymind uv run pytest`
   - 结果：通过
   - 摘要：`51 passed`

2. `conda run -n policymind uv run ruff check src tests`
   - 结果：通过

3. `conda run -n policymind uv run mypy src`
   - 结果：通过

补充说明：

- 并发执行 `conda run` 仍会出现临时文件竞争错误；顺序重跑后门禁通过。
