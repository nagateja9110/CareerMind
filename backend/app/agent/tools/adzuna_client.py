from __future__ import annotations

import logging

import httpx

from app.models.chat import RecommendedJob

logger = logging.getLogger(__name__)

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/in/search/1"


class AdzunaClient:
    def __init__(self, app_id: str, app_key: str) -> None:
        self.app_id = app_id
        self.app_key = app_key

    @property
    def configured(self) -> bool:
        return bool(self.app_id and self.app_key)

    async def search(
        self,
        *,
        role: str | None = None,
        location: str | None = None,
        skills: list[str] | None = None,
        rows: int = 3,
    ) -> list[RecommendedJob]:
        if not self.configured:
            return []

        what_terms = " ".join(filter(None, [role, *(skills or [])]))
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": rows,
            "content-type": "application/json",
        }
        if what_terms:
            params["what"] = what_terms
        if location:
            params["where"] = location

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(ADZUNA_BASE_URL, params=params)
                response.raise_for_status()
        except httpx.HTTPError:
            logger.warning("Adzuna job search failed; falling back to local dataset.", exc_info=True)
            return []

        payload = response.json()
        results = payload.get("results", [])

        matched_skills = [skill for skill in (skills or []) if skill]
        return [
            RecommendedJob(
                title=result.get("title", "Unknown role"),
                company=result.get("company", {}).get("display_name", "Unknown company"),
                location=result.get("location", {}).get("display_name", "Unknown location"),
                matched_skills=matched_skills[:5],
            )
            for result in results
        ]
