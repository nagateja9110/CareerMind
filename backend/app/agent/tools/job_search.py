from __future__ import annotations

import re
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.chat import RecommendedJob


def _regex_filter(value: str) -> re.Pattern[str]:
    return re.compile(re.escape(value), re.IGNORECASE)


def _matches(pattern: re.Pattern[str], value: str) -> bool:
    return bool(pattern.search(value))


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
        role_pattern = _regex_filter(role) if role else None
        location_pattern = _regex_filter(location) if location else None
        skill_patterns = [_regex_filter(skill) for skill in (skills or []) if skill]

        conditions: list[dict[str, Any]] = []
        if role_pattern:
            conditions.append({"title": role_pattern})
        if location_pattern:
            conditions.append({"location": location_pattern})
        if skill_patterns:
            conditions.append({"skills": {"$in": skill_patterns}})

        collection = self.database[self.collection_name]
        if not conditions:
            cursor = collection.find({}).limit(rows)
            docs = await cursor.to_list(length=rows)
        else:
            # Match on ANY of the given filters, not all of them — a strict AND
            # against a finite dataset frequently returns nothing (e.g. no postings
            # in the requested city), then rank candidates by how many filters they
            # actually satisfy so the best partial matches surface first.
            query = conditions[0] if len(conditions) == 1 else {"$or": conditions}
            candidate_limit = max(rows * 10, 50)
            cursor = collection.find(query).limit(candidate_limit)
            candidates = await cursor.to_list(length=candidate_limit)
            candidates.sort(
                key=lambda doc: self._relevance(doc, role_pattern, location_pattern, skill_patterns),
                reverse=True,
            )
            docs = candidates[:rows]

        return [
            RecommendedJob(
                title=doc.get("title", "Unknown role"),
                company=doc.get("company", "Unknown company"),
                location=doc.get("location", "Unknown location"),
                matched_skills=doc.get("skills", [])[:5],
            )
            for doc in docs
        ]

    @staticmethod
    def _relevance(
        doc: dict[str, Any],
        role_pattern: re.Pattern[str] | None,
        location_pattern: re.Pattern[str] | None,
        skill_patterns: list[re.Pattern[str]],
    ) -> int:
        score = 0
        if role_pattern and _matches(role_pattern, doc.get("title", "")):
            score += 1
        if location_pattern and _matches(location_pattern, doc.get("location", "")):
            score += 1
        if skill_patterns:
            doc_skills = doc.get("skills", [])
            score += sum(
                1
                for pattern in skill_patterns
                if any(_matches(pattern, skill) for skill in doc_skills)
            )
        return score
