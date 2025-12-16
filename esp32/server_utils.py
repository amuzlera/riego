import urequests
import uos
import time
import ujson as json

from time_utils import now_local
from config import BASE_API_URL

def reset():
    log("Reiniciando...")
    time.sleep(1)
    import machine
    machine.reset()


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

LOG_FILE = "log.txt"
MAX_LINES = 100


def _write_to_log_file(line):
    """Escribe una línea al archivo de log"""
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def _truncate_log_if_needed():
    """Trunca el archivo de log si es muy grande"""
    if uos.stat(LOG_FILE)[6] > 2000:  # tamaño en bytes (~2 KB)
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        with open(LOG_FILE, "w") as f:
            for l in lines[-MAX_LINES:]:
                f.write(l)


def log(msg, send=True):
    # Crear línea con timestamp
    ts = now_local()
    line = "{:02d}:{:02d}:{:02d} - {}".format(ts[3], ts[4], ts[5], msg)
    print(line)

    # Escribir a archivo
    _write_to_log_file(line)

    # Enviar al servidor
    if send:
        send_logs([line])

    # Truncar si es necesario
    _truncate_log_if_needed()


def send_logs(msg):
    url = f"{BASE_API_URL}/logs"

    headers = {"Content-Type": "application/json; charset=utf-8"}

    try:
        # Leer las últimas 10 líneas del archivo de logs
        try:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()
            last_lines = lines[-10:] if lines else []
            # Convertir a string único con saltos de línea
            logs_content = "".join(last_lines).strip()
        except OSError:
            logs_content = "No log file found"
        
        payload_json = json.dumps({"log": logs_content})
        r = urequests.post(url, data=payload_json, headers=headers)
        r.close()
    except Exception as e:
        # Loguear sin enviar para evitar recursión
        ts = now_local()
        line = "{:02d}:{:02d}:{:02d} - Error enviando logs: {}".format(
            ts[3], ts[4], ts[5], str(e))
        print(line)
        _write_to_log_file(line)


def get_weather_multiplier():
    url = f"{BASE_API_URL}/weather-multiplier"
    try:
        r = urequests.get(url)
        data = r.json()
        r.close()

        # Por si el servidor devolvió algo inesperado
        if "multiplier" not in data:
            return {
                "multiplier": 1.0,
                "details": "invalid response",
                "response": data
            }

        return data

    except Exception as e:
        # Cualquier error: WiFi caída, timeout, JSON inválido, server down, etc.
        return {
            "multiplier": 1.0,
            "details": "fail to fetch"
        }
