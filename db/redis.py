import os

import redis.asyncio as redis
from redis import Redis

redis_url = os.environ.get("REDIS_URL") or "redis://localhost:6379"

async_redis = redis.Redis.from_url(redis_url)
sync_redis = Redis.from_url(redis_url, decode_responses=True)
