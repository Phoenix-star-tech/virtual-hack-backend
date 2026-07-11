from fastapi import APIRouter, HTTPException

from app.schemas.auth_schemas import LoginRequest, RegisterRequest, AuthResponse
from app.services.supabase_service import supabase

router = APIRouter()


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY in .env",
        )

    try:
        response = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )
        user = response.user
        session = response.session

        full_name = ""
        if user and user.user_metadata:
            full_name = user.user_metadata.get("full_name", "")

        return AuthResponse(
            access_token=session.access_token if session else None,
            user_id=user.id if user else None,
            email=user.email if user else None,
            full_name=full_name,
            message="Login successful",
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY in .env",
        )

    try:
        response = supabase.auth.sign_up(
            {
                "email": request.email,
                "password": request.password,
                "options": {
                    "data": {
                        "full_name": request.full_name,
                        "phone": request.phone,
                        "college": request.college,
                    }
                },
            }
        )
        user = response.user
        session = response.session

        if session:
            return AuthResponse(
                access_token=session.access_token,
                user_id=user.id if user else None,
                email=request.email,
                full_name=request.full_name,
                message="Registration successful! Redirecting to dashboard...",
            )
        else:
            return AuthResponse(
                message="Registration completed! Please check your email to verify your account."
            )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/logout")
async def logout():
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured.",
        )
    try:
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get("/session")
async def get_session():
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured.",
        )
    try:
        session = supabase.auth.get_session()
        if session:
            return {
                "authenticated": True,
                "user_id": session.user.id,
                "email": session.user.email,
                "full_name": (
                    session.user.user_metadata.get("full_name", "")
                    if session.user.user_metadata
                    else ""
                ),
            }
        return {"authenticated": False}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )