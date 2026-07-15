# Task 1 第 2 次审查报告

审查日期：2026-07-02

审查目的：

- 复审 Task 1 对第一次审查意见的修复情况。
- 判断是否可以进入 Task 2。
- 按统一规则建立后续可持续使用的审查目录结构。

审查范围：

- `backend/src/policymind/main.py`
- `backend/tests/test_smoke.py`
- `README.md`
- `docs/reviews/`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 1 第 1 次审查报告](/D:/policymind/docs/reviews/task-01/review-01/README.md:1)

## 结论

第一次审查中阻塞 Task 1 收口的两个主要问题已经修复：

1. 已补充模块级 `app = create_app()`，文档中的 `uvicorn policymind.main:app` 路径已对齐。
2. 已修正根目录 `README.md` 对审查材料的引用，文档导航恢复自洽。

但本次复审仍发现 1 个需要先处理的问题：当前 `main.py` 为了提前对齐未来签名，引入了对尚不存在模块的类型引用，并使用了不准确的忽略标记。这很可能导致 Task 1 要求的 `mypy` 门禁失败。

结论判断：

- 不建议现在直接开始 Task 2。
- 先补掉下面这个问题，再进入 Task 2 会更稳。

## 发现的问题

### 1. `create_app()` 的前瞻类型引用很可能破坏当前的 `mypy` 门禁

- 严重性：高
- 位置：
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:5)
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:6)
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:7)
  - [backend/pyproject.toml](/D:/policymind/backend/pyproject.toml:34)

说明：

当前实现通过 `TYPE_CHECKING` 引入：

- `policymind.core.config.Settings`
- `policymind.core.container.ServiceContainer`

但这两个模块在当前仓库里还不存在，而且行内忽略写的是：

- `# type: ignore[import-untyped]`

这并不对应“模块不存在”这类错误。对于严格 `mypy` 配置，更可能触发的是 `import-not-found` 一类问题。也就是说，这个“为了给 Task 2 预留签名”的写法，可能反而让 Task 1 的门禁命令过不去。

影响：

- Task 1 的 `python -m mypy src` 可能失败。
- 这会让你在还没开始 Task 2 前，就带着一个未关闭的质量门禁问题往前走。
- 后续 Task 2 如果再引入真实的 `core/config.py` 和 `core/container.py`，你还得再回头确认这里的前瞻写法有没有副作用。

改进方向：

- 最稳的做法：把签名先收回到 `def create_app() -> FastAPI:`，等 Task 2 真正落地 `Settings` 和 `ServiceContainer` 后再扩展。
- 如果你坚持保留前瞻签名，就至少要改成当前 `mypy` 能接受的方式，并以真实门禁命令验证。
- 无论选哪条路，都建议补一个“门禁已实际跑通”的说明或截图依据。

## 已关闭的问题

### 1. 模块级 `app` 缺失

- 状态：已关闭
- 证据：
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:34)
  - [backend/tests/test_smoke.py](/D:/policymind/backend/tests/test_smoke.py:18)

### 2. README 审查链接失效

- 状态：已关闭
- 证据：
  - [README.md](/D:/policymind/README.md:35)

## 建议改进

1. Task 1 和 Task 2 的边界再收紧一点  
   现在 `main.py` 已经提前出现 Task 2 的类型名了。我的建议是，Task 1 尽量只完成 Task 1 要求的最小闭环，别太早把后续接口形状硬塞进来。

2. 复审通过后再开新 Task  
   这样每一阶段的失败原因会非常清楚，不会出现“是 Task 1 没收干净，还是 Task 2 新引入的问题”这种混战。

## 验证记录

已完成：

- 静态复核 `main.py`、`test_smoke.py`、`README.md`。
- 对照第一次审查报告确认问题关闭情况。
- 确认存在修复提交：`8cc1779 fix: add module-level app, /health/ready, align create_app signature, fix README links`。

本次仍未独立执行成功的命令：

```powershell
python -m pytest
python -m ruff check src tests
python -m mypy src
```

原因：

- 当前环境中的 Python 工具链尚未完整配置。
- 当前环境未安装 Python 3.12，仅发现 Python 3.10 和 3.13。

补充说明：

虽然这次没有在本机执行 `mypy`，但“引用了尚不存在模块且忽略码不匹配”这个问题本身已经足够明确，因此这里将其记为待关闭问题，而不是单纯的环境限制。

