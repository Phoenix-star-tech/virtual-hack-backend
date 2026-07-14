from fastapi import APIRouter, HTTPException, Depends
from app.admin.auth import get_current_admin
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/stats")
async def get_stats(admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    registrations = supabase.from_("registrations").select("id, type, domain, team_members, member_count", count="exact").execute()
    total_submissions = supabase.from_("submissions").select("id", count="exact").execute()
    pending_submissions = supabase.from_("submissions").select("id", count="exact").eq("status", "pending").execute()
    modules = supabase.from_("modules").select("id, name, status, registration_fee", count="exact").execute()

    total_users = 0
    total_teams = 0
    domain_counts = {}
    if registrations.data:
        for r in registrations.data:
            total_users += r.get("member_count", 1)
            if r["type"] == "team":
                total_teams += 1
            domain_counts[r["domain"]] = domain_counts.get(r["domain"], 0) + 1

    module_counts = {}
    if modules.data:
        for m in modules.data:
            module_counts[m["name"]] = {
                "status": m["status"],
                "fee": m.get("registration_fee", 0),
                "registrations": domain_counts.get(m["name"], 0),
            }

    return {
        "total_users": total_users,
        "total_teams": total_teams,
        "total_submissions": total_submissions.count or 0,
        "pending_submissions": pending_submissions.count or 0,
        "module_counts": module_counts,
        "total_modules": len(modules.data) if modules.data else 0,
    }
