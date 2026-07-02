# Task 2 第 1 次审查报告

审查日期：2026-07-02

审查范围：

- `backend/src/policymind/core/config.py`
- `backend/src/policymind/core/errors.py`
- `backend/src/policymind/core/logging.py`
- `backend/src/policymind/infrastructure/postgres/{base,session}.py`
- `backend/src/policymind/auth/{models,schemas,security,service,dependencies,router}.py`
- `backend/src/policymind/main.py`
- `backend/migrations/versions/fe0076a9184f_foundation.py`
- `backend/tests/core/test_config.py`
- `backend/tests/auth/{test_security,test_service,test_router}.py`
- `backend/tests/conftest.py`

审查基线：

- [详细开发手册](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:1)
- [TASK 1-10实施计划](/D:/policymind/docs/policymind/2026-07-01-policymind-implementation.md:1)

## Findings

### 1. `register()` 把租户固定写死为 `tenant_id = 1`，测试却因为 SQLite 外键未开启而没暴露这个问题

- 严重性：高
- 位置：
  - [backend/src/policymind/auth/service.py](/D:/policymind/backend/src/policymind/auth/service.py:24)
  - [backend/src/policymind/auth/service.py](/D:/policymind/backend/src/policymind/auth/service.py:27)
  - [backend/tests/auth/test_service.py](/D:/policymind/backend/tests/auth/test_service.py:68)
  - [backend/tests/conftest.py](/D:/policymind/backend/tests/conftest.py:22)

`AuthService.register()` 当前没有解析邀请码，也没有查租户，而是直接把新用户写到 `tenant_id = 1`。这不只是“先占位”，而是会在真实 PostgreSQL 下直接依赖“数据库里刚好有 id=1 的租户”这个偶然条件。  
更糟的是，当前测试环境使用 SQLite，并且没有启用外键约束，所以 `test_register_*` 会通过，掩盖了生产行为与测试行为不一致的问题。

影响：

- 一旦数据库里没有 `id=1` 的租户，注册会在真实环境直接失败。
- 这不满足 Task 2 “tenant_id 来自邀请码/服务端边界，而不是隐式常量”的要求。
- 当前测试对这个风险没有防护，后续改坏也不容易第一时间被发现。

改进方向：

- 至少先把邀请码解析为明确的租户查找流程，即使是临时实现，也应基于真实租户记录而不是硬编码主键。
- 在测试数据库里开启 SQLite foreign keys，或者补一个集成测试，确保“引用不存在租户时注册失败”能被测出来。
- 去掉 `assert user.tenant_id == 1` 这类把错误行为写成预期的测试。

### 2. `create_app(settings=...)` 的设置注入并没有真正影响数据库和鉴权路径

- 严重性：高
- 位置：
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:12)
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:28)
  - [backend/src/policymind/infrastructure/postgres/session.py](/D:/policymind/backend/src/policymind/infrastructure/postgres/session.py:5)
  - [backend/src/policymind/infrastructure/postgres/session.py](/D:/policymind/backend/src/policymind/infrastructure/postgres/session.py:17)
  - [backend/src/policymind/auth/security.py](/D:/policymind/backend/src/policymind/auth/security.py:8)

`create_app()` 看起来支持传入 `settings`，但实际数据库会话和 JWT 逻辑都继续直接调用全局 `get_settings()`。也就是说，`app.state.settings = settings` 只是存起来了，核心依赖并不会用它。

影响：

- 代码表面上支持依赖注入，实际上核心路径仍然依赖全局缓存配置。
- 这违背了开发手册里“测试通过依赖注入覆盖，不修改全局环境”的约束。
- 后续 Task 里如果想做多环境测试、不同 DB/密钥配置的 app 实例并行运行，会非常别扭。

改进方向：

- 把数据库会话工厂和鉴权/签名所需配置真正接入 `create_app()` 或容器层，而不是继续从全局缓存兜底。
- 至少先统一一条原则：运行时配置要么全走 app/container 注入，要么明确当前阶段不支持注入，不要停在半真半假的状态。

### 3. 每个请求都新建并销毁一次数据库 engine，会把连接池和应用生命周期都绕开

- 严重性：中
- 位置：
  - [backend/src/policymind/infrastructure/postgres/session.py](/D:/policymind/backend/src/policymind/infrastructure/postgres/session.py:15)
  - [backend/src/policymind/infrastructure/postgres/session.py](/D:/policymind/backend/src/policymind/infrastructure/postgres/session.py:18)
  - [backend/src/policymind/infrastructure/postgres/session.py](/D:/policymind/backend/src/policymind/infrastructure/postgres/session.py:28)

