try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    import ujson as json
except ImportError:
    import json

from time_utils import local_time_is_plausible, now_local


DAY_MAP = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _parse_hhmm(value):
    if not isinstance(value, str) or ":" not in value:
        raise ValueError("Hora invalida: {}".format(value))
    hh, mm = value.split(":", 1)
    hour = _safe_int(hh, -1)
    minute = _safe_int(mm, -1)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("Hora invalida: {}".format(value))
    return "{:02d}:{:02d}".format(hour, minute)


def _minutes_from_hhmm(value):
    normalized = _parse_hhmm(value)
    hour, minute = normalized.split(":")
    return _safe_int(hour) * 60 + _safe_int(minute)


def _normalize_days(days):
    if days is None:
        return []

    normalized = []
    for day in days:
        if isinstance(day, int):
            if 0 <= day <= 6:
                normalized.append(day)
            continue

        if isinstance(day, str):
            lowered = day.strip().lower()
            if lowered == "all":
                return [0, 1, 2, 3, 4, 5, 6]
            if lowered.isdigit():
                idx = int(lowered)
                if 0 <= idx <= 6:
                    normalized.append(idx)
                continue
            mapped = DAY_MAP.get(lowered)
            if mapped is not None:
                normalized.append(mapped)

    return sorted(list(set(normalized)))


def _normalize_period(period):
    if isinstance(period, str):
        if "-" not in period:
            raise ValueError("Periodo invalido: {}".format(period))
        start, end = period.split("-", 1)
        normalized = {
            "start": _parse_hhmm(start),
            "end": _parse_hhmm(end),
        }
        if normalized["start"] == normalized["end"]:
            raise ValueError("start y end no pueden ser iguales")
        return normalized

    if isinstance(period, dict):
        start = _parse_hhmm(period.get("start", "00:00"))
        end = _parse_hhmm(period.get("end", "00:00"))
        if start == end:
            raise ValueError("start y end no pueden ser iguales")
        return {
            "start": start,
            "end": end,
        }

    raise ValueError("Periodo invalido")


def _normalize_periods(program):
    raw_periods = program.get("periods", None)
    periods = []

    if isinstance(raw_periods, list) and raw_periods:
        for item in raw_periods:
            periods.append(_normalize_period(item))
    else:
        start = program.get("start")
        end = program.get("end")
        if start is not None and end is not None:
            periods.append(_normalize_period({"start": start, "end": end}))

    if not periods:
        raise ValueError("Faltan periods")

    return periods


def _normalize_program(program):
    program = dict(program or {})
    program["id"] = _safe_int(program.get("id"), 0)
    program["pin"] = str(program.get("pin", "")).strip()
    program["days"] = _normalize_days(program.get("days", []))
    program["periods"] = _normalize_periods(program)
    program.pop("start", None)
    program.pop("end", None)
    program["enabled"] = bool(program.get("enabled", True))
    program["label"] = str(program.get("label", "")).strip()
    return program


def _program_key(program_id, anchor_day, period_index, start, end):
    return "{}:{}:{}:{}:{}".format(program_id, anchor_day, period_index, start, end)


