from fastapi import APIRouter, Depends, Query

from app.agent.tools.job_search import JobSearchTool
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.models.chat import RecommendedJob


router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()


@router.get("/search", response_model=list[RecommendedJob])
async def search_jobs(
    role: str | None = Query(default=None, min_length=2),
    location: str | None = Query(default=None, min_length=2),
    skills: list[str] = Query(default=[]),
    _: dict = Depends(get_current_user),
) -> list[RecommendedJob]:
    tool = JobSearchTool(settings.solr_url)
    return await tool.search(
        role=role,
        location=location,
        skills=skills,
        rows=8,
    )
