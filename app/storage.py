from __future__ import annotations

try:
    import ujson as json
except ImportError:
    import json

from pathlib import Path
from typing import Dict, List, Optional

from .settings import DATA_FILE


class DeviceStore:
    def __init__(self, path: Path = DATA_FILE):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _save(self, data: Dict[str, dict]) -> None:
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def list_devices(self) -> List[dict]:
        data = self._load()
        return list(data.values())

    def get_device(self, name: str) -> Optional[dict]:
        return self._load().get(name)

    def upsert_device(self, device: dict) -> dict:
        data = self._load()
        data[device["name"]] = device
        self._save(data)
        return device

    def patch_device(self, name: str, updates: dict) -> dict:
        data = self._load()
        if name not in data:
            raise KeyError(name)
        data[name].update({k: v for k, v in updates.items() if v is not None})
        self._save(data)
        return data[name]

    def delete_device(self, name: str) -> None:
        data = self._load()
        if name not in data:
            raise KeyError(name)
        del data[name]
        self._save(data)


store = DeviceStore()

