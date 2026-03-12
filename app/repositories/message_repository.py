import uuid

from sqlalchemy import func, select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Conversation, Message
from app.models.store import Store
from app.models.user import User


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    # --- Conversations ---

    async def find_or_create_conversation(
        self, customer_id: uuid.UUID, store_id: uuid.UUID,
    ) -> Conversation:
        result = await self._db.execute(
            select(Conversation).where(
                Conversation.customer_id == customer_id,
                Conversation.store_id == store_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            return conversation

        conversation = Conversation(customer_id=customer_id, store_id=store_id)
        self._db.add(conversation)
        await self._db.flush()
        return conversation

    async def find_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self._db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_conversations_for_customer(
        self, customer_id: uuid.UUID,
    ) -> list[dict]:
        """List conversations with store name, last message, and unread count."""
        last_msg_subq = (
            select(
                Message.conversation_id,
                Message.text.label("last_text"),
                func.row_number().over(
                    partition_by=Message.conversation_id,
                    order_by=Message.created_at.desc(),
                ).label("rn"),
            )
            .subquery()
        )

        unread_subq = (
            select(
                Message.conversation_id,
                func.count().label("unread_count"),
            )
            .where(
                Message.is_read.is_(False),
                Message.sender_id != customer_id,
            )
            .group_by(Message.conversation_id)
            .subquery()
        )

        result = await self._db.execute(
            select(
                Conversation,
                Store.name.label("store_name"),
                last_msg_subq.c.last_text,
                func.coalesce(unread_subq.c.unread_count, 0).label("unread_count"),
            )
            .join(Store, Conversation.store_id == Store.id)
            .outerjoin(
                last_msg_subq,
                and_(
                    last_msg_subq.c.conversation_id == Conversation.id,
                    last_msg_subq.c.rn == 1,
                ),
            )
            .outerjoin(unread_subq, unread_subq.c.conversation_id == Conversation.id)
            .where(Conversation.customer_id == customer_id)
            .order_by(Conversation.last_message_at.desc())
        )
        rows = result.all()
        return [
            {
                "conversation": row[0],
                "store_name": row[1],
                "last_message_text": row[2],
                "unread_count": row[3],
            }
            for row in rows
        ]

    async def list_conversations_for_store(
        self, store_id: uuid.UUID, owner_id: uuid.UUID,
    ) -> list[dict]:
        """List conversations with customer name, last message, and unread count."""
        last_msg_subq = (
            select(
                Message.conversation_id,
                Message.text.label("last_text"),
                func.row_number().over(
                    partition_by=Message.conversation_id,
                    order_by=Message.created_at.desc(),
                ).label("rn"),
            )
            .subquery()
        )

        unread_subq = (
            select(
                Message.conversation_id,
                func.count().label("unread_count"),
            )
            .where(
                Message.is_read.is_(False),
                Message.sender_id != owner_id,
            )
            .group_by(Message.conversation_id)
            .subquery()
        )

        result = await self._db.execute(
            select(
                Conversation,
                User.full_name.label("customer_name"),
                last_msg_subq.c.last_text,
                func.coalesce(unread_subq.c.unread_count, 0).label("unread_count"),
            )
            .join(User, Conversation.customer_id == User.id)
            .outerjoin(
                last_msg_subq,
                and_(
                    last_msg_subq.c.conversation_id == Conversation.id,
                    last_msg_subq.c.rn == 1,
                ),
            )
            .outerjoin(unread_subq, unread_subq.c.conversation_id == Conversation.id)
            .where(Conversation.store_id == store_id)
            .order_by(Conversation.last_message_at.desc())
        )
        rows = result.all()
        return [
            {
                "conversation": row[0],
                "customer_name": row[1],
                "last_message_text": row[2],
                "unread_count": row[3],
            }
            for row in rows
        ]

    # --- Messages ---

    async def create_message(
        self, conversation_id: uuid.UUID, sender_id: uuid.UUID, text: str,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            text=text,
        )
        self._db.add(message)
        await self._db.flush()

        # Update conversation last_message_at
        conversation = await self.find_conversation(conversation_id)
        if conversation:
            from datetime import UTC, datetime
            merged = Conversation(
                id=conversation.id,
                customer_id=conversation.customer_id,
                store_id=conversation.store_id,
                last_message_at=datetime.now(UTC),
                created_at=conversation.created_at,
            )
            await self._db.merge(merged)
            await self._db.flush()

        return message

    async def list_messages(
        self, conversation_id: uuid.UUID, *, offset: int = 0, limit: int = 50,
    ) -> list[Message]:
        result = await self._db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_messages_read(
        self, conversation_id: uuid.UUID, reader_id: uuid.UUID,
    ) -> int:
        """Mark all messages in a conversation as read (except those sent by the reader)."""
        result = await self._db.execute(
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != reader_id,
                Message.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await self._db.flush()
        return result.rowcount
