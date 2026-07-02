from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.auth.models import User
from policymind.auth.security import decode_token
from policymind.core.errors import AuthorizationDenied
from policymind.infrastructure.postgres.session import get_db_session

security_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class RequestContext:
    tenant_id: int
    user_id: int
    access_level: int
    role: str
    trace_id: str = ""


async def get_current_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> RequestContext:
    """解析 JWT 后再次查询用户，验证租户、启用状态、角色和 Token 版本。"""

    if not credentials:
        raise AuthorizationDenied("Missing authentication credentials.")

    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise AuthorizationDenied("Invalid or expired token.")

    user_id = int(str(payload["sub"]))
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthorizationDenied("User not found.")

    if not user.is_active:
        raise AuthorizationDenied("Account is disabled.")

    if user.token_version != payload.get("token_version", 0):
        raise AuthorizationDenied("Token has been revoked.")

    return RequestContext(
        tenant_id=user.tenant_id,
        user_id=user.id,
        access_level=user.access_level,
        role=user.role,
    )


def require_roles(*roles: str) -> "Callable[..., object]":
    """FastAPI RBAC 依赖：要求请求者具备指定角色之一。"""

    async def role_checker(
        ctx: RequestContext = Depends(get_current_context),
    ) -> RequestContext:
        if ctx.role not in roles:
            raise AuthorizationDenied("Insufficient permissions.")
        return ctx

    return role_checker
