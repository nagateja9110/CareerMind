from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import APIError, AsyncOpenAI

from app.agent.tools.job_search import JobSearchTool
from app.agent.tools.resume_parser import ResumeParserTool
from app.agent.tools.skills_lookup import SkillsLookupTool
from app.models.chat import AgentRunResult, RecommendedJob, ToolCallRecord


SYSTEM_PROMPT = (
    "You are CareerMind, a career advisory agent. Ground every answer strictly in "
    "the resume context you are given and in the exact results returned by the "
    "tools you call. When listing required, matched, or missing skills, use ONLY "
    "the skill names that appear verbatim in a tool's output or the resume context "
    "— never add a skill that wasn't explicitly returned. If a tool returns no data, "
    "say so plainly instead of guessing. Call skills_taxonomy when the user asks "
    "about a target role's requirements or a skill gap. Call job_search only when "
    "the user asks about openings, hiring, or companies. Answer directly, without "
    "calling a tool, if the conversation already gives you enough information. Keep "
    "answers concise."
)

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "skills_taxonomy",
            "description": (
                "Look up the required skills and related roles for a target job role."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "description": "Target job role, e.g. 'Data Engineer'.",
                    }
                },
                "required": ["role"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "job_search",
            "description": (
                "Search current job postings by role, location, and/or skills. Only "
                "use this for questions about hiring, openings, or companies."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "location": {"type": "string"},
                    "skills": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
]


@dataclass
class AgentContext:
    message: str
    resume_text: str | None
    prior_messages: list[dict[str, str]]


class CareerAgentOrchestrator:
    def __init__(
        self,
        skills_lookup_tool: SkillsLookupTool,
        job_search_tool: JobSearchTool,
        resume_parser_tool: ResumeParserTool,
        llm_client: AsyncOpenAI | None = None,
        model: str = "",
        max_steps: int = 3,
    ) -> None:
        self.skills_lookup_tool = skills_lookup_tool
        self.job_search_tool = job_search_tool
        self.resume_parser_tool = resume_parser_tool
        self.llm_client = llm_client
        self.model = model
        self.max_steps = max_steps

    async def run(self, context: AgentContext) -> AgentRunResult:
        parsed_resume = self.resume_parser_tool.parse(context.resume_text or "")

        if self.llm_client is None:
            return self._run_heuristic(context, parsed_resume)

        return await self._run_agentic(context, parsed_resume)

    async def _run_agentic(self, context: AgentContext, parsed_resume) -> AgentRunResult:
        tool_calls: list[ToolCallRecord] = []
        recommended_jobs: list[RecommendedJob] = []

        if context.resume_text:
            resume_summary = (
                f"Resume skills detected: {', '.join(parsed_resume.skills) or 'none'}. "
                f"Experience: {parsed_resume.experience_years or 'unknown'} years."
            )
        else:
            resume_summary = "No resume has been uploaded yet."

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": resume_summary},
        ]
        for prior in context.prior_messages[-10:]:
            messages.append({"role": prior["role"], "content": prior["content"]})
        messages.append({"role": "user", "content": context.message})

        for _ in range(self.max_steps):
            response = await self._complete_with_retry(
                messages=messages, tools=TOOL_SCHEMAS, tool_choice="auto"
            )
            if response is None:
                return AgentRunResult(
                    answer=(
                        "The reasoning step failed after a retry, so I can't give a "
                        "grounded answer right now. Please try rephrasing your question."
                    ),
                    tool_calls=tool_calls,
                    recommended_jobs=recommended_jobs,
                )
            choice = response.choices[0].message

            if not choice.tool_calls:
                return AgentRunResult(
                    answer=choice.content
                    or "I don't have enough information to answer that yet.",
                    tool_calls=tool_calls,
                    recommended_jobs=recommended_jobs,
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": choice.content or "",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in choice.tool_calls
                    ],
                }
            )

            for tool_call in choice.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                output = await self._invoke_tool(name, args, recommended_jobs_out=recommended_jobs)

                tool_calls.append(ToolCallRecord(tool=name, input=args, output=output))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(output),
                    }
                )

        final = await self._complete_with_retry(messages=messages)
        final_answer = (
            final.choices[0].message.content if final is not None else None
        )
        return AgentRunResult(
            answer=final_answer
            or "I gathered some data but ran out of reasoning steps — please ask again.",
            tool_calls=tool_calls,
            recommended_jobs=recommended_jobs,
        )

    async def _complete_with_retry(self, **kwargs: Any):
        for attempt in range(2):
            try:
                return await self.llm_client.chat.completions.create(
                    model=self.model, **kwargs
                )
            except APIError:
                if attempt == 1:
                    return None
        return None

    async def _invoke_tool(
        self,
        name: str,
        args: dict[str, Any],
        *,
        recommended_jobs_out: list[RecommendedJob],
    ) -> dict[str, Any]:
        if name == "skills_taxonomy":
            role = args.get("role")
            if not role:
                return {"error": "role not provided"}
            result = await self.skills_lookup_tool.lookup(role)
            return {
                "required_skills": result.required_skills,
                "related_roles": result.related_roles,
                "source": result.source,
            }

        if name == "job_search":
            jobs = await self.job_search_tool.search(
                role=args.get("role"),
                location=args.get("location"),
                skills=args.get("skills"),
            )
            recommended_jobs_out.clear()
            recommended_jobs_out.extend(jobs)
            return {
                "results": [job.model_dump() for job in jobs],
                "results_count": len(jobs),
            }

        return {"error": f"unknown tool {name}"}

    def _run_heuristic(self, context: AgentContext, parsed_resume) -> AgentRunResult:
        """Deterministic fallback used when no LLM API key is configured."""
        tool_calls: list[ToolCallRecord] = []
        recommended_jobs: list[RecommendedJob] = []

        if parsed_resume.skills:
            tool_calls.append(
                ToolCallRecord(
                    tool="resume_parser",
                    input={"resume_present": bool(context.resume_text)},
                    output={
                        "skills": parsed_resume.skills,
                        "experience_years": parsed_resume.experience_years,
                    },
                )
            )

        answer = (
            "No LLM is configured (set GROQ_API_KEY), so I can only confirm what's in "
            "your resume. I found these skills: "
            f"{', '.join(parsed_resume.skills) or 'none detected'}."
        )

        return AgentRunResult(
            answer=answer,
            tool_calls=tool_calls,
            recommended_jobs=recommended_jobs,
        )
