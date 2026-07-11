from fastapi import APIRouter, HTTPException, Depends
from app.admin.auth import get_current_admin, require_role
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/")
async def get_leaderboard(module_id: str = "", admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    query = supabase.from_("leaderboard").select("*, teams!inner(name)").order("rank")
    if module_id:
        query = query.eq("module_id", module_id)
    resp = query.execute()
    for entry in resp.data or []:
        score = entry.get("manual_override") if entry.get("manual_override") is not None else entry.get("total_score", 0)
        entry["display_score"] = score
    return {"leaderboard": resp.data or []}

@router.put("/{entry_id}")
async def update_leaderboard_entry(entry_id: str, total_score: int = None, manual_override: int = None, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    data = {}
    if total_score is not None:
        data["total_score"] = total_score
    if manual_override is not None:
        data["manual_override"] = manual_override
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    supabase.from_("leaderboard").update(data).eq("id", entry_id).execute()
    log_action(admin["sub"], "update_leaderboard", "leaderboard", entry_id, data)
    return {"message": "Leaderboard entry updated"}

@router.put("/toggle-publish/{module_id}")
async def toggle_leaderboard_publish(module_id: str, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    entries = supabase.from_("leaderboard").select("is_published").eq("module_id", module_id).execute()
    if not entries.data:
        raise HTTPException(status_code=404, detail="No leaderboard entries found")
    current = entries.data[0].get("is_published", False)
    new_status = not current
    supabase.from_("leaderboard").update({"is_published": new_status}).eq("module_id", module_id).execute()
    log_action(admin["sub"], "toggle_leaderboard_publish", "leaderboard", module_id, {"is_published": new_status})
    return {"is_published": new_status}

@router.post("/recalculate/{module_id}")
async def recalculate_leaderboard(module_id: str, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    teams = supabase.from_("teams").select("id").eq("module_id", module_id).execute()
    if not teams.data:
        raise HTTPException(status_code=404, detail="No teams in this module")
    for team in teams.data:
        subs = supabase.from_("submissions").select("score").eq("team_id", team["id"]).execute()
        total = sum(s["score"] or 0 for s in subs.data or [])
        existing = supabase.from_("leaderboard").select("id").eq("module_id", module_id).eq("team_id", team["id"]).execute()
        if existing.data:
            supabase.from_("leaderboard").update({"total_score": total}).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.from_("leaderboard").insert({"module_id": module_id, "team_id": team["id"], "total_score": total}).execute()
    ranked = supabase.from_("leaderboard").select("id").eq("module_id", module_id).order("total_score", desc=True).execute()
    for i, entry in enumerate(ranked.data or []):
        supabase.from_("leaderboard").update({"rank": i + 1}).eq("id", entry["id"]).execute()
    log_action(admin["sub"], "recalculate_leaderboard", "leaderboard", module_id)
    return {"message": "Leaderboard recalculated"}
