from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

from jinja2 import Environment, FileSystemLoader
from loguru import logger

TEMPLATE_DIR = Path(__file__).parent / "templates"


def format_int(value):
    if value is None:
        return "-"
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "-"


def format_num(value):
    if value is None:
        return "-"
    try:
        n = float(value)
        return str(int(n)) if n % 1 == 0 else f"{n:.2f}"
    except (TypeError, ValueError):
        return "-"


def format_date(value):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(value)


def _environment() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    env.filters["format_int"] = format_int
    env.filters["format_num"] = format_num
    env.filters["format_date"] = format_date
    return env


def build_html_report(items: Iterable[Mapping[str, object]], meta: Mapping[str, object], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"report_{ts}.html"

    template = _environment().get_template("report.html")
    html = template.render(items=list(items), meta=meta)
    out_path.write_text(html, encoding="utf-8")
    logger.info(f"[html_report] wrote {out_path}")
    return out_path
