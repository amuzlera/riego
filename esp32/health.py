try:
    import uasyncio as asyncio
except Exception:
    import asyncio

import time

HEARTBEAT_TIMEOUT_MS = 30000
CHECK_INTERVAL_MS = 5000
STARTUP_GRACE_MS = 15000

_last_beat_ms = {}
_started_ms = None
_watchdog = None


def _now_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def _diff_ms(now, then):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(now, then)
    return now - then


def _ensure_started():
    global _started_ms
    if _started_ms is None:
        _started_ms = _now_ms()


def mark(name):
    _ensure_started()
    _last_beat_ms[name] = _now_ms()


def _maybe_init_wdt(timeout_ms=HEARTBEAT_TIMEOUT_MS):
    global _watchdog
    if _watchdog is not None:
        return _watchdog

    try:
        import machine

        _watchdog = machine.WDT(timeout=timeout_ms)
    except Exception:
        _watchdog = None
    return _watchdog


def _fresh(name, now, timeout_ms):
    ts = _last_beat_ms.get(name)
    if ts is None:
        return _started_ms is not None and _diff_ms(now, _started_ms) <= STARTUP_GRACE_MS
    return _diff_ms(now, ts) <= timeout_ms


async def monitor(required=("main", "scheduler", "server"), timeout_ms=HEARTBEAT_TIMEOUT_MS, check_ms=CHECK_INTERVAL_MS):
    _ensure_started()
    wdt = _maybe_init_wdt(timeout_ms)

    while True:
        now = _now_ms()
        stale = [name for name in required if not _fresh(name, now, timeout_ms)]

        if stale:
            try:
                from server_utils import log

                log("Watchdog: heartbeat stale for {}".format(", ".join(stale)))
            except Exception:
                pass

            try:
                import machine

                machine.reset()
            except Exception:
                pass
            return

        if wdt is not None:
            try:
                wdt.feed()
            except Exception:
                pass

        await asyncio.sleep(check_ms / 1000.0)
