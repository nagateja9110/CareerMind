from __future__ import annotations

from dataclasses import dataclass
import re


COMMON_SKILLS = [
    "etl",
    "apis",
    "system design",
    "excel",
    "statistics",
    "tableau",
    "tensorflow",
    "pytorch",
    "mlops",
    "python",
    "sql",
    "java",
    "javascript",
    "react",
    "fastapi",
    "spark",
    "airflow",
    "aws",
    "gcp",
    "docker",
    "kubernetes",
    "machine learning",
    "pandas",
    "mongodb",
]


@dataclass
class ParsedResume:
    skills: list[str]
    experience_years: int | None


class ResumeParserTool:
    def parse(self, resume_text: str) -> ParsedResume:
        normalized = resume_text.lower()
        skills = [self._display_skill(skill) for skill in COMMON_SKILLS if skill in normalized]

        years_match = re.search(r"(\d+)\+?\s+years", normalized)
        experience_years = int(years_match.group(1)) if years_match else None

        return ParsedResume(skills=skills, experience_years=experience_years)

    def _display_skill(self, skill: str) -> str:
        aliases = {
            "aws": "AWS",
            "gcp": "GCP",
            "sql": "SQL",
            "etl": "ETL",
            "apis": "APIs",
            "mlops": "MLOps",
        }
        return aliases.get(skill, skill.title())
