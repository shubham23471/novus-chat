from fastapi import FastAPI
from backend.app.api.v1.routes.chat_routes import router as chat_router
from backend.app.api.v1.routes.ws_chat import router as ws_chat_router 

app = FastAPI()

app.include_router(chat_router, prefix="/api/v1", tags=['chat'])
app.include_router(ws_chat_router, prefix="/api/v1", tags=['ws_chat']) 

@app.get("/health")
def health():
    return {"status": "ok"}



