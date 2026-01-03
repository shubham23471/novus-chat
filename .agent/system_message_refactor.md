# System Message Refactoring - ChatGPT Pattern

## Problem
Previously, the system message was being **stored in the database** for every conversation. This approach had several issues:
- Wasted database space (same message repeated for every conversation)
- System messages are configuration, not user data
- Cluttered message history with non-user content

## Solution - How ChatGPT Does It

ChatGPT and similar applications follow this pattern:

### 1. **Store ONLY user and assistant messages** in the database
   - System messages are NOT persisted
   - Only actual conversation content is stored

### 2. **Inject system message at runtime** when making LLM calls
   - System message is added programmatically when loading messages
   - It's treated as application configuration, not data

### 3. **Keep system message in first position** for LLM context
   - When sending to LLM: `[system, user1, assistant1, user2, assistant2, ...]`
   - In database: only `[user1, assistant1, user2, assistant2, ...]`

## Changes Made

### 1. `chat_routes.py`
**Removed:**
- System message insertion when creating new conversations (lines 80-85, 151-156)

**Updated:**
- `load_conversation_messages()` calls now pass `system_message` parameter
- System message is injected at runtime for LLM calls

### 2. `database.py`
**Updated `load_conversation_messages()` function:**
- Added optional `system_message` parameter
- Injects system message at the beginning of message list if provided
- Only loads user/assistant messages from database

### 3. `trim_conversation()` function
**No changes needed:**
- Already correctly preserves system message at index 0
- Trims only user/assistant messages
- Works perfectly with the new approach

## Benefits

1. **Database Efficiency**: No redundant system messages stored
2. **Flexibility**: Easy to change system message without database migration
3. **Scalability**: Less data to store and transfer
4. **Best Practice**: Follows industry standard (ChatGPT pattern)
5. **Separation of Concerns**: Configuration vs. user data

## How It Works Now

```python
# When creating a new conversation:
conversation_id = create_conversation(user_id, title)
# No system message stored! ✅

# When making LLM call:
messages = load_conversation_messages(
    conversation_id,
    system_message="You are a helpful assistant."  # Injected at runtime
)
# Returns: [system_msg, user1, assistant1, user2, ...]

# In database:
# Only: [user1, assistant1, user2, ...]
```

## Migration Note

If you have existing conversations with system messages in the database, you may want to clean them up:

```sql
-- Remove all system messages from existing conversations
DELETE FROM messages WHERE role = 'system';
```

This is safe because system messages will now be injected at runtime.
