# Supabase Integration Implementation Plan

## Goal

Integrate Supabase authentication and PostgreSQL database into the novus-chat application to replace in-memory conversation storage with persistent, user-scoped data storage. This will enable user authentication, secure conversation management, and prepare the application for production deployment.

## User Review Required

> [!IMPORTANT]
> **Authentication Provider Choice Required**
> 
> Please decide which authentication method(s) you want to support:
> - **Email/Password**: Traditional signup/login (recommended for MVP)
> - **Magic Link**: Passwordless email login
> - **OAuth**: Google, GitHub, Discord, etc.
> 
> This plan assumes **email/password** authentication. Let me know if you want different/additional methods.

> [!WARNING]
> **Breaking Changes**
> 
> This integration will introduce breaking changes:
> 1. **All endpoints will require authentication** (except health check)
> 2. **Existing in-memory conversations will be lost** (no migration path from memory)
> 3. **API clients must send JWT tokens** in Authorization header
> 4. **Rate limiting will change from IP-based to user-based**
> 
> Consider creating a `/v2` API version to maintain backward compatibility if needed.

> [!CAUTION]
> **Supabase Account Setup Required**
> 
> Before implementation, you must:
> 1. Create Supabase account at https://supabase.com
> 2. Create a new project
> 3. Run the database schema from the setup guide
> 4. Add credentials to `.env` file
> 
> Implementation cannot proceed without these steps completed.

---

## Proposed Changes

### Core Authentication Module

#### [NEW] [supabase_client.py](file:///Users/shubham/saas/novus-chat/backend/app/core/supabase_client.py)

Singleton Supabase client for the application.

**Purpose**: Centralized Supabase connection management

**Key Features**:
- Singleton pattern (one client instance)
- Environment-based configuration
- Both anon and service role clients
- Connection validation

**Implementation**:
```python
from supabase import create_client, Client
import os
from dotenv import load_dotenv

class SupabaseClient:
    _anon_client: Client = None
    _service_client: Client = None
    
    @classmethod
    def get_anon_client(cls) -> Client:
        """Client for user-scoped operations (respects RLS)"""
        if cls._anon_client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_ANON_KEY")
            cls._anon_client = create_client(url, key)
        return cls._anon_client
    
    @classmethod
    def get_service_client(cls) -> Client:
        """Client for admin operations (bypasses RLS)"""
        if cls._service_client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")
            cls._service_client = create_client(url, key)
        return cls._service_client
```

---

#### [NEW] [auth.py](file:///Users/shubham/saas/novus-chat/backend/app/core/auth.py)

Authentication middleware and user management.

**Purpose**: JWT verification, user extraction, and auth dependencies

**Key Components**:
1. `get_current_user()` - FastAPI dependency for protected routes
2. `verify_token()` - JWT validation helper
3. `User` model - Pydantic model for authenticated user

**Implementation**:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from uuid import UUID
from typing import Optional

security = HTTPBearer()

