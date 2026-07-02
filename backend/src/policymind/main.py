from fastapi import FastAPI


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    app = FastAPI(title="PolicyMind")

    @app.get("/health/live")
    async def health_live() -> dict[str, str]:
        return {"status": "ok"}

    return app
