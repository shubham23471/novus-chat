from backend.app.llm.client import LMStudioClient
import os
from dotenv import load_dotenv
from backend.app.schemas.message import ChatMessage
from fastapi import APIRouter
from uuid import uuid4
from fastapi import HTTPException
from backend.app.schemas import ChatRequest, ChatResponse
from backend.app.core.conversation_store import conversation_store
from fastapi.responses import StreamingResponse
from typing import List
from backend.app.core.redis_lock import conversation_lock
from backend.app.core.rate_limit import allow_request
from fastapi import Request
from backend.db.redis_client import RedisClient

def trim_converstaion(messages: List[ChatMessage], 
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

SYSTEM_MESSAGE = ChatMessage(role="system", 
                             content="You are a helpful assistant.")


router = APIRouter()
redis_client = RedisClient.get_client()  # Initialize Redis client



@router.post("/chat/message", response_model=ChatResponse)
async def chat_message(request: Request, chat_request: ChatRequest):

    # rate limit check
    client_ip = request.client.host
    if not allow_request(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # 1. Load or create conversation
    if chat_request.conversation_id:
        conversation_id = chat_request.conversation_id
        conversation = conversation_store.get(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation_id = uuid4()
        conversation = [SYSTEM_MESSAGE]
        conversation_store[conversation_id] = conversation

    async with conversation_lock(redis_client, conversation_id):
        # 2. Append user message to conversation
        user_message = ChatMessage(role="user", content=chat_request.message)
        conversation.append(user_message)

        # 3. call LLM
        try : 
            assitant_text = await llm_client.generate_chat_completion(
                                                messages=trim_converstaion(conversation, max_messages=12))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        

        # 4. Append assistant message to conversation
        assistant_message = ChatMessage(role="assistant", content=assitant_text)
        conversation.append(assistant_message)

        #5. Return response
        response = ChatResponse(
            conversation_id=conversation_id,
            reply=assitant_text)
    return response

@router.post("/chat/stream")
async def stream_chat(request: Request, chat_request:ChatRequest):
    # rate limit check
    client_ip = request.client.host
    if not allow_request(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # 1. Load or create conversation
    if chat_request.conversation_id:
        conversation_id = chat_request.conversation_id
        conversation = conversation_store.get(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation_id = uuid4()
        conversation = [SYSTEM_MESSAGE]
        conversation_store[conversation_id] = conversation


    async with conversation_lock(redis_client, conversation_id):

        # 2. Append user message to conversation
        user_message = ChatMessage(role="user", content=chat_request.message)
        conversation.append(user_message)

        async def token_generator():
            assistant_text = ""

            async for token in llm_client.stream_chat_completion(trim_converstaion(conversation, max_messages=12)):
                assistant_text += token
                yield token
            
            # persist assistant message after stream completes
            conversation.append(ChatMessage(role='assistant', content=assistant_text))

    return StreamingResponse(token_generator(), 
                                media_type='text/plain')