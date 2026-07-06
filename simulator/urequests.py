from __future__ import annotations

import json as _json
from dataclasses import dataclass
from urllib import error, request


@dataclass
class Response:
    status_code: int
    text: str
    headers: dict[str, str]

    @property
    def content(self):
        return self.text.encode()

    def json(self):
        return _json.loads(self.text)

    def close(self):
        return None


def _request(method, url, headers=None, data=None, json=None, timeout=10):
    headers = dict(headers or {})
    body = data
    if json is not None:
        body = _json.dumps(json).encode()
        headers.setdefault("Content-Type", "application/json")
    if isinstance(body, str):
        body = body.encode()
    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode()
            return Response(resp.status, payload, dict(resp.headers.items()))
    except error.HTTPError as exc:
        payload = exc.read().decode()
        return Response(exc.code, payload, dict(exc.headers.items()))


def get(url, headers=None, timeout=10):
    return _request("GET", url, headers=headers, timeout=timeout)


def post(url, headers=None, data=None, json=None, timeout=10):
    return _request("POST", url, headers=headers, data=data, json=json, timeout=timeout)
