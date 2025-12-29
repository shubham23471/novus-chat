from backend.app.llm.client import LMStudioClient
import os
from dotenv import load_dotenv
from backend.app.schemas.message import ChatMessage
from fastapi import APIRouter
from uuid import uuid4
from fastapi import HTTPException
from backend.app.schemas import ChatRequest, ChatResponse
from backend.app.core.conversation_store import conversation_store

load_dotenv()
API_URL = os.getenv("LM_STUDIO_API_URL")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL")

llm_client = LMStudioClient(api_url=API_URL, model=LM_STUDIO_MODEL)

SYSTEM_MESSAGE = ChatMessage(role="system", 
                             content="You are a helpful assistant.")



router = APIRouter()


@router.post("/chat/message", response_model=ChatResponse)
async def chat_message(request:ChatRequest):

    # 1. Load or create conversation
    if request.conversation_id:
        conversation_id = request.conversation_id
        conversation = conversation_store.get(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation_id = uuid4()
        conversation = [SYSTEM_MESSAGE]
        conversation_store[conversation_id] = conversation

    # 2. Append user message to conversation
    user_message = ChatMessage(role="user", content=request.message)
    conversation.append(user_message)

    # 3. call LLM
    try : 
        assitant_text = await llm_client.generate_chat_completion(messages=conversation)
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