try:
    import ujson as json
except Exception:
    import json

import os
import sys
import time

BOOT_STATE_FILE = "boot_state.json"
BOOT_LOG_FILE = "log.txt"
DEV_SLOT = "dev"
STABLE_SLOT = "stable"
FAILOVER_THRESHOLD = 3

APP_MODULE_PREFIXES = (
    "main",
    "server",
    "task",
    "health",
    "config",
    "server_utils",
    "time_utils",
    "endpoints",
    "endpoints.",
)


def _default_state():
    return {
        "active_slot": DEV_SLOT,
        "pending_slot": None,
        "pending_confirmed": False,
        "consecutive_failures": {DEV_SLOT: 0, STABLE_SLOT: 0},
        "last_good_slot": STABLE_SLOT,
    }


def _normalize_state(state):
    if not isinstance(state, dict):
        state = {}

    normalized = _default_state()
    normalized.update({k: v for k, v in state.items() if k != "consecutive_failures"})

    failures = state.get("consecutive_failures", {})
    if not isinstance(failures, dict):
        failures = {}
    normalized["consecutive_failures"] = {
        DEV_SLOT: int(failures.get(DEV_SLOT, 0) or 0),
        STABLE_SLOT: int(failures.get(STABLE_SLOT, 0) or 0),
    }

    if normalized.get("active_slot") not in (DEV_SLOT, STABLE_SLOT):
        normalized["active_slot"] = DEV_SLOT

    if normalized.get("pending_slot") not in (None, DEV_SLOT, STABLE_SLOT):
        normalized["pending_slot"] = None

    normalized["pending_confirmed"] = bool(normalized.get("pending_confirmed", False))

    if normalized.get("last_good_slot") not in (DEV_SLOT, STABLE_SLOT):
        normalized["last_good_slot"] = STABLE_SLOT

    return normalized


def _read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _write_json(path, value):
    try:
        with open(path, "w") as f:
            f.write(json.dumps(value))
        return True
    except Exception:
        return False


def _append_log(line):
    try:
        with open(BOOT_LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def log(message):
    line = str(message)
    print(line)
    _append_log(line)
    return line


def _traceback_text(exc):
    try:
        import traceback

        return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    except Exception:
        return repr(exc)


def log_exception(context, exc):
    log("{}: {}: {}".format(context, type(exc).__name__, exc))
    tb = _traceback_text(exc)
    if tb:
        for line in tb.splitlines():
            log(line)


def _slot_dir(slot):
    return STABLE_SLOT if slot == STABLE_SLOT else "."


def _set_sys_path(slot):
    chosen = _slot_dir(slot)
    ordered = []
    for entry in (chosen, "."):
        if entry not in ordered:
            ordered.append(entry)
    for entry in list(sys.path):
        if entry not in ordered:
            ordered.append(entry)
    sys.path[:] = ordered


def _clear_app_modules():
    for name in list(sys.modules.keys()):
        if name == "boot_manager":
            continue
        for prefix in APP_MODULE_PREFIXES:
            if name == prefix or name.startswith(prefix):
                try:
                    del sys.modules[name]
                except Exception:
                    pass
                break


def get_state():
    return _normalize_state(_read_json(BOOT_STATE_FILE))


def save_state(state):
    state = _normalize_state(state)
    _write_json(BOOT_STATE_FILE, state)
    return state


def set_active_slot(slot):
    if slot not in (DEV_SLOT, STABLE_SLOT):
        raise ValueError("slot inválido: {}".format(slot))

    state = get_state()
    state["active_slot"] = slot
    state["pending_slot"] = None
    state["pending_confirmed"] = False
    state["consecutive_failures"][slot] = 0
    return save_state(state)


def mark_boot_success(slot=None):
    state = get_state()
    slot = slot or state.get("pending_slot") or state.get("active_slot") or DEV_SLOT
    if slot not in (DEV_SLOT, STABLE_SLOT):
        slot = DEV_SLOT

    state["active_slot"] = slot
    state["pending_slot"] = slot
    state["pending_confirmed"] = True
    state["consecutive_failures"][slot] = 0
    state["last_good_slot"] = slot
    save_state(state)
    log("Boot confirmado para slot {}".format(slot))
    return state


def _finalize_previous_boot(state):
    pending = state.get("pending_slot")
    confirmed = bool(state.get("pending_confirmed"))

    if pending not in (DEV_SLOT, STABLE_SLOT):
        state["pending_slot"] = None
        state["pending_confirmed"] = False
        return state

    if confirmed:
        state["consecutive_failures"][pending] = 0
        state["last_good_slot"] = pending
    else:
        failures = state["consecutive_failures"]
        failures[pending] = int(failures.get(pending, 0) or 0) + 1
        if pending == DEV_SLOT and failures[pending] >= FAILOVER_THRESHOLD:
            if state.get("active_slot") != STABLE_SLOT:
                log("Failover: demasiados fallos seguidos en dev, cambiando a stable")
            state["active_slot"] = STABLE_SLOT
        elif pending == STABLE_SLOT:
            log("Stable falló al arrancar, volviendo a dev")
            state["active_slot"] = DEV_SLOT

    state["pending_slot"] = None
    state["pending_confirmed"] = False
    return state


def boot():
    state = _finalize_previous_boot(get_state())

    active_slot = state.get("active_slot", DEV_SLOT)
    if active_slot not in (DEV_SLOT, STABLE_SLOT):
        active_slot = DEV_SLOT
        state["active_slot"] = active_slot

    if active_slot == DEV_SLOT:
        dev_failures = int(state["consecutive_failures"].get(DEV_SLOT, 0) or 0)
        if dev_failures >= FAILOVER_THRESHOLD:
            active_slot = STABLE_SLOT
            state["active_slot"] = STABLE_SLOT

    state["pending_slot"] = active_slot
    state["pending_confirmed"] = False
    save_state(state)

    log("Arrancando slot {}".format(active_slot))
    _clear_app_modules()
    _set_sys_path(active_slot)

    try:
        __import__("main")
    except Exception as exc:
        log_exception("Boot falló para slot {}".format(active_slot), exc)
        time.sleep(1)
        try:
            import machine

            machine.reset()
        except Exception:
            raise
