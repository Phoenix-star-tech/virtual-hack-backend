from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.admin.auth import get_current_admin, require_role
from app.admin.schemas.module_schemas import ModuleCreate, ModuleUpdate
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/")
async def list_modules(admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("modules").select("*").order("order_index").execute()
    return {"modules": resp.data or []}

@router.get("/{module_id}")
async def get_module(module_id: str, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("modules").select("*").eq("id", module_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Module not found")
    return resp.data

@router.post("/")
async def create_module(data: ModuleCreate, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    payload = data.model_dump()
    if payload.get("start_date"):
        payload["start_date"] = payload["start_date"].isoformat()
    if payload.get("end_date"):
        payload["end_date"] = payload["end_date"].isoformat()
    resp = supabase.from_("modules").insert(payload).execute()
    log_action(admin["sub"], "create_module", "module", resp.data[0]["id"] if resp.data else None, payload)
    return resp.data[0] if resp.data else {"message": "Created"}

@router.put("/{module_id}")
async def update_module(module_id: str, data: ModuleUpdate, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    payload = data.model_dump(exclude_none=True)
    if "start_date" in payload and payload["start_date"]:
        payload["start_date"] = payload["start_date"].isoformat()
    if "end_date" in payload and payload["end_date"]:
        payload["end_date"] = payload["end_date"].isoformat()
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    supabase.from_("modules").update(payload).eq("id", module_id).execute()
    log_action(admin["sub"], "update_module", "module", module_id, payload)
    return {"message": "Module updated"}

@router.delete("/{module_id}")
async def delete_module(module_id: str, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    supabase.from_("modules").delete().eq("id", module_id).execute()
    log_action(admin["sub"], "delete_module", "module", module_id)
    return {"message": "Module deleted"}

@router.put("/{module_id}/toggle-status")
async def toggle_module_status(module_id: str, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("modules").select("status").eq("id", module_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Module not found")
    new_status = "open" if resp.data["status"] == "locked" else "locked"
    supabase.from_("modules").update({"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", module_id).execute()
    log_action(admin["sub"], "toggle_module_status", "module", module_id, {"new_status": new_status})
    return {"status": new_status}
