import json
import os
from pathlib import Path
from typing import Any

from loguru import logger

# other session export tools spell these differently
_KEY_ALIASES = {
    "device_model": ("device_model", "device"),
    "system_version": ("system_version", "sdk"),
    "app_version": ("app_version",),
    "lang_code": ("lang_code", "lang_pack"),
    "system_lang_code": ("system_lang_code", "system_lang_pack"),
}


def global_fingerprint_kwargs() -> dict[str, Any]:
    mapping = {
        "device_model": os.getenv("TG_DEVICE"),
        "system_version": os.getenv("TG_SDK"),
        "app_version": os.getenv("TG_APP_VERSION"),
        "lang_code": os.getenv("TG_LANG_CODE"),
        "system_lang_code": os.getenv("TG_SYSTEM_LANG_CODE"),
    }
    return {k: v for k, v in mapping.items() if v}


def load_device_params_for_session(session_path: Path) -> dict[str, Any]:
    json_path = session_path.with_suffix(".json")
    if not json_path.exists():
        logger.warning(f"[device_fingerprint] no {json_path.name}, using the global fingerprint")
        return global_fingerprint_kwargs()

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[device_fingerprint] failed to read {json_path.name}: {e!r}, using the global fingerprint")
        return global_fingerprint_kwargs()

    params: dict[str, Any] = {}
    for field, aliases in _KEY_ALIASES.items():
        for key in aliases:
            if data.get(key):
                params[field] = data[key]
                break

    if not params:
        logger.warning(f"[device_fingerprint] {json_path.name} has no usable fields, using the global fingerprint")
        return global_fingerprint_kwargs()

    logger.info(f"[device_fingerprint] loaded fingerprint for {session_path.stem} from {json_path.name}")
    return params
