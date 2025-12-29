from typing import Dict, List
from uuid import UUID
from backend.app.schemas.message import ChatMessage

ConversationStore = Dict[UUID, List[ChatMessage]]

conversation_store: ConversationStore = {}
