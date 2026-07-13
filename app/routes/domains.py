import logging
from fastapi import APIRouter, HTTPException
from app.services.supabase_service import supabase_admin

logger = logging.getLogger("domains")
router = APIRouter()


@router.get("/")
async def get_domains():
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    try:
        resp = supabase_admin.table("domains").select("*").order("name").execute()
        return {"domains": resp.data if resp.data else []}
    except Exception as e:
        logger.error("Failed to fetch domains: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch domains")
