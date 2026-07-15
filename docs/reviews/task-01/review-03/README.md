# Task 1 第 3 次审查报告

审查日期：2026-07-02

审查目的：

- 复审 Task 1 第 2 次审查中遗留的问题。
- 判断 Task 1 是否可以正式收口并进入 Task 2。

审查范围：

- `backend/src/policymind/main.py`
- `backend/tests/test_smoke.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 1 第 2 次审查报告](/D:/policymind/docs/reviews/task-01/review-02/README.md:1)

## 结论

Task 1 第 2 次审查中指出的阻塞问题已经修复：

- `create_app()` 已收回到 Task 1 需要的最小签名。
- 已移除对尚不存在模块的前瞻类型引用。
- 模块级 `app`、`/health/live`、`/health/ready` 与 smoke tests 保持一致。

本次审查未发现新的阻塞问题。

结论判断：

- Task 1 可以收口。
- 可以开始 Task 2。

## 已关闭的问题

### 1. `create_app()` 的前瞻类型引用可能破坏 `mypy` 门禁

- 状态：已关闭
- 证据：
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:4)
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:7)

说明：

当前 `create_app()` 已恢复为：

```python
def create_app() -> FastAPI:
```

不再引用尚未在 Task 2 中实现的 `Settings` 或 `ServiceContainer`，因此不会继续把 Task 2 的未落地接口带回 Task 1。

## 发现的问题

本次复审未发现新的代码问题。

## 改进方向

进入 Task 2 时建议保持这条边界：

1. 先落地 `core.config`、数据库会话与认证基础设施，再扩展 `create_app(settings, container)`。
2. 新增 `create_app()` 参数时，同步补测试，覆盖默认启动路径和测试注入路径。
3. Task 2 一开始就跑认证相关红灯测试，避免把配置、数据库和鉴权一起糊成一团。

## 验证记录

已完成：

- 静态复核 `main.py` 与 `test_smoke.py`。
- 确认存在修复提交：`0e4ef8d fix: remove forward type refs from main.py, keep Task 1 minimal`。
- 对照第 2 次审查报告确认阻塞问题已关闭。

未完成：

```powershell
python -m pytest
python -m ruff check src tests
python -m mypy src
```

原因：

- 当前环境中的 Python 工具链尚未完整配置。
- 当前环境未安装 Python 3.12，仅发现 Python 3.10 和 3.13。

说明：

虽然本次仍未在当前机器独立复跑门禁命令，但第 2 次审查中指出的静态阻塞点已明确移除，因此不再作为阻塞 Task 2 的理由。

