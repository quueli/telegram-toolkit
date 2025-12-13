from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

from loguru import logger

MAX_PART_SIZE = 50 * 1024 * 1024  # tg caps bot uploads at 50mb
SAFETY_MARGIN = 1_000_000


def format_line(item: Mapping[str, object]) -> str:
    username = f"@{item['username']}" if item.get("username") else "-"
    return (
        f"{username} | {item.get('title', '')} | {item.get('subscribers', '-')} | "
        f"{item.get('er', '-')}% | {item.get('link', '')}\n"
    )


def build_txt_report(items: Iterable[Mapping[str, object]], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"report_{ts}.txt"
    with out_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(format_line(it))
    logger.info(f"[txt_report] wrote {out_path}")
    return out_path


def split_if_too_large(path: Path, max_size: int = MAX_PART_SIZE) -> list[Path]:
    if path.stat().st_size <= max_size:
        return [path]

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    max_bytes = max_size - SAFETY_MARGIN

    chunks: list[str] = []
    buf: list[str] = []
    buf_bytes = 0
    for line in lines:
        encoded = line.encode("utf-8")
        if buf and buf_bytes + len(encoded) > max_bytes:
            chunks.append("".join(buf))
            buf = [line]
            buf_bytes = len(encoded)
        else:
            buf.append(line)
            buf_bytes += len(encoded)
    if buf:
        chunks.append("".join(buf))

    parts = []
    for idx, chunk_text in enumerate(chunks, start=1):
        part_path = path.with_name(f"{path.stem}.part{idx}{path.suffix}")
        part_path.write_text(chunk_text, encoding="utf-8")
        parts.append(part_path)

    path.unlink(missing_ok=True)
    logger.info(f"[txt_report] {path.name} was too large, split into {len(parts)} part(s)")
    return parts
