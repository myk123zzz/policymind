from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from policymind.auth.dependencies import RequestContext, get_current_context
from policymind.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserResponse,
)
from policymind.auth.service import AuthService
from policymind.core.config import Settings
from policymind.infrastructure.postgres.session import get_db_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _get_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(_get_settings),
) -> UserResponse:
    svc = AuthService(session, settings=settings)
    user = await svc.register(body)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(_get_settings),
) -> TokenPair:
    svc = AuthService(session, settings=settings)
    return await svc.authenticate(body.tenant_slug, body.username, body.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(_get_settings),
) -> TokenPair:
    svc = AuthService(session, settings=settings)
    return await svc.refresh(body.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(_get_settings),
) -> None:
    svc = AuthService(session, settings=settings)
    await svc.revoke(body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(_get_settings),
) -> UserResponse:
    from sqlalchemy import select

    from policymind.auth.models import User

    result = await session.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one()
    return UserResponse.model_validate(user)
