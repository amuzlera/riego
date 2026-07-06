"""Thin client helpers for the ESP32 or simulator."""

from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx
from fastapi.responses import JSONResponse, PlainTextResponse


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f"{name} must be set")


ESP_HOST = _required_env("ESP_HOST")
ESP_USER = os.getenv("ESP_USER", "admin")
ESP_PASS = os.getenv("ESP_PASS", "1234")
ESP_TIMEOUT = float(os.getenv("ESP_TIMEOUT", "5"))


def _esp_url(path: str, params: dict | None = None) -> str:
    url = f"{ESP_HOST}{path}"
    if params:
        url += f"?{urlencode(params)}"
    return url


async def _esp_get(path: str, params: dict | None = None):
    auth = httpx.BasicAuth(ESP_USER, ESP_PASS)
    async with httpx.AsyncClient(timeout=ESP_TIMEOUT) as client:
        return await client.get(_esp_url(path, params), auth=auth)


async def _esp_post(path: str, params: dict | None = None, data: str = ""):
    auth = httpx.BasicAuth(ESP_USER, ESP_PASS)
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    async with httpx.AsyncClient(timeout=ESP_TIMEOUT) as client:
        return await client.post(
            _esp_url(path, params),
            auth=auth,
            content=data.encode("utf-8"),
            headers=headers,
        )


def _as_response(r: httpx.Response):
    ctype = r.headers.get("content-type", "")
    if "application/json" in ctype:
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return PlainTextResponse(status_code=r.status_code, content=r.text)
    return PlainTextResponse(status_code=r.status_code, content=r.text)


async def proxy_get(path: str, params: dict | None = None):
    try:
        return _as_response(await _esp_get(path, params))
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "timeout"})
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


async def proxy_post(path: str, params: dict | None = None, data: str = ""):
    try:
        return _as_response(await _esp_post(path, params, data=data))
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "timeout"})
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"error": str(e)})
