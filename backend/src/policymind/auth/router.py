from fastapi import APIRouter, Depends
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
from policymind.infrastructure.postgres.session import get_db_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    svc = AuthService(session)
    user = await svc.register(body)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPair:
    svc = AuthService(session)
    return await svc.authenticate(body.tenant_slug, body.username, body.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPair:
    svc = AuthService(session)
    return await svc.refresh(body.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    svc = AuthService(session)
    await svc.revoke(body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(
    ctx: RequestContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    from sqlalchemy import select

    from policymind.auth.models import User

    result = await session.execute(select(User).where(User.id == ctx.user_id))
    user = result.scalar_one()
    return UserResponse.model_validate(user)
