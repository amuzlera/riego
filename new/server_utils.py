import time
import ujson as json


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
    except:
        return {"error": "unknown"}


LOG_FILE = "riego.log"


def log(msg):
    ts = time.localtime()
    # Formato: YYYY-MM-DD HH:MM:SS - mensaje
    line = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d} - {}\n".format(
        ts[0], ts[1], ts[2], ts[3], ts[4], ts[5], msg
    )
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except Exception as e:
        print("Error escribiendo log:", e)
    # Además mostrar en consola (opcional)
    print(line, end="")
