from pydantic import SecretStr


def test_hash_password_is_argon2id() -> None:
    """密码哈希必须使用 Argon2id。"""
    from policymind.auth.security import hash_password

    password = SecretStr("MySecurePass123!")
    hashed = hash_password(password)

    assert hashed != password.get_secret_value()
    assert hashed.startswith("$argon2id$")


def test_verify_password_same_password_returns_true() -> None:
    """相同密码验证返回 True。"""
    from policymind.auth.security import hash_password, verify_password

    password = SecretStr("correct-horse-battery-staple")
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_different_password_returns_false() -> None:
    """不同密码验证返回 False。"""
    from policymind.auth.security import hash_password, verify_password

    hashed = hash_password(SecretStr("original-password"))
    assert verify_password(SecretStr("wrong-password"), hashed) is False


def test_jwt_encode_and_decode() -> None:
    """JWT 编码和解码往返正确。"""
    from policymind.auth.security import create_access_token, decode_token

    token = create_access_token(data={"sub": "1", "tenant_id": 1, "role": "employee"})
    payload = decode_token(token)

    assert payload["sub"] == "1"
    assert payload["tenant_id"] == 1
    assert payload["role"] == "employee"


def test_jwt_expired_token_raises() -> None:
    """过期 Token 解码时抛出异常。"""
    from datetime import timedelta

    import pytest

    from policymind.auth.security import create_access_token, decode_token

    token = create_access_token(
        data={"sub": "1"},
        expires_delta=timedelta(seconds=-1),
    )
    with pytest.raises(ValueError, match="expired"):
        decode_token(token)
