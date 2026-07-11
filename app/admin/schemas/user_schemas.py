from pydantic import BaseModel
from datetime import datetime

class UserResponse(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    phone: str | None = None
    college: str | None = None
    module_status: str | None = None
    created_at: str | None = None

class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    college: str | None = None
    module_status: str | None = None
    is_banned: bool | None = None
