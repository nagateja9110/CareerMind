# AgenticHire-AI — Software Specification Document (SDD)

> **Project type:** Agentic AI Career Advisor Chatbot
> **Author:** Naga Teja
> **Status:** Draft — pre-execution plan
> **Last updated:** June 2026

---

## 1. Project Overview

**AgenticHire-AI** is a full-stack, agent-driven career advisory application. A user uploads their résumé (or describes their background), and an LLM-based agent answers personalized career questions by reasoning over real job-market data instead of relying only on its training knowledge.

**Problem it solves:** Job seekers struggle to know which skills they lack, which roles fit their profile, and where the opportunities are. Generic chatbots hallucinate. This agent grounds every answer in a searchable job-postings dataset and a structured skills taxonomy.

**What makes it "agentic":** The system is not a single prompt-response wrapper. The agent decides *when* to call tools (job search, skills lookup, résumé parsing), observes the results, and reasons over multiple steps before answering — a ReAct-style loop.

**Target users:**
- Students and early-career professionals planning a career move
- Career counsellors who want data-backed guidance
- Anyone evaluating a skill gap for a target role

**Example queries the agent must handle:**
- "What skills am I missing to become a Data Engineer?"
- "Which companies are hiring for my profile in Bangalore?"
- "How do I transition from backend developer to ML engineer?"

---

## 2. Tech Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Frontend | React, Redux, Webpack | Component-based chat UI; Redux for conversation state |
| Backend | Python, FastAPI | Async API, fast to build, native typing |
| Agent framework | LangChain (or custom ReAct loop) | Tool-calling orchestration |
| LLM | OpenAI / Gemini API (or local model via Ollama) | Reasoning engine |
| Search index | Apache Solr | Faceted, low-latency job search |
| Database | MongoDB | Flexible document storage for users, chats, résumés |
| Auth | JWT + bcrypt | Stateless session tokens |
| Containerization | Docker | Reproducible deployment |
| Hosting | AWS ECS + Elastic Beanstalk + S3 | Scalable cloud infra |

---

## 3. Core Features

1. **Résumé upload & parsing** — user uploads a PDF/text résumé; system extracts skills, roles, and experience.
2. **Conversational agent** — multi-turn chat where the agent maintains context across messages.
3. **Tool-augmented reasoning** — agent autonomously calls:
   - *Job search tool* — queries Solr by skill, role, location
   - *Skills taxonomy tool* — returns required skills for a target role
   - *Résumé parser tool* — extracts structured data from the upload
4. **Skill-gap analysis** — compares user's current skills vs. target role requirements.
5. **Company / role recommendations** — surfaces matching job postings with relevance scores.
6. **Chat history** — saved per user, resumable across sessions.
7. **Explainability** — every recommendation shows *why* it was suggested (which skills matched).

---

## 4. Authentication

- **Method:** Email + password registration with JWT-based sessions.
- **Password storage:** Hashed with bcrypt (never plaintext).
- **Token flow:** On login, server issues a short-lived access token + a refresh token. Access token sent in the `Authorization: Bearer <token>` header on every protected request.
- **Protected routes:** All `/chat`, `/resume`, and `/history` endpoints require a valid token.
- **Session expiry:** Access token expires in 1 hour; refresh token in 7 days.
- **Optional enhancement:** Google OAuth sign-in for faster onboarding.

---

## 5. Backend Architecture

The backend follows a layered, service-oriented design:

```
Client (React)
      |
   FastAPI Gateway  ──  Auth middleware (JWT verify)
      |
   Agent Orchestrator (ReAct loop)
      |
   ┌──────────────┬──────────────────┬────────────────┐
   │  Job Search  │  Skills Taxonomy │ Résumé Parser  │   <- Tools
   │   (Solr)     │     (MongoDB)    │   (PDF/NLP)    │
   └──────────────┴──────────────────┴────────────────┘
      |
   MongoDB (users, chats, résumés)  +  Solr index (jobs)
```

**Request lifecycle:**
1. Client sends a chat message + JWT.
2. Auth middleware validates the token.
3. Orchestrator passes the message + résumé context to the LLM.
4. LLM decides whether to answer directly or call a tool.
5. If a tool is called, the result is fed back into the loop.
6. Loop continues until the agent produces a final answer.
7. Answer + updated chat history are returned and persisted.

