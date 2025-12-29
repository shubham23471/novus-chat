from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class ChatRequest(BaseModel):
    "Request schema for chat message"
    message:str 
    conversation_id: Optional[UUID] = None


class ChatResponse(BaseModel):
    "Response schema for chat message"
    conversation_id: UUID
    reply : str