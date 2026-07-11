from pydantic import BaseModel
from datetime import datetime

class TaskCreate(BaseModel):
    module_id: str
    title: str
    description: str = ""
    points: int = 0
    attachments: list = []
    deadline: datetime | None = None
    order_index: int = 0

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    points: int | None = None
    attachments: list | None = None
    deadline: datetime | None = None
    order_index: int | None = None

class TaskResponse(BaseModel):
    id: str
    module_id: str
    title: str
    description: str
    points: int
    attachments: list
    deadline: str | None = None
    order_index: int
    created_at: str
    updated_at: str
