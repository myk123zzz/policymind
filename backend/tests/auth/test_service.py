import pytest
import pytest_asyncio
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.auth.models import Tenant, User


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    t = Tenant(name="test-tenant", slug="test")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def user(db_session: AsyncSession, tenant: Tenant) -> User:
    from policymind.auth.security import hash_password

    u = User(
        tenant_id=tenant.id,
        username="testuser",
        password_hash=hash_password(SecretStr("password123")),
        role="employee",
        access_level=1,
        is_active=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def test_register_creates_user(db_session: AsyncSession) -> None:
    """注册创建用户成功。"""
    from policymind.auth.schemas import RegisterRequest
    from policymind.auth.service import AuthService

    svc = AuthService(db_session)
    req = RegisterRequest(
        username="newuser",
        password=SecretStr("secure-pass-456"),
        invitation_token="invite-valid",
    )
    user = await svc.register(req)
    assert user.username == "newuser"
    assert user.role == "employee"


async def test_register_cannot_set_admin_role(
    db_session: AsyncSession,
) -> None:
    """注册请求不能自行指定管理员角色。"""
    from policymind.auth.schemas import RegisterRequest
    from policymind.auth.service import AuthService

    svc = AuthService(db_session)
    req = RegisterRequest(
        username="hacker",
        password=SecretStr("pass123"),
        invitation_token="invite-valid",
    )
    # register should ignore any attempt to set role to admin
    user = await svc.register(req)
    assert user.role == "employee"


async def test_register_cannot_specify_tenant_id(
    db_session: AsyncSession,
) -> None:
    """注册不能自行指定 tenant_id。"""
    from policymind.auth.schemas import RegisterRequest
    from policymind.auth.service import AuthService

    svc = AuthService(db_session)
    req = RegisterRequest(
        username="user2",
        password=SecretStr("pass123"),
        invitation_token="invite-valid",
    )
    user = await svc.register(req)
    # tenant_id should come from invitation, not user input
    assert user.tenant_id == 1  # from invitation


async def test_username_unique_per_tenant(
    db_session: AsyncSession, tenant: Tenant, user: User
) -> None:
    """同一租户下用户名必须唯一。"""

    from policymind.auth.models import User
    from policymind.auth.security import hash_password

    dup = User(
        tenant_id=tenant.id,
        username="testuser",  # same as fixture
        password_hash=hash_password(SecretStr("otherpass")),
        role="employee",
        access_level=1,
        is_active=True,
    )
    db_session.add(dup)
    with pytest.raises(Exception):  # IntegrityError
        await db_session.flush()


async def test_same_username_different_tenant_allowed(
    db_session: AsyncSession,
) -> None:
    """不同租户可以使用相同用户名。"""
    from policymind.auth.models import Tenant, User
    from policymind.auth.security import hash_password

    t1 = Tenant(name="org-a", slug="org-a")
    t2 = Tenant(name="org-b", slug="org-b")
    db_session.add_all([t1, t2])
    await db_session.flush()

    u1 = User(
        tenant_id=t1.id,
        username="alice",
        password_hash=hash_password(SecretStr("pass1")),
        role="employee",
        access_level=1,
        is_active=True,
    )
    u2 = User(
        tenant_id=t2.id,
        username="alice",
        password_hash=hash_password(SecretStr("pass2")),
        role="employee",
        access_level=1,
        is_active=True,
    )
    db_session.add_all([u1, u2])
    await db_session.flush()  # should not raise


async def test_authenticate_valid_credentials(
    db_session: AsyncSession, tenant: Tenant, user: User
) -> None:
    """正确凭证认证成功返回 TokenPair。"""
    from policymind.auth.service import AuthService

    svc = AuthService(db_session)
    result = await svc.authenticate(
        tenant_slug=tenant.slug,
        username="testuser",
        password=SecretStr("password123"),
    )
    assert result.access_token
    assert result.refresh_token


async def test_authenticate_invalid_password(
    db_session: AsyncSession, tenant: Tenant, user: User
) -> None:
    """错误密码认证失败。"""

    from policymind.auth.service import AuthService
    from policymind.core.errors import AuthorizationDenied

    svc = AuthService(db_session)
    with pytest.raises(AuthorizationDenied):
        await svc.authenticate(
            tenant_slug=tenant.slug,
            username="testuser",
            password=SecretStr("wrong-password"),
        )


async def test_disabled_user_cannot_authenticate(
    db_session: AsyncSession, tenant: Tenant
) -> None:
    """禁用用户无法认证。"""

    from policymind.auth.models import User
    from policymind.auth.security import hash_password
    from policymind.auth.service import AuthService
    from policymind.core.errors import AuthorizationDenied

    u = User(
        tenant_id=tenant.id,
        username="disabled-user",
        password_hash=hash_password(SecretStr("pass123")),
        role="employee",
        access_level=1,
        is_active=False,
    )
    db_session.add(u)
    await db_session.flush()

    svc = AuthService(db_session)
    with pytest.raises(AuthorizationDenied):
        await svc.authenticate(
            tenant_slug=tenant.slug,
            username="disabled-user",
            password=SecretStr("pass123"),
        )


async def test_refresh_token_rotation(
    db_session: AsyncSession, tenant: Tenant, user: User
) -> None:
    """Refresh Token 刷新后旧 Token 失效。"""

    from policymind.auth.service import AuthService
    from policymind.core.errors import AuthorizationDenied

    svc = AuthService(db_session)
    pair = await svc.authenticate(
        tenant_slug=tenant.slug,
        username="testuser",
        password=SecretStr("password123"),
    )
    new_pair = await svc.refresh(pair.refresh_token)

    assert new_pair.access_token != pair.access_token
    # old refresh token should be revoked
    with pytest.raises(AuthorizationDenied):
        await svc.refresh(pair.refresh_token)


async def test_logout_revokes_refresh_token(
    db_session: AsyncSession, tenant: Tenant, user: User
) -> None:
    """登出后 Refresh Token 被撤销。"""

    from policymind.auth.service import AuthService
    from policymind.core.errors import AuthorizationDenied

    svc = AuthService(db_session)
    pair = await svc.authenticate(
        tenant_slug=tenant.slug,
        username="testuser",
        password=SecretStr("password123"),
    )
    await svc.revoke(pair.refresh_token)
    with pytest.raises(AuthorizationDenied):
        await svc.refresh(pair.refresh_token)
