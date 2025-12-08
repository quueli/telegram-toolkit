import asyncio
import time

import pytest

from rate_limit.backoff import jittered_delay, retry_with_backoff


def test_delay_stays_in_range():
    start = time.perf_counter()
    asyncio.run(jittered_delay(0.05, 0.1))
    assert 0.04 <= time.perf_counter() - start <= 0.5


def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("reset")
        return "ok"

    out = asyncio.run(retry_with_backoff(flaky, retry_on=ConnectionError, tries=3, initial=0.01, max_wait=0.02))
    assert out == "ok"
    assert calls["n"] == 3


def test_retry_gives_up_and_reraises():
    async def always_fails():
        raise TimeoutError("nope")

    with pytest.raises(TimeoutError):
        asyncio.run(retry_with_backoff(always_fails, retry_on=TimeoutError, tries=2, initial=0.01, max_wait=0.02))


def test_retry_ignores_other_errors():
    async def wrong_error():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        asyncio.run(retry_with_backoff(wrong_error, retry_on=ConnectionError, tries=3, initial=0.01))
