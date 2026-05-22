import redis
import dotenv
import os

dotenv.load_dotenv()

redis_url = os.environ.get("REDIS_URL") or "redis://localhost:6379"

r = redis.Redis.from_url(redis_url)


async def get(key: str):
    return r.get(key)


async def set(key: str, value: str):
    r.set(key, value,ex=3600)
