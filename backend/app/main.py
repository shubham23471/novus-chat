from fastapi import FastAPI
from backend.app.api.v1.routes.chat_routes import router as chat_router


app = FastAPI()

app.include_router(chat_router, prefix="/api/v1", tags=['chat'])

@app.get("/health")
def health():
    return {"status": "ok"}



