import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.notification import NotificationType
from app.models.user import User, UserRole
from app.repositories.message_repository import MessageRepository
from app.repositories.store_repository import StoreRepository
from app.schemas.message import (
    ConversationResponse,
    MessageCreateRequest,
    MessageResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter()


# --- Customer: start or get conversation with a store ---

@router.post("/conversations/store/{store_id}", response_model=ConversationResponse)
async def get_or_create_conversation(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    store_repo = StoreRepository(db)
    store = await store_repo.find_by_id(store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    msg_repo = MessageRepository(db)
    conversation = await msg_repo.find_or_create_conversation(user.id, store_id)

    return ConversationResponse(
        id=conversation.id,
        customer_id=conversation.customer_id,
        store_id=conversation.store_id,
        store_name=store.name,
        other_user_name=store.name,
        last_message_text=None,
        last_message_at=conversation.last_message_at,
        unread_count=0,
        created_at=conversation.created_at,
    )


# --- List conversations ---

@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    msg_repo = MessageRepository(db)

    if user.role == UserRole.MERCHANT:
        store_repo = StoreRepository(db)
        store = await store_repo.find_by_owner(user.id)
        if not store:
            return []
        rows = await msg_repo.list_conversations_for_store(store.id, user.id)
        return [
            ConversationResponse(
                id=row["conversation"].id,
                customer_id=row["conversation"].customer_id,
                store_id=row["conversation"].store_id,
                store_name=store.name,
                other_user_name=row["customer_name"] or "Customer",
                last_message_text=row["last_message_text"],
                last_message_at=row["conversation"].last_message_at,
                unread_count=row["unread_count"],
                created_at=row["conversation"].created_at,
            )
            for row in rows
        ]
    else:
        rows = await msg_repo.list_conversations_for_customer(user.id)
        return [
            ConversationResponse(
                id=row["conversation"].id,
                customer_id=row["conversation"].customer_id,
                store_id=row["conversation"].store_id,
                store_name=row["store_name"],
                other_user_name=row["store_name"],
                last_message_text=row["last_message_text"],
                last_message_at=row["conversation"].last_message_at,
                unread_count=row["unread_count"],
                created_at=row["conversation"].created_at,
            )
            for row in rows
        ]


# --- Messages within a conversation ---

@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    msg_repo = MessageRepository(db)
    conversation = await msg_repo.find_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # Verify user has access
    if user.role == UserRole.MERCHANT:
        store_repo = StoreRepository(db)
        store = await store_repo.find_by_owner(user.id)
        if not store or store.id != conversation.store_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif user.id != conversation.customer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Mark messages as read
    await msg_repo.mark_messages_read(conversation_id, user.id)

    messages = await msg_repo.list_messages(conversation_id, offset=offset, limit=limit)
    return [MessageResponse.model_validate(m) for m in messages]


# --- Send message ---

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    msg_repo = MessageRepository(db)
    conversation = await msg_repo.find_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # Verify user has access
    store_repo = StoreRepository(db)
    store = await store_repo.find_by_id(conversation.store_id)

    if user.role == UserRole.MERCHANT:
        if not store or store.owner_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        recipient_id = conversation.customer_id
    elif user.id == conversation.customer_id:
        recipient_id = store.owner_id if store else None
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    message = await msg_repo.create_message(conversation_id, user.id, body.text)

    # Send notification to recipient
    if recipient_id:
        notif_service = NotificationService(db)
        sender_name = store.name if user.role == UserRole.MERCHANT else (user.full_name or "Customer")
        await notif_service.notify(
            user_id=recipient_id,
            notification_type=NotificationType.NEW_MESSAGE,
            title=f"New message from {sender_name}",
            body=body.text[:100],
            data={
                "conversation_id": str(conversation.id),
                "store_id": str(conversation.store_id),
                "sender_id": str(user.id),
            },
        )

    return MessageResponse.model_validate(message)
