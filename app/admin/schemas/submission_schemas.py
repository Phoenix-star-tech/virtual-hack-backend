from pydantic import BaseModel

class SubmissionReview(BaseModel):
    status: str = "reviewed"
    score: int | None = None
    admin_notes: str = ""

class SubmissionResponse(BaseModel):
    id: str
    task_id: str
    team_id: str | None = None
    submitter_id: str | None = None
    links: list = []
    files: list = []
    notes: str = ""
    status: str
    score: int | None = None
    admin_notes: str = ""
    reviewed_by: str | None = None
    created_at: str
    updated_at: str
    task_title: str = ""
    team_name: str = ""
    submitter_name: str = ""
