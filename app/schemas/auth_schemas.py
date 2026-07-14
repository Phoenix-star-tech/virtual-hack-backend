from pydantic import BaseModel, Field


class SoloRegisterRequest(BaseModel):
    type: str = "solo"
    full_name: str = Field(..., description="User full name")
    email: str = Field(..., description="User email address")
    phone: str = Field(..., description="User phone number")
    college: str = Field(..., description="User college or organization")
    password: str = Field(..., min_length=6, description="User password")
    domain: str = Field(..., description="Selected domain")
    transaction_id: str = Field(..., description="Payment transaction ID")


class TeamMemberSchema(BaseModel):
    full_name: str
    email: str


class TeamRegisterRequest(BaseModel):
    type: str = "team"
    team_name: str = Field(..., description="Team name")
    full_name: str = Field(..., description="Team leader full name")
    email: str = Field(..., description="Team leader email address")
    phone: str = Field(..., description="Team leader phone number")
    college: str = Field(..., description="Team leader college")
    password: str = Field(..., min_length=6, description="Common team password")
    domain: str = Field(..., description="Selected domain")
    transaction_id: str = Field(..., description="Payment transaction ID")
    team_members: list[TeamMemberSchema] = Field(default_factory=list, description="Additional team members (max 3)")


class AuthResponse(BaseModel):
    access_token: str | None = None
    user_id: str | None = None
    email: str | None = None
    full_name: str | None = None
    registration_type: str | None = None
    team_name: str | None = None
    message: str = ""


class LoginRequest(BaseModel):
    type: str = Field(..., description="solo or team")
    email: str | None = Field(None, description="Email for solo login")
    team_name: str | None = Field(None, description="Team name for team login")
    password: str = Field(..., min_length=6, description="User password")


class ErrorResponse(BaseModel):
    detail: str


class TransactionCheckRequest(BaseModel):
    transaction_id: str


class TransactionCheckResponse(BaseModel):
    exists: bool


class EmailCheckResponse(BaseModel):
    available: bool


class TeamNameCheckResponse(BaseModel):
    available: bool
