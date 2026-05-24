import inspect
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def logit(func):
    # async generator
    if inspect.isasyncgenfunction(func):

        @wraps(func)
        async def asyncgen_wrapper(*args, **kwargs):
            start = time.perf_counter()

            logger.info("fn_start fn=%s", func.__name__)

            try:
                async for item in func(*args, **kwargs):
                    yield item

                duration = round((time.perf_counter() - start) * 1000, 2)

                logger.info(
                    "fn_success fn=%s duration_ms=%s",
                    func.__name__,
                    duration,
                )

            except Exception:
                duration = round((time.perf_counter() - start) * 1000, 2)

                logger.exception(
                    "fn_failed fn=%s duration_ms=%s",
                    func.__name__,
                    duration,
                )

                raise

        return asyncgen_wrapper

    # async coroutine
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()

            logger.info("fn_start fn=%s", func.__name__)

            try:
                result = await func(*args, **kwargs)

                duration = round((time.perf_counter() - start) * 1000, 2)

                logger.info(
                    "fn_success fn=%s duration_ms=%s",
                    func.__name__,
                    duration,
                )

                return result

            except Exception:
                duration = round((time.perf_counter() - start) * 1000, 2)

                logger.exception(
                    "fn_failed fn=%s duration_ms=%s",
                    func.__name__,
                    duration,
                )

                raise

        return async_wrapper

    # sync fn
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.perf_counter()

        logger.info("fn_start fn=%s", func.__name__)

        try:
            result = func(*args, **kwargs)

            duration = round((time.perf_counter() - start) * 1000, 2)

            logger.info(
                "fn_success fn=%s duration_ms=%s",
                func.__name__,
                duration,
            )

            return result

        except Exception:
            duration = round((time.perf_counter() - start) * 1000, 2)

            logger.exception(
                "fn_failed fn=%s duration_ms=%s",
                func.__name__,
                duration,
            )

            raise

    return sync_wrapper
