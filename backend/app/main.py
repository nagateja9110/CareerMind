from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.mongodb import close_mongo_client, connect_to_mongo
from app.db.seed import seed_jobs, seed_skills_taxonomy
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.routes.profile import router as profile_router
from app.routes.resume import router as resume_router


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    database = await connect_to_mongo()
    await seed_skills_taxonomy(database)
    await seed_jobs(database)
    try:
        yield
    finally:
        close_mongo_client()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Agent-driven career advisor API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(jobs_router, prefix=settings.api_prefix)
app.include_router(profile_router, prefix=settings.api_prefix)
app.include_router(resume_router, prefix=settings.api_prefix)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "CareerMind backend is running"}
