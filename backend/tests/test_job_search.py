import httpx
import respx

from app.agent.tools.job_search import JobSearchTool


SOLR_URL = "http://solr:8983/solr/jobs"


@respx.mock
async def test_search_returns_parsed_jobs():
    respx.get(f"{SOLR_URL}/select").mock(
        return_value=httpx.Response(
            200,
            json={
                "response": {
                    "docs": [
                        {
                            "title": "Data Engineer",
                            "company": "BridgeStack",
                            "location": "Bangalore",
                            "skills": ["Python", "SQL", "Spark"],
                        }
                    ]
                }
            },
        )
    )

    tool = JobSearchTool(SOLR_URL)
    jobs = await tool.search(role="Data Engineer", location="Bangalore", skills=["Python"])

    assert len(jobs) == 1
    assert jobs[0].title == "Data Engineer"
    assert jobs[0].company == "BridgeStack"
    assert jobs[0].matched_skills == ["Python", "SQL", "Spark"]


@respx.mock
async def test_search_returns_empty_list_on_http_error():
    respx.get(f"{SOLR_URL}/select").mock(return_value=httpx.Response(500))

    tool = JobSearchTool(SOLR_URL)
    jobs = await tool.search(role="Data Engineer")

    assert jobs == []


@respx.mock
async def test_search_returns_empty_list_on_connection_error():
    respx.get(f"{SOLR_URL}/select").mock(side_effect=httpx.ConnectError("refused"))

    tool = JobSearchTool(SOLR_URL)
    jobs = await tool.search(role="Data Engineer")

    assert jobs == []


@respx.mock
async def test_search_builds_wildcard_query_with_no_filters():
    route = respx.get(f"{SOLR_URL}/select").mock(
        return_value=httpx.Response(200, json={"response": {"docs": []}})
    )

    tool = JobSearchTool(SOLR_URL)
    await tool.search()

    assert route.calls.last.request.url.params["q"] == "*:*"
