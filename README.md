# Agentic career 

AgenticHire-AI is an agent-driven career advisor that will answer questions using a user's resume, role skill requirements, and real job-market search data.

## Phase 1 Foundation

This repository currently includes:

- FastAPI backend with a health endpoint
- React + Vite frontend shell
- Docker Compose for MongoDB, Solr, backend, and frontend
- Starter Solr config for a `jobs` collection
- Environment variable examples

## Run Locally

```bash
docker compose up --build
```

Services:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health check: http://localhost:8000/api/health
- Solr admin: http://localhost:8983
- MongoDB: `mongodb://localhost:27018`

## Phase 2 Authentication

The backend now includes:

- User registration with hashed passwords
- Login with JWT access and refresh tokens
- Refresh endpoint for short-lived access token renewal
- Protected `/api/auth/me` and `/api/profile/me` routes

Auth endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/auth/me`
- `GET /api/profile/me`

## Phase 3 Agent Core

The backend now also includes:

- A protected `POST /api/chat` endpoint
- Persistent chat history in MongoDB
- A custom agent orchestrator with tool-call tracing
- Tool modules for skills lookup, job search, and resume parsing
- History endpoints at `GET /api/chat/history` and `GET /api/chat/{id}`

## Phase 4 Grounding Data

The backend now also includes:

- `POST /api/resume/upload` for PDF or text resumes
- `GET /api/resume` for the latest parsed resume
- Startup seeding for the skills taxonomy in MongoDB
- Startup seeding for a sample Solr jobs index so chat responses can return real matches
