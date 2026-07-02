from unittest.mock import patch

import pytest


def test_production_refuses_default_jwt_secret() -> None:
    """生产环境必须拒绝默认 JWT Secret。"""
    from policymind.core.config import Settings, validate_production_settings

    settings = Settings(
        APP_ENV="production",
        JWT_SECRET="change-me",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
    )
    with pytest.raises(ValueError, match="JWT_SECRET"):
        validate_production_settings(settings)


def test_production_refuses_wildcard_cors_with_credentials() -> None:
    """生产环境下 Credentials 和通配 CORS 不能共存。"""
    from policymind.core.config import Settings, validate_production_settings

    settings = Settings(
        APP_ENV="production",
        JWT_SECRET="a-real-secret-key-that-is-at-least-32-chars-long",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        CORS_ORIGINS=["*"],
    )
    with pytest.raises(ValueError, match="CORS"):
        validate_production_settings(settings)


def test_get_settings_caches_result() -> None:
    """get_settings() 必须使用 lru_cache 缓存配置。"""
    from policymind.core.config import get_settings

    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_settings_loads_from_env() -> None:
    """Settings 能从环境变量读取。"""
    from policymind.core.config import Settings

    with patch.dict("os.environ", {"JWT_SECRET": "env-secret", "DATABASE_URL": "sqlite://"}):
        settings = Settings()
        assert settings.JWT_SECRET == "env-secret"
