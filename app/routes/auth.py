import os
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

from app.schemas.auth_schemas import (
    LoginRequest,
    SoloRegisterRequest,
    TeamRegisterRequest,
    AuthResponse,
    TransactionCheckRequest,
    TransactionCheckResponse,
)
from app.services.supabase_service import supabase_admin

load_dotenv()

logger = logging.getLogger("auth")

SECRET_KEY = os.getenv("JWT_SECRET", os.getenv("SUPABASE_ANON_KEY", "fallback-secret-change-me"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()


def hash_password(plain: str) -> str:
    try:
        plain_bytes = plain.encode("utf-8")
        if len(plain_bytes) > 72:
            plain = plain_bytes[:72].decode("utf-8", "ignore")
    except Exception:
        plain = plain[:72]
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        plain_bytes = plain.encode("utf-8")
        if len(plain_bytes) > 72:
            plain = plain_bytes[:72].decode("utf-8", "ignore")
        return pwd_context.verify(plain, hashed)
    except Exception as e:
        logger.error(f"Password verification crash: {e}")
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _get_solo_base_amount():
    try:
        resp = supabase_admin.table("payment_config").select("amount").limit(1).execute()
        if resp.data:
            return resp.data[0].get("amount", 9)
    except Exception as e:
        logger.warning("Failed to read payment_config amount, using default: %s", e)
    return 9


@router.post("/register/solo", response_model=AuthResponse)
async def register_solo(request: SoloRegisterRequest):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")

    tid = request.transaction_id.strip()
    if not tid:
        raise HTTPException(status_code=400, detail="Transaction ID is required")

    try:
        existing = supabase_admin.table("registrations").select("id").eq("transaction_id", tid).execute()
        if existing.data:
            raise HTTPException(status_code=409, detail="Transaction ID already used for another registration")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check transaction_id uniqueness: %s", e)
        raise HTTPException(status_code=500, detail="Failed to validate transaction ID")

    try:
        existing_email = supabase_admin.table("registrations").select("id").eq("email", request.email).eq("type", "solo").execute()
        if existing_email.data:
            raise HTTPException(status_code=409, detail="An account with this email already exists. Please login instead.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check email uniqueness: %s", e)

    amount = _get_solo_base_amount()
    password_hash = hash_password(request.password)

    try:
        resp = supabase_admin.table("registrations").insert({
            "type": "solo",
            "email": request.email,
            "full_name": request.full_name,
            "phone": request.phone,
            "college": request.college,
            "password_hash": password_hash,
            "domain": request.domain,
            "transaction_id": tid,
            "amount": amount,
            "member_count": 1,
            "team_members": [],
        }).execute()

        user = resp.data[0]
        token = create_access_token({
            "sub": user["id"],
            "email": request.email,
            "type": "solo",
            "role": "user",
        })

        return AuthResponse(
            access_token=token,
            user_id=user["id"],
            email=request.email,
            full_name=request.full_name,
            registration_type="solo",
            message="Registration successful! Please proceed to login.",
        )
    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e).lower()
        if "already" in err_msg or "duplicate" in err_msg or "exists" in err_msg:
            raise HTTPException(status_code=409, detail="An account with this email already exists. Please login instead.")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/register/team", response_model=AuthResponse)
async def register_team(request: TeamRegisterRequest):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")

    tid = request.transaction_id.strip()
    if not tid:
        raise HTTPException(status_code=400, detail="Transaction ID is required")

    team_name = request.team_name.strip()
    if not team_name:
        raise HTTPException(status_code=400, detail="Team name is required")

    member_count = 1 + len(request.team_members)
    if member_count > 4:
        raise HTTPException(status_code=400, detail="Team cannot have more than 4 members (including leader)")

    if len(request.team_members) != len(set(m.full_name for m in request.team_members)):
        raise HTTPException(status_code=400, detail="Duplicate team member names are not allowed")

    try:
        existing = supabase_admin.table("registrations").select("id").eq("transaction_id", tid).execute()
        if existing.data:
            raise HTTPException(status_code=409, detail="Transaction ID already used for another registration")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check transaction_id uniqueness: %s", e)
        raise HTTPException(status_code=500, detail="Failed to validate transaction ID")

    try:
        existing_team = supabase_admin.table("registrations").select("id").eq("team_name", team_name).execute()
        if existing_team.data:
            raise HTTPException(status_code=409, detail="Team name already exists. Please choose another name.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check team name uniqueness: %s", e)

    base_amount = _get_solo_base_amount()
    amount = base_amount * member_count
    password_hash = hash_password(request.password)

    team_members_data = [{"full_name": m.full_name, "email": m.email} for m in request.team_members]

    try:
        resp = supabase_admin.table("registrations").insert({
            "type": "team",
            "team_name": team_name,
            "email": request.email,
            "full_name": request.full_name,
            "phone": request.phone,
            "college": request.college,
            "password_hash": password_hash,
            "domain": request.domain,
            "transaction_id": tid,
            "amount": amount,
            "member_count": member_count,
            "team_members": team_members_data,
        }).execute()

        user = resp.data[0]
        token = create_access_token({
            "sub": user["id"],
            "team_name": team_name,
            "type": "team",
            "role": "user",
        })

        return AuthResponse(
            access_token=token,
            user_id=user["id"],
            email=request.email,
            full_name=request.full_name,
            registration_type="team",
            team_name=team_name,
            message="Team registration successful! Please proceed to login.",
        )
    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e).lower()
        if "already" in err_msg or "duplicate" in err_msg or "exists" in err_msg:
            raise HTTPException(status_code=409, detail="A team with this name already exists. Please choose another name.")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")

    if request.type == "solo":
        if not request.email:
            raise HTTPException(status_code=400, detail="Email is required for solo login")

        try:
            resp = supabase_admin.table("registrations").select("*").eq("email", request.email).eq("type", "solo").execute()
        except Exception as e:
            logger.error("Login lookup failed: %s", e)
            raise HTTPException(status_code=500, detail="Login failed")

        if not resp.data:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user = resp.data[0]

        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token({
            "sub": user["id"],
            "email": user["email"],
            "type": "solo",
            "role": "user",
        })

        return AuthResponse(
            access_token=token,
            user_id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            registration_type="solo",
            message="Login successful",
        )

    elif request.type == "team":
        if not request.team_name:
            raise HTTPException(status_code=400, detail="Team name is required for team login")

        try:
            resp = supabase_admin.table("registrations").select("*").eq("team_name", request.team_name).eq("type", "team").execute()
        except Exception as e:
            logger.error("Team login lookup failed: %s", e)
            raise HTTPException(status_code=500, detail="Login failed")

        if not resp.data:
            raise HTTPException(status_code=401, detail="Invalid team name or password")

        user = resp.data[0]

        if not verify_password(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid team name or password")

        token = create_access_token({
            "sub": user["id"],
            "team_name": user["team_name"],
            "type": "team",
            "role": "user",
        })

        return AuthResponse(
            access_token=token,
            user_id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            registration_type="team",
            team_name=user["team_name"],
            message="Login successful",
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid login type. Must be 'solo' or 'team'")


@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}


@router.get("/session")
async def get_session():
    from app.services.supabase_service import supabase
    if not supabase:
        return {"authenticated": False}
    try:
        session = supabase.auth.get_session()
        if session:
            return {
                "authenticated": True,
                "user_id": session.user.id,
                "email": session.user.email,
                "full_name": (session.user.user_metadata.get("full_name", "") if session.user.user_metadata else ""),
            }
        return {"authenticated": False}
    except Exception:
        return {"authenticated": False}


@router.post("/check-transaction", response_model=TransactionCheckResponse)
async def check_transaction(request: TransactionCheckRequest):
    if not supabase_admin:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    try:
        existing = supabase_admin.table("registrations").select("id").eq("transaction_id", request.transaction_id.strip()).execute()
        return TransactionCheckResponse(exists=len(existing.data) > 0)
    except Exception as e:
        logger.error("Transaction check failed: %s", e)
        return TransactionCheckResponse(exists=False)
