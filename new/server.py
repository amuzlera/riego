import uasyncio as asyncio
import network
import ubinascii
import config
from server_utils import send_response, parse_headers, _err_payload
from endpoints import ls, cat, upload, rm

# ---------- WiFi ----------
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect(config.WIFI_SSID, config.WIFI_PASS)

while not sta_if.isconnected():
    pass
print("Conectado a WiFi:", sta_if.ifconfig())


# ---------- Auth ----------
def check_auth(header):
    if not header or "Authorization" not in header:
        return False
    auth_value = header["Authorization"].split()[1]
    expected = ubinascii.b2a_base64(b"%s:%s" % (
        config.HTTP_USER.encode(), config.HTTP_PASS.encode())).decode().strip()
    return auth_value == expected


# ---------- Cliente ----------
async def handle_client(reader, writer):
    try:
        # Primera línea
        req_line = await reader.readline()
        if not req_line:
            await writer.aclose()
            return

        parts = req_line.decode().split(" ")
        if len(parts) < 2:
            await writer.aclose()
            return

        method, path = parts[0], parts[1]
        route = path.split("?")[0]
        query = path.split("?")[1] if "?" in path else ""
        query = query.replace('-_-', '/')

        # Headers
        headers_raw = ""
        while True:
            line = await reader.readline()
            if line == b"\r\n":
                break
            headers_raw += line.decode()
        headers = parse_headers(headers_raw)

        # Auth
        if not check_auth(headers):
            resp = 'HTTP/1.1 401 Unauthorized\r\nWWW-Authenticate: Basic realm="ESP32"\r\n\r\n'
            writer.write(resp.encode())
            await writer.aclose()
            return

        # ---------- Dispatch ----------
        print(route, query)
        if route == "/ls":
            await ls.handle(writer, query)

        elif route == "/cat":
            await cat.handle(writer, query)

        elif route == "/upload" and method == "POST":
            await upload.handle(reader, writer, query, headers)

        elif route == "/rm":
            await rm.handle(writer, query)

        else:
            send_response(writer, {"error": f"Ruta {route} no encontrada"}, "404 Not Found")

        await writer.drain()
        await writer.aclose()

    except Exception as e:
        print("Error:", repr(e))
        send_response(writer, _err_payload(e), "500 Internal Server Error")
        try:
            await writer.aclose()
        except:
            pass


# ---------- Servidor ----------
async def start_server():
    print("Servidor escuchando en 0.0.0.0:80")
    server = await asyncio.start_server(handle_client, "0.0.0.0", 80)
    await server.wait_closed()


# ---------- Loop principal ----------
async def main():
    asyncio.create_task(start_server())
    while True:
        await asyncio.sleep(1)
