from __future__ import annotations

import httpx

from .settings import DEFAULT_TIMEOUT


def _join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def _auth_headers(api_key: str) -> dict:
    if not api_key:
        return {}
    return {
        "X-API-Key": api_key,
        "Authorization": f"Bearer {api_key}",
    }


class Esp32Client:
    def __init__(self, device: dict):
        self.device = device

    @property
    def base_url(self) -> str:
        return self.device["base_url"]

    @property
    def api_key(self) -> str:
        return self.device.get("api_key", "")

    async def _request(self, method: str, path: str, *, json_body=None):
        url = _join_url(self.base_url, path)
        headers = _auth_headers(self.api_key)
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            return await client.request(method, url, headers=headers, json=json_body)

    async def health(self):
        return await self._request("GET", "/health")

    async def status(self):
        return await self._request("GET", "/status")

    async def list_pins(self):
        return await self._request("GET", "/pins")

    async def get_pin(self, name: str):
        return await self._request("GET", f"/pins/{name}")

    async def set_pin(self, name: str, value: bool):
        return await self._request("POST", f"/pins/{name}/set", json_body={"value": value})

    async def pin_on(self, name: str):
        return await self._request("POST", f"/pins/{name}/on")

    async def pin_off(self, name: str):
        return await self._request("POST", f"/pins/{name}/off")

    async def pin_toggle(self, name: str):
        return await self._request("POST", f"/pins/{name}/toggle")

    async def pin_run_for(self, name: str, duration_s: int, value: bool = True):
        return await self._request(
            "POST",
            f"/pins/{name}/run_for",
            json_body={"seconds": duration_s, "value": value},
        )

    async def list_sensors(self):
        return await self._request("GET", "/sensors")

    async def get_sensor(self, name: str):
        return await self._request("GET", f"/sensors/{name}")

    async def list_actions(self):
        return await self._request("GET", "/actions")

    async def list_jobs(self):
        return await self._request("GET", "/jobs")

    async def environment(self):
        return await self._request("GET", "/environment")

    async def list_programs(self):
        return await self._request("GET", "/programs")

    async def create_program(self, payload: dict):
        return await self._request("POST", "/programs", json_body=payload)

    async def update_program(self, program_id, payload: dict):
        return await self._request("PUT", f"/programs/{program_id}", json_body=payload)

    async def delete_program(self, program_id):
        return await self._request("DELETE", f"/programs/{program_id}")

    async def run_action(self, name: str, payload: dict | None = None):
        return await self._request("POST", f"/actions/{name}", json_body=payload or {})

    async def execute(self, name: str, args: dict | None = None):
        return await self._request("POST", "/execute", json_body={"name": name, "args": args or {}})
