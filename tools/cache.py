from db.redis import r
import json


async def get_cached(key: str) -> dict | None:
    value = await r.get(key)
    if value:
        return json.loads(value)
    return None


async def set_cache(key: str, value, ttl: int = 3600):
    r.set(key, json.dumps(value), ex=ttl)
