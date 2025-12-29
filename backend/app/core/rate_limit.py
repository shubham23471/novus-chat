import time
from collections import defaultdict

RATE_LIMIT = 20  # requests
WINDOW = 60      # seconds

requests = defaultdict(list)

def allow_request(ip: str) -> bool:
    now = time.time()
    requests[ip] = [t for t in requests[ip] if now - t < WINDOW]

    if len(requests[ip]) >= RATE_LIMIT:
        return False

    requests[ip].append(now)
    return True
