import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from app.admin.auth import get_current_admin, require_role
from app.admin.schemas.user_schemas import UserUpdate
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin as supabase

logger = logging.getLogger("admin_users")
router = APIRouter()


def _normalize_registration(r):
    return {
        "id": r.get("id"),
        "full_name": r.get("full_name", ""),
        "email": r.get("email", ""),
        "phone": r.get("phone", ""),
        "college": r.get("college", ""),
        "module_status": "Module 1",
        "registration_type": r.get("type", "solo"),
        "team_name": r.get("team_name"),
        "team_members": r.get("team_members", []),
        "domain": r.get("domain"),
        "transaction_id": r.get("transaction_id"),
        "amount": r.get("amount"),
        "member_count": r.get("member_count"),
        "created_at": r.get("created_at"),
        "is_banned": False,
    }


def _normalize_profile(p):
    return {
        "id": p.get("id"),
        "full_name": p.get("full_name", ""),
        "email": p.get("email", ""),
        "phone": p.get("phone", ""),
        "college": p.get("college", ""),
        "module_status": p.get("module_status", "Module 1"),
        "registration_type": "legacy",
        "team_name": None,
        "team_members": [],
        "domain": None,
        "transaction_id": p.get("transaction_id"),
        "amount": None,
        "member_count": None,
        "created_at": p.get("created_at"),
        "is_banned": p.get("is_banned", False),
    }


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

    all_users = []

    # Fetch from registrations table
    try:
        reg_query = supabase.from_("registrations").select("*").order("created_at", desc=True)
        if search:
            reg_query = reg_query.or_(f"full_name.ilike.%{search}%,email.ilike.%{search}%,team_name.ilike.%{search}%")
        reg_resp = reg_query.execute()
        for r in (reg_resp.data or []):
            all_users.append(_normalize_registration(r))
    except Exception as e:
        logger.warning("Failed to fetch registrations: %s", e)

    # Fetch from profiles table (legacy Supabase Auth users)
    try:
        prof_query = supabase.from_("profiles").select("*").order("created_at", desc=True)
        if search:
            prof_query = prof_query.or_(f"full_name.ilike.%{search}%,email.ilike.%{search}%")
        if module:
            prof_query = prof_query.eq("module_status", module)
        prof_resp = prof_query.execute()
        for p in (prof_resp.data or []):
            all_users.append(_normalize_profile(p))
    except Exception as e:
        logger.warning("Failed to fetch profiles: %s", e)

    # Sort by created_at descending
    all_users.sort(key=lambda u: u.get("created_at") or "", reverse=True)

    total = len(all_users)
    start = (page - 1) * per_page
    paginated = all_users[start:start + per_page]

    return {"users": paginated, "total": total, "page": page, "per_page": per_page}


@router.get("/{user_id}")
async def get_user(user_id: str, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    # Try registrations first
    try:
        reg_resp = supabase.from_("registrations").select("*").eq("id", user_id).single().execute()
        if reg_resp.data:
            return _normalize_registration(reg_resp.data)
    except Exception:
        pass

    # Fallback to profiles
    try:
        prof_resp = supabase.from_("profiles").select("*").eq("id", user_id).single().execute()
        if prof_resp.data:
            return _normalize_profile(prof_resp.data)
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="User not found")


@router.put("/{user_id}")
async def update_user(user_id: str, update: UserUpdate, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    data = update.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Check if it's a registration or profile
    try:
        reg_resp = supabase.from_("registrations").select("id").eq("id", user_id).execute()
        if reg_resp.data:
            raise HTTPException(status_code=400, detail="Cannot edit new registration users. Contact support for changes.")
    except HTTPException:
        raise
    except Exception:
        pass

    # Update profiles table (legacy users)
    supabase.from_("profiles").update(data).eq("id", user_id).execute()
    log_action(admin["sub"], "update_user", "user", user_id, data)
    return {"message": "User updated"}


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    # Try registrations first
    try:
        reg_resp = supabase.from_("registrations").select("id").eq("id", user_id).execute()
        if reg_resp.data:
            supabase.from_("registrations").delete().eq("id", user_id).execute()
            log_action(admin["sub"], "delete_user", "registration", user_id)
            return {"message": "Registration deleted"}
    except Exception:
        pass

    # Fallback to profiles
    supabase.from_("profiles").delete().eq("id", user_id).execute()
    log_action(admin["sub"], "delete_user", "user", user_id)
    return {"message": "User deleted"}


@router.post("/{user_id}/toggle-ban")
async def toggle_ban(user_id: str, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    # Only works for legacy profiles
    try:
        resp = supabase.from_("profiles").select("is_banned").eq("id", user_id).single().execute()
        if not resp.data:
            raise HTTPException(status_code=404, detail="User not found or ban not supported for this user type")
        new_status = not resp.data.get("is_banned", False)
        supabase.from_("profiles").update({"is_banned": new_status}).eq("id", user_id).execute()
        log_action(admin["sub"], "toggle_ban", "user", user_id, {"is_banned": new_status})
        return {"is_banned": new_status}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="User not found or ban not supported")
