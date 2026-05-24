import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def retry(
    retries: int = 3,
    delay: float = 1,
    exceptions: tuple = (Exception,),
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_error = e

                    logger.warning(
                        "retry_attempt_failed",
                        extra={
                            "fn": func.__name__,
                            "attempt": attempt,
                            "retries": retries,
                            "error": str(e),
                        },
                    )

                    if attempt < retries:
                        await asyncio.sleep(delay)

            logger.error(
                "retry_exhausted",
                extra={
                    "fn": func.__name__,
                    "retries": retries,
                    "error": str(last_error),
                },
            )
            if last_error is not None:
                raise last_error

        return wrapper

    return decorator
