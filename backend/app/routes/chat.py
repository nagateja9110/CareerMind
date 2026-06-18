from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from openai import AsyncOpenAI

from app.agent.orchestrator import AgentContext, CareerAgentOrchestrator
from app.agent.tools.job_search import JobSearchTool
from app.agent.tools.resume_parser import ResumeParserTool
from app.agent.tools.skills_lookup import SkillsLookupTool
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.mongodb import get_database
from app.models.chat import ChatRequest, ChatResponse, ChatSummary, ChatThread


router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()

_llm_client = (
    AsyncOpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
    if settings.groq_api_key
    else None
)


def _get_user_id(user: dict) -> str:
    return str(user["_id"])


def _build_orchestrator(database: AsyncIOMotorDatabase) -> CareerAgentOrchestrator:
    return CareerAgentOrchestrator(
        skills_lookup_tool=SkillsLookupTool(database, settings.skills_taxonomy_collection),
        job_search_tool=JobSearchTool(settings.solr_url),
        resume_parser_tool=ResumeParserTool(),
        llm_client=_llm_client,
        model=settings.groq_model,
        max_steps=settings.agent_max_tool_steps,
    )


@router.post("", response_model=ChatResponse)
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
    database: AsyncIOMotorDatabase = Depends(get_database),
) -> ChatResponse:
    chat_id = payload.chat_id or str(uuid4())
    chat_collection = database[settings.chats_collection]
    user_id = _get_user_id(current_user)

    chat = await chat_collection.find_one({"chat_id": chat_id, "user_id": user_id})
    if payload.chat_id and chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat thread not found.",
        )

    resume = await database[settings.resumes_collection].find_one(
        {"user_id": user_id},
        sort=[("uploaded_at", -1)],
    )
    resume_text = resume.get("raw_text") if resume else None

    orchestrator = _build_orchestrator(database)
    prior_messages = [
        {"role": message["role"], "content": message["content"]}
        for message in (chat or {}).get("messages", [])
    ]
    result = await orchestrator.run(
        AgentContext(
            message=payload.message,
            resume_text=resume_text,
            prior_messages=prior_messages,
        )
    )

    now = datetime.now(UTC)
    user_message = {
        "role": "user",
        "content": payload.message,
        "timestamp": now,
    }
    assistant_message = {
        "role": "assistant",
        "content": result.answer,
        "timestamp": now,
    }

    if chat is None:
        chat_document = {
            "chat_id": chat_id,
            "user_id": user_id,
            "title": payload.message[:80],
            "messages": [user_message, assistant_message],
            "tool_calls": [tool_call.model_dump() for tool_call in result.tool_calls],
            "updated_at": now,
            "created_at": now,
        }
        await chat_collection.insert_one(chat_document)
    else:
        await chat_collection.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {
                "$push": {"messages": {"$each": [user_message, assistant_message]}},
                "$set": {
                    "tool_calls": [tool_call.model_dump() for tool_call in result.tool_calls],
                    "updated_at": now,
                },
            },
        )

    return ChatResponse(
        chat_id=chat_id,
        answer=result.answer,
        tool_calls=result.tool_calls,
        recommended_jobs=result.recommended_jobs,
    )


@router.get("/history", response_model=list[ChatSummary])
async def get_chat_history(
    current_user: dict = Depends(get_current_user),
    database: AsyncIOMotorDatabase = Depends(get_database),
) -> list[ChatSummary]:
    cursor = (
        database[settings.chats_collection]
        .find({"user_id": _get_user_id(current_user)})
        .sort("updated_at", -1)
    )
    chats = await cursor.to_list(length=50)
    return [
        ChatSummary(
            chat_id=chat["chat_id"],
            title=chat.get("title", "Untitled chat"),
            updated_at=chat["updated_at"],
        )
        for chat in chats
    ]


@router.get("/{chat_id}", response_model=ChatThread)
async def get_chat_thread(
    chat_id: str,
    current_user: dict = Depends(get_current_user),
    database: AsyncIOMotorDatabase = Depends(get_database),
) -> ChatThread:
    chat = await database[settings.chats_collection].find_one(
        {"chat_id": chat_id, "user_id": _get_user_id(current_user)}
    )
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat thread not found.",
        )

    return ChatThread(
        chat_id=chat["chat_id"],
        messages=chat.get("messages", []),
        updated_at=chat["updated_at"],
    )
