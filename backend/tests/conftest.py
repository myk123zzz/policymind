import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import policymind.auth.models  # noqa: F401
import policymind.documents.orm  # noqa: F401
from policymind.core.config import Settings
from policymind.infrastructure.postgres.base import Base
from policymind.infrastructure.postgres.session import get_db_session

TEST_JWT_SECRET = "test-secret-key-for-testing-only-32chars"


@pytest.fixture(autouse=True)
def _reset_test_env():
    """每个测试前重置环境变量 + 清除 settings 缓存。"""
    os.environ["JWT_SECRET"] = TEST_JWT_SECRET
    from policymind.core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragma(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.begin()
        yield session
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def _seed_test_user(db_session):
    """确保测试数据库中存在 user id=1，供 auth 验证使用。"""
    from pydantic import SecretStr

    from policymind.auth.models import Tenant, User
    from policymind.auth.security import hash_password

    existing = await db_session.execute(select(Tenant).where(Tenant.id == 1))
    if not existing.scalar_one_or_none():
        t = Tenant(id=1, name="test", slug="test-tenant")
        db_session.add(t)

    existing_user = await db_session.execute(select(User).where(User.id == 1))
    if not existing_user.scalar_one_or_none():
        u = User(
            id=1,
            tenant_id=1,
            username="testuser",
            password_hash=hash_password(SecretStr("testpass")),
            role="employee",
            access_level=1,
            is_active=True,
        )
        db_session.add(u)
    await db_session.flush()


@pytest.fixture
def app(db_session) -> FastAPI:
    from policymind.main import create_app

    app_inst = create_app(
        settings=Settings(
            JWT_SECRET=TEST_JWT_SECRET,
            DATABASE_URL="sqlite+aiosqlite://",
        )
    )

    async def _override_get_db():
        yield db_session

    app_inst.dependency_overrides[get_db_session] = _override_get_db
    return app_inst


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        JWT_SECRET=TEST_JWT_SECRET,
        DATABASE_URL="sqlite+aiosqlite://",
    )


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
