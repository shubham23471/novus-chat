from pydantic import BaseModel, Field
from typing import Literal


Role = Literal['user', 'assistant', 'system']


class ChatMessage(BaseModel):
    """Schema for chat message"""
    role : Role
    content: str = Field(min_length=1,
                         max_length=1000,
                         description="Message content")