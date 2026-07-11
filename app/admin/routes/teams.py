from fastapi import APIRouter, HTTPException, Depends
from app.admin.auth import get_current_admin
from app.admin.schemas.team_schemas import TeamCreate, TeamUpdate
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/")
async def list_teams(admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    teams = supabase.from_("teams").select("*").order("created_at", desc=True).execute()
    result = []
    for t in teams.data or []:
        members = supabase.from_("team_members").select("*, auth.users!inner(email, raw_user_meta_data->>full_name)").eq("team_id", t["id"]).execute()
        t["members"] = members.data or []
        result.append(t)
    return {"teams": result}

@router.get("/{team_id}")
async def get_team(team_id: str, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    t = supabase.from_("teams").select("*").eq("id", team_id).single().execute()
    if not t.data:
        raise HTTPException(status_code=404, detail="Team not found")
    members = supabase.from_("team_members").select("*, auth.users!inner(email, raw_user_meta_data->>full_name)").eq("team_id", team_id).execute()
    t.data["members"] = members.data or []
    return t.data

@router.post("/")
async def create_team(data: TeamCreate, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    payload = data.model_dump(exclude={"member_ids"})
    member_ids = data.member_ids or []
    resp = supabase.from_("teams").insert(payload).execute()
    if not resp.data:
        raise HTTPException(status_code=400, detail="Failed to create team")
    team = resp.data[0]
    for uid in member_ids:
        role = "leader" if uid == data.leader_id else "member"
        supabase.from_("team_members").insert({"team_id": team["id"], "user_id": uid, "role": role}).execute()
    log_action(admin["sub"], "create_team", "team", team["id"], payload)
    return team

@router.put("/{team_id}")
async def update_team(team_id: str, data: TeamUpdate, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    payload = data.model_dump(exclude_none=True)
    supabase.from_("teams").update(payload).eq("id", team_id).execute()
    log_action(admin["sub"], "update_team", "team", team_id, payload)
    return {"message": "Team updated"}

@router.delete("/{team_id}")
async def delete_team(team_id: str, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    supabase.from_("teams").delete().eq("id", team_id).execute()
    log_action(admin["sub"], "delete_team", "team", team_id)
    return {"message": "Team deleted"}

@router.post("/{team_id}/members")
async def add_team_member(team_id: str, user_id: str, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    supabase.from_("team_members").insert({"team_id": team_id, "user_id": user_id, "role": "member"}).execute()
    log_action(admin["sub"], "add_team_member", "team_member", team_id, {"user_id": user_id})
    return {"message": "Member added"}

@router.delete("/{team_id}/members/{user_id}")
async def remove_team_member(team_id: str, user_id: str, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    supabase.from_("team_members").delete().eq("team_id", team_id).eq("user_id", user_id).execute()
    log_action(admin["sub"], "remove_team_member", "team_member", team_id, {"user_id": user_id})
    return {"message": "Member removed"}
