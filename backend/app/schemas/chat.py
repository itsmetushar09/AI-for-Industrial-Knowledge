"""Grounded chat and conversation-history API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import MessageRole


class ChatRequest(BaseModel):
    """One semantic question against indexed industrial knowledge."""

    question: str = Field(min_length=2, max_length=4000)
    conversation_id: UUID | None = None

    @field_validator("question")
    @classmethod
    def question_must_contain_text(cls, value: str) -> str:
        """Normalize whitespace and reject whitespace-only input."""

        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("question must contain at least two characters")
        return normalized


class ChatCitation(BaseModel):
    """One source location supporting the generated answer."""

    document: str
    page: int
    score: float = Field(ge=0, le=1)


class ChatResponse(BaseModel):
    """Grounded answer with deterministic retrieval evidence."""

    answer: str
    confidence: float = Field(ge=0, le=1)
    citations: list[ChatCitation]
    conversation_id: UUID | None = None


class ChatMessage(BaseModel):
    """One persisted message in a conversation."""

    id: UUID
    role: MessageRole
    content: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    citations: list[ChatCitation]
    created_at: datetime


class ChatHistoryItem(BaseModel):
    """One browser-owned conversation and its ordered messages."""

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessage]
