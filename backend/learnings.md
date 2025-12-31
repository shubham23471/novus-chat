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

- Create a steaming end-point. LMstudio also support streaming. 

---
# Context Window Safety

## simple context trimming strategy

`keep system message + last N messages`

---
# Next we’ll tackle:

1. WebSockets vs HTTP streaming
    - Suport real-time chat over websockets. 
    - https://www.wallarm.com/what/websocket-vs-http-how-are-these-2-different
    - 
2. Per-conversation locks
    - prevent two requests corrupting the same conversation.
3. Rate limiting
    - Protect itself from abuse and overload
4. Backpressure
    - Handle disconnects gracefully
5. Preparing for real users

## Problem: The Concurrency Problem
```
Conversation A
User sends message 1
User sends message 2 (quickly)

|

Two requests arrive at the same time. --> both load conversation --> append user message --> call LLM
```

`solution: Per-conversation Locks`: Only one LLM call per conversation at a time. 

**TODO: Fix memory leak issue with lock.**

## Why Websockets
HTTPS streaming is 
- one way 
- Fragile on mobile
- hard to reconnect

Chat apps need:
```arduino
- Persistent connection
- Bi-directional flow
- Reconnect handling
That’s WebSockets.

Client ── WS ── FastAPI ── LLM
   ↑        ↓ tokens
   └──── messages ───────┘

```

HTTP vs WebSocket
```
HTTP (used by /chat/message and /chat/stream endpoints):
- Request-response model
- Connection closes after response is sent
- One message exchange per connection

WebSocket (used by /ws/chat endpoint):

- Persistent, bidirectional connection
- Stays open indefinitely until explicitly closed
- Allows multiple message exchanges on the same connection
```

## Rate Limiting 
**Why**
Without it:

- One user can freeze your server
- Accidental infinite loops kill you
- Public demos get destroyed

Solution: 
- per IP 
- Per minute
- In-memory


--- 
# Test1: Two simultaneous messages don’t corrupt state

`pip install pytest pytest-asyncio httpx`