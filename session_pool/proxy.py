import os
from pathlib import Path
from random import choice
from typing import Any
from urllib.parse import urlparse

from loguru import logger

try:
    import socks  # PySocks
except Exception:
    socks = None

# (type, host, port, rdns, user, pass) - the shape telethon hands to PySocks
ProxyTuple = tuple[Any, str, int, bool, str | None, str | None]

SESSION_DIR = Path(os.getenv("SESSION_DIR", "./sessions"))


def _proxies_file() -> Path:
    return SESSION_DIR / "proxies.txt"


def _valid_port(port: int) -> bool:
    return 1 <= port <= 65535


def _parse_url(s: str):
    try:
        parsed = urlparse(s)
    except Exception:
        logger.error(f"could not parse proxy url: {s}")
        return None
    scheme = (parsed.scheme or "").lower()
    host = parsed.hostname or ""
    try:
        port = int(parsed.port) if parsed.port is not None else -1
    except Exception:
        logger.error(f"invalid port in proxy url: {s}")
        return None
    if not host or not _valid_port(port):
        logger.error(f"invalid host/port in proxy url: {s}")
        return None

    if scheme in {"socks5", "socks", "socks5h"}:
        proxy_type = socks.SOCKS5
    elif scheme in {"socks4", "socks4a"}:
        proxy_type = getattr(socks, "SOCKS4", socks.SOCKS5)
    elif scheme in {"http", "https"}:
        proxy_type = socks.HTTP
    else:
        logger.error(f"unsupported proxy scheme: {scheme}")
        return None

    return (proxy_type, host, port, True, parsed.username or None, parsed.password or None)


def _parse_proxy(line: str):
    if not socks:
        logger.error("PySocks is not installed, cannot use a proxy")
        return None

    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if "://" in s:
        return _parse_url(s)

    parts = s.split(":")
    if len(parts) not in (2, 4):
        logger.error(f"unrecognized proxy line (expected host:port, host:port:login:pass or a url): {s}")
        return None

    host = parts[0]
    try:
        port = int(parts[1])
    except ValueError:
        logger.error(f"invalid port in proxy line: {s}")
        return None
    if not _valid_port(port):
        logger.error(f"port out of range 1-65535: {s}")
        return None

    username = parts[2] if len(parts) == 4 and parts[2] else None
    password = parts[3] if len(parts) == 4 and parts[3] else None
    return (socks.SOCKS5, host, port, True, username, password)


def load_proxies_from_file() -> list[ProxyTuple]:
    path = _proxies_file()
    results: list[ProxyTuple] = []
    if not path.exists():
        return results
    for raw in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_proxy(raw)
        if parsed:
            results.append(parsed)
        elif raw.strip() and not raw.strip().startswith("#"):
            logger.warning(f"skipping invalid proxy line: {raw.strip()}")
    return results


def load_effective_proxies() -> list[ProxyTuple]:
    path = _proxies_file()
    if path.exists():
        return load_proxies_from_file()

    env_proxy = os.getenv("PROXY", "").strip()
    if not env_proxy:
        return []

    parsed = _parse_proxy(env_proxy)
    if not parsed:
        logger.warning("PROXY env var is set but could not be parsed, ignoring it")
        return []

    # persist it so the next run reads it from the file like any other entry
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(env_proxy + "\n", encoding="utf-8")
    except Exception as e:
        logger.warning(f"could not persist PROXY into {path}: {e!r}")

    return [parsed]


def pick_proxy_for_telethon():
    proxies = load_effective_proxies()
    return choice(proxies) if proxies else None
