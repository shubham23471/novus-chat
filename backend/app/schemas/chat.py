from pydantic import BaseModel, Field

class ChatMessageRequest(BaseModel):
    "Request schema for chat message"
    message:str = Field(min_length=1,
                        max_length=1000,
                        description="Message content")



class ChatMessageResponse(BaseModel):
    "Response schema for chat message"
    
    