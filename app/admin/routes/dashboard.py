from fastapi import APIRouter, HTTPException, Depends
from app.admin.auth import get_current_admin
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/stats")
async def get_stats(admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    total_users = supabase.from_("profiles").select("id", count="exact").execute()
    total_teams = supabase.from_("teams").select("id", count="exact").execute()
    total_submissions = supabase.from_("submissions").select("id", count="exact").execute()
    pending_submissions = supabase.from_("submissions").select("id", count="exact").eq("status", "pending").execute()
    modules = supabase.from_("modules").select("id, name, status, registration_fee", count="exact").execute()

    module_counts = {}
    if modules.data:
        for m in modules.data:
            count = supabase.from_("profiles").select("id", count="exact").eq("module_status", m["name"]).execute()
            module_counts[m["name"]] = {
                "status": m["status"],
                "fee": m.get("registration_fee", 0),
                "registrations": count.count if count.count else 0,
            }

    return {
        "total_users": total_users.count or 0,
        "total_teams": total_teams.count or 0,
        "total_submissions": total_submissions.count or 0,
        "pending_submissions": pending_submissions.count or 0,
        "module_counts": module_counts,
        "total_modules": len(modules.data) if modules.data else 0,
    }
