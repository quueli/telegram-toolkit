import asyncio
import sys
import tempfile
import types
from pathlib import Path

from examples.fake_telethon import FakeFloodWaitError, FakeTelegramClient


def _install_fake_telethon():
    # the pool imports telethon at module level, so swap it out before that happens
    telethon = types.ModuleType("telethon")
    telethon.TelegramClient = FakeTelegramClient
    errors = types.ModuleType("telethon.errors")
    errors.FloodWaitError = FakeFloodWaitError
    telethon.errors = errors
    sys.modules.setdefault("telethon", telethon)
    sys.modules.setdefault("telethon.errors", errors)


async def pool_demo(session_dir: Path):
    from session_pool.pool import SessionPool

    for name in ("acc_1", "acc_2"):
        (session_dir / f"{name}.session").touch()

    pool = SessionPool(session_dir)
    print(f"pool sees {pool.sessions_total()} sessions")

    a = await pool.acquire(user_id=1)
    b = await pool.acquire(user_id=2)
    print(f"acquired two, {pool.sessions_available()} left")

    await pool.mark_resting(b, seconds=900)
    await pool.release(user_id=2, client=b)
    print(f"one is resting, wait estimate ~{pool.get_wait_time_estimate()}s")

    await pool.release(user_id=1, client=a)


def matcher_demo():
    from keyword_matcher.matcher import KeywordMatcher

    m = KeywordMatcher(["python", "веб дизайн", "marketing"])
    messages = [
        "ищу python разработчика",
        "нужен веб дизайн для лендинга",
        "просто про погоду",
        "markting budget please",
    ]
    for msg in messages:
        print(f"  {msg!r:40} -> {m.find_matches(msg)}")


def main():
    _install_fake_telethon()
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(pool_demo(Path(d)))
    print("keyword matches:")
    matcher_demo()


if __name__ == "__main__":
    main()
