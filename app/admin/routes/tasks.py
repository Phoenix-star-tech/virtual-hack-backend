from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from datetime import datetime, timezone
from app.admin.auth import get_current_admin, require_role
from app.admin.schemas.task_schemas import TaskCreate, TaskUpdate
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin as supabase
from app.services.cloudinary_service import upload_image, is_available
import logging

logger = logging.getLogger("admin_tasks")

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
    if not payload.get("link"):
        payload.pop("link", None)
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
    if "link" in payload and not payload["link"]:
        payload.pop("link")
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

@router.put("/{task_id}/toggle-active")
async def toggle_task_active(task_id: str, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("tasks").select("is_active").eq("id", task_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Task not found")
    new_active = not resp.data.get("is_active", True)
    supabase.from_("tasks").update({"is_active": new_active, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", task_id).execute()
    log_action(admin["sub"], "toggle_task_active", "task", task_id, {"is_active": new_active})
    return {"is_active": new_active}

@router.put("/{task_id}/reorder")
async def reorder_tasks(task_id: str, order_index: int, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    supabase.from_("tasks").update({"order_index": order_index, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", task_id).execute()
    log_action(admin["sub"], "reorder_task", "task", task_id, {"order_index": order_index})
    return {"message": "Task reordered"}


@router.post("/upload-image")
async def upload_task_image(
    file: UploadFile = File(...),
    admin: dict = Depends(require_role("super_admin")),
):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    if not is_available():
        raise HTTPException(status_code=503, detail="Cloudinary is not configured")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    try:
        contents = await file.read()
        result = upload_image(contents, folder="virtual_hack_2k26/tasks")
        image_url = result.get("secure_url")
        public_id = result.get("public_id")
    except Exception as e:
        logger.error("Cloudinary upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to upload image to Cloudinary")
    log_action(admin["sub"], "upload_task_image", "task", None, {"image_url": image_url})
    return {"url": image_url, "public_id": public_id}
