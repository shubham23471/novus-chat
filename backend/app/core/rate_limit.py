import time
from collections import defaultdict

RATE_LIMIT = 20  # requests
WINDOW = 60      # seconds

requests = defaultdict(list)

def allow_request(user_id: str) -> bool:
    """
    Check if user is within rate limit.
    
    Changed from IP-based to user-based rate limiting for authenticated requests.
    
    Args:
        user_id: User ID (UUID as string) or IP address for unauthenticated requests
        
    Returns:
        bool: True if request is allowed, False if rate limit exceeded
    """
    now = time.time()
    requests[user_id] = [t for t in requests[user_id] if now - t < WINDOW]

    if len(requests[user_id]) >= RATE_LIMIT:
        return False

    requests[user_id].append(now)
    return True