class User(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Verify JWT token and return current user.
    Raises 401 if token is invalid or expired.
    """
    token = credentials.credentials
    
    try:
        from backend.app.core.supabase_client import SupabaseClient
        supabase = SupabaseClient.get_anon_client()
        
        # Verify token with Supabase
        user_response = supabase.auth.get_user(token)
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        return User(
            id=user_response.user.id,
            email=user_response.user.email,
            full_name=user_response.user.user_metadata.get('full_name')
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
```

---

### Database Operations Module

#### [NEW] [database.py](file:///Users/shubham/saas/novus-chat/backend/app/core/database.py)

Database operations for conversations and messages.

**Purpose**: Abstraction layer for Supabase database operations

**Key Functions**:
- `get_conversation()` - Fetch conversation with messages
- `create_conversation()` - Create new conversation
- `add_message()` - Add message to conversation
- `list_user_conversations()` - Get all user conversations
- `delete_conversation()` - Delete conversation

**Implementation Highlights**:
```python
from uuid import UUID
from typing import List, Optional
from backend.app.schemas.message import ChatMessage
from backend.app.core.supabase_client import SupabaseClient

async def get_conversation(conversation_id: UUID, user_id: UUID) -> Optional[dict]:
    """
    Get conversation with all messages.
    RLS ensures user can only access their own conversations.
    """
    supabase = SupabaseClient.get_anon_client()
    
    response = supabase.table('conversations')\
        .select('*, messages(*)')\
        .eq('id', str(conversation_id))\
        .eq('user_id', str(user_id))\
        .single()\
        .execute()
    
    return response.data

async def create_conversation(user_id: UUID, title: str = "New Chat") -> dict:
    """Create new conversation for user"""
    supabase = SupabaseClient.get_anon_client()
    
    response = supabase.table('conversations')\
        .insert({'user_id': str(user_id), 'title': title})\
        .execute()
    
    return response.data[0]

async def add_message(
    conversation_id: UUID, 
    role: str, 
    content: str
) -> dict:
    """Add message to conversation"""
    supabase = SupabaseClient.get_anon_client()
    
    response = supabase.table('messages')\
        .insert({
            'conversation_id': str(conversation_id),
            'role': role,
            'content': content
        })\
        .execute()
    
    return response.data[0]
```

---

### API Routes - Authentication

#### [NEW] [auth_routes.py](file:///Users/shubham/saas/novus-chat/backend/app/api/v1/routes/auth_routes.py)

Authentication endpoints for signup, login, logout.

**Endpoints**:
1. `POST /auth/signup` - User registration
2. `POST /auth/login` - User login
3. `POST /auth/logout` - User logout
4. `GET /auth/me` - Get current user info
5. `POST /auth/refresh` - Refresh access token

**Example Implementation**:
```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from backend.app.core.supabase_client import SupabaseClient
from backend.app.core.auth import get_current_user, User

router = APIRouter()

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup")
async def signup(request: SignupRequest):
    supabase = SupabaseClient.get_anon_client()
    
    try:
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "full_name": request.full_name
                }
            }
        })
        
        return {
            "user": response.user,
            "session": response.session
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(request: LoginRequest):
    supabase = SupabaseClient.get_anon_client()
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": response.user
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

---

### API Routes - Chat (Updated)

#### [MODIFY] [chat_routes.py](file:///Users/shubham/saas/novus-chat/backend/app/api/v1/routes/chat_routes.py)

Update existing chat routes to use authentication and Supabase database.

**Key Changes**:
1. Add `current_user: User = Depends(get_current_user)` to all endpoints
2. Replace in-memory conversation store with database calls
3. Update rate limiting to use `user_id` instead of IP
4. Keep Redis locks for concurrency control
5. Add system message to new conversations in database

**Modified Endpoint Example**:
```python
@router.post("/chat/message", response_model=ChatResponse)
async def chat_message(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user)  # ← NEW: Require auth
):
    # Rate limit check (now user-based)
    if not allow_request(str(current_user.id)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Get or create conversation
    if chat_request.conversation_id:
        conversation_data = await get_conversation(
            chat_request.conversation_id, 
            current_user.id
        )
        if not conversation_data:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation
        conversation_data = await create_conversation(current_user.id)
        # Add system message
        await add_message(
            conversation_data['id'],
            'system',
            'You are a helpful assistant.'
        )

    conversation_id = UUID(conversation_data['id'])
    
    async with conversation_lock(redis_client, conversation_id):
        # Add user message to database
        await add_message(conversation_id, 'user', chat_request.message)
        
        # Load conversation history for LLM
        messages = await load_conversation_messages(conversation_id)
        
        # Call LLM
        try:
            assistant_text = await llm_client.generate_chat_completion(
                messages=trim_conversation(messages, max_messages=12)
            )
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        
        # Save assistant response
        await add_message(conversation_id, 'assistant', assistant_text)
        
        return ChatResponse(
            conversation_id=conversation_id,
            reply=assistant_text
        )
```

---

#### [MODIFY] [ws_chat.py](file:///Users/shubham/saas/novus-chat/backend/app/api/v1/routes/ws_chat.py)

Update WebSocket chat to support authentication.

**Key Changes**:
1. Accept JWT token as query parameter or in first message
2. Verify token before accepting connection
3. Use database instead of in-memory storage
4. Associate conversation with authenticated user

**Note**: WebSocket authentication is more complex. Consider using query parameter:
```python
@router.websocket("/ws/chat")
async def websocket_chat(
    ws: WebSocket,
    token: str = Query(...)  # JWT token as query param
):
    # Verify token before accepting
    try:
        user = await verify_token(token)
    except:
        await ws.close(code=1008, reason="Unauthorized")
        return
    
    await ws.accept()
    # Rest of implementation...
```

---

### API Routes - Conversations

#### [NEW] [conversation_routes.py](file:///Users/shubham/saas/novus-chat/backend/app/api/v1/routes/conversation_routes.py)

Conversation management endpoints.

**Endpoints**:
1. `GET /conversations` - List user's conversations
2. `GET /conversations/{id}` - Get specific conversation with messages
3. `DELETE /conversations/{id}` - Delete conversation
4. `PATCH /conversations/{id}` - Update conversation (e.g., title)

**Implementation**:
```python
@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """List user's conversations"""
    supabase = SupabaseClient.get_anon_client()
    
    response = supabase.table('conversations')\
        .select('id, title, created_at, updated_at')\
        .eq('user_id', str(current_user.id))\
        .order('updated_at', desc=True)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    return response.data

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Delete conversation (RLS ensures user owns it)"""
    supabase = SupabaseClient.get_anon_client()
    
    response = supabase.table('conversations')\
        .delete()\
        .eq('id', str(conversation_id))\
        .eq('user_id', str(current_user.id))\
        .execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": "Conversation deleted"}
```

---

### Core Modules Updates

#### [MODIFY] [rate_limit.py](file:///Users/shubham/saas/novus-chat/backend/app/core/rate_limit.py)

Change from IP-based to user-based rate limiting.

**Changes**:
```python
# OLD
def allow_request(ip: str) -> bool:
    requests[ip] = [t for t in requests[ip] if now - t < WINDOW]
    if len(requests[ip]) >= RATE_LIMIT:
        return False
    requests[ip].append(now)
    return True

# NEW
def allow_request(user_id: str) -> bool:
    """Rate limit by user_id instead of IP"""
    now = time.time()
    requests[user_id] = [t for t in requests[user_id] if now - t < WINDOW]
    
    if len(requests[user_id]) >= RATE_LIMIT:
        return False
    
    requests[user_id].append(now)
    return True
```

---

#### [MODIFY] [main.py](file:///Users/shubham/saas/novus-chat/backend/app/main.py)

Register new auth and conversation routers.

**Changes**:
```python
from backend.app.api.v1.routes.auth_routes import router as auth_router
from backend.app.api.v1.routes.conversation_routes import router as conversation_router

app.include_router(auth_router, prefix="/api/v1/auth", tags=['auth'])
app.include_router(conversation_router, prefix="/api/v1", tags=['conversations'])
```

---

### Configuration & Dependencies

#### [MODIFY] [requirements.txt](file:///Users/shubham/saas/novus-chat/backend/requirements.txt)

Add Supabase client dependency.

**Changes**:
```diff
 fastapi
 httpx
 python-dotenv
 pytest 
 pytest-asyncio 
 httpx
 redis
+supabase>=2.0.0
+pydantic[email]
```

---

#### [MODIFY] [.env](file:///Users/shubham/saas/novus-chat/backend/.env)

Add Supabase configuration.

**New Variables**:
```bash
# Supabase Configuration
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here
```

---

### Database Schema

#### [MODIFY] [init.sql](file:///Users/shubham/saas/novus-chat/backend/db/init.sql)

Update schema for Supabase compatibility (already provided in setup guide).

**Key Changes**:
- Reference `auth.users` instead of custom `users` table
- Add RLS policies
- Add triggers for profile creation
- Add `updated_at` triggers

---

## Verification Plan

### Automated Tests

#### 1. Authentication Tests

**File**: `backend/tests/test_auth.py` (new)

**Command**:
```bash
pytest backend/tests/test_auth.py -v
```

**Test Cases**:
- `test_signup_success` - Valid signup creates user
- `test_signup_duplicate_email` - Duplicate email returns 400
- `test_login_success` - Valid credentials return JWT
- `test_login_invalid_credentials` - Invalid credentials return 401
- `test_protected_route_without_token` - Returns 401
- `test_protected_route_with_valid_token` - Returns 200
- `test_protected_route_with_expired_token` - Returns 401

---

#### 2. Chat Integration Tests

**File**: `backend/tests/test_chat_with_auth.py` (new)

**Command**:
```bash
pytest backend/tests/test_chat_with_auth.py -v
```

**Test Cases**:
- `test_chat_message_authenticated` - Authenticated user can send message
- `test_chat_message_unauthenticated` - Unauthenticated request returns 401
- `test_conversation_isolation` - User A cannot access User B's conversations
- `test_conversation_persistence` - Messages persist across requests
- `test_concurrent_messages_with_auth` - Concurrent requests work with auth

---

#### 3. Database Operations Tests

**File**: `backend/tests/test_database.py` (new)

**Command**:
```bash
pytest backend/tests/test_database.py -v
```

**Test Cases**:
- `test_create_conversation` - Creates conversation in database
- `test_add_message` - Adds message to conversation
- `test_get_conversation` - Retrieves conversation with messages
- `test_list_conversations` - Lists user conversations
- `test_delete_conversation` - Deletes conversation and messages (cascade)

---

#### 4. Existing Tests Update

**File**: `backend/tests/test_concurrent_messages.py` (modify)

**Command**:
```bash
pytest backend/tests/test_concurrent_messages.py -v
```

**Changes Needed**:
- Add authentication to test client
- Create test user before running tests
- Update assertions for database-backed storage

---

### Manual Verification

#### 1. Supabase Setup Verification

**Steps**:
1. Log into Supabase dashboard
2. Navigate to Table Editor
3. Verify tables exist: `profiles`, `conversations`, `messages`
4. Check RLS is enabled on all tables
5. Review policies in Authentication → Policies

**Expected Result**: All tables present with RLS enabled

---

#### 2. User Signup Flow

**Steps**:
1. Start FastAPI server: `uvicorn backend.app.main:app --reload`
2. Send signup request:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/signup \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "password": "SecurePass123!",
       "full_name": "Test User"
     }'
   ```
3. Check Supabase dashboard → Authentication → Users
4. Verify user appears in list
5. Check Table Editor → profiles table
6. Verify profile was auto-created

**Expected Result**: User created in both `auth.users` and `profiles` table

---

#### 3. Login and Chat Flow

**Steps**:
1. Login to get JWT:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "password": "SecurePass123!"
     }'
   ```
2. Copy `access_token` from response
3. Send chat message with token:
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/message \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "message": "Hello, how are you?"
     }'
   ```
4. Check Supabase Table Editor → conversations
5. Verify conversation created
6. Check messages table
7. Verify system message and user message exist

**Expected Result**: Conversation and messages saved to database

---

#### 4. Conversation Isolation Test

**Steps**:
1. Create two users (User A and User B)
2. User A creates a conversation and sends messages
3. Note the `conversation_id`
4. Login as User B
5. Try to access User A's conversation:
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/message \
     -H "Authorization: Bearer USER_B_TOKEN" \
     -d '{
       "conversation_id": "USER_A_CONVERSATION_ID",
       "message": "Trying to access"
     }'
   ```

**Expected Result**: 404 error (RLS prevents access)

---

#### 5. WebSocket Chat Test

**Steps**:
1. Use a WebSocket client (e.g., `wscat` or browser console)
2. Connect with JWT token:
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/api/v1/ws/chat?token=YOUR_JWT');
   ws.onmessage = (event) => console.log(event.data);
   ws.send('Hello via WebSocket!');
   ```
3. Verify messages stream back
4. Check database for saved messages

**Expected Result**: WebSocket works with authentication, messages persist

---

### Performance Testing

**Tool**: `pytest-benchmark` or manual timing

**Test**: 
- 100 concurrent authenticated requests
- Measure response time
- Check for database connection pool issues

**Command**:
```bash
pytest backend/tests/test_performance.py -v
```

---

### Security Audit Checklist

- [ ] Service key not exposed in frontend
- [ ] All tables have RLS enabled
- [ ] RLS policies tested with different users
- [ ] JWT tokens expire appropriately (1 hour)
- [ ] Passwords not logged or exposed
- [ ] CORS configured correctly
- [ ] Rate limiting works per user
- [ ] SQL injection prevented (Supabase handles this)

---

## Migration Notes

### Data Migration

**Current State**: Conversations in memory (lost on restart)

**Migration Strategy**: 
- No migration needed (in-memory data is ephemeral)
- Fresh start with persistent storage

**If you need to preserve data**:
1. Export in-memory conversations before deployment
2. Create script to import into Supabase
3. Associate with a default user or prompt users to claim conversations

---

### Backward Compatibility

**Option 1: Breaking Change (Recommended for MVP)**
- All endpoints require auth
- Update all clients to use JWT tokens

**Option 2: Versioned API**
- Keep `/api/v1` endpoints as-is (no auth)
- Create `/api/v2` with authentication
- Gradually migrate clients

---

## Rollback Plan

If integration fails:

1. **Keep old code in git branch**: `git checkout -b supabase-integration`
2. **Environment flag**: Add `USE_SUPABASE=false` to toggle between implementations
3. **Revert database**: Supabase projects can be paused/deleted
4. **Restore in-memory store**: Keep old `conversation_store.py` as backup

---

## Questions for User

1. **Authentication Method**: Email/password only, or also magic link/OAuth?
2. **API Versioning**: Breaking change or create `/v2` endpoints?
3. **WebSocket Auth**: Query parameter or first message with token?
4. **Conversation Titles**: Auto-generate from first message or user-provided?
5. **Data Migration**: Any existing data to preserve?

---

## Next Steps

1. **Complete Supabase setup** (follow setup guide)
2. **Review this plan** and provide feedback
3. **Approve to proceed** with implementation
4. **Decide on questions above**

Ready to implement once you've set up your Supabase account! 🚀
