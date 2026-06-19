from app.agent.tools.job_search import JobSearchTool
from app.models.chat import RecommendedJob


class FakeAdzunaClient:
    def __init__(self, results, configured=True):
        self.results = results
        self.configured = configured
        self.called_with = None

    async def search(self, **kwargs):
        self.called_with = kwargs
        return self.results


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def limit(self, _rows):
        return self

    async def to_list(self, length):
        return self._docs[:length]


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs
        self.last_query = None

    def find(self, query):
        self.last_query = query
        return FakeCursor(self.docs)


class FakeDatabase:
    def __init__(self, docs):
        self._collection = FakeCollection(docs)

    def __getitem__(self, _name):
        return self._collection


async def test_search_returns_parsed_jobs():
    docs = [
        {
            "title": "Data Engineer",
            "company": "BridgeStack",
            "location": "Bangalore",
            "skills": ["Python", "SQL", "Spark"],
        }
    ]
    database = FakeDatabase(docs)
    tool = JobSearchTool(database, "jobs")
    jobs = await tool.search(role="Data Engineer", location="Bangalore", skills=["Python"])

    assert len(jobs) == 1
    assert jobs[0].title == "Data Engineer"
    assert jobs[0].company == "BridgeStack"
    assert jobs[0].matched_skills == ["Python", "SQL", "Spark"]


async def test_search_returns_empty_list_when_nothing_matches():
    database = FakeDatabase([])
    tool = JobSearchTool(database, "jobs")
    jobs = await tool.search(role="Astronaut")

    assert jobs == []


async def test_search_builds_empty_query_with_no_filters():
    database = FakeDatabase([])
    tool = JobSearchTool(database, "jobs")
    await tool.search()

    assert database._collection.last_query == {}


async def test_search_filters_on_title_location_and_skills():
    database = FakeDatabase([])
    tool = JobSearchTool(database, "jobs")
    await tool.search(role="Data Engineer", location="Bangalore", skills=["Python", "SQL"])

    query = database._collection.last_query
    conditions = query["$or"]
    assert {"title", "location", "skills"} == {
        key for condition in conditions for key in condition
    }
    title_condition = next(c for c in conditions if "title" in c)
    skills_condition = next(c for c in conditions if "skills" in c)
    assert title_condition["title"].pattern == "Data\\ Engineer"
    assert skills_condition["skills"]["$in"][0].pattern == "Python"


async def test_search_ranks_partial_matches_above_non_matches():
    docs = [
        {
            "title": "Backend Developer",
            "company": "NoMatchCo",
            "location": "Remote",
            "skills": ["Java"],
        },
        {
            "title": "Data Engineer",
            "company": "PartialMatchCo",
            "location": "Austin, TX",
            "skills": ["Python", "SQL"],
        },
    ]
    database = FakeDatabase(docs)
    tool = JobSearchTool(database, "jobs")
    jobs = await tool.search(role="Data Engineer", location="Bangalore", skills=["Python"], rows=2)

    assert jobs[0].company == "PartialMatchCo"


async def test_search_prefers_adzuna_results_when_configured():
    database = FakeDatabase([{"title": "Should not be used", "company": "Mongo", "location": "X", "skills": []}])
    live_job = RecommendedJob(title="AI Engineer", company="Adzuna Co", location="Bangalore", matched_skills=["python"])
    adzuna_client = FakeAdzunaClient([live_job])
    tool = JobSearchTool(database, "jobs", adzuna_client)

    jobs = await tool.search(role="AI", location="Bangalore", skills=["python"])

    assert jobs == [live_job]
    assert adzuna_client.called_with == {
        "role": "AI",
        "location": "Bangalore",
        "skills": ["python"],
        "rows": 3,
    }


async def test_search_falls_back_to_mongo_when_adzuna_returns_nothing():
    docs = [{"title": "Data Engineer", "company": "BridgeStack", "location": "Bangalore", "skills": ["Python"]}]
    database = FakeDatabase(docs)
    adzuna_client = FakeAdzunaClient([])
    tool = JobSearchTool(database, "jobs", adzuna_client)

    jobs = await tool.search(role="Data Engineer", location="Bangalore", skills=["Python"])

    assert len(jobs) == 1
    assert jobs[0].company == "BridgeStack"


async def test_search_skips_adzuna_when_not_configured():
    docs = [{"title": "Data Engineer", "company": "BridgeStack", "location": "Bangalore", "skills": ["Python"]}]
    database = FakeDatabase(docs)
    adzuna_client = FakeAdzunaClient([], configured=False)
    tool = JobSearchTool(database, "jobs", adzuna_client)

    jobs = await tool.search(role="Data Engineer")

    assert adzuna_client.called_with is None
    assert len(jobs) == 1
