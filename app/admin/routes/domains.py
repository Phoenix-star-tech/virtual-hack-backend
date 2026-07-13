import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.admin.auth import get_current_admin, require_role
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin

logger = logging.getLogger("admin_domains")
router = APIRouter()


class DomainCreate(BaseModel):
    name: str


class DomainResponse(BaseModel):
    id: str
    name: str
    created_at: str | None = None


@router.get("/")
async def get_domains(admin: dict = Depends(get_current_admin)):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    try:
        resp = supabase_admin.table("domains").select("*").order("name").execute()
        return {"domains": resp.data if resp.data else []}
    except Exception as e:
        logger.error("Failed to fetch domains: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch domains")


@router.post("/")
async def create_domain(
    data: DomainCreate,
    admin: dict = Depends(require_role("super_admin")),
):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Domain name is required")

    try:
        existing = supabase_admin.table("domains").select("id").eq("name", name).execute()
        if existing.data:
            raise HTTPException(status_code=409, detail="Domain already exists")

        resp = supabase_admin.table("domains").insert({"name": name}).execute()
        log_action(admin["sub"], "create_domain", "domains", resp.data[0]["id"], {"name": name})
        return resp.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create domain: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create domain")


@router.delete("/{domain_id}")
async def delete_domain(
    domain_id: str,
    admin: dict = Depends(require_role("super_admin")),
):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        existing = supabase_admin.table("domains").select("id").eq("id", domain_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Domain not found")

        supabase_admin.table("domains").delete().eq("id", domain_id).execute()
        log_action(admin["sub"], "delete_domain", "domains", domain_id, {})
        return {"message": "Domain deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete domain: %s", e)
        raise HTTPException(status_code=500, detail="Failed to delete domain")
