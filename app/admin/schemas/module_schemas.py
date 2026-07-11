from pydantic import BaseModel
from datetime import datetime

class ModuleCreate(BaseModel):
    name: str
    description: str = ""
    order_index: int = 0
    status: str = "locked"
    registration_fee: float = 0
    start_date: datetime | None = None
    end_date: datetime | None = None

class ModuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    order_index: int | None = None
    status: str | None = None
    registration_fee: float | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

class ModuleResponse(BaseModel):
    id: str
    name: str
    description: str
    order_index: int
    status: str
    registration_fee: float
    start_date: str | None = None
    end_date: str | None = None
    created_at: str
    updated_at: str
