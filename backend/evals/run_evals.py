"""Run the agent orchestrator against fixed scenarios and score the output.

This is deliberately not a pytest suite: it makes real calls to the
configured LLM (so the agent's actual tool-choice reasoning is under test,
not a scripted fake), while keeping the data those tools return frozen
(see evals/fakes.py) so a failing run always points at the agent's
behavior rather than a flaky upstream API or a changed dataset.

Usage:
    cd backend
    python -m evals.run_evals
"""

from __future__ import annotations

import asyncio
import sys

from openai import AsyncOpenAI

from app.agent.orchestrator import AgentContext, CareerAgentOrchestrator
from app.agent.tools.job_search import JobSearchTool
from app.agent.tools.resume_parser import ResumeParserTool
from app.agent.tools.skills_lookup import SkillsLookupTool
from app.core.config import get_settings
from evals.fakes import SEEDED_JOBS, FakeDatabase
from evals.fixtures import CASES, EvalCase


def _terms_found(answer: str, terms: list[str]) -> list[str]:
    lowered = answer.lower()
    return [term for term in terms if term.lower() in lowered]


def _score_case(case: EvalCase, actual_tools: set[str], answer: str) -> tuple[bool, list[str]]:
    failures: list[str] = []

    if case.strict_tools:
        if actual_tools != case.expected_tools:
            failures.append(f"expected tools {sorted(case.expected_tools)}, got {sorted(actual_tools)}")
    elif not case.expected_tools.issubset(actual_tools):
        failures.append(f"expected at least {sorted(case.expected_tools)}, got {sorted(actual_tools)}")

    missing_required = [term for term in case.required_terms if term not in _terms_found(answer, case.required_terms)]
    if missing_required:
        failures.append(f"answer is missing expected terms: {missing_required}")

    hallucinated = _terms_found(answer, case.forbidden_terms)
    if hallucinated:
        failures.append(f"answer contains terms it shouldn't have invented: {hallucinated}")

    return not failures, failures


async def _run_case(orchestrator: CareerAgentOrchestrator, case: EvalCase) -> dict:
    result = await orchestrator.run(
        AgentContext(
            message=case.message,
            resume_text=case.resume_text,
            prior_messages=case.prior_messages,
        )
    )
    actual_tools = {tc.tool for tc in result.tool_calls}
    passed, failures = _score_case(case, actual_tools, result.answer)
    return {
        "case": case,
        "answer": result.answer,
        "actual_tools": actual_tools,
        "passed": passed,
        "failures": failures,
    }


async def main() -> int:
    settings = get_settings()
    if not settings.groq_api_key:
        print(
            "GROQ_API_KEY is not set — skipping evals (they exercise real LLM "
            "tool-calling, not the heuristic fallback). Set it in backend/.env "
            "and re-run.",
        )
        return 0

    llm_client = AsyncOpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
    orchestrator = CareerAgentOrchestrator(
        skills_lookup_tool=SkillsLookupTool(FakeDatabase(SEEDED_JOBS), "skills_taxonomy"),
        job_search_tool=JobSearchTool(FakeDatabase(SEEDED_JOBS), "jobs"),
        resume_parser_tool=ResumeParserTool(),
        llm_client=llm_client,
        model=settings.groq_model,
        max_steps=settings.agent_max_tool_steps,
    )

    # Run sequentially with a short gap, not via asyncio.gather: each case can
    # take up to max_steps LLM calls, and firing them all at once (or back to
    # back across repeated runs) reliably trips the Groq free-tier rate limit,
    # which then looks like a grounding failure (the orchestrator's "reasoning
    # step failed" fallback) instead of what it actually is — a 429.
    results = []
    for index, case in enumerate(CASES):
        if index:
            await asyncio.sleep(2)
        results.append(await _run_case(orchestrator, case))

    failed = 0
    for outcome in results:
        case: EvalCase = outcome["case"]
        status = "PASS" if outcome["passed"] else "FAIL"
        print(f"[{status}] {case.name} — {case.description}")
        print(f"       tools called: {sorted(outcome['actual_tools']) or 'none'}")
        print(f"       answer: {outcome['answer'][:200]}")
        if not outcome["passed"]:
            failed += 1
            for failure in outcome["failures"]:
                print(f"       ✗ {failure}")
        print()

    total = len(results)
    print(f"{total - failed}/{total} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
