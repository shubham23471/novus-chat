import redis.asyncio
import uuid
from uuid import UUID
from contextlib import asynccontextmanager


class RedisLock:
    def __init__(self, redis_client: redis.asyncio.Redis):
        self.redis = redis_client
        # Lua script remains the same, but execution becomes awaitable
        self._release_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
        """

    async def acquire(self, conversation_id: UUID, ttl: int = 30) -> str | None:
        lock_key = f"lock:conversation:{conversation_id}"
        token = str(uuid.uuid4())
        
        # We 'await' the network call to Redis
        success = await self.redis.set(lock_key, token, nx=True, ex=ttl)
        return token if success else None

    async def release(self, conversation_id: UUID, token: str):
        lock_key = f"lock:conversation:{conversation_id}"
        # Execute script asynchronously
        await self.redis.eval(self._release_script, 1, lock_key, token)

@asynccontextmanager
async def conversation_lock(redis_client: redis.asyncio.Redis, conv_id: UUID, ttl: int = 30):
    lock_manager = RedisLock(redis_client)
    token = await lock_manager.acquire(conv_id, ttl)
    
    if not token:
        # 409 Conflict is the standard HTTP code for this
        raise Exception("Resource locked: Another update is in progress.")
    
    try:
        yield token
    finally:
        await lock_manager.release(conv_id, token)