class WeeklyProgramScheduler:
    def __init__(self, device, storage_path="programs.json", tz_offset_seconds=10800):
        self.device = device
        self.storage_path = storage_path
        self.tz_offset_seconds = int(tz_offset_seconds)
        self.programs = []
        self.active_windows = {}
        self.pin_ref_counts = {}
        self._next_id = 1
        self._load_from_disk()

    def _snapshot(self):
        return {
            "next_id": self._next_id,
            "programs": self.programs,
        }

    def _save_to_disk(self):
        tmp_path = self.storage_path + ".tmp"
        payload = json.dumps(self._snapshot())
        with open(tmp_path, "w") as f:
            f.write(payload)
        try:
            import uos as os
        except ImportError:
            import os
        try:
            os.remove(self.storage_path)
        except Exception:
            pass
        os.rename(tmp_path, self.storage_path)

    def _load_from_disk(self):
        try:
            with open(self.storage_path, "r") as f:
                data = json.loads(f.read())
        except Exception:
            return

        if not isinstance(data, dict):
            return

        try:
            self._next_id = int(data.get("next_id", 1))
        except Exception:
            self._next_id = 1

        raw_programs = data.get("programs", [])
        if isinstance(raw_programs, list):
            self.programs = []
            for item in raw_programs:
                try:
                    self.programs.append(_normalize_program(item))
                except Exception:
                    continue

    def _allocate_id(self):
        program_id = self._next_id
        self._next_id += 1
        return program_id

    def _find_index(self, program_id):
        program_id = _safe_int(program_id, -1)
        for index, program in enumerate(self.programs):
            if _safe_int(program.get("id"), -1) == program_id:
                return index
        return None

    def list_programs(self):
        return [dict(program) for program in self.programs]

    def get_program(self, program_id):
        index = self._find_index(program_id)
        if index is None:
            return None
        return dict(self.programs[index])

    def create_program(self, payload):
        program = _normalize_program(payload)
        if not program["pin"]:
            raise ValueError("Falta 'pin'")
        if not program["days"]:
            raise ValueError("Faltan 'days'")
        program["id"] = self._allocate_id()
        self.programs.append(program)
        self._save_to_disk()
        return dict(program)

    def update_program(self, program_id, payload):
        index = self._find_index(program_id)
        if index is None:
            raise KeyError(program_id)

        current = dict(self.programs[index])
        updates = dict(payload or {})

        for key in ("pin", "days", "periods", "start", "end", "enabled", "label"):
            if key in updates and updates[key] is not None:
                current[key] = updates[key]

        normalized = _normalize_program(current)
        normalized["id"] = current["id"]
        self.programs[index] = normalized
        self._save_to_disk()
        return dict(normalized)

    def delete_program(self, program_id):
        index = self._find_index(program_id)
        if index is None:
            raise KeyError(program_id)
        removed = self.programs.pop(index)
        self._save_to_disk()
        return removed

    def _should_run_period(self, program, period_index, period, weekday, minute_of_day, previous_weekday):
        if not program.get("enabled", True):
            return False, None

        days = set(program.get("days", []))
        if not days:
            return False, None

        start_min = _minutes_from_hhmm(period["start"])
        end_min = _minutes_from_hhmm(period["end"])
        program_id = _safe_int(program.get("id"), 0)
        pin = program.get("pin")

        if start_min < end_min:
            if weekday in days and start_min <= minute_of_day < end_min:
                key = _program_key(program_id, weekday, period_index, period["start"], period["end"])
                return True, {"key": key, "pin": pin}
            return False, None

        if weekday in days and minute_of_day >= start_min:
            key = _program_key(program_id, weekday, period_index, period["start"], period["end"])
            return True, {"key": key, "pin": pin}

        if previous_weekday in days and minute_of_day < end_min:
            key = _program_key(program_id, previous_weekday, period_index, period["start"], period["end"])
            return True, {"key": key, "pin": pin}

        return False, None

    def _increment_pin(self, pin):
        count = self.pin_ref_counts.get(pin, 0) + 1
        self.pin_ref_counts[pin] = count
        if count == 1:
            self.device.on(pin)

    def _decrement_pin(self, pin):
        count = self.pin_ref_counts.get(pin, 0)
        if count <= 1:
            self.pin_ref_counts.pop(pin, None)
            self.device.off(pin)
            return
        self.pin_ref_counts[pin] = count - 1

    def reconcile(self):
        if not local_time_is_plausible(self.tz_offset_seconds):
            return

        current = now_local(self.tz_offset_seconds)
        if not current:
            return

        weekday = current[6]
        minute_of_day = current[3] * 60 + current[4]
        previous_weekday = (weekday - 1) % 7

        desired = {}
        for program in self.programs:
            periods = program.get("periods", []) or []
            for index, period in enumerate(periods):
                active, payload = self._should_run_period(
                    program,
                    index,
                    period,
                    weekday,
                    minute_of_day,
                    previous_weekday,
                )
                if active and payload:
                    desired[payload["key"]] = payload["pin"]

        current_keys = set(self.active_windows.keys())
        desired_keys = set(desired.keys())

        for key in desired_keys - current_keys:
            pin = desired[key]
            self.active_windows[key] = {"pin": pin}
            self._increment_pin(pin)

        for key in current_keys - desired_keys:
            pin = self.active_windows.get(key, {}).get("pin")
            if pin:
                self._decrement_pin(pin)
            self.active_windows.pop(key, None)

    def active_programs(self):
        return dict(self.active_windows)

    async def loop(self, poll_s=30):
        while True:
            try:
                self.reconcile()
            except Exception as exc:
                print("Program scheduler error: {}".format(exc))
            await asyncio.sleep(poll_s)
