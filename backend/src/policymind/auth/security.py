import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import SecretStr

from policymind.core.config import get_settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: SecretStr) -> str:
    """Argon2id 哈希。"""
    return _pwd_context.hash(password.get_secret_value())


def verify_password(password: SecretStr, password_hash: str) -> bool:
    """常量时间校验密码。"""
    return _pwd_context.verify(password.get_secret_value(), password_hash)


def create_access_token(
    data: dict[str, object],
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
        )
    to_encode["exp"] = expire
    to_encode["iat"] = datetime.now(UTC)
    to_encode["jti"] = uuid.uuid4().hex
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(data: dict[str, object]) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    to_encode["exp"] = expire
    to_encode["iat"] = datetime.now(UTC)
    to_encode["jti"] = uuid.uuid4().hex
    to_encode["type"] = "refresh"
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict[str, object]:
    settings = get_settings()
    try:
        payload: dict[str, object] = jwt.decode(
            token, settings.JWT_SECRET, algorithms=["HS256"]
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Token invalid or expired: {e}") from e
