import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.admin.auth import get_current_admin, require_role
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin

logger = logging.getLogger("admin_platform")
router = APIRouter()

TABLE = "platform_settings"


class PlatformSettingsResponse(BaseModel):
    tasks_visible: bool = True
    certificate_download_enabled: bool = False
    active_module: str = "Module 1"


class PlatformSettingsUpdate(BaseModel):
    tasks_visible: bool | None = None
    certificate_download_enabled: bool | None = None
    active_module: str | None = None


def _get_settings():
    resp = supabase_admin.table(TABLE).select("*").limit(1).execute()
    return resp.data[0] if resp.data else None


@router.get("/", response_model=PlatformSettingsResponse)
async def get_platform_settings(admin: dict = Depends(get_current_admin)):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    config = _get_settings()
    if not config:
        return PlatformSettingsResponse()
    return PlatformSettingsResponse(
        tasks_visible=config.get("tasks_visible", True),
        certificate_download_enabled=config.get("certificate_download_enabled", False),
        active_module=config.get("active_module", "Module 1"),
    )


@router.put("/", response_model=PlatformSettingsResponse)
async def update_platform_settings(
    data: PlatformSettingsUpdate,
    admin: dict = Depends(require_role("super_admin")),
):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["updated_by"] = admin["sub"]

    config = _get_settings()
    try:
        if config:
            supabase_admin.table(TABLE).update(payload).eq("id", config["id"]).execute()
        else:
            supabase_admin.table(TABLE).insert(payload).execute()
    except Exception as e:
        logger.error("Failed to update platform settings: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update settings")

    log_action(admin["sub"], "update_platform_settings", "platform_settings", None, payload)

    updated = _get_settings()
    return PlatformSettingsResponse(
        tasks_visible=updated.get("tasks_visible", True),
        certificate_download_enabled=updated.get("certificate_download_enabled", False),
        active_module=updated.get("active_module", "Module 1"),
    )
