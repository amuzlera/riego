from boot import SERVER_URL
import urequests
import uos
import time
import ujson as json

from time_utils import now_local


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


def log(msg, ts=None):
    # Crear línea con timestamp
    ts = ts or now_local()
    line = "{:02d}:{:02d}:{:02d} - {}".format(ts[3], ts[4], ts[5], msg)
    print(line)

    # Escribir a archivo
    _write_to_log_file(line)

    # Truncar si es necesario
    _truncate_log_if_needed()


def send_logs(log_str, ts=None):
    try:
        ts = ts or now_local()
        time = "{:02d}:{:02d}:{:02d} - ".format(ts[3], ts[4], ts[5])
        payload = {"log": f"{time}{log_str}"}

    except Exception as e:
        log("Error preparing logs payload: {}".format(e))
        return {"ok": False, "error": str(e)}

    try:
        log(f"Sending logs to server... {payload.get("log")}")
        r = urequests.post(f"{SERVER_URL}/api/logs", json=payload)
        text = r.text
        r.close()
        log(f"Logs sent successfully. {text}")
        return {"ok": True}
    except Exception as e:
        log("Error sending logs: {}".format(e))
        return {"ok": False, "error": str(e)}

# la dejo por las dudas
def send_logs_batch(logs, ts=None):
    try:
        ts = ts or now_local()
        lines = []
        for l in logs:
            if isinstance(l, dict):
                lines.append(json.dumps(l))   # JSON por línea
            else:
                lines.append(str(l))
                
        time = "{:02d}:{:02d}:{:02d} - ".format(ts[3], ts[4], ts[5])
        payload = {
            "log": "\n".join(f"{time}{line}" for line in lines)
        }

    except Exception as e:
        log("Error preparing logs payload: {}".format(e))
        return {"ok": False, "error": str(e)}

    try:
        r = urequests.post(f"{SERVER_URL}/api/logs", json=payload)
        text = r.text
        r.close()
        log(f"Logs sent successfully. {text}")
        return {"ok": True}
    except Exception as e:
        log("Error sending logs: {}".format(e))
        return {"ok": False, "error": str(e)}

def log_and_send(msg):
    ts = now_local()
    log(msg, ts=ts)
    send_logs(msg, ts=ts)

def send_logs_from_file():
    """Envía los logs guardados en el archivo al servidor remoto"""
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        if not lines:
            return {"ok": True, "message": "No logs to send"}

        result = send_logs([line.strip() for line in lines])
        return result
    except Exception as e:
        log("Error sending logs from file: {}".format(e))
        return {"ok": False, "error": str(e)}


def get_weather_multiplier():
    url = "http://192.168.0.105:8000/api/weather-multiplier"

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

def get_remote_config():
    url = f"{SERVER_URL}/api/esp/config"
    r = urequests.get(url)
    data = r.json()
    r.close()
    return data