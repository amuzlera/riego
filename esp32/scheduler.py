try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    import ujson as json
except ImportError:
    import json

try:
    import utime as time
except ImportError:
    import time

try:
    import uos as os
except ImportError:
    import os

try:
    from time import monotonic as _monotonic
except ImportError:
    _monotonic = None


def _now_ms():
    if _monotonic is not None:
        return int(_monotonic() * 1000)
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def _now_epoch():
    try:
        return int(time.time())
    except Exception:
        return 0


def _has_plausible_epoch(epoch_value):
    return epoch_value >= 1700000000


def _diff_ms(a, b):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(a, b)
    return a - b


class JobScheduler:
    def __init__(self, device, storage_path="jobs.json"):
        self.device = device
        self.storage_path = storage_path
        self.jobs = {}
        self.pending_jobs = {}
        self._next_id = 1
        self._load_from_disk()

    def _new_job_id(self):
        job_id = self._next_id
        self._next_id += 1
        return job_id

    def _snapshot(self):
        return {
            "next_id": self._next_id,
            "jobs": self.jobs,
            "pending_jobs": self.pending_jobs,
        }

    def _save_to_disk(self):
        tmp_path = self.storage_path + ".tmp"
        payload = json.dumps(self._snapshot())
        with open(tmp_path, "w") as f:
            f.write(payload)
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

        loaded_jobs = {}

        jobs = data.get("jobs", {})
        if isinstance(jobs, dict):
            for pin_name, job in jobs.items():
                loaded_jobs[pin_name] = job

        pending_jobs = data.get("pending_jobs", {})
        if isinstance(pending_jobs, dict):
            for pin_name, job in pending_jobs.items():
                loaded_jobs[pin_name] = job

        self.jobs = {}
        self.pending_jobs = loaded_jobs

    def _restore_job_now(self, pin_name, job):
        value = job.get("value", True)
        try:
            if value:
                self.device.on(pin_name)
            else:
                self.device.off(pin_name)
        except Exception as exc:
            print("scheduler restore failed for {}: {}".format(pin_name, exc))
            return False

        self.jobs[pin_name] = job
        self.pending_jobs.pop(pin_name, None)
        return True

    def restore_pending_jobs(self):
        now_epoch = _now_epoch()
        if not _has_plausible_epoch(now_epoch):
            return

        restored = []
        expired = []

        for pin_name, job in self.pending_jobs.items():
            expires_at_epoch = int(job.get("expires_at_epoch", 0) or 0)
            if expires_at_epoch <= 0:
                expired.append(pin_name)
                continue

            if expires_at_epoch > now_epoch:
                restored.append(pin_name)
            else:
                expired.append(pin_name)

        for pin_name in restored:
            job = self.pending_jobs.get(pin_name)
            if job:
                self._restore_job_now(pin_name, job)

        for pin_name in expired:
            self.pending_jobs.pop(pin_name, None)

        if restored or expired:
            self._save_to_disk()

    def run_for(self, pin_name, duration_s, logical_value=True):
        duration_s = int(duration_s)
        if duration_s <= 0:
            raise ValueError("duration_s debe ser mayor que 0")

        logical_value = bool(logical_value)
        if logical_value:
            self.device.on(pin_name)
        else:
            self.device.off(pin_name)

        now = _now_ms()
        now_epoch = _now_epoch()
        expires_at = now + (duration_s * 1000)
        job = {
            "id": self._new_job_id(),
            "pin": pin_name,
            "value": logical_value,
            "duration_s": duration_s,
            "started_at_ms": now,
            "expires_at_ms": expires_at,
            "started_at_epoch": now_epoch,
            "expires_at_epoch": now_epoch + duration_s if now_epoch else 0,
        }
        self.jobs[pin_name] = job
        self.pending_jobs[pin_name] = job
        self._save_to_disk()
        return job

    def cancel(self, pin_name):
        job = self.jobs.pop(pin_name, None)
        if job is None:
            job = self.pending_jobs.pop(pin_name, None)
        else:
            self.pending_jobs.pop(pin_name, None)
        if job is not None:
            self._save_to_disk()
        return job

    def list_jobs(self):
        combined = {}
        for pin_name, job in self.pending_jobs.items():
            combined[pin_name] = job
        for pin_name, job in self.jobs.items():
            combined[pin_name] = job
        return list(combined.values())

    def has_job(self, pin_name):
        return pin_name in self.jobs or pin_name in self.pending_jobs

    async def loop(self, poll_s=1):
        self.restore_pending_jobs()
        while True:
            now = _now_ms()
            expired = []

            for pin_name, job in self.jobs.items():
                if _diff_ms(now, job["expires_at_ms"]) >= 0:
                    expired.append(pin_name)

            for pin_name in expired:
                try:
                    self.device.off(pin_name)
                except Exception as exc:
                    print("scheduler expiry failed for {}: {}".format(pin_name, exc))
                finally:
                    self.jobs.pop(pin_name, None)
                    self.pending_jobs.pop(pin_name, None)

            self.restore_pending_jobs()
            if expired:
                self._save_to_disk()
            await asyncio.sleep(poll_s)
