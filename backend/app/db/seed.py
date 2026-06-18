from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.agent.tools.skills_lookup import DEFAULT_ROLE_SKILLS
from app.core.config import get_settings


settings = get_settings()

JOBS_DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs_dataset.csv"


def _load_jobs_dataset() -> list[dict[str, Any]]:
    if not JOBS_DATASET_PATH.exists():
        return []

    jobs: list[dict[str, Any]] = []
    with JOBS_DATASET_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            jobs.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "company": row["company"],
                    "location": row["location"],
                    "skills": [skill for skill in row["skills"].split(";") if skill],
                    "description": row["description"],
                    "seniority": row["seniority"],
                }
            )
    return jobs


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

        jobs = _load_jobs_dataset()
        if not jobs:
            return

        try:
            update_response = await client.post(
                f"{settings.solr_url}/update",
                params={"commit": "true"},
                json=jobs,
            )
            update_response.raise_for_status()
        except httpx.HTTPError:
            return
