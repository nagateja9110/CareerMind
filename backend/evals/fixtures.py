"""Fixed eval scenarios for the agent orchestrator.

Each case pins the resume and job-market "facts" the agent must reason
over (via evals/fakes.py) and checks two things real users actually care
about, separate from whether the prose reads nicely:

1. Tool-call correctness  — did the agent look up the right thing instead
   of answering from the LLM's own (possibly wrong) training data?
2. Groundedness            — does the answer only mention skills/companies
   that the tools actually returned or that are in the resume, instead of
   inventing plausible-sounding ones (the failure mode this whole project
   exists to avoid)?
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalCase:
    name: str
    description: str
    message: str
    resume_text: str | None
    expected_tools: set[str]
    strict_tools: bool = False
    required_terms: list[str] = field(default_factory=list)
    forbidden_terms: list[str] = field(default_factory=list)
    prior_messages: list[dict[str, str]] = field(default_factory=list)


CASES: list[EvalCase] = [
    EvalCase(
        name="skill_gap_known_role",
        description="Asks for a skill gap against a role that exists in the taxonomy.",
        message="What skills am I missing for a Data Engineer role?",
        resume_text="I know Python and SQL. 2 years experience as a backend developer.",
        expected_tools={"skills_taxonomy"},
        required_terms=["Spark", "Airflow"],
        forbidden_terms=["Kubernetes", "Terraform"],
    ),
    EvalCase(
        name="hiring_question",
        description="Asks who is hiring; the only real posting for this role/city is BridgeStack.",
        message="Who is hiring Data Engineers in Bangalore right now?",
        resume_text="Python, SQL, Spark, Airflow, AWS, ETL. 3 years of experience.",
        expected_tools={"job_search"},
        required_terms=["BridgeStack"],
        forbidden_terms=["Google", "Microsoft", "Amazon"],
    ),
    EvalCase(
        name="combined_skill_and_hiring",
        description="A single question that needs both tools to answer fully.",
        message="What am I missing for an ML Engineer role, and who's hiring for it?",
        resume_text="I know Python and TensorFlow.",
        expected_tools={"skills_taxonomy", "job_search"},
        required_terms=["PyTorch", "Nimbus AI"],
        forbidden_terms=["Kubernetes"],
    ),
    EvalCase(
        name="no_tool_needed",
        description="A conversational follow-up after the skill gap was already answered, needing no new lookup.",
        message="Thanks, that's helpful!",
        resume_text="Python, SQL.",
        prior_messages=[
            {"role": "user", "content": "What skills am I missing for a Data Engineer role?"},
            {
                "role": "assistant",
                "content": "For a Data Engineer role, you're missing Spark, Airflow, and AWS.",
            },
        ],
        expected_tools=set(),
        strict_tools=True,
        forbidden_terms=["Kubernetes", "BridgeStack"],
    ),
    EvalCase(
        name="unknown_role_no_hallucination",
        description="The role isn't in the taxonomy — the agent must not invent skills for it.",
        message="What skills do I need to become an Astronaut Engineer?",
        resume_text="Python, SQL.",
        expected_tools={"skills_taxonomy"},
        forbidden_terms=["Physics", "Rocket Science", "Aerospace Engineering"],
    ),
    EvalCase(
        name="already_qualified",
        description="Resume already covers every required skill for the role asked about.",
        message="Am I ready for a Data Engineer role?",
        resume_text="Python, SQL, Spark, Airflow, AWS, ETL. 5 years as a Data Engineer.",
        expected_tools={"skills_taxonomy"},
        forbidden_terms=["Kubernetes", "Java"],
    ),
]
