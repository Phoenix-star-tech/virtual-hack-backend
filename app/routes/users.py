import logging
from fastapi import APIRouter, HTTPException

from app.schemas.user_schemas import ProfileResponse, ProfileUpdate
from app.services.supabase_service import supabase, supabase_admin

logger = logging.getLogger("users")

router = APIRouter()


@router.get("/profile/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: str):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")

    # Try new registrations table first
    try:
        reg_resp = supabase_admin.table("registrations").select("*").eq("id", user_id).single().execute()
        if reg_resp.data:
            reg = reg_resp.data
            return ProfileResponse(
                id=reg["id"],
                full_name=reg.get("full_name", ""),
                email=reg.get("email", ""),
                phone=reg.get("phone", ""),
                college=reg.get("college", ""),
                module_status="Module 1",
                registration_type=reg.get("type", "solo"),
                team_name=reg.get("team_name"),
                team_members=reg.get("team_members", []),
                domain=reg.get("domain"),
            )
    except Exception as e:
        logger.warning("Registration lookup failed (may be old user): %s", e)

    # Fallback to old profiles table (Supabase Auth users)
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    try:
        response = supabase.from_("profiles").select("*").eq("id", user_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile = response.data
        return ProfileResponse(
            id=profile["id"],
            full_name=profile.get("full_name", ""),
            email=profile.get("email", ""),
            phone=profile.get("phone", ""),
            college=profile.get("college", ""),
            module_status=profile.get("module_status", "Module 1"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/profile/{user_id}", response_model=ProfileResponse)
async def update_profile(user_id: str, update: ProfileUpdate):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")

    # Try registrations table first
    try:
        reg_resp = supabase_admin.table("registrations").select("id").eq("id", user_id).execute()
        if reg_resp.data:
            raise HTTPException(status_code=400, detail="Profile updates are not available for new registrations. Contact support.")
    except HTTPException:
        raise
    except Exception:
        pass

    # Fallback to old profiles table
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    try:
        update_data = update.model_dump(exclude_none=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        response = (
            supabase.from_("profiles")
            .update(update_data)
            .eq("id", user_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile = response.data[0]
        return ProfileResponse(
            id=profile["id"],
            full_name=profile.get("full_name", ""),
            email=profile.get("email", ""),
            phone=profile.get("phone", ""),
            college=profile.get("college", ""),
            module_status=profile.get("module_status", "Module 1"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))