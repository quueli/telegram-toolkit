import asyncio
import random
from typing import Awaitable, Callable, Type, TypeVar

from loguru import logger
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

T = TypeVar("T")


async def jittered_delay(min_seconds: float, max_seconds: float, context: str = "") -> None:
    delay = random.uniform(min_seconds, max_seconds)
    if context:
        logger.debug(f"[backoff] delay {delay:.2f}s ({context})")
    await asyncio.sleep(delay)


async def retry_with_backoff(
    op: Callable[[], Awaitable[T]],
    *,
    retry_on: Type[BaseException] = Exception,
    tries: int = 3,
    initial: float = 5,
    max_wait: float = 20,
) -> T:
    # not for FloodWaitError, that one already tells you how long to wait
    result: T
    async for attempt in AsyncRetrying(
        retry=retry_if_exception_type(retry_on),
        stop=stop_after_attempt(tries),
        wait=wait_exponential_jitter(initial=initial, max=max_wait),
        reraise=True,
    ):
        with attempt:
            result = await op()
    return result
