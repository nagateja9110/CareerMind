from dataclasses import dataclass
from types import SimpleNamespace

import httpx
import pytest
from openai import APIError

from app.agent.orchestrator import AgentContext, CareerAgentOrchestrator
from app.agent.tools.resume_parser import ResumeParserTool
from app.models.chat import RecommendedJob


@dataclass
class FakeSkillsResult:
    role: str
    required_skills: list
    related_roles: list
    source: str


class FakeSkillsLookupTool:
    async def lookup(self, role):
        return FakeSkillsResult(
            role=role,
            required_skills=["Python", "SQL", "Spark"],
            related_roles=["Analytics Engineer"],
            source="fallback",
        )


class FakeJobSearchTool:
    async def search(self, *, role=None, location=None, skills=None, rows=3):
        return [
            RecommendedJob(
                title="Data Engineer",
                company="BridgeStack",
                location="Bangalore",
                matched_skills=["Python", "SQL"],
            )
        ]


def _tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class ScriptedLLMClient:
    """Fake AsyncOpenAI client that returns scripted responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        next_item = self._responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item


def _build_orchestrator(llm_client):
    return CareerAgentOrchestrator(
        skills_lookup_tool=FakeSkillsLookupTool(),
        job_search_tool=FakeJobSearchTool(),
        resume_parser_tool=ResumeParserTool(),
        llm_client=llm_client,
        model="test-model",
        max_steps=3,
    )


async def test_heuristic_fallback_when_no_llm_client():
    orchestrator = _build_orchestrator(llm_client=None)
    result = await orchestrator.run(
        AgentContext(message="hi", resume_text="I know Python and SQL.", prior_messages=[])
    )
    assert "Python" in result.answer
    assert result.tool_calls[0].tool == "resume_parser"


async def test_agentic_run_calls_tools_and_returns_grounded_answer():
    client = ScriptedLLMClient(
        [
            _response(
                tool_calls=[_tool_call("call_1", "skills_taxonomy", '{"role": "Data Engineer"}')]
            ),
            _response(
                tool_calls=[_tool_call("call_2", "job_search", '{"role": "Data Engineer"}')]
            ),
            _response(content="You're missing Spark. BridgeStack is hiring."),
        ]
    )
    orchestrator = _build_orchestrator(llm_client=client)
    result = await orchestrator.run(
        AgentContext(message="What am I missing for Data Engineer?", resume_text="Python, SQL", prior_messages=[])
    )

    assert result.answer == "You're missing Spark. BridgeStack is hiring."
    assert [tc.tool for tc in result.tool_calls] == ["skills_taxonomy", "job_search"]
    assert result.recommended_jobs[0].company == "BridgeStack"


async def test_agentic_run_answers_directly_without_tools():
    client = ScriptedLLMClient([_response(content="You're on track already.")])
    orchestrator = _build_orchestrator(llm_client=client)
    result = await orchestrator.run(
        AgentContext(message="Am I doing okay?", resume_text=None, prior_messages=[])
    )

    assert result.answer == "You're on track already."
    assert result.tool_calls == []


async def test_agentic_run_degrades_gracefully_after_repeated_api_errors():
    error = APIError("boom", httpx.Request("POST", "http://example.com"), body=None)
    client = ScriptedLLMClient([error, error])
    orchestrator = _build_orchestrator(llm_client=client)
    result = await orchestrator.run(
        AgentContext(message="hello", resume_text=None, prior_messages=[])
    )

    assert "try rephrasing" in result.answer
    assert len(client.calls) == 2


async def test_agentic_run_recovers_after_one_transient_error():
    error = APIError("boom", httpx.Request("POST", "http://example.com"), body=None)
    client = ScriptedLLMClient([error, _response(content="Recovered fine.")])
    orchestrator = _build_orchestrator(llm_client=client)
    result = await orchestrator.run(
        AgentContext(message="hello", resume_text=None, prior_messages=[])
    )

    assert result.answer == "Recovered fine."
