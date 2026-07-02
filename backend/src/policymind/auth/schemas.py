from pydantic import BaseModel, SecretStr


class LoginRequest(BaseModel):
    tenant_slug: str
    username: str
    password: SecretStr


class RegisterRequest(BaseModel):
    username: str
    password: SecretStr
    invitation_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    tenant_id: int
    username: str
    role: str
    access_level: int
    is_active: bool

    model_config = {"from_attributes": True}
