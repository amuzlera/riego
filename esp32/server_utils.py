import time
import ujson as json

from time_utils import now_local


def send_response(writer, data, status="200 OK", content_type="application/json"):
    if isinstance(data, dict):
        data = json.dumps(data)
    resp = "HTTP/1.1 {}\r\nContent-Type: {}\r\n\r\n{}".format(
        status, content_type, data)
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


# --- logger simple ---
LOG_FILE = "riego.log"


import os

LOG_FILE = "log.txt"
MAX_LINES = 11
CHECK_INTERVAL = 50   # cada cuántos logs revisar el tamaño

_write_count = 0

def log(msg):
    global _write_count
    ts = now_local()
    line = "{:02d}:{:02d}:{:02d} - {}\n".format(ts[3], ts[4], ts[5], msg)

    try:
        # 1. Escribir
        with open(LOG_FILE, "a") as f:
            f.write(line)

        _write_count += 1

        # 2. Cada cierto número de escrituras revisamos
        if _write_count >= CHECK_INTERVAL:
            _write_count = 0
            trim_log(LOG_FILE, MAX_LINES)

    except Exception as e:
        print("Log error:", e)

    print(line, end="")


def trim_log(filename, max_lines):
    """Recorta el archivo manteniendo solo las últimas `max_lines`."""
    line_count = 0
    with open(filename, "r") as f:
        for _ in f:
            line_count += 1

    if line_count <= max_lines:
        return

    # saltar las primeras (line_count - max_lines) líneas y copiar el resto
    skip = line_count - max_lines
    tmpfile = filename + ".tmp"

    with open(filename, "r") as fin, open(tmpfile, "w") as fout:
        for i, line in enumerate(fin):
            if i >= skip:
                fout.write(line)

    # reemplazar original por el recortado
    os.rename(tmpfile, filename)

