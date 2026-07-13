from fastapi import APIRouter, HTTPException, Query

from app.services.supabase_service import supabase_admin as db

router = APIRouter()


@router.get("/")
async def list_public_tasks(module_id: str = Query("")):
    if not db:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    query = db.from_("tasks").select("*").eq("is_active", True).order("order_index")
    if module_id:
        query = query.eq("module_id", module_id)
    resp = query.execute()
    return {"tasks": resp.data or []}


@router.get("/modules")
async def list_public_modules():
    if not db:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = db.from_("modules").select("id, name").order("order_index").execute()
    return {"modules": resp.data or []}
