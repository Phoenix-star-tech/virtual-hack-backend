from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")


class RegisterRequest(BaseModel):
    full_name: str = Field(..., description="User full name")
    email: str = Field(..., description="User email address")
    phone: str = Field(..., description="User phone number")
    college: str = Field(..., description="User college or organization")
    password: str = Field(..., min_length=6, description="User password")


class AuthResponse(BaseModel):
    access_token: str | None = None
    user_id: str | None = None
    email: str | None = None
    full_name: str | None = None
    message: str = ""


class ErrorResponse(BaseModel):
    detail: str