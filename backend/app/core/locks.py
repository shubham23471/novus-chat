# lock store

import threading
from uuid import UUID
from collections import defaultdict


conversation_locks = defaultdict(threading.Lock)

def get_conversation_lock(conversation_id: UUID) -> threading.Lock:
    """Get the lock for a specific conversation"""
    return conversation_locks[conversation_id]