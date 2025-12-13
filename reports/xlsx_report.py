from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

from loguru import logger

try:
    from openpyxl import Workbook
except Exception as e:
    Workbook = None
    logger.warning(f"openpyxl is not installed, XLSX export is disabled: {e!r}")


def _coerce_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _coerce_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def build_xlsx_report(
    items: Iterable[Mapping[str, object]],
    meta: Mapping[str, object],
    out_dir: Path,
) -> Path | None:
    if Workbook is None:
        logger.warning("build_xlsx_report called but openpyxl is unavailable")
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"report_{ts}.xlsx"

    wb = Workbook()
    ws_data = wb.active
    ws_data.title = "Data"

    headers = [
        "type", "title", "username", "link", "id", "is_public",
        "subscribers", "avg_views", "post_freq_per_day", "er_percent",
        "locale", "description",
    ]
    ws_data.append(headers)

    for it in items:
        ws_data.append([
            it.get("type"),
            it.get("title"),
            it.get("username"),
            it.get("link"),
            it.get("id"),
            bool(it.get("is_public")),
            _coerce_int(it.get("subscribers")),
            _coerce_float(it.get("avg_views")),
            _coerce_float(it.get("post_freq")),
            _coerce_float(it.get("er")),
            (it.get("locale") or "").upper() if it.get("locale") else "",
            it.get("description"),
        ])

    ws_meta = wb.create_sheet(title="Meta")
    ws_meta.append(["key", "value"])
    for key, value in (meta or {}).items():
        if isinstance(value, (list, tuple, set)):
            value_str = ", ".join(str(v) for v in value)
        else:
            value_str = str(value)
        ws_meta.append([str(key), value_str])

    wb.save(out_path)
    logger.info(f"[xlsx_report] wrote {out_path}")
    return out_path
