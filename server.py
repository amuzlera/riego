import uasyncio as asyncio
import network
import socket
import os
import ure
import ubinascii
import config
import ujson as json

# ---------- Conexión WiFi ----------
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect(config.WIFI_SSID, config.WIFI_PASS)

while not sta_if.isconnected():
    pass
print("Conectado a WiFi:", sta_if.ifconfig())

# ---------- Autenticación básica ----------
def check_auth(header):
    if not header or "Authorization" not in header:
        return False
    auth_value = header["Authorization"].split()[1]
    expected = ubinascii.b2a_base64(b"%s:%s" % (config.HTTP_USER.encode(), config.HTTP_PASS.encode())).decode().strip()
    return auth_value == expected

# ---------- Helpers ----------
def send_response(writer, data, status="200 OK", content_type="application/json"):
    if isinstance(data, dict):
        data = json.dumps(data)
    resp = "HTTP/1.1 {}\r\nContent-Type: {}\r\n\r\n{}".format(status, content_type, data)
    writer.write(resp.encode())

def parse_headers(req):
    headers = {}
    lines = req.split("\r\n")
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
    return headers

# ---------- Manejador de cada cliente ----------
async def handle_client(reader, writer):
    try:
        req = await reader.read(2048)
        req = req.decode()
        if not req:
            await writer.aclose()
            return

        headers = parse_headers(req)
        if not check_auth(headers):
            resp = 'HTTP/1.1 401 Unauthorized\r\nWWW-Authenticate: Basic realm="ESP32"\r\n\r\n'
            writer.write(resp.encode())
            await writer.aclose()
            return

        # Parsear método y ruta
        method, path, _ = req.split(" ", 2)
        route = path.split("?")[0]
        query = path.split("?")[1] if "?" in path else ""

        # Endpoints
        if route == "/ls":
            files = os.listdir()
            send_response(writer, {"files": files})

        elif route == "/cat":
            file_match = ure.search("file=([^&]+)", query)
            if file_match:
                filename = file_match.group(1)
                if filename in os.listdir():
                    with open(filename) as f:
                        send_response(writer, {"file": filename, "content": f.read()})
                else:
                    send_response(writer, {"error": "Archivo no encontrado"}, "404 Not Found")
            else:
                send_response(writer, {"error": "Falta parametro file"}, "400 Bad Request")

        elif route == "/upload" and method == "POST":
            body = req.split("\r\n\r\n", 1)[1]
            file_match = ure.search("file=([^&]+)", query)
            if file_match:
                filename = file_match.group(1)
                with open(filename, "w") as f:
                    f.write(body)
                send_response(writer, {"status": "Archivo guardado", "file": filename})
            else:
                send_response(writer, {"error": "Falta parametro file"}, "400 Bad Request")

        elif route == "/rm":
            file_match = ure.search("file=([^&]+)", query)
            if file_match:
                filename = file_match.group(1)
                if filename in os.listdir():
                    os.remove(filename)
                    send_response(writer, {"status": "Archivo eliminado", "file": filename})
                else:
                    send_response(writer, {"error": "Archivo no encontrado"}, "404 Not Found")
            else:
                send_response(writer, {"error": "Falta parametro file"}, "400 Bad Request")
        else:
            send_response(writer, {"error": "Ruta no encontrada"}, "404 Not Found")

        await writer.drain()
        await writer.aclose()

    except Exception as e:
        print("Error manejando cliente:", e)
        try:
            await writer.aclose()
        except:
            pass

# ---------- Servidor ----------
async def start_server():
    print("Servidor escuchando en 0.0.0.0:80")
    server = await asyncio.start_server(handle_client, "0.0.0.0", 80)
    # await server.wait_closed()

# ---------- Loop principal ----------
async def main():
    asyncio.create_task(start_server())
    # Aquí podés agregar tu loop de riego también:
    # asyncio.create_task(riego_loop())
    while True:
        await asyncio.sleep(1)

# Ejecutar todo
# asyncio.run(main())
