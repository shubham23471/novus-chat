import redis.asyncio
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)  

class RedisClient:
    _client = None

    @classmethod
    def get_client(cls) -> redis.asyncio.Redis:
        if cls._client is None:
            cls._client = redis.asyncio.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                decode_responses=True  # to get string responses instead of bytes
            )
        return cls._client
    
if __name__ == "__main__":
    redis_client = RedisClient.get_client()
    print(type(redis_client))

    async def main():
        # Test the connection
        try:
            ping_status = await redis_client.ping()
            print("Connected to Redis successfully!")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
    
    asyncio.run(main())

