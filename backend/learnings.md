# Multi-turn chat

First request: `POST /api/v1/chat/message`
```json
{
  "message": "Hello"
}
```

Response
```json
{
  "conversation_id": "8a3e6d0b-7cbb-4c63-9c61-4d2fda1a1e33",
  "reply": "Hello! How can I help you today?"
}
```

Second request (continue conversation)
    `POST /api/v1/chat/message`


```json
{
  "conversation_id": "8a3e6d0b-7cbb-4c63-9c61-4d2fda1a1e33",
  "message": "What did I just say?"
}

```

---

# Stream response
🔹 Key Design Rule :The LLM client must yield tokens, not strings.
This keeps it reusable for:
- WebSockets
- SSE
- Batch jobs