from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.admin.auth import get_current_admin, require_role
from app.admin.schemas.task_schemas import TaskCreate, TaskUpdate
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/module/{module_id}")
async def list_tasks(module_id: str, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("tasks").select("*").eq("module_id", module_id).order("order_index").execute()
    return {"tasks": resp.data or []}

@router.get("/{task_id}")
async def get_task(task_id: str, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("tasks").select("*").eq("id", task_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return resp.data

@router.post("/")
async def create_task(data: TaskCreate, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    payload = data.model_dump()
    if isinstance(payload.get("attachments"), list):
        payload["attachments"] = payload["attachments"]
    if payload.get("deadline"):
        payload["deadline"] = payload["deadline"].isoformat()
    resp = supabase.from_("tasks").insert(payload).execute()
    log_action(admin["sub"], "create_task", "task", resp.data[0]["id"] if resp.data else None, payload)
    return resp.data[0] if resp.data else {"message": "Created"}

@router.put("/{task_id}")
async def update_task(task_id: str, data: TaskUpdate, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    payload = data.model_dump(exclude_none=True)
    if "deadline" in payload and payload["deadline"]:
        payload["deadline"] = payload["deadline"].isoformat()
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    supabase.from_("tasks").update(payload).eq("id", task_id).execute()
    log_action(admin["sub"], "update_task", "task", task_id, payload)
    return {"message": "Task updated"}

@router.delete("/{task_id}")
async def delete_task(task_id: str, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    supabase.from_("tasks").delete().eq("id", task_id).execute()
    log_action(admin["sub"], "delete_task", "task", task_id)
    return {"message": "Task deleted"}

@router.put("/{task_id}/reorder")
async def reorder_tasks(task_id: str, order_index: int, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    supabase.from_("tasks").update({"order_index": order_index, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", task_id).execute()
    log_action(admin["sub"], "reorder_task", "task", task_id, {"order_index": order_index})
    return {"message": "Task reordered"}
