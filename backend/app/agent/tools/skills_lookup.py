from __future__ import annotations

import re
from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorDatabase


DEFAULT_ROLE_SKILLS = {
    "Data Engineer": {
        "required_skills": ["Python", "SQL", "Spark", "Airflow", "AWS", "ETL"],
        "related_roles": ["Analytics Engineer", "Backend Developer", "ML Engineer"],
    },
    "ML Engineer": {
        "required_skills": ["Python", "Machine Learning", "TensorFlow", "PyTorch", "AWS", "MLOps"],
        "related_roles": ["Data Scientist", "Data Engineer", "Backend Developer"],
    },
    "Backend Developer": {
        "required_skills": ["Python", "Java", "APIs", "SQL", "Docker", "System Design"],
        "related_roles": ["Software Engineer", "Platform Engineer", "Data Engineer"],
    },
    "Data Analyst": {
        "required_skills": ["SQL", "Excel", "Python", "Statistics", "Tableau", "Communication"],
        "related_roles": ["Business Analyst", "Analytics Engineer", "Data Scientist"],
    },
    "Data Scientist": {
        "required_skills": ["Python", "Machine Learning", "Statistics", "SQL", "Pandas", "Communication"],
        "related_roles": ["ML Engineer", "Data Analyst", "Analytics Engineer"],
    },
    "Frontend Developer": {
        "required_skills": ["JavaScript", "React", "HTML", "CSS", "TypeScript", "APIs"],
        "related_roles": ["Full Stack Developer", "UI/UX Designer", "Software Engineer"],
    },
    "Full Stack Developer": {
        "required_skills": ["JavaScript", "React", "Node.js", "SQL", "APIs", "Docker"],
        "related_roles": ["Frontend Developer", "Backend Developer", "Software Engineer"],
    },
    "Software Engineer": {
        "required_skills": ["Python", "Java", "Git", "System Design", "APIs", "SQL"],
        "related_roles": ["Backend Developer", "Full Stack Developer", "Platform Engineer"],
    },
    "DevOps Engineer": {
        "required_skills": ["Docker", "Kubernetes", "CI/CD", "AWS", "Terraform", "Linux"],
        "related_roles": ["Site Reliability Engineer", "Cloud Engineer", "Platform Engineer"],
    },
    "Site Reliability Engineer": {
        "required_skills": ["Kubernetes", "Linux", "Monitoring", "AWS", "CI/CD", "System Design"],
        "related_roles": ["DevOps Engineer", "Cloud Engineer", "Platform Engineer"],
    },
    "Cloud Engineer": {
        "required_skills": ["AWS", "GCP", "Terraform", "Docker", "Kubernetes", "Networking"],
        "related_roles": ["DevOps Engineer", "Site Reliability Engineer", "Platform Engineer"],
    },
    "Platform Engineer": {
        "required_skills": ["Kubernetes", "Docker", "CI/CD", "AWS", "System Design", "Python"],
        "related_roles": ["DevOps Engineer", "Backend Developer", "Cloud Engineer"],
    },
    "Security Engineer": {
        "required_skills": ["Networking", "Linux", "Penetration Testing", "Python", "Cloud Security", "Incident Response"],
        "related_roles": ["DevOps Engineer", "Cloud Engineer", "Backend Developer"],
    },
    "QA Engineer": {
        "required_skills": ["Selenium", "Test Automation", "Python", "API Testing", "CI/CD", "SQL"],
        "related_roles": ["Software Engineer", "Backend Developer", "DevOps Engineer"],
    },
    "Mobile Developer (Android)": {
        "required_skills": ["Kotlin", "Android SDK", "Java", "APIs", "Git", "Material Design"],
        "related_roles": ["Mobile Developer (iOS)", "Frontend Developer", "Software Engineer"],
    },
    "Mobile Developer (iOS)": {
        "required_skills": ["Swift", "iOS SDK", "Xcode", "APIs", "Git", "UIKit"],
        "related_roles": ["Mobile Developer (Android)", "Frontend Developer", "Software Engineer"],
    },
    "Product Manager": {
        "required_skills": ["Product Strategy", "Roadmapping", "Communication", "SQL", "Agile", "User Research"],
        "related_roles": ["Business Analyst", "UI/UX Designer", "Data Analyst"],
    },
    "Business Analyst": {
        "required_skills": ["SQL", "Excel", "Communication", "Statistics", "Tableau", "Agile"],
        "related_roles": ["Data Analyst", "Product Manager", "Analytics Engineer"],
    },
    "UI/UX Designer": {
        "required_skills": ["Figma", "Wireframing", "User Research", "Prototyping", "Communication", "HTML"],
        "related_roles": ["Product Manager", "Frontend Developer", "Business Analyst"],
    },
    "Database Administrator": {
        "required_skills": ["SQL", "PostgreSQL", "MySQL", "Backup & Recovery", "Linux", "Performance Tuning"],
        "related_roles": ["Data Engineer", "Backend Developer", "Cloud Engineer"],
    },
    "Analytics Engineer": {
        "required_skills": ["SQL", "Python", "ETL", "dbt", "Airflow", "Data Modeling"],
        "related_roles": ["Data Engineer", "Data Analyst", "Data Scientist"],
    },
}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def _closest_known_role(role: str, known_roles: list[str]) -> str | None:
    """Map free-text role phrasing (e.g. 'Software Development Engineer') to the
    closest entry in the fixed taxonomy (e.g. 'Software Engineer') so minor wording
    differences from the LLM's tool call don't return an empty result."""
    role_words = _words(role)
    if not role_words:
        return None

    best_role: str | None = None
    best_score = 0.0
    for known in known_roles:
        if known.lower() == role.strip().lower():
            return known
        known_words = _words(known)
        union = role_words | known_words
        if not union:
            continue
        score = len(role_words & known_words) / len(union)
        if score > best_score:
            best_score = score
            best_role = known

    return best_role if best_score >= 0.4 else None


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
        canonical_role = _closest_known_role(role, list(DEFAULT_ROLE_SKILLS)) or role

        record = await self.database[self.collection_name].find_one(
            {"role": re.compile(f"^{re.escape(canonical_role)}$", re.IGNORECASE)}
        )
        if record:
            return SkillsLookupResult(
                role=record["role"],
                required_skills=record.get("required_skills", []),
                related_roles=record.get("related_roles", []),
                source="mongodb",
            )

        fallback = DEFAULT_ROLE_SKILLS.get(canonical_role)
        if fallback:
            return SkillsLookupResult(
                role=canonical_role,
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
