from __future__ import annotations

from typing import Any

import httpx

from app.models.chat import RecommendedJob


class JobSearchTool:
    def __init__(self, solr_url: str) -> None:
        self.solr_url = solr_url.rstrip("/")

    async def search(
        self,
        *,
        role: str | None = None,
        location: str | None = None,
        skills: list[str] | None = None,
        rows: int = 3,
    ) -> list[RecommendedJob]:
        query_parts: list[str] = []
        if role:
            query_parts.append(f'title:"{role}"')
        if location:
            query_parts.append(f'location:"{location}"')
        if skills:
            query_parts.extend(f'skills:"{skill}"' for skill in skills if skill)

        query = " OR ".join(query_parts) if query_parts else "*:*"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.solr_url}/select",
                    params={
                        "q": query,
                        "rows": rows,
                        "wt": "json",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError:
            return []

        payload = response.json()
        docs: list[dict[str, Any]] = payload.get("response", {}).get("docs", [])
        jobs: list[RecommendedJob] = []
        for doc in docs:
            jobs.append(
                RecommendedJob(
                    title=doc.get("title", "Unknown role"),
                    company=doc.get("company", "Unknown company"),
                    location=doc.get("location", "Unknown location"),
                    matched_skills=doc.get("skills", [])[:5],
                )
            )
        return jobs
