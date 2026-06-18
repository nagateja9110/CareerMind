from __future__ import annotations

from dataclasses import dataclass
import re


COMMON_SKILLS = [
    "etl",
    "apis",
    "api testing",
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
    "typescript",
    "react",
    "node.js",
    "html",
    "css",
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
    "postgresql",
    "mysql",
    "git",
    "ci/cd",
    "terraform",
    "linux",
    "monitoring",
    "networking",
    "penetration testing",
    "cloud security",
    "incident response",
    "selenium",
    "test automation",
    "kotlin",
    "android sdk",
    "material design",
    "swift",
    "ios sdk",
    "xcode",
    "uikit",
    "product strategy",
    "roadmapping",
    "agile",
    "user research",
    "figma",
    "wireframing",
    "prototyping",
    "backup & recovery",
    "performance tuning",
    "dbt",
    "data modeling",
    "communication",
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
            "api testing": "API Testing",
            "mlops": "MLOps",
            "tensorflow": "TensorFlow",
            "pytorch": "PyTorch",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "node.js": "Node.js",
            "html": "HTML",
            "css": "CSS",
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "ci/cd": "CI/CD",
            "android sdk": "Android SDK",
            "ios sdk": "iOS SDK",
            "uikit": "UIKit",
            "dbt": "dbt",
        }
        return aliases.get(skill, skill.title())
