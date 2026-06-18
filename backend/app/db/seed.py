from __future__ import annotations

from typing import Any

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agent.tools.skills_lookup import DEFAULT_ROLE_SKILLS
from app.core.config import get_settings


settings = get_settings()

SAMPLE_JOBS: list[dict[str, Any]] = [
    {
        "id": "job-001",
        "title": "Data Engineer",
        "company": "BridgeStack",
        "location": "Bangalore",
        "skills": ["Python", "SQL", "Spark", "Airflow", "AWS"],
        "description": "Build batch and streaming pipelines for analytics teams.",
        "seniority": "Mid",
    },
    {
        "id": "job-002",
        "title": "ML Engineer",
        "company": "NeuronForge",
        "location": "Bangalore",
        "skills": ["Python", "PyTorch", "AWS", "MLOps"],
        "description": "Productionize model training and inference systems.",
        "seniority": "Mid",
    },
    {
        "id": "job-003",
        "title": "Backend Developer",
        "company": "Railbyte",
        "location": "Hyderabad",
        "skills": ["Python", "APIs", "SQL", "Docker"],
        "description": "Develop internal platform services and APIs.",
        "seniority": "Mid",
    },
    {
        "id": "job-004",
        "title": "Analytics Engineer",
        "company": "MetricLoop",
        "location": "Bangalore",
        "skills": ["SQL", "Python", "ETL", "Airflow"],
        "description": "Model warehouse data and support self-serve analytics.",
        "seniority": "Mid",
    },
]


async def seed_skills_taxonomy(database: AsyncIOMotorDatabase) -> None:
    collection = database[settings.skills_taxonomy_collection]
    for role, payload in DEFAULT_ROLE_SKILLS.items():
        await collection.update_one(
            {"role": role},
            {
                "$set": {
                    "role": role,
                    "required_skills": payload["required_skills"],
                    "related_roles": payload["related_roles"],
                }
            },
            upsert=True,
        )


async def seed_solr_jobs() -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            status_response = await client.get(
                f"{settings.solr_url}/select",
                params={"q": "*:*", "rows": 0, "wt": "json"},
            )
            status_response.raise_for_status()
        except httpx.HTTPError:
            return

        num_docs = status_response.json().get("response", {}).get("numFound", 0)
        if num_docs > 0:
            return

        try:
            update_response = await client.post(
                f"{settings.solr_url}/update",
                params={"commit": "true"},
                json=SAMPLE_JOBS,
            )
            update_response.raise_for_status()
        except httpx.HTTPError:
            return
