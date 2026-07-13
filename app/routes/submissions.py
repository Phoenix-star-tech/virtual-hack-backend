import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import re

from app.services.supabase_service import supabase_admin as db
from app.services.cloudinary_service import upload_image, is_available

logger = logging.getLogger("submissions")

router = APIRouter()


class SubmitRequest(BaseModel):
    task_id: str
    submitter_id: str
    answer: str = ""
    files: list = []


def _validate_answer(answer_type: str, answer: str, files: list):
    if answer_type == "quiz":
        if answer not in ("A", "B", "C", "D"):
            raise HTTPException(status_code=400, detail="Quiz answer must be one of: A, B, C, D")
    elif answer_type == "link":
        if not re.match(r"^https?://", answer.strip()):
            raise HTTPException(status_code=400, detail="Link answer must be a valid URL starting with http:// or https://")
    elif answer_type == "description":
        if not answer.strip():
            raise HTTPException(status_code=400, detail="Description answer cannot be empty")
    elif answer_type == "image":
        if not files and not re.match(r"^https?://", answer.strip()):
            raise HTTPException(status_code=400, detail="Image submission requires an uploaded image or valid image URL")


@router.post("/")
async def create_submission(req: SubmitRequest):
    if not db:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    task = db.from_("tasks").select("id, answer_type").eq("id", req.task_id).single().execute()
    if not task.data:
        raise HTTPException(status_code=404, detail="Task not found")

    answer_type = task.data.get("answer_type", "link")
    _validate_answer(answer_type, req.answer, req.files)

    existing = db.from_("submissions").select("id").eq("task_id", req.task_id).eq("submitter_id", req.submitter_id).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="You have already submitted this task")

    payload = {
        "task_id": req.task_id,
        "submitter_id": req.submitter_id,
        "notes": req.answer,
        "files": req.files,
        "links": [],
        "status": "pending",
    }
    resp = db.from_("submissions").insert(payload).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create submission")
    return resp.data[0]


@router.post("/upload-image")
async def upload_submission_image(file: UploadFile = File(...)):
    if not db:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    if not is_available():
        raise HTTPException(status_code=503, detail="Cloudinary is not configured")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    try:
        contents = await file.read()
        result = upload_image(contents, folder="virtual_hack_2k26/submissions")
        image_url = result.get("secure_url")
    except Exception as e:
        logger.error("Cloudinary upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to upload image")
    return {"url": image_url}


@router.get("/my")
async def get_my_submissions(submitter_id: str = ""):
    if not db:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    if not submitter_id:
        return {"submissions": []}
    resp = db.from_("submissions").select("*").eq("submitter_id", submitter_id).order("created_at", desc=True).execute()
    for s in resp.data or []:
        task = db.from_("tasks").select("title, answer_type, quiz_options").eq("id", s["task_id"]).single().execute()
        s["task_title"] = task.data["title"] if task.data else ""
        s["answer_type"] = task.data["answer_type"] if task.data else "link"
        s["quiz_options"] = task.data["quiz_options"] if task.data else []
    return {"submissions": resp.data or []}
