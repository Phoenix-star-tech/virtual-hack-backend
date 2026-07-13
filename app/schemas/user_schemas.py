from pydantic import BaseModel


class TeamMemberItem(BaseModel):
    full_name: str
    email: str


class ProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str
    college: str
    module_status: str = "Module 1"
    registration_type: str | None = None
    team_name: str | None = None
    team_members: list[TeamMemberItem] = []
    domain: str | None = None


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    college: str | None = None
    module_status: str | None = None