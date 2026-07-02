from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    JWT_SECRET: str = "change-me"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "sqlite+aiosqlite:///policymind.db"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    REDIS_URL: str = ""
    MILVUS_HOST: str = ""
    MILVUS_PORT: int = 19530
    NEO4J_URI: str = ""
    NEO4J_USER: str = ""
    NEO4J_PASSWORD: str = ""
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    EMBEDDING_MODEL: str = ""
    RERANK_MODEL: str = ""
    MCP_SERVER_URL: str = ""


@lru_cache
def get_settings() -> Settings:
    """读取并校验环境配置；测试通过依赖注入覆盖，不修改全局环境。"""
    settings = Settings()
    if settings.APP_ENV == "production":
        validate_production_settings(settings)
    return settings


def validate_production_settings(settings: Settings) -> None:
    """拒绝默认 JWT、弱密码、通配 CORS 和缺失依赖 URL。"""
    if settings.JWT_SECRET == "change-me":
        raise ValueError("JWT_SECRET must not be default in production")
    if len(settings.JWT_SECRET) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters in production")
    if "*" in settings.CORS_ORIGINS:
        raise ValueError("CORS_ORIGINS must not contain wildcard '*' in production")
