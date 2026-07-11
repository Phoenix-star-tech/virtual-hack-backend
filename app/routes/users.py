from fastapi import APIRouter, HTTPException

from app.schemas.user_schemas import ProfileResponse, ProfileUpdate
from app.services.supabase_service import supabase

router = APIRouter()


@router.get("/profile/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: str):
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured.",
        )
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
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured.",
        )
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