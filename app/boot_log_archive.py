from __future__ import annotations

import asyncio
import json
import hashlib
from datetime import datetime
from pathlib import Path

import httpx

from .handlers import ESP_HOST, ESP_PASS, ESP_TIMEOUT, ESP_USER

BASE_DIR = Path(__file__).resolve().parent
ARCHIVE_DIR = BASE_DIR / "esp32_boot_logs"
INDEX_FILE = ARCHIVE_DIR / "index.jsonl"
_last_archived_sha1: str | None = None


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _load_last_sha1() -> str | None:
    try:
        if not INDEX_FILE.exists():
            return None
        lines = INDEX_FILE.read_text(encoding="utf-8").splitlines()
        if not lines:
            return None
        record = json.loads(lines[-1])
        if isinstance(record, dict):
            value = record.get("sha1")
            if isinstance(value, str) and value:
                return value
    except Exception:
        return None
    return None


def _archive_content(content: str, filename: str = "last_log.txt") -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sha1 = _sha1(content)
    out_path = ARCHIVE_DIR / f"{stamp}.txt"
    out_path.write_text(content, encoding="utf-8")

    record = {
        "timestamp": stamp,
        "filename": filename,
        "archive": out_path.name,
        "content_lines": len(content.splitlines()),
        "sha1": sha1,
    }
    with INDEX_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return out_path


async def capture_boot_log(filename: str = "last_log.txt") -> Path | None:
    url = f"{ESP_HOST}/cat"
    params = {"filename": filename}
    auth = httpx.BasicAuth(ESP_USER, ESP_PASS)
    async with httpx.AsyncClient(timeout=ESP_TIMEOUT) as client:
        try:
            response = await client.get(url, params=params, auth=auth)
        except httpx.RequestError:
            return None

    if response.status_code != 200:
        return None

    try:
        payload = response.json()
    except Exception:
        return None

    content = payload.get("content") if isinstance(payload, dict) else None
    if not content:
        return None

    global _last_archived_sha1
    sha1 = _sha1(content)
    if _last_archived_sha1 is None:
        _last_archived_sha1 = _load_last_sha1()

    if sha1 == _last_archived_sha1:
        return None

    out_path = _archive_content(content, filename=filename)
    _last_archived_sha1 = sha1
    return out_path


async def watch_boot_logs(poll_s: int = 15):
    global _last_archived_sha1
    if _last_archived_sha1 is None:
        _last_archived_sha1 = _load_last_sha1()

    while True:
        try:
            await capture_boot_log()
        except Exception:
            pass
        await asyncio.sleep(poll_s)
