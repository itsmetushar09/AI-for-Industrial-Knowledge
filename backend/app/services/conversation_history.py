"""Persistence and ownership rules for chat conversations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditLog
from app.models.conversation import Conversation, Message
from app.models.enums import MessageRole
from app.schemas.chat import ChatHistoryItem, ChatMessage, ChatResponse


class ConversationNotFoundError(Exception):
    """The requested conversation is absent or owned by another session."""


class ConversationHistoryService:
    """Store and retrieve conversations scoped to one anonymous browser session."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def claim_anonymous(self, session_id: UUID | None, user_id: UUID) -> None:
        """Attach this browser's pre-authentication history to its verified user."""

        if session_id is None:
            return
        await self.session.execute(
            update(Conversation)
            .where(
                Conversation.anonymous_session_id == session_id,
                Conversation.user_id.is_(None),
            )
            .values(user_id=user_id, anonymous_session_id=None)
        )

    async def assert_access(self, conversation_id: UUID, user_id: UUID) -> None:
        """Reject unknown or cross-session conversation identifiers before AI work."""

        statement = select(Conversation.id).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        if (await self.session.scalar(statement)) is None:
            raise ConversationNotFoundError

    async def record_exchange(
        self,
        user_id: UUID,
        question: str,
        response: ChatResponse,
        conversation_id: UUID | None = None,
    ) -> UUID:
        """Atomically persist one user question and assistant response."""

        if conversation_id is None:
            conversation = Conversation(
                user_id=user_id,
                title=self._title(question),
            )
            self.session.add(conversation)
            await self.session.flush()
        else:
            statement = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            conversation = await self.session.scalar(statement)
            if conversation is None:
                raise ConversationNotFoundError
            conversation.updated_at = datetime.now(UTC)

        self.session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.USER,
                    content=question,
                    confidence=None,
                    citations=[],
                ),
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=response.answer,
                    confidence=response.confidence,
                    citations=[citation.model_dump(mode="json") for citation in response.citations],
                ),
                AuditLog(
                    actor_id=user_id,
                    action="ai.question_asked",
                    entity_type="conversation",
                    entity_id=conversation.id,
                    details={
                        "confidence": response.confidence,
                        "citations": len(response.citations),
                    },
                ),
            ]
        )
        await self.session.commit()
        return conversation.id

    async def history(self, user_id: UUID) -> list[ChatHistoryItem]:
        """Return the latest 50 conversations with messages in chronological order."""

        statement = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
            )
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
            .limit(50)
        )
        conversations = (await self.session.scalars(statement)).all()
        return [
            ChatHistoryItem(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                messages=[
                    ChatMessage(
                        id=message.id,
                        role=message.role,
                        content=message.content,
                        confidence=(
                            float(message.confidence) if message.confidence is not None else None
                        ),
                        citations=message.citations,
                        created_at=message.created_at,
                    )
                    for message in conversation.messages
                ],
            )
            for conversation in conversations
        ]

    async def delete(self, conversation_id: UUID, user_id: UUID) -> None:
        """Delete one owned conversation and its cascade-owned messages."""

        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        conversation = await self.session.scalar(statement)
        if conversation is None:
            raise ConversationNotFoundError
        await self.session.delete(conversation)
        await self.session.commit()

    @staticmethod
    def _title(question: str) -> str:
        normalized = " ".join(question.split())
        return normalized if len(normalized) <= 80 else f"{normalized[:77]}..."
