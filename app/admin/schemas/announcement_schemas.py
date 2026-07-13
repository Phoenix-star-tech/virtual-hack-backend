from pydantic import BaseModel

class AnnouncementCreate(BaseModel):
    title: str
    body: str
    type: str = "info"
    priority: str = "normal"
    target_module: str | None = None
    send_email: bool = False

class AnnouncementResponse(BaseModel):
    id: str
    title: str
    body: str
    type: str = "info"
    priority: str = "normal"
    created_by: str | None = None
    sent_as_email: bool = False
    target_module: str | None = None
    created_at: str
    author_name: str = ""
