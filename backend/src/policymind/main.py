from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from policymind.agents.graph import PolicyAgentRuntime
from policymind.api.v1.chat import router as chat_router
from policymind.api.v1.graph import router as graph_router
from policymind.api.v1.reviews import router as reviews_router
from policymind.auth.router import router as auth_router
from policymind.core.config import Settings, get_settings
from policymind.core.errors import PolicyMindError
from policymind.core.logging import setup_logging
from policymind.documents.router import router as documents_router
from policymind.graph.repository import MemoryGraphRepository
from policymind.infrastructure.postgres.session import (
    create_engine,
    create_session_factory,
)


def create_app(
    settings: Settings | None = None,
) -> FastAPI:
    if settings is None:
        settings = get_settings()

    setup_logging()

    app = FastAPI(title="PolicyMind")
    app.state.settings = settings

    engine = create_engine(settings.DATABASE_URL)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    # 共享 Agent runtime（Chat + Reviews + HITL 共享状态）
    app.state.agent_runtime = PolicyAgentRuntime()
    # 共享 Graph repository（Graph API 使用）
    app.state.graph_repo = MemoryGraphRepository()

    # Mount all API routers
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(chat_router)
    app.include_router(reviews_router)
    app.include_router(graph_router)

    @app.get("/health/live")
    async def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready() -> dict[str, object]:
        """检查核心依赖就绪状态。不可用时返回 503。"""
        deps: dict[str, str] = {}
        try:
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            deps["database"] = "ok"
        except Exception:
            deps["database"] = "unavailable"

        all_ok = all(v == "ok" for v in deps.values())
        status_code = 200 if all_ok else 503
        return JSONResponse(  # type: ignore[return-value]
            status_code=status_code,
            content={"status": "ok" if all_ok else "degraded", "dependencies": deps},
        )

    @app.exception_handler(PolicyMindError)
    async def policy_mind_error_handler(
        request: Request, exc: PolicyMindError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.public_message},
        )

    return app


app = create_app()
