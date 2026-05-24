import hashlib
import inspect
import json
import logging
from functools import wraps
from typing import Any, Callable

from db.redis import async_redis, sync_redis

logger = logging.getLogger(__name__)


def cached(
    ttl: int = 3600,
    namespace: str | None = None,
    skip_cache_if: Callable[[Any], bool] | None = lambda result: (
        bool(result.get("error")) if isinstance(result, dict) else False
    ),
):
    """
    Usage:

    @cached()
    async def get_user(user_id: int):
        ...

    @cached(ttl=60)
    def expensive():
        ...
    """

    def decorator(func):
        prefix = namespace or func.__qualname__

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = build_cache_key(prefix, args, kwargs)

                cached_value = await get_cached(key)

                if cached_value is not None:
                    logger.info("cache_hit key=%s", key)
                    return cached_value

                logger.info("cache_miss key=%s", key)

                result = await func(*args, **kwargs)

                if skip_cache_if and skip_cache_if(result):
                    return result

                await set_cache(key=key, value=result, ttl=ttl)

                return result

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = build_cache_key(prefix, args, kwargs)

            try:
                cached_value: Any = sync_redis.get(key)
            except Exception as e:
                logger.warning("cache_get_error key=%s error=%s", key, str(e))
                cached_value = None

            if cached_value is not None:
                logger.info("cache_hit key=%s", key)

                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    logger.warning("cache_decode_error key=%s", key)

            logger.info("cache_miss key=%s", key)

            result = func(*args, **kwargs)

            if skip_cache_if and skip_cache_if(result):
                return result

            try:
                serialized = json.dumps(result, default=str)

                sync_redis.set(key, serialized, ex=ttl)

            except Exception as e:
                logger.warning("cache_set_error key=%s error=%s", key, str(e))

            return result

        return sync_wrapper

    return decorator


async def get_cached(key: str) -> Any | None:
    try:
        value = await async_redis.get(key)
    except Exception as e:
        logger.warning("cache_get_error key=%s error=%s", key, str(e))
        return None

    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        logger.warning("cache_decode_error key=%s", key)
        return None


async def set_cache(
    key: str,
    value: Any,
    ttl: int,
) -> None:
    try:
        serialized = json.dumps(
            value,
            default=str,
        )
    except TypeError as e:
        logger.warning(
            "cache_encode_error key=%s error=%s",
            key,
            str(e),
        )
        return

    try:
        await async_redis.set(
            key,
            serialized,
            ex=ttl,
        )
    except Exception as e:
        logger.warning(
            "cache_set_error key=%s error=%s",
            key,
            str(e),
        )


def make_hash(data: Any) -> str:
    serialized = json.dumps(
        data,
        sort_keys=True,
        default=str,
    )

    return hashlib.sha256(serialized.encode()).hexdigest()


def build_cache_key(
    prefix: str,
    args: tuple,
    kwargs: dict,
) -> str:
    payload = {
        "args": args,
        "kwargs": kwargs,
    }

    hashed = make_hash(payload)

    return f"cache:{prefix}:{hashed}"
