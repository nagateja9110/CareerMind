from __future__ import annotations

from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorDatabase


DEFAULT_ROLE_SKILLS = {
    "Data Engineer": {
        "required_skills": ["Python", "SQL", "Spark", "Airflow", "AWS", "ETL"],
        "related_roles": ["Analytics Engineer", "Backend Engineer", "ML Engineer"],
    },
    "ML Engineer": {
        "required_skills": ["Python", "Machine Learning", "TensorFlow", "PyTorch", "AWS", "MLOps"],
        "related_roles": ["Data Scientist", "Data Engineer", "Backend Engineer"],
    },
    "Backend Developer": {
        "required_skills": ["Python", "Java", "APIs", "SQL", "Docker", "System Design"],
        "related_roles": ["Software Engineer", "Platform Engineer", "Data Engineer"],
    },
    "Data Analyst": {
        "required_skills": ["SQL", "Excel", "Python", "Statistics", "Tableau", "Communication"],
        "related_roles": ["Business Analyst", "Analytics Engineer", "Data Scientist"],
    },
}


@dataclass
class SkillsLookupResult:
    role: str
    required_skills: list[str]
    related_roles: list[str]
    source: str


class SkillsLookupTool:
    def __init__(self, database: AsyncIOMotorDatabase, collection_name: str) -> None:
        self.database = database
        self.collection_name = collection_name

    async def lookup(self, role: str) -> SkillsLookupResult:
        record = await self.database[self.collection_name].find_one({"role": role})
        if record:
            return SkillsLookupResult(
                role=record["role"],
                required_skills=record.get("required_skills", []),
                related_roles=record.get("related_roles", []),
                source="mongodb",
            )

        fallback = DEFAULT_ROLE_SKILLS.get(role)
        if fallback:
            return SkillsLookupResult(
                role=role,
                required_skills=fallback["required_skills"],
                related_roles=fallback["related_roles"],
                source="fallback",
            )

        return SkillsLookupResult(
            role=role,
            required_skills=[],
            related_roles=[],
            source="empty",
        )
