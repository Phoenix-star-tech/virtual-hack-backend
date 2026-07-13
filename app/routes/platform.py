import logging
from fastapi import APIRouter, HTTPException
from app.services.supabase_service import supabase_admin

logger = logging.getLogger("platform")
router = APIRouter()

TABLE = "platform_settings"


@router.get("/settings")
async def get_platform_settings():
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    try:
        resp = supabase_admin.table(TABLE).select("*").limit(1).execute()
        if resp.data:
            row = resp.data[0]
            return {
                "tasks_visible": row.get("tasks_visible", True),
                "certificate_download_enabled": row.get("certificate_download_enabled", False),
                "active_module": row.get("active_module", "Module 1"),
            }
        return {"tasks_visible": True, "certificate_download_enabled": False, "active_module": "Module 1"}
    except Exception as e:
        logger.error("Failed to fetch platform settings: %s", e)
        return {"tasks_visible": True, "certificate_download_enabled": False, "active_module": "Module 1"}
