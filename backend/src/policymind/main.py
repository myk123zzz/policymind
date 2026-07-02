from typing import TYPE_CHECKING

from fastapi import FastAPI

if TYPE_CHECKING:
    from policymind.core.config import Settings  # type: ignore[import-untyped]  # Task 2
    from policymind.core.container import ServiceContainer  # type: ignore[import-untyped]  # Task 2


def create_app(
    settings: "Settings | None" = None,
    container: "ServiceContainer | None" = None,
) -> FastAPI:
    """创建 FastAPI 应用实例。

    Args:
        settings: 应用配置，测试时可传入内存配置覆盖环境变量。
        container: 服务容器，测试时可传入内存适配器。
    """
    app = FastAPI(title="PolicyMind")

    @app.get("/health/live")
    async def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready() -> dict[str, str]:
        # TODO: Task 2+ 根据 settings 检查 PostgreSQL、Redis 等依赖是否就绪
        return {"status": "ok"}

    return app


app = create_app()
