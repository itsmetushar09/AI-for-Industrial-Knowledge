"""Grounded RAG chat and browser-scoped conversation history endpoints."""

import logging
import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.auth import AuthenticatedUser, get_current_user
from app.database.session import get_db_session
from app.rag.chat import PgVectorRetriever, RagChatError, RagChatService
from app.rag.providers import build_answer_provider, build_embedding_provider
from app.schemas.chat import ChatHistoryItem, ChatRequest, ChatResponse
from app.services.conversation_history import (
    ConversationHistoryService,
    ConversationNotFoundError,
)

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)
SESSION_COOKIE = "indus_chat_session"


def get_chat_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RagChatService:
    """Build the request-scoped RAG service from shared dependencies."""

    try:
        embeddings = build_embedding_provider(settings)
        answers = build_answer_provider(settings)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{settings.ai_provider.title()} is not configured",
        ) from exc
    return RagChatService(
        embeddings=embeddings,
        retriever=PgVectorRetriever(
            session,
            settings.rag_top_k,
            settings.ai_provider,
            settings.active_embedding_model,
        ),
        answers=answers,
    )


def get_history_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConversationHistoryService:
    """Build request-scoped conversation persistence."""

    return ConversationHistoryService(session)


def legacy_anonymous_session(request: Request) -> UUID | None:
    """Read the Phase 7 cookie so its history can be claimed after sign-in."""

    raw_value = request.cookies.get(SESSION_COOKIE)
    try:
        return UUID(raw_value) if raw_value else None
    except ValueError:
        return None


@router.post("/chat", response_model=ChatResponse, summary="Ask indexed industrial knowledge")
async def chat(
    payload: ChatRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[RagChatService, Depends(get_chat_service)],
    history: Annotated[ConversationHistoryService, Depends(get_history_service)],
) -> ChatResponse:
    """Answer one question using top-five semantic retrieval and citations."""

    started = time.perf_counter()
    logger.info(
        "Chat request started",
        extra={
            "event": "chat_request_started",
            "user_id": str(user.id),
            "continuation": payload.conversation_id is not None,
        },
    )
    try:
        await history.claim_anonymous(legacy_anonymous_session(request), user.id)
        if payload.conversation_id is not None:
            await history.assert_access(payload.conversation_id, user.id)
        answer = await service.ask(payload.question)
        conversation_id = await history.record_exchange(
            user.id,
            payload.question,
            answer,
            payload.conversation_id,
        )
        result = answer.model_copy(update={"conversation_id": conversation_id})
        logger.info(
            "Chat request completed",
            extra={
                "event": "chat_request_completed",
                "user_id": str(user.id),
                "conversation_id": str(conversation_id),
                "confidence": result.confidence,
                "citations": len(result.citations),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return result
    except ConversationNotFoundError as exc:
        logger.warning(
            "Chat conversation not found",
            extra={
                "event": "chat_request_rejected",
                "user_id": str(user.id),
                "reason": "conversation_not_found",
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found") from exc
    except RagChatError as exc:
        logger.exception(
            "Chat request failed",
            extra={
                "event": "chat_request_failed",
                "user_id": str(user.id),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/chat/history", response_model=list[ChatHistoryItem], summary="List chat history")
async def chat_history(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    history: Annotated[ConversationHistoryService, Depends(get_history_service)],
) -> list[ChatHistoryItem]:
    """Return conversations owned by this anonymous browser session."""

    await history.claim_anonymous(legacy_anonymous_session(request), user.id)
    return await history.history(user.id)


@router.delete("/chat/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    conversation_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    history: Annotated[ConversationHistoryService, Depends(get_history_service)],
) -> Response:
    """Delete one conversation owned by this anonymous browser session."""

    try:
        await history.delete(conversation_id, user.id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
