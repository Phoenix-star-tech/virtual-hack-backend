from pydantic import BaseModel

class TeamCreate(BaseModel):
    name: str
    module_id: str | None = None
    leader_id: str | None = None
    member_ids: list[str] = []

class TeamUpdate(BaseModel):
    name: str | None = None
    module_id: str | None = None
    leader_id: str | None = None

class TeamResponse(BaseModel):
    id: str
    name: str
    module_id: str | None = None
    leader_id: str | None = None
    created_at: str
    members: list = []
