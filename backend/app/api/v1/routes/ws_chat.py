"Minimal websocket chat route"

from fastapi import WebSocket, WebSocketDisconnect
from uuid import UUID, uuid4
from backend.app.schemas.message import ChatMessage
from backend.app.llm.client import LMStudioClient
from fastapi import APIRouter
from dotenv import load_dotenv
import os 
from typing import List
from fastapi import HTTPException
from backend.app.core.rate_limit import allow_request


router = APIRouter()

load_dotenv()
API_URL = os.getenv("LM_STUDIO_API_URL")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL")

llm_client = LMStudioClient(api_url=API_URL, model=LM_STUDIO_MODEL)

SYSTEM_MESSAGE = ChatMessage(role="system", 
                             content="You are a helpful assistant.")

def trim_conversation(messages: List[ChatMessage], 
                      max_messages: int = 12) -> List[ChatMessage]:
    """Trim conversation to the last `max_messages` messages, keeping the system message."""
    system_message = messages[0]
    rest_messages = messages[1:]

    if len(rest_messages) <= max_messages:
        return messages
    
    trimmed_messages = rest_messages[-max_messages:]
    return [system_message] + trimmed_messages


@router.websocket("/ws/chat")
async def webssocket_chat(ws: WebSocket):
    """websocket chat endpoint"""

    client_ip = ws.client.host
    if not allow_request(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    await ws.accept()

    conversation_id = uuid4()
    conversation = [SYSTEM_MESSAGE]
    
    try:
        while True: 
            user_text = await ws.receive_text()
            
            if not allow_request(client_ip):  # Check for each message
                await ws.send_text("Rate limit exceeded")
                continue
            
            conversation.append(ChatMessage(role="user", 
                                            content=user_text))    
            
            assistant_text = ""  # Initialize accumulator for assistant's tokens
            try:
                async for token in llm_client.stream_chat_completion(
                                            trim_conversation(conversation, max_messages=12)):
                    assistant_text += token
                    await ws.send_text(token)
                
                if not assistant_text:
                    await ws.send_text("Error: No response from LLM")
                
                conversation.append(ChatMessage(role="assistant", 
                                                content=assistant_text))
            except Exception as e:
                error_msg = f"Error generating response: {str(e)}"
                print(error_msg)
                await ws.send_text(error_msg)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {conversation_id}")