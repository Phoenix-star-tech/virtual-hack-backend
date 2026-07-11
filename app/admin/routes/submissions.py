from fastapi import APIRouter, HTTPException, Depends, Query
from app.admin.auth import get_current_admin
from app.admin.schemas.submission_schemas import SubmissionReview
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/")
async def list_submissions(
    task_id: str = "",
    module_id: str = "",
    status: str = "",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    query = supabase.from_("submissions").select("*", count="exact")
    if task_id:
        query = query.eq("task_id", task_id)
    if status:
        query = query.eq("status", status)
    if module_id:
        task_ids = supabase.from_("tasks").select("id").eq("module_id", module_id).execute()
        if task_ids.data:
            ids = [t["id"] for t in task_ids.data]
            query = query.in_("task_id", ids)

    total = query.execute()
    start = (page - 1) * per_page
    subs = supabase.from_("submissions").select("*").range(start, start + per_page - 1).order("created_at", desc=True).execute()

    for s in subs.data or []:
        task = supabase.from_("tasks").select("title").eq("id", s["task_id"]).single().execute()
        s["task_title"] = task.data["title"] if task.data else ""
        if s.get("team_id"):
            team = supabase.from_("teams").select("name").eq("id", s["team_id"]).single().execute()
            s["team_name"] = team.data["name"] if team.data else ""

    return {"submissions": subs.data or [], "total": total.count or 0, "page": page, "per_page": per_page}

@router.put("/{submission_id}/review")
async def review_submission(submission_id: str, review: SubmissionReview, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    data = review.model_dump()
    data["reviewed_by"] = admin["sub"]
    supabase.from_("submissions").update(data).eq("id", submission_id).execute()
    log_action(admin["sub"], "review_submission", "submission", submission_id, data)
    return {"message": "Submission reviewed"}
