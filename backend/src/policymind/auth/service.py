import hashlib
from datetime import UTC, datetime, timedelta

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.auth.models import RefreshToken, Tenant, User
from policymind.auth.schemas import RegisterRequest, TokenPair
from policymind.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from policymind.core.errors import AuthorizationDenied


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, request: RegisterRequest) -> User:
        """注册新用户；tenant_id 来自邀请码，不允许自行指定。"""
        # 模拟从邀请码解析租户（Task 3+ 实现真实邀请系统）
        tenant_id = 1  # default tenant for now

        # 检查用户名在租户内唯一
        result = await self.session.execute(
            select(User).where(
                User.tenant_id == tenant_id, User.username == request.username
            )
        )
        if result.scalar_one_or_none():
            raise AuthorizationDenied("Username already exists in this tenant.")

        user = User(
            tenant_id=tenant_id,
            username=request.username,
            password_hash=hash_password(request.password),
            role="employee",  # 不允许注册时自行指定角色
            access_level=1,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def authenticate(
        self, tenant_slug: str, username: str, password: SecretStr
    ) -> TokenPair:
        """验证凭证并返回 Token 对。"""
        # 查找租户
        tenant_result = await self.session.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        tenant: Tenant | None = tenant_result.scalar_one_or_none()
        if not tenant:
            raise AuthorizationDenied("Invalid credentials.")

        # 查找用户
        user_result = await self.session.execute(
            select(User).where(
                User.tenant_id == tenant.id, User.username == username
            )
        )
        user: User | None = user_result.scalar_one_or_none()
        if not user:
            raise AuthorizationDenied("Invalid credentials.")

        if not user.is_active:
            raise AuthorizationDenied("Account is disabled.")

        if not verify_password(password, user.password_hash):
            raise AuthorizationDenied("Invalid credentials.")

        return await self._issue_tokens(user)

    async def refresh(self, refresh_token_str: str) -> TokenPair:
        """使用 Refresh Token 获取新 Token 对；旧 Refresh Token 撤销。"""
        # 解码并验证
        try:
            payload = decode_token(refresh_token_str)
        except ValueError:
            raise AuthorizationDenied("Invalid refresh token.")

        if payload.get("type") != "refresh":
            raise AuthorizationDenied("Invalid token type.")

        token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
        token_result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,  # noqa: E712
            )
        )
        stored: RefreshToken | None = token_result.scalar_one_or_none()
        if not stored:
            raise AuthorizationDenied("Refresh token revoked or not found.")

        # 撤销旧 token
        stored.revoked = True

        # 查找用户
        user_id = int(str(payload["sub"]))
        user_result = await self.session.execute(select(User).where(User.id == user_id))
        user: User | None = user_result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthorizationDenied("User not found or disabled.")

        return await self._issue_tokens(user)

    async def revoke(self, refresh_token_str: str) -> None:
        """撤销 Refresh Token。"""
        token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored:
            stored.revoked = True
            await self.session.flush()

    async def _issue_tokens(self, user: User) -> TokenPair:
        token_data = {
            "sub": str(user.id),
            "tenant_id": user.tenant_id,
            "role": user.role,
            "access_level": user.access_level,
            "token_version": user.token_version,
        }
        access_token = create_access_token(data=token_data)
        refresh_token_str = create_refresh_token(data=token_data)

        # 存储 refresh token 哈希
        rt = RefreshToken(
            user_id=user.id,
            token_hash=hashlib.sha256(refresh_token_str.encode()).hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        self.session.add(rt)
        await self.session.flush()

        return TokenPair(access_token=access_token, refresh_token=refresh_token_str)
