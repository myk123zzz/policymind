from fastapi import FastAPI


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。

    Task 2 将扩展为 create_app(settings, container) 以支持依赖注入。
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
