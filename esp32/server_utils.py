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


def log(msg, send=True):
    # Append directo
    ts = now_local()
    line = "{:02d}:{:02d}:{:02d} - {}".format(ts[3], ts[4], ts[5], msg)
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

    if send and False:
        send_logs([msg])

    # Truncar si es muy grande
    if uos.stat(LOG_FILE)[6] > 2000:  # tamaño en bytes (~2 KB)
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        with open(LOG_FILE, "w") as f:
            # MicroPython puede no tener writelines(); escribimos en un bucle
            for l in lines[-MAX_LINES:]:
                f.write(l)


def send_logs(msg):
    url = "http://192.168.0.105:8000/api/logs"

    payload = {"log": msg}
    headers = {"Content-Type": "application/json"}

    try:
        log(f'data: {json.dumps(payload)}', send=False)
        r = urequests.post(url, data=json.dumps(payload), headers=headers)
        log(f"response: {r.text}", send=False)
        r.close()
    except Exception as e:
        log("Error enviando logs: " + str(e), send=False)



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
