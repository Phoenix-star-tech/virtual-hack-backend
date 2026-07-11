from fastapi import APIRouter, HTTPException, Depends
from app.admin.auth import get_current_admin, require_role, hash_password
from app.admin.schemas.auth_schemas import AdminCreateRequest, AdminUpdateRequest
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/")
async def list_admins(admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("admin_users").select("id, email, full_name, role, is_active, last_login, created_at").order("created_at").execute()
    return {"admins": resp.data or []}

@router.post("/")
async def create_admin(data: AdminCreateRequest, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    existing = supabase.from_("admin_users").select("id").eq("email", data.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    payload = data.model_dump()
    payload["password_hash"] = hash_password(data.password)
    del payload["password"]
    resp = supabase.from_("admin_users").insert(payload).execute()
    log_action(admin["sub"], "create_admin", "admin", resp.data[0]["id"] if resp.data else None)
    return resp.data[0] if resp.data else {"message": "Created"}

@router.put("/{admin_id}")
async def update_admin(admin_id: str, data: AdminUpdateRequest, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    payload = data.model_dump(exclude_none=True)
    supabase.from_("admin_users").update(payload).eq("id", admin_id).execute()
    log_action(admin["sub"], "update_admin", "admin", admin_id, payload)
    return {"message": "Admin updated"}
