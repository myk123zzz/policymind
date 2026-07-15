# Task 2 第 2 次审查报告

审查日期：2026-07-02

审查目的：

- 复审 [Task 2 第 1 次审查报告](/D:/policymind/docs/reviews/task-02/review-01/README.md:1) 中提出的问题。
- 判断 Task 2 是否可以收口并进入下一任务。

审查范围：

- `backend/src/policymind/auth/{service,security,dependencies,router}.py`
- `backend/src/policymind/infrastructure/postgres/session.py`
- `backend/src/policymind/main.py`
- `backend/src/policymind/core/{config,logging}.py`
- `backend/tests/conftest.py`
- `backend/tests/auth/{test_service,test_router}.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)
- [Task 2 第 1 次审查报告](/D:/policymind/docs/reviews/task-02/review-01/README.md:1)

## 结论

上一次审查里提出的 5 个问题中，前 4 个核心实现问题已经明显修复：

1. 注册不再硬编码 `tenant_id = 1`，而是通过邀请码解析租户。
2. 数据库会话和 JWT 路径已经接入应用级 `settings`。
3. engine / session factory 已提升到应用级状态，不再按请求反复创建销毁。
4. 领域错误响应不再把 `detail` 直接暴露给客户端。

此外，本次在你的真实环境里实际跑通了：

- `conda run -n policymind python -m pytest`
- `conda run -n policymind python -m ruff check src tests`
- `conda run -n policymind python -m mypy src`

结论判断：

- Task 2 可以收口。
- 可以进入下一任务。

## 已关闭的问题

### 1. `register()` 硬编码租户主键

- 状态：已关闭
- 证据：
  - [backend/src/policymind/auth/service.py](/D:/policymind/backend/src/policymind/auth/service.py:33)
  - [backend/tests/auth/test_service.py](/D:/policymind/backend/tests/auth/test_service.py:43)
  - [backend/tests/conftest.py](/D:/policymind/backend/tests/conftest.py:27)

说明：

注册现在通过 `invite-<slug>` 解析租户，并补上了有效邀请码 / 无效邀请码测试；SQLite 外键也已在测试环境中开启，不再掩盖租户引用问题。

### 2. `create_app(settings=...)` 注入没有真正影响核心路径

- 状态：已关闭
- 证据：
  - [backend/src/policymind/auth/router.py](/D:/policymind/backend/src/policymind/auth/router.py:19)
  - [backend/src/policymind/auth/dependencies.py](/D:/policymind/backend/src/policymind/auth/dependencies.py:27)
  - [backend/src/policymind/auth/security.py](/D:/policymind/backend/src/policymind/auth/security.py:25)

说明：

路由层已经从 `request.app.state.settings` 取配置，并把它传入 `AuthService` / JWT 编解码路径，这次不是“看起来支持注入”了。

### 3. 每请求重建数据库 engine

- 状态：已关闭
- 证据：
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:31)
  - [backend/src/policymind/infrastructure/postgres/session.py](/D:/policymind/backend/src/policymind/infrastructure/postgres/session.py:22)

说明：

`create_app()` 现在在应用级创建 engine 和 `session_factory`，`get_db_session()` 只负责从应用状态中取 session。

### 4. 领域异常把 `detail` 直接返回客户端

- 状态：已关闭
- 证据：
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:46)

说明：

当前响应只返回 `code` 和 `message`，已经不再把内部 detail 直接暴露出去。

## Remaining Risk

### 1. `setup_logging()` 仍然走全局 `get_settings()`，和新的应用级配置注入还没有完全统一

- 严重性：低
- 位置：
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:26)
  - [backend/src/policymind/core/logging.py](/D:/policymind/backend/src/policymind/core/logging.py:4)
  - [backend/src/policymind/core/logging.py](/D:/policymind/backend/src/policymind/core/logging.py:8)

说明：

`main.py` 已经接受显式 `settings`，但 `setup_logging()` 内部还是重新调用全局 `get_settings()`。这意味着当你构造一个带自定义 `settings` 的 app 实例时，日志级别不一定跟这个 app 的配置完全一致。

为什么这次我不把它算成阻塞：

- 它不会破坏 Task 2 的认证、租户边界或数据库行为。
- 本次测试、ruff、mypy 全部通过，没有表现出直接功能性故障。
- 它更像是配置注入链条里剩下的一小截尾巴，适合在后续整理 app/container 时顺手收掉。

改进方向：

- 让 `setup_logging()` 接受显式 `settings` 参数。
- 或者把 logging 初始化也并入未来的应用容器 / 启动生命周期里，避免再回读全局缓存配置。

## Change Summary

这次修复把 Task 2 从“能跑但有几处假注入/假边界”拉到了“基础认证闭环基本可信”的状态：

- 注册、登录、刷新、登出、`/auth/me` 已形成完整最小链路。
- 配置注入已经真正打通到 JWT 和数据库会话。
- 测试基线比上次更可靠，SQLite 外键约束已开启。

## 验证记录

实际执行结果：

1. `conda run -n policymind python -m pytest`
   - 结果：通过
   - 摘要：`31 passed`

2. `conda run -n policymind python -m ruff check src tests`
   - 结果：通过

3. `conda run -n policymind python -m mypy src`
   - 结果：通过

补充观察：

- `pytest` 仍有 warning，主要来自 `datetime.utcnow()` 弃用和上游 `TestClient/httpx` 提示；当前不构成 Task 2 阻塞项。