`get_db_session()` 每次请求都 `create_async_engine(...)`，结束后再 `dispose()`。这会让连接池完全失去意义，也把数据库资源管理从应用生命周期退化成了“按请求反复建拆”。

影响：

- 性能和稳定性都会受影响，尤其是在登录、鉴权请求增多时。
- 后续一旦引入更多 repository/service，请求时延会被这个模式放大。
- 这也让 readiness、迁移、长连接诊断更难做，因为 engine 没有稳定归属。

改进方向：

- 把 engine/sessionmaker 提升到应用级或容器级单例。
- `get_db_session()` 只负责从已有 `sessionmaker` 取 session，不负责建 engine。
- 测试继续通过 override 注入 session 生成器，生产运行则走共享工厂。

### 4. 领域异常响应把 `detail` 直接返回给客户端，和文档要求不一致

- 严重性：中
- 位置：
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:46)
  - [backend/src/policymind/main.py](/D:/policymind/backend/src/policymind/main.py:55)
  - [docs/policymind/DEVELOPMENT_GUIDE.md](/D:/policymind/docs/policymind/DEVELOPMENT_GUIDE.md:270)

开发手册要求 FastAPI 异常处理只返回公开信息和 `trace_id`。当前实现把 `exc.detail` 直接回给客户端。对认证接口来说，这相当于把内部失败原因当成外部 API 协议的一部分。

影响：

- 容易把内部实现细节暴露给调用方。
- 后面如果把更多领域错误挂到同一个 handler，下意识塞进去的 detail 可能会越来越敏感。
- 和文档约定已经发生偏差，后续前后端会围绕错误负载形成错误依赖。

改进方向：

- 对外只返回稳定的公开字段，例如 `code`、`message`、`trace_id`。
- 详细异常原因写日志，不进公共响应。

### 5. 生产配置校验只检查了 JWT 和 CORS，遗漏了“缺失依赖 URL 应拒绝启动”的约束

- 严重性：中
- 位置：
  - [backend/src/policymind/core/config.py](/D:/policymind/backend/src/policymind/core/config.py:50)
  - [backend/tests/core/test_config.py](/D:/policymind/backend/tests/core/test_config.py:6)

文档写的是“拒绝默认 JWT、弱密码、通配 CORS 和缺失依赖 URL”。现在 `validate_production_settings()` 只覆盖了 JWT 和 CORS，没有对数据库、对象存储、模型服务等关键依赖的 URL/凭据做校验。

影响：

- 应用可能在“生产配置不完整”的情况下照样启动，直到运行时才暴露故障。
- 这会把本该启动期暴露的问题拖到请求期。

改进方向：

- 明确 Task 2 阶段哪些依赖是“生产必需”的，并在校验里显式检查。
- 为这些校验补对应测试，不要只停留在 JWT/CORS 两条。

## Open Questions / Assumptions

- 我假设当前 `invitation_token` 允许是临时方案，但即使如此，也不应退化为硬编码租户主键。
- 我把 SQLite 外键未开启视为测试基线问题，因为它已经直接掩盖了 `register()` 的真实风险。
- `pytest`、`ruff`、`mypy` 本次都通过了，所以这里的结论不是“代码跑不通”，而是“实现与架构约束之间还有真实偏差”。

## Change Summary

本次 Task 2 已经把基础认证链路跑起来了：

- Alembic foundation migration 已创建。
- `Tenant` / `User` / `RefreshToken` 模型已落地。
- 登录、刷新、登出、`/auth/me` 和基础鉴权依赖都已接通。
- 在你的真实环境里，本次实际跑通了：
  - `conda run -n policymind uv run pytest`
  - `conda run -n policymind uv run ruff check src tests`
  - `conda run -n policymind uv run mypy src`

但从 reviewer 视角看，还不建议把 Task 2 直接判为完全收口，至少应先处理前两条高优先级问题。

## 验证记录

实际执行结果：

1. `conda run -n policymind uv run pytest`
   - 结果：通过
   - 摘要：`30 passed`

2. `conda run -n policymind uv run ruff check src tests`
   - 结果：通过

3. `conda run -n policymind uv run mypy src`
   - 结果：通过

补充观察：

- `pytest` 过程中出现若干 warning，包括 `datetime.utcnow()` 弃用和 `TestClient/httpx` 的上游弃用提示；这些当前不构成阻塞问题，但后续可以顺手清理。
