from __future__ import annotations

from dataclasses import dataclass

from app.agent.tools.job_search import JobSearchTool
from app.agent.tools.resume_parser import ResumeParserTool
from app.agent.tools.skills_lookup import SkillsLookupTool
from app.models.chat import AgentRunResult, RecommendedJob, ToolCallRecord


@dataclass
class AgentContext:
    message: str
    resume_text: str | None
    prior_messages: list[str]


class CareerAgentOrchestrator:
    def __init__(
        self,
        skills_lookup_tool: SkillsLookupTool,
        job_search_tool: JobSearchTool,
        resume_parser_tool: ResumeParserTool,
    ) -> None:
        self.skills_lookup_tool = skills_lookup_tool
        self.job_search_tool = job_search_tool
        self.resume_parser_tool = resume_parser_tool

    async def run(self, context: AgentContext) -> AgentRunResult:
        tool_calls: list[ToolCallRecord] = []
        recommended_jobs: list[RecommendedJob] = []
        reasoning_notes: list[str] = []

        parsed_resume = self.resume_parser_tool.parse(context.resume_text or "")
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

        target_role = self._extract_target_role(context.message)
        if target_role is None:
            target_role = self._infer_role_from_history(context.prior_messages)
        required_skills: list[str] = []
        missing_skills: list[str] = []
        matched_skills: list[str] = []
        related_roles: list[str] = []

        if target_role:
            skills_result = await self.skills_lookup_tool.lookup(target_role)
            required_skills = skills_result.required_skills
            related_roles = skills_result.related_roles
            matched_skills = sorted(
                skill for skill in parsed_resume.skills if skill in required_skills
            )
            missing_skills = sorted(
                skill for skill in required_skills if skill not in parsed_resume.skills
            )
            tool_calls.append(
                ToolCallRecord(
                    tool="skills_taxonomy",
                    input={"role": target_role},
                    output={
                        "required_skills": required_skills,
                        "related_roles": related_roles,
                        "source": skills_result.source,
                    },
                )
            )

        should_search_jobs = any(
            phrase in context.message.lower()
            for phrase in ["job", "jobs", "company", "companies", "hiring", "openings"]
        )
        if should_search_jobs:
            search_skills = missing_skills[:3] or parsed_resume.skills[:3]
            jobs = await self.job_search_tool.search(
                role=target_role,
                location=self._extract_location(context.message),
                skills=search_skills,
            )
            recommended_jobs = jobs
            tool_calls.append(
                ToolCallRecord(
                    tool="job_search",
                    input={
                        "role": target_role,
                        "location": self._extract_location(context.message),
                        "skills": search_skills,
                    },
                    output={"results_count": len(jobs)},
                )
            )

        answer = self._compose_answer(
            message=context.message,
            target_role=target_role,
            parsed_resume=parsed_resume,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            related_roles=related_roles,
            recommended_jobs=recommended_jobs,
            reasoning_notes=reasoning_notes,
        )

        return AgentRunResult(
            answer=answer,
            tool_calls=tool_calls,
            recommended_jobs=recommended_jobs,
        )

    def _extract_target_role(self, message: str) -> str | None:
        normalized = message.lower()
        known_roles = [
            "data engineer",
            "ml engineer",
            "machine learning engineer",
            "backend developer",
            "backend engineer",
            "data analyst",
            "software engineer",
            "frontend developer",
            "product manager",
        ]
        for role in known_roles:
            if role in normalized:
                return self._title_case_role(role)
        return None

    def _extract_location(self, message: str) -> str | None:
        lowered = message.lower()
        for marker in [" in ", " at ", " near "]:
            if marker in lowered:
                location = message.lower().split(marker, 1)[1].strip(" ?.")
                if location:
                    return location.title()
        return None

    def _infer_role_from_history(self, prior_messages: list[str]) -> str | None:
        for prior_message in reversed(prior_messages):
            role = self._extract_target_role(prior_message)
            if role:
                return role
        return None

    def _title_case_role(self, role: str) -> str:
        replacements = {
            "Ml": "ML",
        }
        parts = [replacements.get(word.capitalize(), word.capitalize()) for word in role.split()]
        return " ".join(parts)

    def _compose_answer(
        self,
        *,
        message: str,
        target_role: str | None,
        parsed_resume,
        matched_skills: list[str],
        missing_skills: list[str],
        related_roles: list[str],
        recommended_jobs: list[RecommendedJob],
        reasoning_notes: list[str],
    ) -> str:
        if target_role:
            intro = f"You look closest to a {target_role} path based on the question you asked."
        else:
            intro = "I used the available profile context and your message to frame the next-step advice."

        skill_line = ""
        if matched_skills or missing_skills:
            matched_text = ", ".join(matched_skills) if matched_skills else "no direct matches yet"
            missing_text = ", ".join(missing_skills[:5]) if missing_skills else "no major gaps identified"
            skill_line = (
                f" Matched skills: {matched_text}. Missing or under-evidenced skills: {missing_text}."
            )

        resume_line = ""
        if parsed_resume.skills:
            resume_line = (
                f" I found these profile signals in the available resume context: "
                f"{', '.join(parsed_resume.skills[:8])}."
            )

        job_line = ""
        if recommended_jobs:
            top_jobs = "; ".join(
                f"{job.title} at {job.company}" for job in recommended_jobs[:3]
            )
            job_line = f" Current job matches I found: {top_jobs}."
        elif "job" in message.lower() or "hiring" in message.lower():
            job_line = (
                " I checked the job-search layer, but there are no indexed jobs yet, "
                "so this recommendation is coming from the skills taxonomy and your profile context."
            )

        related_line = ""
        if related_roles:
            related_line = f" Nearby roles worth exploring: {', '.join(related_roles[:3])}."

        notes_line = f" {' '.join(reasoning_notes)}" if reasoning_notes else ""
        return f"{intro}{resume_line}{skill_line}{job_line}{related_line}{notes_line}".strip()
