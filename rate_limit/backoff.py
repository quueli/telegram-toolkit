import asyncio
import random

from loguru import logger


async def jittered_delay(min_seconds: float, max_seconds: float, context: str = "") -> None:
    delay = random.uniform(min_seconds, max_seconds)
    if context:
        logger.debug(f"[backoff] delay {delay:.2f}s ({context})")
    await asyncio.sleep(delay)
