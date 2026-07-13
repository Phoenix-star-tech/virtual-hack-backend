import os
import logging
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from app.admin.auth import get_current_admin, require_role
from app.admin.services.audit import log_action
from app.services.supabase_service import supabase_admin
from app.services.cloudinary_service import upload_image, delete_image, is_available
from app.schemas.payment_schemas import QRConfigUpdate

logger = logging.getLogger("admin_payment")
router = APIRouter()

QR_CONFIG_TABLE = "payment_config"


def _get_config():
    resp = supabase_admin.table(QR_CONFIG_TABLE).select("*").limit(1).execute()
    return resp.data[0] if resp.data else None


@router.get("/")
async def get_payment_settings(admin: dict = Depends(get_current_admin)):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    config = _get_config()
    if not config:
        return {"qr_image_url": None, "upi_id": None, "amount": 9, "id": None}
    return config


@router.post("/qr-upload")
async def upload_qr_image(
    file: UploadFile = File(...),
    admin: dict = Depends(require_role("super_admin")),
):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    if not is_available():
        raise HTTPException(status_code=503, detail="Cloudinary is not configured")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    config = _get_config()
    old_public_id = None
    if config and config.get("qr_public_id"):
        old_public_id = config["qr_public_id"]

    try:
        contents = await file.read()
        result = upload_image(contents, public_id="payment_qr", folder="virtual_hack_2k26/qr")
        image_url = result.get("secure_url")
        public_id = result.get("public_id")
    except Exception as e:
        logger.error("Cloudinary upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to upload image to Cloudinary")

    if old_public_id and old_public_id != public_id:
        try:
            delete_image(old_public_id)
        except Exception as e:
            logger.warning("Failed to delete old QR image: %s", e)

    payload = {"qr_image_url": image_url, "qr_public_id": public_id}
    try:
        if config:
            supabase_admin.table(QR_CONFIG_TABLE).update(payload).eq("id", config["id"]).execute()
        else:
            supabase_admin.table(QR_CONFIG_TABLE).insert(payload).execute()
    except Exception as e:
        logger.error("Failed to save QR config: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save QR configuration")

    log_action(admin["sub"], "upload_qr_image", "payment_config", None, {"image_url": image_url})
    return {"qr_image_url": image_url, "message": "QR code image updated successfully"}


@router.put("/")
async def update_payment_settings(
    data: QRConfigUpdate,
    admin: dict = Depends(require_role("super_admin")),
):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    config = _get_config()
    try:
        if config:
            supabase_admin.table(QR_CONFIG_TABLE).update(payload).eq("id", config["id"]).execute()
        else:
            supabase_admin.table(QR_CONFIG_TABLE).insert(payload).execute()
    except Exception as e:
        logger.error("Failed to update payment config: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update payment configuration")

    log_action(admin["sub"], "update_payment_settings", "payment_config", None, payload)
    return {"message": "Payment settings updated successfully"}
