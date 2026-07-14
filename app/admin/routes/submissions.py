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
        task_resp = supabase.from_("tasks").select("title, module_id, answer_type, quiz_options").eq("id", s["task_id"]).execute()
        task = task_resp.data[0] if task_resp.data else None
        s["task_title"] = task["title"] if task else ""
        s["module_id"] = task["module_id"] if task else ""
        s["answer_type"] = task["answer_type"] if task else "link"
        s["quiz_options"] = task["quiz_options"] if task else []
        if task and task.get("module_id"):
            mod_resp = supabase.from_("modules").select("name").eq("id", task["module_id"]).execute()
            s["module_name"] = mod_resp.data[0]["name"] if mod_resp.data else ""
        else:
            s["module_name"] = ""
        submitter_resp = supabase.from_("registrations").select("full_name, email").eq("id", s["submitter_id"]).execute()
        if not submitter_resp.data:
            submitter_resp = supabase.from_("profiles").select("full_name, email").eq("id", s["submitter_id"]).execute()
        s["submitter_name"] = submitter_resp.data[0]["full_name"] if submitter_resp.data else ""
        s["submitter_email"] = submitter_resp.data[0]["email"] if submitter_resp.data else ""
        if s.get("team_id"):
            team_resp = supabase.from_("registrations").select("team_name").eq("id", s["team_id"]).execute()
            if not team_resp.data:
                team_resp = supabase.from_("teams").select("name").eq("id", s["team_id"]).execute()
            s["team_name"] = team_resp.data[0].get("team_name") or team_resp.data[0].get("name") or "" if team_resp.data else ""

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
