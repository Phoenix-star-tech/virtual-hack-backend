from fastapi import APIRouter, HTTPException
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/")
async def list_active_announcements():
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    anns = supabase.from_("announcements").select("*").order("created_at", desc=True).execute()
    for a in anns.data or []:
        if a.get("created_by"):
            au = supabase.from_("admin_users").select("full_name").eq("id", a["created_by"]).single().execute()
            a["author_name"] = au.data["full_name"] if au.data else ""
    return {"announcements": anns.data or []}
