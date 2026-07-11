from pydantic import BaseModel, Field

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: str
    email: str
    full_name: str
    role: str

class AdminChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class AdminCreateRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    full_name: str = ""
    role: str = "moderator"

class AdminUpdateRequest(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
