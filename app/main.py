from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routes import auth, users, faq, payment
from app.admin.routes import dashboard, users as admin_users, modules, tasks, teams, submissions, announcements, leaderboard, admins
from app.admin import auth as admin_auth

load_dotenv()

app = FastAPI(
    title="Virtual Hackathon 2K26 API",
    description="Backend API for Virtual Hackathon 2K26",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://virtual-hackathon-three.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(faq.router, prefix="/api/faq", tags=["faq"])
app.include_router(payment.router, prefix="/api/payment", tags=["payment"])

app.include_router(dashboard.router, prefix="/api/admin/dashboard", tags=["admin"])
app.include_router(admin_users.router, prefix="/api/admin/users", tags=["admin"])
app.include_router(modules.router, prefix="/api/admin/modules", tags=["admin"])
app.include_router(tasks.router, prefix="/api/admin/tasks", tags=["admin"])
app.include_router(teams.router, prefix="/api/admin/teams", tags=["admin"])
app.include_router(submissions.router, prefix="/api/admin/submissions", tags=["admin"])
app.include_router(announcements.router, prefix="/api/admin/announcements", tags=["admin"])
app.include_router(leaderboard.router, prefix="/api/admin/leaderboard", tags=["admin"])
app.include_router(admin_auth.router, prefix="/api/admin/auth", tags=["admin"])
app.include_router(admins.router, prefix="/api/admin/admins", tags=["admin"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Virtual Hackathon 2K26 API is running"}