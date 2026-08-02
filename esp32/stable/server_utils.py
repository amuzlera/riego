import gc
import os
import time

try:
    import ujson as json
except Exception:  # pragma: no cover - simulator fallback
    import json  # type: ignore

try:
    import traceback
except Exception:  # pragma: no cover - MicroPython fallback
    traceback = None

from time_utils import now_local

LOG_FILE = "log.txt"
MAX_LINES = 200


def reset():
    log("Reiniciando...")
    time.sleep(1)
    import machine

    machine.reset()


def send_response(writer, data, status="200 OK", content_type="application/json"):
    if isinstance(data, dict):
        data = json.dumps(data)
    resp = "HTTP/1.1 {}\r\nContent-Type: {}\r\n\r\n{}".format(status, content_type, data)
    writer.write(resp.encode())


def parse_headers(header_text):
    headers = {}
    lines = header_text.split("\r\n")
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
    return headers


def parse_query(query):
    params = {}
    if query:
        for pair in query.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = v
    return params


def _err_payload(e):
    try:
        etype = type(e).__name__
        return {"error": "{}: {}".format(etype, repr(e))}
    except BaseException:
        return {"error": "unknown"}


def _traceback_text(exc=None):
    if exc is None:
        return ""
    if traceback is not None and hasattr(traceback, "format_exception"):
        try:
            return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        except Exception:
            pass
    try:
        import io
        import sys

        buf = io.StringIO()
        sys.print_exception(exc, buf)
        return buf.getvalue()
    except Exception:
        return repr(exc)


def _write_to_log_file(line: str):
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def _truncate_log_if_needed(path):
    try:
        if os.stat(path)[6] <= 8192:
            return
    except OSError:
        return

    try:
        with open(path, "r") as f:
            lines = f.readlines()
        with open(path, "w") as f:
            for l in lines[-MAX_LINES:]:
                f.write(l)
    except Exception:
        pass


def start_new_boot_log():
    pass


def log(msg, ts=None):
    ts = ts or now_local()
    line = "{:02d}:{:02d}:{:02d} - {}".format(ts[3], ts[4], ts[5], msg)
    print(line)
    try:
        _write_to_log_file(line)
        _truncate_log_if_needed(LOG_FILE)
        _truncate_log_if_needed(LAST_LOG_FILE)
    except Exception:
        pass
    return line


def log_exception(context: str, exc: BaseException):
    log(f"{context}: {type(exc).__name__}: {exc}")
    tb = _traceback_text(exc)
    if tb:
        for chunk in tb.splitlines():
            log(chunk)


def log_and_send(msg):
    log(msg)


def get_weather_multiplier():
    return {"multiplier": 1.0, "details": "local-only"}
