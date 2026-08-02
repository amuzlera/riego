import time

import network
import uasyncio as asyncio
import ubinascii

import config
from endpoints import actions, cat, excecute, firmware, ls, rm, tail, upload
from server_utils import _err_payload, log, log_exception, parse_headers, reset, send_response


def connect_wifi(ssid, password, ip, netmask, gateway, dns):
    sta_if = network.WLAN(network.STA_IF)
    log("WiFi init: active={}, connected={}".format(sta_if.active(), sta_if.isconnected()))
    try:
        log("WiFi init: status={}".format(sta_if.status()))
    except Exception:
        pass

    try:
        if sta_if.isconnected():
            sta_if.ifconfig((ip, netmask, gateway, dns))
            log("Conectado a WiFi. IP: {}".format(sta_if.ifconfig()[0]))
            return sta_if
    except Exception:
        pass

    try:
        sta_if.disconnect()
    except Exception:
        pass

    try:
        sta_if.active(False)
        time.sleep(0.5)
    except Exception:
        pass

    sta_if.active(True)
    time.sleep(0.5)

    log("WiFi connect: ssid={}".format(ssid))
    sta_if.connect(ssid, password)

    for i in range(200):
        if sta_if.isconnected():
            break
        if i in (0, 10, 20, 50, 100, 150, 199):
            try:
                log("WiFi waiting: connected={}, status={}".format(sta_if.isconnected(), sta_if.status()))
            except Exception:
                log("WiFi waiting: connected={}".format(sta_if.isconnected()))
        time.sleep(0.1)

    try:
        log("WiFi final: connected={}, status={}".format(sta_if.isconnected(), sta_if.status()))
    except Exception:
        log("WiFi final: connected={}".format(sta_if.isconnected()))

    if not sta_if.isconnected():
        raise OSError("WiFi connection failed")

    sta_if.ifconfig((ip, netmask, gateway, dns))
    log("Conectado a WiFi. IP: {}".format(sta_if.ifconfig()[0]))
    log("WiFi config: {}".format(sta_if.ifconfig()))
    return sta_if


def check_auth(header):
    if not header or "Authorization" not in header:
        return False
    auth_value = header["Authorization"].split()[1]
    expected = ubinascii.b2a_base64(b"%s:%s" % (config.HTTP_USER.encode(), config.HTTP_PASS.encode())).decode().strip()
    return auth_value == expected


async def _dispatch(route, method, query, reader, writer, headers):
    if route == "/ls":
        await ls.handle(writer, query)
    elif route == "/tail":
        await tail.handle(writer, query)
    elif route == "/logs":
        await tail.handle(writer, query or "filename=log.txt")
    elif route == "/cat":
        await cat.handle(writer, query)
    elif route == "/upload" and method == "POST":
        await upload.handle(reader, writer, query, headers)
    elif route == "/firmware/status":
        await firmware.status(writer)
    elif route == "/firmware/slot":
        await firmware.slot(writer, query)
    elif route == "/rm":
        await rm.handle(writer, query)
    elif route == "/zone":
        await actions.handle(writer, query)
    elif route == "/execute":
        await excecute.handle(writer, query)
    elif route == "/reset":
        send_response(writer, {"status": "Reseteando controlador..."})
        await writer.drain()
        await asyncio.sleep(1)
        await reset()
    else:
        send_response(writer, {"error": f"Ruta {route} no encontrada"}, "404 Not Found")


async def handle_client(reader, writer):
    try:
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
        query = query.replace("-_-", "/")

        headers_raw = ""
        while True:
            line = await reader.readline()
            if line == b"\r\n":
                break
            headers_raw += line.decode()
        headers = parse_headers(headers_raw)

        if not check_auth(headers):
            resp = 'HTTP/1.1 401 Unauthorized\r\nWWW-Authenticate: Basic realm="ESP32"\r\n\r\n'
            writer.write(resp.encode())
            await writer.aclose()
            return

        log("{}, {}".format(route, query))
        try:
            await _dispatch(route, method, query, reader, writer, headers)
        except Exception as e:
            log_exception("Request handler failed for {}".format(route), e)
            send_response(writer, _err_payload(e), "500 Internal Server Error")

        await writer.drain()
        await writer.aclose()

    except Exception as e:
        log_exception("handle_client crashed", e)
        try:
            send_response(writer, _err_payload(e), "500 Internal Server Error")
            await writer.drain()
            await writer.aclose()
        except Exception:
            pass


async def start_server():
    from health import mark

    log("Servidor escuchando en 0.0.0.0:80")
    connect_wifi(
        ssid=config.WIFI_SSID,
        password=config.WIFI_PASS,
        ip="192.168.1.50",
        netmask="255.255.255.0",
        gateway="192.168.1.1",
        dns="192.168.1.1",
    )
    server = await asyncio.start_server(handle_client, "0.0.0.0", 80)
    mark("server")
    asyncio.create_task(_server_heartbeat())
    return server


async def main():
    asyncio.create_task(start_server())
    while True:
        await asyncio.sleep(1)


async def _server_heartbeat():
    from health import mark

    while True:
        mark("server")
        await asyncio.sleep(10)
