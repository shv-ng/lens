from db.redis import r


async def get_cached(key: str):
    return r.get(key)


async def set_cache(key: str, value):
    r.set(key, value, ex=3600)
