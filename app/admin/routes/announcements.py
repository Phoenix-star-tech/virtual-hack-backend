from fastapi import APIRouter, HTTPException, Depends
from app.admin.auth import get_current_admin, require_role
from app.admin.schemas.announcement_schemas import AnnouncementCreate
from app.admin.services.audit import log_action
from app.admin.services.email import send_email
from app.services.supabase_service import supabase_admin as supabase

router = APIRouter()

@router.get("/")
async def list_announcements(admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    anns = supabase.from_("announcements").select("*").order("created_at", desc=True).execute()
    for a in anns.data or []:
        if a.get("created_by"):
            au = supabase.from_("admin_users").select("full_name").eq("id", a["created_by"]).execute()
            a["author_name"] = au.data[0]["full_name"] if au.data else ""
    return {"announcements": anns.data or []}

@router.post("/")
async def create_announcement(data: AnnouncementCreate, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    from datetime import datetime, timezone

    payload = {
        "title": data.title,
        "body": data.body,
        "type": data.type,
        "priority": data.priority,
        "target_module": data.target_module,
        "sent_as_email": data.send_email,
        "created_by": admin["sub"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    resp = supabase.from_("announcements").insert(payload).execute()
    log_action(admin["sub"], "create_announcement", "announcement", resp.data[0]["id"] if resp.data else None, payload)

    if data.send_email:
        users = supabase.from_("registrations").select("email").execute()
        if not users.data:
            users = supabase.from_("profiles").select("email").execute()
        emails = list(set(u["email"] for u in users.data if u.get("email")))
        if emails:
            send_email(emails, data.title, data.body)

    return resp.data[0] if resp.data else {"message": "Created"}

@router.delete("/{announcement_id}")
async def delete_announcement(announcement_id: str, admin: dict = Depends(require_role("super_admin"))):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    supabase.from_("announcements").delete().eq("id", announcement_id).execute()
    log_action(admin["sub"], "delete_announcement", "announcement", announcement_id)
    return {"message": "Announcement deleted"}
