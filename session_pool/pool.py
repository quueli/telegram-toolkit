import asyncio
import os
import random
import time
from pathlib import Path

from loguru import logger
from telethon import TelegramClient

from session_pool.device_fingerprint import load_device_params_for_session
from session_pool.proxy import ProxyTuple, load_effective_proxies

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_DIR = os.getenv("SESSION_DIR", "./sessions")


class SessionPool:
    MAX_QUEUE_WAIT_SECONDS = 600

    # rest an account long before it gets anywhere near a real floodwait
    PROACTIVE_REST_MIN_SECONDS = 15 * 60
    PROACTIVE_REST_MAX_SECONDS = 25 * 60

    def __init__(self, sessions_dir: Path):
        self._dir = sessions_dir
        self._lock = asyncio.Lock()
        self._all_sessions: list[Path] = []
        self._in_use: set[str] = set()
        self._proxies: list[ProxyTuple] = []
        self._proxy_index = 0
        self._waiters: list[asyncio.Event] = []
        self._blocked: dict[str, float] = {}
        self._resting: dict[str, float] = {}

    def _ensure_proxies_loaded(self):
        if self._proxies:
            return
        self._proxies = load_effective_proxies()
        if self._proxies:
            logger.info(f"[session_pool] loaded {len(self._proxies)} proxy(ies) for rotation")
        else:
            logger.warning("[session_pool] no proxies configured, connecting directly")

    def _get_next_proxy(self):
        self._ensure_proxies_loaded()
        if not self._proxies:
            return None
        proxy = self._proxies[self._proxy_index % len(self._proxies)]
        self._proxy_index += 1
        return proxy

    def _ensure_sessions_loaded(self):
        if self._all_sessions:
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        self._all_sessions = sorted(self._dir.glob("*.session"))
        logger.info(f"[session_pool] discovered {len(self._all_sessions)} session file(s) in {self._dir}")

    def _is_session_blocked(self, session_path: str) -> bool:
        until = self._blocked.get(session_path)
        if until is None:
            return False
        if time.time() >= until:
            del self._blocked[session_path]
            return False
        return True

    def _is_session_resting(self, session_path: str) -> bool:
        until = self._resting.get(session_path)
        if until is None:
            return False
        if time.time() >= until:
            del self._resting[session_path]
            return False
        return True

    def _is_free(self, key: str) -> bool:
        return key not in self._in_use and not self._is_session_blocked(key) and not self._is_session_resting(key)

    def _find_available_session(self):
        # call with the lock held
        for p in self._all_sessions:
            if self._is_free(str(p)):
                return p
        return None

    def get_earliest_available_time(self):
        now = time.time()
        earliest = None
        for until in list(self._blocked.values()) + list(self._resting.values()):
            if until > now and (earliest is None or until < earliest):
                earliest = until
        return earliest

    def get_wait_time_estimate(self) -> int:
        for p in self._all_sessions:
            if self._is_free(str(p)):
                return 0
        earliest = self.get_earliest_available_time()
        if earliest is None:
            return 0
        return max(0, int(earliest - time.time()))

    async def mark_blocked(self, client: TelegramClient, seconds: int) -> None:
        session_path = getattr(client, "_session_path", None)
        if not session_path:
            logger.warning("[session_pool] cannot mark blocked: client has no _session_path")
            return
        until = time.time() + seconds
        async with self._lock:
            self._blocked[session_path] = until
        logger.warning(
            f"[session_pool] {Path(session_path).name} blocked for {seconds}s "
            f"(unblocks at {time.strftime('%H:%M:%S', time.localtime(until))})"
        )

    async def mark_resting(self, client: TelegramClient, seconds: int | None = None) -> None:
        session_path = getattr(client, "_session_path", None)
        if not session_path:
            logger.warning("[session_pool] cannot mark resting: client has no _session_path")
            return
        if seconds is None:
            seconds = random.randint(self.PROACTIVE_REST_MIN_SECONDS, self.PROACTIVE_REST_MAX_SECONDS)
        async with self._lock:
            self._resting[session_path] = time.time() + seconds
        logger.info(f"[session_pool] {Path(session_path).name} resting for {seconds // 60}min (proactive rotation)")

    async def _connect(self, session_path: Path) -> TelegramClient:
        proxy = self._get_next_proxy()
        proxy_info = f"{proxy[1]}:{proxy[2]}" if proxy else "direct"

        client = TelegramClient(
            session=str(session_path),
            api_id=API_ID,
            api_hash=API_HASH,
            proxy=proxy,
            **load_device_params_for_session(session_path),
        )
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise RuntimeError(f"session {session_path.name} is not authorized")

        client._session_path = str(session_path)
        client._proxy_info = proxy_info
        logger.info(
            f"[session_pool] acquired {session_path.name} "
            f"(in_use={len(self._in_use)}/{len(self._all_sessions)}, proxy={proxy_info})"
        )
        return client

    async def acquire(self, user_id: int) -> TelegramClient:
        self._ensure_sessions_loaded()
        if not self._all_sessions:
            raise RuntimeError("no sessions available in the pool")

        async with self._lock:
            session_path = self._find_available_session()
            if session_path is None:
                blocked = len([k for k in self._blocked if k not in self._in_use])
                raise RuntimeError(f"no free session (in_use={len(self._in_use)}, blocked={blocked})")
            self._in_use.add(str(session_path))

        try:
            return await self._connect(session_path)
        except Exception:
            async with self._lock:
                self._in_use.discard(str(session_path))
            raise

    async def release(self, user_id: int, client: TelegramClient, *, _disconnect: bool = True) -> None:
        session_path = getattr(client, "_session_path", None)
        waiter_to_notify = None

        async with self._lock:
            if session_path:
                self._in_use.discard(str(session_path))
                logger.debug(
                    f"[session_pool] released {Path(session_path).name} "
                    f"(in_use={len(self._in_use)}/{len(self._all_sessions)})"
                )
            if self._waiters:
                waiter_to_notify = self._waiters.pop(0)

        if _disconnect:
            try:
                await client.disconnect()
            except Exception:
                logger.debug("[session_pool] error while disconnecting client", exc_info=True)

        if waiter_to_notify:
            waiter_to_notify.set()

    async def acquire_or_wait(self, user_id: int) -> TelegramClient:
        self._ensure_sessions_loaded()
        if not self._all_sessions:
            raise RuntimeError("no sessions available in the pool")

        async with self._lock:
            session_path = self._find_available_session()
            waiter = None
            if session_path is not None:
                self._in_use.add(str(session_path))
            else:
                waiter = asyncio.Event()
                self._waiters.append(waiter)
                logger.info(f"[session_pool] user_id={user_id} queued (position={len(self._waiters)})")

        if session_path is None:
            try:
                await asyncio.wait_for(waiter.wait(), timeout=self.MAX_QUEUE_WAIT_SECONDS)
            except asyncio.TimeoutError:
                async with self._lock:
                    if waiter in self._waiters:
                        self._waiters.remove(waiter)
                raise RuntimeError(f"timed out after {self.MAX_QUEUE_WAIT_SECONDS}s waiting for a session")

            async with self._lock:
                session_path = self._find_available_session()
                if session_path is None:
                    # someone else grabbed it between the notify and us waking up
                    raise RuntimeError("no session became available after waiting")
                self._in_use.add(str(session_path))

        try:
            return await self._connect(session_path)
        except Exception:
            async with self._lock:
                self._in_use.discard(str(session_path))
            raise

    def sessions_total(self) -> int:
        self._ensure_sessions_loaded()
        return len(self._all_sessions)

    def sessions_available(self) -> int:
        self._ensure_sessions_loaded()
        return len(self._all_sessions) - len(self._in_use)

    def queue_length(self) -> int:
        return len(self._waiters)


_pool = None


def get_session_pool() -> SessionPool:
    global _pool
    if _pool is None:
        _pool = SessionPool(Path(SESSION_DIR))
    return _pool


async def acquire_session(user_id: int) -> TelegramClient:
    return await get_session_pool().acquire(user_id)


async def acquire_session_or_wait(user_id: int) -> TelegramClient:
    return await get_session_pool().acquire_or_wait(user_id)


async def release_session(user_id: int, client: TelegramClient) -> None:
    await get_session_pool().release(user_id, client)


async def mark_session_blocked(client: TelegramClient, seconds: int) -> None:
    await get_session_pool().mark_blocked(client, seconds)


async def mark_session_resting(client: TelegramClient, seconds: int | None = None) -> None:
    await get_session_pool().mark_resting(client, seconds)


def get_wait_time_estimate() -> int:
    return get_session_pool().get_wait_time_estimate()
