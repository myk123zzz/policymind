import pytest_asyncio
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.auth.models import Tenant, User
from policymind.auth.security import create_access_token, hash_password
from policymind.core.config import Settings


@pytest_asyncio.fixture
async def auth_tenant(db_session: AsyncSession) -> Tenant:
    t = Tenant(name="router-test", slug="router-test")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def active_user(db_session: AsyncSession, auth_tenant: Tenant) -> User:
    u = User(
        tenant_id=auth_tenant.id,
        username="active",
        password_hash=hash_password(SecretStr("pass123")),
        role="employee",
        access_level=1,
        is_active=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def disabled_user(db_session: AsyncSession, auth_tenant: Tenant) -> User:
    u = User(
        tenant_id=auth_tenant.id,
        username="disabled",
        password_hash=hash_password(SecretStr("pass123")),
        role="employee",
        access_level=1,
        is_active=False,
    )
    db_session.add(u)
    await db_session.flush()
    return u


def token_for(user: User, settings: Settings | None = None) -> str:
    return create_access_token(
        data={"sub": str(user.id), "tenant_id": user.tenant_id, "role": user.role},
        settings=settings,
    )


def test_login_returns_tokens(
    client: TestClient, db_session: AsyncSession, auth_tenant: Tenant, active_user: User
) -> None:
    """登录成功返回 access_token 和 refresh_token。"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": auth_tenant.slug,
            "username": "active",
            "password": "pass123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_invalid_credentials_returns_401(
    client: TestClient, auth_tenant: Tenant
) -> None:
    """错误密码返回 401。"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": auth_tenant.slug,
            "username": "active",
            "password": "wrong",
        },
    )
    assert response.status_code == 401


def test_auth_me_returns_user_info(
    client: TestClient, active_user: User, test_settings: Settings
) -> None:
    """认证后 /auth/me 返回当前用户信息。"""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_for(active_user, test_settings)}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "active"
    assert data["role"] == "employee"


def test_disabled_user_cannot_reuse_token(
    client: TestClient, disabled_user: User, test_settings: Settings
) -> None:
    """禁用用户的 Token 立即失效。"""
    token = token_for(disabled_user, test_settings)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_auth_me_without_token_returns_401(client: TestClient) -> None:
    """无 Token 访问 /auth/me 返回 401。"""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_login_disabled_user_returns_401(
    client: TestClient, auth_tenant: Tenant, disabled_user: User
) -> None:
    """禁用用户登录返回 401。"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": auth_tenant.slug,
            "username": "disabled",
            "password": "pass123",
        },
    )
    assert response.status_code == 401
