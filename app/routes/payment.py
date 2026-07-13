import os
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from app.admin.auth import get_current_admin
from app.services.supabase_service import supabase_admin
from app.services.cloudinary_service import upload_image, delete_image

logger = logging.getLogger("payment")
router = APIRouter()

QR_CONFIG_TABLE = "payment_config"

@router.get("/qr")
async def get_qr_config():
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    try:
        resp = supabase_admin.table(QR_CONFIG_TABLE).select("*").limit(1).execute()
        if resp.data:
            return resp.data[0]
        return {"qr_image_url": None, "upi_id": None, "amount": 9}
    except Exception as e:
        logger.error("Failed to fetch QR config: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch payment config")
