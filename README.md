# CareerMind

Live demo: https://careermind-5obn.onrender.com/

CareerMind is a career advisor chatbot that actually does its homework before answering. Most "AI career advisor" demos are just a chatbot prompt wrapped around an LLM — they'll happily make up skills, companies, and job openings because the model is just pattern-matching on what sounds plausible. CareerMind is built differently: it's an agent that looks things up before it answers.

## Problem Identification

If you ask a generic chatbot "what skills am I missing to become a Data Engineer," it will give you a confident, fluent answer that's frequently wrong or generic — because it's reciting averages from its training data, not looking at real, current job requirements or your actual background.

The real problem people have when planning a career move:
- They don't know which skills are actually expected for a target role *right now*.
- They don't know who's hiring for that role, or where.
- They want this compared against their own resume, not a generic answer.

Generic LLM chat doesn't solve this because it has no access to your resume or to live job-market data, and it has no incentive to say "I don't know" instead of guessing.

## The Impact

If you get this wrong, you waste months — either learning skills nobody's hiring for, or applying to roles you're not actually positioned for. The cost of bad career advice is time, and time is the one thing you can't get back in a job search.

CareerMind's bet is that grounding every answer in real data (your resume, a skills taxonomy, and real job postings) turns a generic chatbot into something people can actually trust enough to act on.

## How It Works

You upload a resume. You ask a question like "What am I missing for an ML Engineer role?" or "Who's hiring Data Engineers in Bangalore?" Behind the scenes, an LLM-driven agent decides what it needs to look up — your resume's skills, the target role's requirements, or live job postings — fetches that data, and only then writes an answer. If the data isn't there, it says so instead of inventing it.

This is the "agentic" part: it's not one LLM call with a big prompt. It's a loop where the model can call tools, look at what comes back, and decide whether it needs to call another tool before it's ready to answer.

```
You: "What am I missing for a Data Engineer role, and who's hiring?"
        │
        ▼
   Agent (LLM) reasons: "I need the role's required skills, then I should check job openings"
        │
        ├──► calls skills_taxonomy tool ──► required skills for Data Engineer
        │
        ├──► calls job_search tool ──► real job postings matching that role
        │
        ▼
   Agent compares your resume's skills against what came back,
   and writes an answer using only that data.
```

## Architecture

```
┌─────────────┐        ┌──────────────────────────────────────────────┐
│   React UI   │  HTTP  │                  FastAPI Backend                │
│ (chat, login,│ ─────► │                                                  │
│  resume      │ JWT +  │   Auth (JWT access + refresh, bcrypt)           │
│  upload, job │ refresh│        │                                        │
│  results)    │ ◄───── │        ▼                                        │
└─────────────┘        │   Chat Route ──► Agent Orchestrator (ReAct loop)│
                        │                        │                       │
                        │         ┌──────────────┼──────────────┐        │
                        │         ▼              ▼              ▼        │
                        │   Resume Parser   Skills Lookup   Job Search    │
                        │   (PDF/DOCX/TXT)  (MongoDB)     (Adzuna live API,│
                        │                                  Mongo fallback)│
                        └────┬───────────────────┬──────────────┬────────┘
                             │                    │              │
                             ▼                    ▼              ▼
                        MongoDB             MongoDB          Adzuna API
                    (users, chats,       (skills taxonomy,   (real-time job
                     resumes)             21 roles)           postings) ──►
                                                                falls back to
                                                                MongoDB (791
                                                                seeded postings)
                             │
                             ▼
                    Groq API (Llama 3.3 70B)
                    — the actual reasoning engine
```

**Why these pieces:**
- **FastAPI** — async, typed, fast to iterate on.
- **MongoDB** — chats and resumes are naturally document-shaped (variable structure, nested tool-call traces); no benefit from a rigid schema here.
- **Adzuna API, with MongoDB fallback** — `job_search` calls Adzuna first for real, current postings; if Adzuna isn't configured or returns nothing for that query, it falls back to a regex-ranked search over a seeded MongoDB dataset, so the tool never just returns empty because one upstream API hiccuped.
- **Groq (Llama 3.3 70B)** — an OpenAI-compatible, fast, inexpensive way to give the agent real reasoning and tool-calling ability, instead of hand-written keyword matching.
- **React + Vite** — a small, fast frontend; no heavier framework needed for a single chat-first UI.

## Implementation

**The agent loop** ([backend/app/agent/orchestrator.py](backend/app/agent/orchestrator.py)) is the core of the project. On each message, the LLM is given the conversation, a summary of the user's resume, and two tools it can call:

- `skills_taxonomy(role)` — required skills and related roles for a target role.
- `job_search(role, location, skills)` — real job postings matching the criteria.

The model decides whether it needs either tool, calls it, reads the result, and can call another tool or answer. The system prompt explicitly forbids it from stating a skill or job that didn't come back from a tool call or the resume — if a tool finds nothing, it has to say so. If no `GROQ_API_KEY` is configured, the orchestrator falls back to a simple deterministic resume-only response instead of failing, which keeps local development possible without an API key.

**Grounding data:**
- The skills taxonomy covers 21 roles (Data Engineer, ML Engineer, DevOps Engineer, Product Manager, UI/UX Designer, and others), each with required skills and related roles, seeded into MongoDB on startup.
- `job_search` prefers live Adzuna results so postings and companies are real and current; the fallback dataset is 791 job postings sourced from a public [LinkedIn job postings dataset](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) on Kaggle, classified into those 21 roles and skill-tagged using the same parser that reads resumes — so a skill detected in a resume and a skill required by a job posting are always named consistently, regardless of which source answered.
- Every job result also links out to a live, real-time search on LinkedIn, Indeed, Naukri, and Glassdoor for that exact role/location — generated client-side from the result, not scraped, so it's never stale and needs no extra API keys.

**Other things worth knowing:**
- Resume uploads accept PDF, DOCX, and plain text, capped at 5 MB.
- Auth uses short-lived JWT access tokens with a longer-lived refresh token; the frontend silently refreshes on a 401 instead of forcing a re-login.
- `/api/auth/login` and `/api/chat` are rate-limited per IP to curb abuse.
- 31 backend tests cover auth, resume parsing, the skills/job-search tools (with mocked HTTP calls), and the agent loop itself (including its retry/fallback behavior when the LLM returns a malformed tool call).

## API

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Log in, get JWT |
| POST | `/api/auth/refresh` | No | Refresh access token |
| GET | `/api/auth/me` | Yes | Current user |
| POST | `/api/resume/upload` | Yes | Upload and parse a resume |
| GET | `/api/resume` | Yes | Get the latest parsed resume |
| POST | `/api/chat` | Yes | Send a message to the agent |
| GET | `/api/chat/history` | Yes | List past conversations |
| GET | `/api/chat/{id}` | Yes | Fetch one conversation |
| GET | `/api/jobs/search` | Yes | Direct job search |
| GET | `/api/health` | No | Health check |

## Running it locally

You'll need Docker and a [Groq API key](https://console.groq.com) (free tier is fine).

```bash
cp backend/.env.example backend/.env
# then edit backend/.env and set GROQ_API_KEY=...

docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

Set `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` (free at [developer.adzuna.com](https://developer.adzuna.com)) in `backend/.env` for live job search; without them, `job_search` falls back to the seeded MongoDB dataset automatically.

Running tests:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## What's not here yet

- The frontend doesn't use Redux yet, even though it's a listed dependency — state is currently plain `useState`. Fine for the current UI size, would matter if it grew.
- No interview-question generator or resume rewrite suggestions (listed as stretch goals, not built).
