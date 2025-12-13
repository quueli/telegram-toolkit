import asyncio
from typing import Any


class FakeFloodWaitError(Exception):
    def __init__(self, seconds: int):
        self.seconds = seconds
        super().__init__(f"a wait of {seconds} seconds is required")


class FakeTelegramClient:
    def __init__(self, session: str, api_id: int, api_hash: str, proxy: tuple | None = None, **device_params: Any):
        self.session = session
        self.api_id = api_id
        self.api_hash = api_hash
        self.proxy = proxy
        self.device_params = device_params
        self.connected = False

    async def connect(self):
        await asyncio.sleep(0)  # a real client opens a socket here
        self.connected = True

    async def is_user_authorized(self) -> bool:
        return True

    async def disconnect(self):
        await asyncio.sleep(0)
        self.connected = False

    def __repr__(self) -> str:
        return f"FakeTelegramClient({self.session!r})"
