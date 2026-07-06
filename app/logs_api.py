from __future__ import annotations

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from .handlers import ESP_HOST, ESP_PASS, ESP_TIMEOUT, ESP_USER

router = APIRouter()


async def _tail_from_device(filename: str, n: int):
    url = f"{ESP_HOST}/tail?{urlencode({'filename': filename, 'n': str(n)})}"
    auth = httpx.BasicAuth(ESP_USER, ESP_PASS)
    async with httpx.AsyncClient(timeout=ESP_TIMEOUT) as client:
        try:
            r = await client.get(url, auth=auth)
        except httpx.TimeoutException:
            return JSONResponse(status_code=504, content={"error": "timeout", "lines": []})
        except httpx.RequestError as e:
            return JSONResponse(status_code=502, content={"error": str(e), "lines": []})

    if "application/json" in r.headers.get("content-type", ""):
        try:
            payload = r.json()
            if isinstance(payload, dict) and "lines" in payload:
                return JSONResponse(status_code=r.status_code, content=payload)
        except Exception:
            pass

    text = r.text.strip()
    lines = [] if not text else text.splitlines()
    return JSONResponse(
        status_code=r.status_code,
        content={"lines": lines, "file": filename, "count": len(lines)},
    )


@router.get("/logs/tail")
async def tail_log(n: int = Query(30, ge=1, le=500), filename: str = "log.txt"):
    return await _tail_from_device(filename, n)


@router.get("/logs")
async def logs_alias(n: int = Query(30, ge=1, le=500), filename: str = "log.txt"):
    return await _tail_from_device(filename, n)

