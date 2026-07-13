import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.services.supabase_service import supabase_admin as supabase

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", os.getenv("SUPABASE_ANON_KEY", "fallback-secret-change-me"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)
router = APIRouter()

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: str
    email: str
    full_name: str
    role: str

class AdminChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

def verify_password(plain: str, hashed: str) -> bool:
    if len(plain) > 72:
        plain = plain[:72]
    return pwd_context.verify(plain, hashed)

def hash_password(plain: str) -> str:
    if len(plain) > 72:
        plain = plain[:72]
    return pwd_context.hash(plain)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "admin":
        raise HTTPException(status_code=403, detail="Not an admin token")
    return payload

def require_role(*roles: str):
    async def role_checker(admin: dict = Depends(get_current_admin)):
        if admin.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return admin
    return role_checker

@router.post("/login", response_model=AdminTokenResponse)
async def admin_login(req: AdminLoginRequest):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    resp = supabase.from_("admin_users").select("*").eq("email", req.email).single().execute()
    if not resp.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    admin = resp.data
    if not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is disabled")

    if not verify_password(req.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": admin["id"],
        "email": admin["email"],
        "role": admin["role"],
        "type": "admin",
    })

    supabase.from_("admin_users").update({"last_login": datetime.now(timezone.utc).isoformat()}).eq("id", admin["id"]).execute()

    return AdminTokenResponse(
        access_token=token,
        admin_id=admin["id"],
        email=admin["email"],
        full_name=admin.get("full_name", ""),
        role=admin["role"],
    )

@router.get("/me")
async def admin_me(admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("admin_users").select("id, email, full_name, role, last_login, created_at").eq("id", admin["sub"]).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Admin not found")
    return resp.data

@router.post("/change-password")
async def change_password(req: AdminChangePasswordRequest, admin: dict = Depends(get_current_admin)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    resp = supabase.from_("admin_users").select("password_hash").eq("id", admin["sub"]).single().execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Admin not found")
    if not verify_password(req.current_password, resp.data["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    new_hash = hash_password(req.new_password)
    supabase.from_("admin_users").update({"password_hash": new_hash}).eq("id", admin["sub"]).execute()
    return {"message": "Password changed successfully"}