---

## 6. Database Collections

**MongoDB collections:**

### `users`
| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | Primary key |
| `name` | String | |
| `email` | String | Unique, indexed |
| `password_hash` | String | bcrypt |
| `created_at` | Timestamp | |

### `resumes`
| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref → users |
| `raw_text` | String | Extracted text |
| `parsed_skills` | Array[String] | |
| `experience_years` | Number | |
| `uploaded_at` | Timestamp | |

### `chats`
| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | |
| `user_id` | ObjectId | Ref → users |
| `messages` | Array[Object] | `{role, content, tool_calls, timestamp}` |
| `created_at` | Timestamp | |

### `skills_taxonomy`
| Field | Type | Notes |
|-------|------|-------|
| `role` | String | e.g. "Data Engineer" |
| `required_skills` | Array[String] | |
| `related_roles` | Array[String] | |

**Solr index (`jobs`):** stores job postings with fields `title`, `company`, `location`, `skills`, `description`, `seniority` — configured for faceted search.

---

## 7. API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Log in, return JWT |
| POST | `/api/auth/refresh` | No | Refresh access token |
| POST | `/api/resume/upload` | Yes | Upload & parse résumé |
| GET | `/api/resume` | Yes | Fetch parsed résumé |
| POST | `/api/chat` | Yes | Send a message to the agent |
| GET | `/api/chat/history` | Yes | List user's past chats |
| GET | `/api/chat/{id}` | Yes | Fetch a single chat thread |
| GET | `/api/jobs/search` | Yes | Direct job search (debug/dev) |
| GET | `/api/health` | No | Health check |

**Sample `/api/chat` request:**
```json
{
  "chat_id": "optional-existing-id",
  "message": "What skills am I missing to become a Data Engineer?"
}
```

**Sample response:**
```json
{
  "chat_id": "abc123",
  "answer": "Based on your résumé, you have Python and SQL. For a Data Engineer role you'd also want Apache Spark, Airflow, and cloud (AWS/GCP). Here are 3 matching openings...",
  "tool_calls": ["skills_taxonomy", "job_search"],
  "recommended_jobs": [ ... ]
}
```

---

## 8. Folder Structure

```
agentichire-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── auth/                # JWT, register, login
│   │   ├── agent/
│   │   │   ├── orchestrator.py  # ReAct loop
│   │   │   └── tools/
│   │   │       ├── job_search.py
│   │   │       ├── skills_lookup.py
│   │   │       └── resume_parser.py
│   │   ├── db/                  # MongoDB + Solr connectors
│   │   ├── models/             # Pydantic schemas
│   │   └── routes/             # API routers
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # ChatWindow, MessageBubble, ResumeUpload
│   │   ├── store/              # Redux slices
│   │   ├── api/                # Axios client
│   │   └── App.jsx
│   ├── webpack.config.js
│   └── package.json
├── data/
│   └── jobs_dataset.csv        # Source data for Solr index
├── docker-compose.yml
└── README.md
```

---

## 9. Development Phases


Here’s the end-to-end plan I’d follow to build **AgenticHire-AI** into a working project.

**Phase 1: Project Setup**
Set up the repo structure with `backend/`, `frontend/`, `data/`, and Docker Compose. Run MongoDB, Solr, backend, and frontend locally. Add basic config files, environment variables, and health checks.

**Phase 2: Backend Foundation**
Build the FastAPI backend with auth first:
- Register/login APIs
- JWT access and refresh tokens
- bcrypt password hashing
- Protected routes
- MongoDB connection
- Pydantic request/response models

**Phase 3: Resume System**
Implement résumé upload and parsing:
- Accept PDF or text upload
- Extract raw text
- Detect skills, roles, experience, education
- Store parsed résumé data in MongoDB
- Return parsed skills to the frontend

**Phase 4: Job Search Data**
Prepare the job-market grounding layer:
- Add or download a jobs dataset
- Clean fields like title, company, location, skills, description
- Index jobs into Apache Solr
- Build a backend job search tool that can query by role, skill, location, and seniority

**Phase 5: Skills Taxonomy**
Create the skills intelligence layer:
- Build a `skills_taxonomy` collection
- Store required skills for roles like Data Engineer, ML Engineer, Backend Developer, Analyst
- Add related roles and skill categories
- Build a lookup tool for the agent

