from backend.app.schemas import ChatMessageRequest
import uuid
from fastapi import APIRouter


router = APIRouter()

@router.post("/chat/message")
def create_chat(request:ChatMessageRequest):
    id = uuid.uuid4().hex
    return {"id": id, 
            "response" : "hello from other side"}
