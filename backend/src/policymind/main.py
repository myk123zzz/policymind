from collections.abc import AsyncGenerator, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.auth.router import router as auth_router
from policymind.core.config import Settings, get_settings
from policymind.core.errors import PolicyMindError


def create_app(
    settings: Settings | None = None,
    get_session: Callable[
        [], AsyncGenerator[AsyncSession, None]
    ] | None = None,
) -> FastAPI:
    """创建 FastAPI 应用实例。

    Args:
        settings: 应用配置，测试时传入覆盖环境变量。
        get_session: 数据库会话工厂，测试时传入固定 session 的生成器。
    """
    app = FastAPI(title="PolicyMind")

    app.include_router(auth_router)

    if settings is None:
        settings = get_settings()
    app.state.settings = settings

    # 注入数据库会话依赖
    if get_session is not None:
        from policymind.infrastructure.postgres.session import get_db_session

        app.dependency_overrides[get_db_session] = get_session

    @app.get("/health/live")
    async def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(PolicyMindError)
    async def policy_mind_error_handler(
        request: Request, exc: PolicyMindError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.public_message,
                "detail": exc.detail,
            },
        )

    return app


app = create_app()
