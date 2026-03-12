import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    text: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    store_id: uuid.UUID
    store_name: str
    other_user_name: str
    last_message_text: str | None = None
    last_message_at: datetime
    unread_count: int = 0
    created_at: datetime
