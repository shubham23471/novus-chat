from backend.app.llm.client import LMStudioClient
import os
from dotenv import load_dotenv
from backend.app.schemas.message import ChatMessage
from fastapi import APIRouter, Depends
from uuid import uuid4, UUID
from fastapi import HTTPException
from backend.app.schemas import ChatRequest, ChatResponse
from fastapi.responses import StreamingResponse
from typing import List
from backend.app.core.redis_lock import conversation_lock
from backend.app.core.rate_limit import allow_request
from backend.db.redis_client import RedisClient
from backend.app.core.auth import get_current_user, User
from backend.app.core.database import (
    get_conversation,
    create_conversation,
    add_message,
    load_conversation_messages
)

def trim_conversation(messages: List[ChatMessage], 
                      max_messages: int = 12) -> List[ChatMessage]:
    """Trim conversation to the last `max_messages` messages, keeping the system message."""

    system_message = messages[0]
    rest_messages = messages[1:]

    if len(rest_messages) <= max_messages:
        return messages
    
    trimmed_messages = rest_messages[-max_messages:]
    return [system_message] + trimmed_messages

load_dotenv()
API_URL = os.getenv("LM_STUDIO_API_URL")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL")

llm_client = LMStudioClient(api_url=API_URL, model=LM_STUDIO_MODEL)

SYSTEM_MESSAGE_CONTENT = "You are a helpful assistant."

router = APIRouter()
redis_client = RedisClient.get_client()  # Initialize Redis client



@router.post("/chat/message", response_model=ChatResponse)
async def chat_message(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send a chat message and receive a response.
    
    Requires authentication. Creates a new conversation if conversation_id is not provided.
    """
    # Rate limit check (now user-based)
    if not allow_request(str(current_user.id)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # 1. Load or create conversation
    if chat_request.conversation_id:
        conversation_data = await get_conversation(
            chat_request.conversation_id,
            current_user.id
        )
        if not conversation_data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation_id = UUID(conversation_data['id'])
    else:
        # Create new conversation
        conversation_data = await create_conversation(
            user_id=current_user.id,
            title="New Chat"
        )
        conversation_id = UUID(conversation_data['id'])

    async with conversation_lock(redis_client, conversation_id):
        # 2. Add user message to database
        await add_message(
            conversation_id=conversation_id,
            role="user",
            content=chat_request.message
        )

        # 3. Load conversation history for LLM (with system message injected)
        messages = await load_conversation_messages(
            conversation_id,
            system_message=SYSTEM_MESSAGE_CONTENT
        )

        # 4. Call LLM
        try:
            assistant_text = await llm_client.generate_chat_completion(
                messages=trim_conversation(messages, max_messages=12)
            )
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        
        # 5. Save assistant response to database
        await add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_text
        )

        # 6. Return response
        return ChatResponse(
            conversation_id=conversation_id,
            reply=assistant_text
        )

@router.post("/chat/stream")
async def stream_chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Stream chat response tokens in real-time.
    
    Requires authentication. Creates a new conversation if conversation_id is not provided.
    """
    # Rate limit check (now user-based)
    if not allow_request(str(current_user.id)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # 1. Load or create conversation
    if chat_request.conversation_id:
        conversation_data = await get_conversation(
            chat_request.conversation_id,
            current_user.id
        )
        if not conversation_data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation_id = UUID(conversation_data['id'])
    else:
        # Create new conversation
        conversation_data = await create_conversation(
            user_id=current_user.id,
            title="New Chat"
        )
        conversation_id = UUID(conversation_data['id'])
        
    async with conversation_lock(redis_client, conversation_id):
        # 2. Add user message to database
        await add_message(
            conversation_id=conversation_id,
            role="user",
            content=chat_request.message
        )

        # 3. Load conversation history for LLM (with system message injected)
        messages = await load_conversation_messages(
            conversation_id,
            system_message=SYSTEM_MESSAGE_CONTENT
        )

        async def token_generator():
            assistant_text = ""

            async for token in llm_client.stream_chat_completion(
                trim_conversation(messages, max_messages=12)
            ):
                assistant_text += token
                yield token
            
            # Persist assistant message after stream completes
            await add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_text
            )

    return StreamingResponse(token_generator(), 
                                media_type='text/plain')