# lock store

import asyncio
from uuid import UUID
from collections import defaultdict


conversation_locks = defaultdict(asyncio.Lock)

def get_conversation_lock(conversation_id: UUID) -> asyncio.Lock:
    """Get the lock for a specific conversation"""
    return conversation_locks[conversation_id]