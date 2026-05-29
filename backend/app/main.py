from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.v1.routes.chat_routes import router as chat_router
from backend.app.api.v1.routes.ws_chat import router as ws_chat_router
from backend.app.api.v1.routes.auth_routes import router as auth_router
from backend.app.api.v1.routes.conversation_routes import router as conversation_router

app = FastAPI(
    title="Novus Chat API",
    description="ChatGPT-like API with Supabase authentication",
    version="1.0.0"
)

# CORS middleware (configure as needed for your frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=['authentication'])
app.include_router(chat_router, prefix="/api/v1", tags=['chat'])
app.include_router(conversation_router, prefix="/api/v1", tags=['conversations'])
app.include_router(ws_chat_router, prefix="/api/v1", tags=['websocket']) 

@app.get("/health")
def health():
    return {"status": "ok"}



