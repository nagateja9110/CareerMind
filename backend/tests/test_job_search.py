from app.agent.tools.job_search import JobSearchTool


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
    assert set(query.keys()) == {"title", "location", "skills"}
    assert query["title"].pattern == "Data\\ Engineer"
    assert query["skills"]["$in"][0].pattern == "Python"
