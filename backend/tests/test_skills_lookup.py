from app.agent.tools.skills_lookup import DEFAULT_ROLE_SKILLS, SkillsLookupTool


class FakeCollection:
    def __init__(self, record=None):
        self.record = record

    async def find_one(self, _query):
        return self.record


class FakeDatabase:
    def __init__(self, record=None):
        self._collection = FakeCollection(record)

    def __getitem__(self, _name):
        return self._collection


async def test_lookup_returns_mongodb_record_when_present():
    record = {
        "role": "Data Engineer",
        "required_skills": ["Python", "SQL"],
        "related_roles": ["Analytics Engineer"],
    }
    tool = SkillsLookupTool(FakeDatabase(record), "skills_taxonomy")
    result = await tool.lookup("Data Engineer")
    assert result.source == "mongodb"
    assert result.required_skills == ["Python", "SQL"]


async def test_lookup_falls_back_to_default_taxonomy():
    tool = SkillsLookupTool(FakeDatabase(None), "skills_taxonomy")
    result = await tool.lookup("Data Engineer")
    assert result.source == "fallback"
    assert result.required_skills == DEFAULT_ROLE_SKILLS["Data Engineer"]["required_skills"]


async def test_lookup_returns_empty_for_unknown_role():
    tool = SkillsLookupTool(FakeDatabase(None), "skills_taxonomy")
    result = await tool.lookup("Astronaut")
    assert result.source == "empty"
    assert result.required_skills == []
    assert result.related_roles == []


def test_taxonomy_has_at_least_twenty_roles():
    assert len(DEFAULT_ROLE_SKILLS) >= 20
