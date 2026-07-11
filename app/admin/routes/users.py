from fastapi import APIRouter, HTTPException, Depends, Query
from app.admin.auth import get_current_admin, require_role
from app.admin.schemas.user_schemas import UserUpdate
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/")
async def list_users(
    search: str = "",
    module: str = "",
    payment: str = "",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    query = supabase.from_("profiles").select("*", count="exact")

    if search:
        query = query.or_(f"full_name.ilike.%{search}%,email.ilike.%{search}%")
    if module:
        query = query.eq("module_status", module)

    total = query.execute()
    start = (page - 1) * per_page
    users = supabase.from_("profiles").select("*").range(start, start + per_page - 1).order("created_at", desc=True).execute()

    return {"users": users.data or [], "total": total.count or 0, "page": page, "per_page": per_page}

@router.get("/{user_id}")
async def get_user(user_id: str, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("profiles").select("*").eq("id", user_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    return resp.data

@router.put("/{user_id}")
async def update_user(user_id: str, update: UserUpdate, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    data = update.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    supabase.from_("profiles").update(data).eq("id", user_id).execute()
    log_action(admin["sub"], "update_user", "user", user_id, data)
    return {"message": "User updated"}

@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    supabase.from_("profiles").delete().eq("id", user_id).execute()
    log_action(admin["sub"], "delete_user", "user", user_id)
    return {"message": "User deleted"}

@router.post("/{user_id}/toggle-ban")
async def toggle_ban(user_id: str, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("profiles").select("is_banned").eq("id", user_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="User not found")
    new_status = not resp.data.get("is_banned", False)
    supabase.from_("profiles").update({"is_banned": new_status}).eq("id", user_id).execute()
    log_action(admin["sub"], "toggle_ban", "user", user_id, {"is_banned": new_status})
    return {"is_banned": new_status}
