from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pypdf import PdfReader

from app.agent.tools.resume_parser import ResumeParserTool
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.db.mongodb import get_database
from app.models.resume import ResumeResponse


router = APIRouter(prefix="/resume", tags=["resume"])
settings = get_settings()


def _get_user_id(user: dict) -> str:
    return str(user["_id"])


async def _extract_resume_text(upload: UploadFile) -> str:
    content = await upload.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    content_type = upload.content_type or ""
    filename = (upload.filename or "").lower()

    if content_type == "text/plain" or filename.endswith(".txt"):
        return content.decode("utf-8", errors="ignore").strip()

    if content_type == "application/pdf" or filename.endswith(".pdf"):
        reader = PdfReader(BytesIO(content))
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        if text:
            return text
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract text from the PDF.",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Only PDF and plain text resumes are supported right now.",
    )


@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    database: AsyncIOMotorDatabase = Depends(get_database),
) -> ResumeResponse:
    raw_text = await _extract_resume_text(file)
    parser = ResumeParserTool()
    parsed = parser.parse(raw_text)
    now = datetime.now(UTC)

    document = {
        "user_id": _get_user_id(current_user),
        "filename": file.filename,
        "content_type": file.content_type,
        "raw_text": raw_text,
        "parsed_skills": parsed.skills,
        "experience_years": parsed.experience_years,
        "uploaded_at": now,
    }
    await database[settings.resumes_collection].insert_one(document)

    return ResumeResponse(
        raw_text=raw_text,
        parsed_skills=parsed.skills,
        experience_years=parsed.experience_years,
        uploaded_at=now,
    )


@router.get("", response_model=ResumeResponse)
async def get_latest_resume(
    current_user: dict = Depends(get_current_user),
    database: AsyncIOMotorDatabase = Depends(get_database),
) -> ResumeResponse:
    resume = await database[settings.resumes_collection].find_one(
        {"user_id": _get_user_id(current_user)},
        sort=[("uploaded_at", -1)],
    )
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found for this user.",
        )

    return ResumeResponse(
        raw_text=resume["raw_text"],
        parsed_skills=resume.get("parsed_skills", []),
        experience_years=resume.get("experience_years"),
        uploaded_at=resume["uploaded_at"],
    )
