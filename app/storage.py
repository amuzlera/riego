from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import Lock

try:
    import ujson as json
except ImportError:
    import json

from pathlib import Path
from typing import Dict, List, Optional

from .settings import DATA_FILE, READINGS_FILE


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


class SensorReadingStore:
    def __init__(self, path: Path = READINGS_FILE, max_entries: int = 500):
        self.path = Path(path)
        self.max_entries = max_entries
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

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

    def record(self, device_name: str, sensor_name: str, reading: dict) -> dict:
        payload = deepcopy(reading)
        payload.update(
            {
                "device": device_name,
                "sensor": sensor_name,
                "recorded_at": payload.get("recorded_at") or datetime.now().astimezone().isoformat(),
            }
        )

        with self._lock:
            data = self._load()
            device_bucket = data.setdefault(device_name, {})
            sensor_bucket = device_bucket.setdefault(sensor_name, [])
            sensor_bucket.append(payload)
            if self.max_entries > 0 and len(sensor_bucket) > self.max_entries:
                device_bucket[sensor_name] = sensor_bucket[-self.max_entries :]
            self._save(data)

        return payload

    def latest(self, device_name: str, sensor_name: Optional[str] = None) -> Optional[dict]:
        data = self._load()
        device_bucket = data.get(device_name)
        if not isinstance(device_bucket, dict):
            return None

        if sensor_name:
            sensor_bucket = device_bucket.get(sensor_name)
            if not isinstance(sensor_bucket, list) or not sensor_bucket:
                return None
            latest = sensor_bucket[-1]
            return latest if isinstance(latest, dict) else None

        latest_payload: Optional[dict] = None
        latest_timestamp: Optional[datetime] = None
        for sensor_bucket in device_bucket.values():
            if not isinstance(sensor_bucket, list) or not sensor_bucket:
                continue
            candidate = sensor_bucket[-1]
            if not isinstance(candidate, dict):
                continue

            recorded_at = candidate.get("recorded_at")
            try:
                candidate_timestamp = datetime.fromisoformat(str(recorded_at)) if recorded_at else None
            except ValueError:
                candidate_timestamp = None

            if candidate_timestamp is None:
                if latest_payload is None:
                    latest_payload = candidate
                continue

            if latest_timestamp is None or candidate_timestamp >= latest_timestamp:
                latest_timestamp = candidate_timestamp
                latest_payload = candidate

        return latest_payload


store = DeviceStore()
reading_store = SensorReadingStore()
