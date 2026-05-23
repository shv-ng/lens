import json

from db.redis import r


async def get_cached(key: str) -> dict | None:
    value = await r.get(key)
    if value:
        return json.loads(value)
    return None


async def set_cache(key: str, value, ttl: int = 3600 * 24):
    await r.set(key, json.dumps(value), ex=ttl)
