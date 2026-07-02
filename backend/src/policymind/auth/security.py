import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import SecretStr

if TYPE_CHECKING:
    from policymind.core.config import Settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: SecretStr) -> str:
    """Argon2id 哈希。"""
    return _pwd_context.hash(password.get_secret_value())


def verify_password(password: SecretStr, password_hash: str) -> bool:
    """常量时间校验密码。"""
    return _pwd_context.verify(password.get_secret_value(), password_hash)


def _resolve_settings(settings: "Settings | None" = None) -> "Settings":
    if settings is not None:
        return settings
    from policymind.core.config import get_settings

    return get_settings()


def create_access_token(
    data: dict[str, object],
    expires_delta: timedelta | None = None,
    *,
    settings: "Settings | None" = None,
) -> str:
    _s = _resolve_settings(settings)
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=_s.JWT_ACCESS_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    to_encode["iat"] = datetime.now(UTC)
    to_encode["jti"] = uuid.uuid4().hex
    return jwt.encode(to_encode, _s.JWT_SECRET, algorithm="HS256")


def create_refresh_token(
    data: dict[str, object],
    *,
    settings: "Settings | None" = None,
) -> str:
    _s = _resolve_settings(settings)
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=_s.JWT_REFRESH_EXPIRE_DAYS)
    to_encode["exp"] = expire
    to_encode["iat"] = datetime.now(UTC)
    to_encode["jti"] = uuid.uuid4().hex
    to_encode["type"] = "refresh"
    return jwt.encode(to_encode, _s.JWT_SECRET, algorithm="HS256")


def decode_token(
    token: str,
    *,
    settings: "Settings | None" = None,
) -> dict[str, object]:
    _s = _resolve_settings(settings)
    try:
        payload: dict[str, object] = jwt.decode(
            token, _s.JWT_SECRET, algorithms=["HS256"]
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Token invalid or expired: {e}") from e