**Phase 6: Agent Core**
Build the actual “agentic” part:
- Start with a custom ReAct loop or LangChain agent
- Give the agent access to tools:
  - résumé parser
  - job search
  - skills lookup
- Let it decide when to call tools
- Return final answers with tool-call traces and explanations
- Add guardrails so it says when data is missing instead of hallucinating

**Phase 7: Chat API**
Implement the main chat workflow:
- `POST /api/chat`
- Load user résumé and chat history
- Pass context to the agent
- Save user message, tool calls, and assistant response
- Return recommended jobs and explanation metadata

**Phase 8: Frontend App**
Build the React app as a usable product, not just a demo:
- Login/register screens
- Chat-first interface
- Résumé upload panel
- Parsed skills as chips
- Agent messages with tool activity indicators
- Job recommendation cards
- History sidebar
- Mobile responsive layout

**Phase 9: Explainability**
Make recommendations trustworthy:
- Show matched skills
- Show missing skills
- Explain why a role/company/job was suggested
- Separate “based on your résumé” from “based on job-market data”
- Display when the agent searched jobs or looked up role requirements

**Phase 10: Testing**
Add practical tests:
- Backend unit tests for auth, résumé parser, Solr search, skills lookup
- Agent tool tests with mocked LLM responses
- API integration tests
- Frontend component tests for chat, upload, and recommendation cards
- Manual end-to-end test with a sample résumé

**Phase 11: Docker + Deployment**
Package the app:
- Dockerfiles for backend/frontend
- Docker Compose for local development
- Seed scripts for MongoDB and Solr
- Production config
- Deploy backend and services to AWS
- Host frontend on S3/CloudFront or similar

**Phase 12: Demo Polish**
Prepare it for portfolio/demo use:
- README with setup steps
- Architecture diagram
- Sample résumé
- Sample job dataset
- Demo video flow
- Clear project explanation: problem, architecture, agentic behavior, tools, and results

My recommended build order would be:

1. Backend + auth  
2. Resume parsing  
3. Solr job search  
4. Skills taxonomy  
5. Agent loop  
6. Chat API  
7. Frontend  
8. Testing and deployment  

That order gives us a working core early, then we layer the agent and UI on top.
---

## 10. UI and UX Requirements

- **Chat-first layout:** central chat window, message bubbles for user vs. agent.
- **Résumé upload zone:** drag-and-drop, shows parsed skills as chips once processed.
- **Tool transparency:** a small inline indicator when the agent is "searching jobs" or "looking up skills" (builds trust).
- **Recommendation cards:** matched jobs displayed as cards with title, company, location, and matched-skills badges.
- **Responsive:** works on desktop and mobile.
- **Loading states:** typing indicator while the agent reasons.
- **History sidebar:** list of past conversations, clickable to resume.
- **Accessibility:** keyboard navigable, sufficient color contrast, alt text on icons.

---

## 11. Security Requirements

- **Password hashing** with bcrypt; never store or log plaintext passwords.
- **JWT verification** on every protected endpoint.
- **Input validation** via Pydantic on all request bodies.
- **File upload limits:** restrict résumé uploads to PDF/DOCX/TXT, max 5 MB, scan for malformed content.
- **Rate limiting** on `/api/chat` and `/api/auth/login` to prevent abuse.
- **Secrets management:** API keys (LLM, DB) stored in environment variables, never committed.
- **CORS:** restrict allowed origins to the deployed frontend domain.
- **No PII in logs:** résumé contents and chat messages excluded from application logs.
- **HTTPS only** in production.

---

## 12. Final Expected Outcome

A deployed, working web application where a logged-in user can:

1. Upload their résumé and see extracted skills.
2. Chat with an AI agent that answers career questions grounded in real job data.
3. Receive a clear skill-gap analysis for any target role.
4. Get a ranked list of matching job openings with explanations.
5. Revisit past conversations.

**Definition of done:**
- All 10 API endpoints implemented and tested.
- Agent correctly invokes tools and never fabricates job data.
- Frontend deployed and reachable over HTTPS.
- Public GitHub repo with a clean README, architecture diagram, and demo.

**Stretch goals (post-MVP):**
- Resume improvement suggestions
- Interview question generator per target role
- Multi-language support
