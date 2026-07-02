
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from policymind.auth.router import router as auth_router
from policymind.core.config import Settings, get_settings
from policymind.core.errors import PolicyMindError
from policymind.core.logging import setup_logging
from policymind.infrastructure.postgres.session import (
    create_engine,
    create_session_factory,
)


def create_app(
    settings: Settings | None = None,
) -> FastAPI:
    """创建 FastAPI 应用实例。

    Args:
        settings: 应用配置，测试时传入覆盖环境变量。
    """
    if settings is None:
        settings = get_settings()

    setup_logging()

    app = FastAPI(title="PolicyMind")
    app.state.settings = settings

    # 创建应用级 engine 和 session factory
    engine = create_engine(settings.DATABASE_URL)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    app.include_router(auth_router)

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
            },
        )

    return app


app = create_app()
