import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 确保所有 ORM 模型表在测试数据库中创建
import policymind.auth.models  # noqa: F401
import policymind.documents.orm  # noqa: F401
from policymind.core.config import Settings
from policymind.infrastructure.postgres.base import Base
from policymind.infrastructure.postgres.session import get_db_session


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    # 启用 SQLite 外键约束
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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


@pytest.fixture
def app(db_session) -> FastAPI:
    from policymind.main import create_app

    app_inst = create_app(
        settings=Settings(
            JWT_SECRET="test-secret-key-for-testing-only-32chars",
            DATABASE_URL="sqlite+aiosqlite://",
        )
    )

    # 覆盖 session factory 为测试 session
    async def _override_get_db():
        yield db_session

    app_inst.dependency_overrides[get_db_session] = _override_get_db
    return app_inst


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        JWT_SECRET="test-secret-key-for-testing-only-32chars",
        DATABASE_URL="sqlite+aiosqlite://",
    )


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
