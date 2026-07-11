from pydantic import BaseModel


class ProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str
    college: str
    module_status: str


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    college: str | None = None
    module_status: str | None = None