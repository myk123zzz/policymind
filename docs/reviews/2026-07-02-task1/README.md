# Task 1 审查报告

审查日期：2026-07-02

审查范围：

- `backend/pyproject.toml`
- `backend/src/policymind/__init__.py`
- `backend/src/policymind/main.py`
- `backend/tests/test_smoke.py`
- `.gitignore`
- `.env.example`
- `README.md`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)

## 结论

Task 1 已经完成了最小工程骨架，`policymind` 包、`create_app()`、`/health/live` 和基础 smoke test 都已经落地，提交也存在：`9d2b325 chore: bootstrap policymind`。

但目前还不能判定为“完全达标”。存在 2 个需要优先修复的问题：

1. `backend/src/policymind/main.py` 没有暴露模块级 `app`，与文档给出的启动命令不兼容。
2. 根目录 `README.md` 中声明的审查文档和运行手册链接当前不存在，文档导航不自洽。

此外，本次无法按文档原命令完成环境验证，因为当前机器缺少 `uv`，且未安装 Python 3.12。这一点不直接构成 Task 1 代码缺陷，但说明“本机可执行性”仍未被这次审查确认。

## 发现的问题

### 1. `uvicorn policymind.main:app` 目前无法按文档启动

- 严重性：高
- 位置：
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:4)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:84)

说明：

开发手册要求使用：

```powershell
uv run uvicorn policymind.main:app --reload
```

但当前 `main.py` 只定义了 `create_app()`，没有定义模块级 `app = create_app()`。这意味着即使依赖齐全，`uvicorn policymind.main:app` 也无法按文档约定找到应用对象。

影响：

- Task 1 的“工程可启动”目标没有被当前代码完整满足。
- 后续如果团队成员严格按文档启动，会直接失败。
- 测试虽然通过了 `create_app()` 路径，但没有覆盖文档要求的实际启动路径。

改进方向：

- 在 `main.py` 增加模块级 `app = create_app()`。
- 保留 `create_app()`，为后续测试注入 `settings/container` 预留接口。
- 新增一个针对模块级 `app` 的 smoke test，避免文档启动路径和测试路径再次分叉。

### 2. README 指向的审查与运行文档当前不存在

- 严重性：中
- 位置：
  - [README.md](/D:/policymind/README.md:30)
  - [README.md](/D:/policymind/README.md:35)
  - [README.md](/D:/policymind/README.md:36)
  - [README.md](/D:/policymind/README.md:37)

说明：

README 已经声明“审查发现的缺陷与后续修复，以 `docs/reviews/2026-07-02-task1-10/` 中的材料为准”，同时还链接了：

- `../reviews/2026-07-02-task1-10/README.md`
- `../reviews/2026-07-02-task1-10/remediation-plan.md`
- `../runbook.md`

但这些文件在当前仓库中不存在。

影响：

- 文档导航断裂，读者无法从 README 跳转到约定的材料。
- 以后你让我做“按文档审查”时，会出现基线引用失效，降低审查一致性。
- 容易给后续任务造成“文档已经补齐”的错觉。

改进方向：

- 如果这些文件还没准备好，先删除或标注“待创建”。
- 如果它们是本轮 Task 1 就要存在的项目入口材料，应立刻补齐最小版占位文档。
- 后续审查建议统一放在 `docs/reviews/` 下，并让 README 只链接真实存在的路径。

## 建议改进

除上面两个问题外，Task 1 还有几项值得尽早补强，虽然不一定阻塞当前提交：

1. 对齐 `create_app()` 签名  
   开发手册已经约定未来签名为：
   `create_app(settings: Settings | None = None, container: ServiceContainer | None = None) -> FastAPI`。  
   现在不一定要把依赖都实现完，但至少可以把函数签名预留出来，避免 Task 2 再改 public API。

2. 提前补 `/health/ready` 的占位实现或测试 TODO  
   开发手册已经把 `/health/live` 和 `/health/ready` 区分开了。Task 1 不一定要做完 readiness，但可以在测试或代码里明确注释，让后续任务少踩一脚“健康检查语义混淆”。

3. 用 `fastapi.testclient.TestClient` 代替 `starlette.testclient.TestClient`  
   当前测试可用，但项目已经以 FastAPI 为主，直接从 FastAPI 导入更贴近实际公共接口。

4. 明确开发环境要求  
   `backend/pyproject.toml` 要求 `>=3.12`，这和文档一致；但这次审查机器上只有 Python 3.10/3.13。建议在 README 或后续 runbook 里把“必须用 3.12”写得更醒目。

## 验证记录

已完成的静态检查：

- 阅读 Task 1 相关文件。
- 校对实现与文档约定的一致性。
- 确认存在提交：`9d2b325 chore: bootstrap policymind`。

未能完成的命令验证：

```powershell
uv run pytest
uv run ruff check src tests
uv run mypy src
```

原因：

- 当前环境中 `uv` 不在 PATH 上。
- 当前环境未安装 Python 3.12，仅发现 Python 3.10 和 3.13。

结论说明：

本报告中的“发现的问题”基于代码与文档的一致性审查，可以确认成立；但关于测试、ruff、mypy 是否在目标环境全部通过，本次无法独立复核。
