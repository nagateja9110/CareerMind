"""Deterministic, in-memory stand-ins for MongoDB collections.

The eval harness wants the LLM's reasoning and tool-calling to be real, but
the *data* the tools return needs to be frozen so a run is reproducible and
doesn't depend on what's actually seeded in a live database or what Adzuna
happens to return today. These fakes implement just enough of the Motor
cursor API for SkillsLookupTool and JobSearchTool to run unmodified.
"""

from __future__ import annotations


class FakeCursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs

    def limit(self, _rows: int) -> "FakeCursor":
        return self

    async def to_list(self, length: int) -> list[dict]:
        return self._docs[:length]


class FakeCollection:
    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs

    async def find_one(self, _query: dict) -> dict | None:
        # The eval harness always wants SkillsLookupTool to fall through to
        # its real, production DEFAULT_ROLE_SKILLS table rather than depend
        # on a seeded taxonomy collection.
        return None

    def find(self, _query: dict) -> FakeCursor:
        return FakeCursor(self.docs)


class FakeDatabase:
    def __init__(self, jobs: list[dict]) -> None:
        self._jobs = FakeCollection(jobs)
        self._empty = FakeCollection([])

    def __getitem__(self, name: str) -> FakeCollection:
        return self._jobs if name == "jobs" else self._empty


SEEDED_JOBS: list[dict] = [
    {
        "title": "Data Engineer",
        "company": "BridgeStack",
        "location": "Bangalore",
        "skills": ["Python", "SQL", "Spark", "Airflow"],
    },
    {
        "title": "ML Engineer",
        "company": "Nimbus AI",
        "location": "Hyderabad",
        "skills": ["Python", "TensorFlow", "PyTorch", "MLOps"],
    },
    {
        "title": "DevOps Engineer",
        "company": "Cloudly",
        "location": "Pune",
        "skills": ["Docker", "Kubernetes", "AWS", "Terraform"],
    },
    {
        "title": "Frontend Developer",
        "company": "PixelWorks",
        "location": "Remote",
        "skills": ["JavaScript", "React", "CSS"],
    },
]
