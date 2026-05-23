import os

import redis.asyncio as redis

redis_url = os.environ.get("REDIS_URL") or "redis://localhost:6379"

r = redis.Redis.from_url(redis_url)
