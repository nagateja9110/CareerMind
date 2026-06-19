from __future__ import annotations

import re
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.chat import RecommendedJob


def _regex_filter(value: str) -> re.Pattern[str]:
    return re.compile(re.escape(value), re.IGNORECASE)


class JobSearchTool:
    def __init__(self, database: AsyncIOMotorDatabase, collection_name: str) -> None:
        self.database = database
        self.collection_name = collection_name

    async def search(
        self,
        *,
        role: str | None = None,
        location: str | None = None,
        skills: list[str] | None = None,
        rows: int = 3,
    ) -> list[RecommendedJob]:
        query: dict[str, Any] = {}
        if role:
            query["title"] = _regex_filter(role)
        if location:
            query["location"] = _regex_filter(location)
        if skills:
            clean_skills = [skill for skill in skills if skill]
            if clean_skills:
                query["skills"] = {"$in": [_regex_filter(skill) for skill in clean_skills]}

        cursor = self.database[self.collection_name].find(query).limit(rows)
        docs = await cursor.to_list(length=rows)

        return [
            RecommendedJob(
                title=doc.get("title", "Unknown role"),
                company=doc.get("company", "Unknown company"),
                location=doc.get("location", "Unknown location"),
                matched_skills=doc.get("skills", [])[:5],
            )
            for doc in docs
        ]
