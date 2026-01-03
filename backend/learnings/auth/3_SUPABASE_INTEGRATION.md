# Supabase Integration - Quick Start

## ✅ What's Been Implemented

The novus-chat application now has full Supabase integration with:

- **Authentication**: Email/password signup, login, logout, token refresh
- **Database**: PostgreSQL storage for conversations and messages
- **Row Level Security**: Users can only access their own data
- **User-based rate limiting**: 20 requests per 60 seconds per user
- **Protected routes**: All chat endpoints require JWT authentication

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up Supabase

Follow the complete guide in the artifacts:
- `supabase_setup_guide.md` - Step-by-step Supabase account and project setup

Key steps:
1. Create account at https://supabase.com
2. Create new project
3. Run the database schema from the setup guide
4. Copy your API credentials

### 3. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your Supabase credentials:

```bash
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here
```

### 4. Start Infrastructure

```bash
# Start Redis (required for distributed locks)
docker compose up -d redis
```

### 5. Run the Application

```bash
uvicorn backend.app.main:app --reload
```

The API will be available at http://localhost:8000

## 📚 API Documentation

Once running, visit:
- **Interactive docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

## 🔐 Authentication Flow

### 1. Sign Up

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "full_name": "John Doe"
  },
  "expires_in": 3600
}
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### 3. Use Chat (with authentication)

```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "message": "Hello, how are you?"
  }'
```

## 🧪 Testing

Run the test suite:

```bash
# All tests
pytest

# Authentication tests only
pytest backend/tests/test_auth.py -v

# With output
pytest -v -s
```

## 📁 New File Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── auth.py              # NEW: Authentication middleware
│   │   ├── supabase_client.py   # NEW: Supabase client singleton
│   │   ├── database.py          # NEW: Database operations
│   │   └── rate_limit.py        # UPDATED: User-based rate limiting
│   ├── api/v1/routes/
│   │   ├── auth_routes.py       # NEW: Authentication endpoints
│   │   ├── conversation_routes.py # NEW: Conversation management
│   │   ├── chat_routes.py       # UPDATED: Now requires auth
│   │   └── ws_chat.py           # TODO: Update with auth
│   └── main.py                  # UPDATED: New routers registered
├── tests/
│   └── test_auth.py             # NEW: Authentication tests
├── .env.example                 # NEW: Environment template
└── requirements.txt             # UPDATED: Added supabase
```

## 🔑 API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Create new user
- `POST /api/v1/auth/login` - Login and get tokens
- `POST /api/v1/auth/logout` - Logout current user
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info

### Chat (all require authentication)
- `POST /api/v1/chat/message` - Send message, get response
- `POST /api/v1/chat/stream` - Send message, stream response

### Conversations (all require authentication)
- `GET /api/v1/conversations` - List user's conversations
- `GET /api/v1/conversations/{id}` - Get conversation with messages
- `DELETE /api/v1/conversations/{id}` - Delete conversation
- `PATCH /api/v1/conversations/{id}` - Update conversation title

### Health
- `GET /health` - Health check (no auth required)

## ⚠️ Breaking Changes

**All chat endpoints now require authentication!**

Old (no auth):
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -d '{"message": "Hello"}'
```

New (with auth):
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "Hello"}'
```

## 🔧 Troubleshooting

### "Invalid authentication credentials"
- Check that your token is valid and not expired (tokens expire after 1 hour)
- Use the `/auth/refresh` endpoint to get a new token

### "Database error"
- Verify Supabase credentials in `.env`
- Check that database schema has been run
- Verify RLS policies are enabled

### "Rate limit exceeded"
- Wait 60 seconds or increase `RATE_LIMIT` in `rate_limit.py`

### "Connection refused" to Redis
- Make sure Redis is running: `docker compose up -d redis`
- Check Redis credentials in `.env`

## 📖 Additional Documentation

See the artifacts folder for:
- `codebase_documentation.md` - Complete codebase overview
- `supabase_setup_guide.md` - Detailed Supabase setup
- `implementation_plan.md` - Technical implementation details

## 🎯 Next Steps

1. **WebSocket Authentication**: Update `ws_chat.py` to require authentication
2. **Frontend Integration**: Build a frontend that uses the authentication flow
3. **Conversation Titles**: Auto-generate titles from first message
4. **User Profiles**: Add profile picture and bio fields
5. **Conversation Sharing**: Allow users to share conversations

## 💡 Tips

- Access tokens expire after 1 hour - implement auto-refresh in your client
- Use the `/docs` endpoint to test API interactively
- Check Supabase dashboard to view data and monitor usage
- RLS policies protect your data even if there's a bug in your code

## 🆘 Need Help?

1. Check the setup guide: `supabase_setup_guide.md`
2. Review the implementation plan: `implementation_plan.md`
3. Look at test examples: `backend/tests/test_auth.py`
4. Visit Supabase docs: https://supabase.com/docs
