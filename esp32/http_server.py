try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    import ujson as json
except ImportError:
    import json

import config
from time_utils import format_local_time


STATUS_TEXT = {
    200: "OK",
    400: "Bad Request",
    401: "Unauthorized",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}


def _lower_headers(headers):
    normalized = {}
    for key, value in headers.items():
        normalized[key.lower()] = value
    return normalized


def _parse_headers(raw_lines):
    headers = {}
    for line in raw_lines:
        if b":" not in line:
            continue
        key, value = line.split(b":", 1)
        headers[key.decode().strip()] = value.decode().strip()
    return _lower_headers(headers)


def _parse_query_string(query_string):
    query = {}
    if not query_string:
        return query

    for part in query_string.split("&"):
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
        else:
            key, value = part, ""
        query[key] = value
    return query


def _decode_body(body):
    if not body:
        return {}
    try:
        if isinstance(body, bytes):
            body = body.decode()
        return json.loads(body)
    except Exception:
        return {}


def _coerce_state(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("1", "true", "on", "yes", "high"):
            return True
        if normalized in ("0", "false", "off", "no", "low"):
            return False
    raise ValueError("Valor de estado invalido: {}".format(value))


def _auth_ok(headers):
    expected = getattr(config, "API_KEY", "")
    if not expected:
        return True

    header_value = headers.get("x-api-key", "")
    if header_value == expected:
        return True

    authorization = headers.get("authorization", "")
    return authorization == "Bearer {}".format(expected)


async def _read_headers(reader):
    lines = []
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        lines.append(line)
    return _parse_headers(lines)


async def _read_body(reader, headers):
    content_length = headers.get("content-length")
    if not content_length:
        return b""

    try:
        size = int(content_length)
    except Exception:
        return b""

    if size <= 0:
        return b""
    return await reader.readexactly(size)


def _json_response(status_code, payload):
    body = json.dumps(payload)
    return (
        "HTTP/1.1 {} {}\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n\r\n{}"
    ).format(status_code, STATUS_TEXT.get(status_code, "OK"), len(body), body)


def _text_response(status_code, payload):
    body = payload if isinstance(payload, str) else str(payload)
    return (
        "HTTP/1.1 {} {}\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n\r\n{}"
    ).format(status_code, STATUS_TEXT.get(status_code, "OK"), len(body), body)


def _split_path(path):
    if "?" in path:
        route, query_string = path.split("?", 1)
    else:
        route, query_string = path, ""
    return route, _parse_query_string(query_string)


async def handle_client(reader, writer, device, action_registry, scheduler, program_scheduler):
    try:
        request_line = await reader.readline()
        if not request_line:
            await writer.aclose()
            return

        parts = request_line.decode().strip().split()
        if len(parts) < 2:
            writer.write(_text_response(400, "Bad request").encode())
            await writer.drain()
            await writer.aclose()
            return

        method = parts[0].upper()
        route, query = _split_path(parts[1])
        headers = await _read_headers(reader)

        if not _auth_ok(headers):
            writer.write(_json_response(401, {"ok": False, "error": "unauthorized"}).encode())
            await writer.drain()
            await writer.aclose()
            return

        body_bytes = await _read_body(reader, headers)
        body = _decode_body(body_bytes)

        if route in ("/", "/health"):
            payload = {
                "ok": True,
                "device": getattr(config, "DEVICE_NAME", "esp32"),
                "method": method,
            }
            writer.write(_json_response(200, payload).encode())

        elif route == "/status":
            payload = {
                "ok": True,
                "device": getattr(config, "DEVICE_NAME", "esp32"),
                "outputs": device.list_outputs(),
                "sensors": device.list_sensors(),
                "jobs": scheduler.list_jobs(),
                "programs": program_scheduler.list_programs(),
            }
            writer.write(_json_response(200, payload).encode())

        elif route == "/pins" and method == "GET":
            writer.write(_json_response(200, {"ok": True, "pins": device.list_outputs()}).encode())

        elif route.startswith("/pins/"):
            parts = route.strip("/").split("/")
            if len(parts) == 2 and method == "GET":
                name = parts[1]
                writer.write(_json_response(200, {"ok": True, "pin": device.get_output(name).as_dict()}).encode())
            elif len(parts) == 3 and method == "POST":
                name = parts[1]
                command = parts[2]
                if command == "run_for":
                    seconds = body.get("seconds")
                    if seconds is None:
                        seconds = body.get("duration_s")
                    if seconds is None:
                        raise ValueError("Falta 'seconds'")
                    value = body.get("value", True)
                    job = scheduler.run_for(name, seconds, value)
                    writer.write(_json_response(200, {"ok": True, "job": job}).encode())
                elif command == "on":
                    state = device.on(name)
                    writer.write(_json_response(200, {
                        "ok": True,
                        "pin": name,
                        "state": state,
                    }).encode())
                elif command == "off":
                    state = device.off(name)
                    writer.write(_json_response(200, {
                        "ok": True,
                        "pin": name,
                        "state": state,
                    }).encode())
                elif command == "toggle":
                    state = device.toggle(name)
                    writer.write(_json_response(200, {
                        "ok": True,
                        "pin": name,
                        "state": state,
                    }).encode())
                elif command == "set":
                    value = body.get("value")
                    if value is None:
                        raise ValueError("Falta 'value'")
                    state = device.set_output(name, _coerce_state(value))
                    writer.write(_json_response(200, {
                        "ok": True,
                        "pin": name,
                        "state": state,
                    }).encode())
                else:
                    raise ValueError("Comando invalido: {}".format(command))
            else:
                writer.write(_json_response(405, {"ok": False, "error": "method_not_allowed"}).encode())

        elif route == "/jobs" and method == "GET":
            writer.write(_json_response(200, {"ok": True, "jobs": scheduler.list_jobs()}).encode())

        elif route == "/environment" and method == "GET":
            sensor_name = "temp_humedad"
            sensor_payload = device.read_sensor(sensor_name)
            temperature = sensor_payload.get("temperature")
            humidity = sensor_payload.get("humidity")
            payload = {
                "ok": True,
                "device": getattr(config, "DEVICE_NAME", "esp32"),
                "time": format_local_time(getattr(config, "TZ_OFFSET_SECONDS", -10800)),
                "timezone_offset_seconds": int(getattr(config, "TZ_OFFSET_SECONDS", -10800)),
                "sensor": sensor_payload,
                "temperature": temperature,
                "humidity": humidity,
            }
            writer.write(_json_response(200, payload).encode())

        elif route == "/programs" and method == "GET":
            writer.write(_json_response(200, {
                "ok": True,
                "programs": program_scheduler.list_programs(),
                "active": program_scheduler.active_programs(),
            }).encode())

        elif route == "/programs" and method == "POST":
            try:
                program = program_scheduler.create_program(body)
                writer.write(_json_response(200, {"ok": True, "program": program}).encode())
            except ValueError as exc:
                writer.write(_json_response(400, {"ok": False, "error": str(exc)}).encode())

        elif route.startswith("/programs/"):
            parts = route.strip("/").split("/")
            if len(parts) == 2 and method == "PUT":
                try:
                    program_id = int(parts[1])
                    program = program_scheduler.update_program(program_id, body)
                    writer.write(_json_response(200, {"ok": True, "program": program}).encode())
                except ValueError as exc:
                    writer.write(_json_response(400, {"ok": False, "error": str(exc)}).encode())
                except KeyError:
                    writer.write(_json_response(404, {"ok": False, "error": "program_not_found"}).encode())
            elif len(parts) == 2 and method == "DELETE":
                try:
                    program_id = int(parts[1])
                    program_scheduler.delete_program(program_id)
                    writer.write(_json_response(200, {"ok": True}).encode())
                except KeyError:
                    writer.write(_json_response(404, {"ok": False, "error": "program_not_found"}).encode())
            else:
                writer.write(_json_response(405, {"ok": False, "error": "method_not_allowed"}).encode())

        elif route == "/sensors" and method == "GET":
            writer.write(_json_response(200, {"ok": True, "sensors": device.read_all_sensors()}).encode())

        elif route.startswith("/sensors/") and method == "GET":
            parts = route.strip("/").split("/")
            if len(parts) == 2:
                name = parts[1]
                writer.write(_json_response(200, {"ok": True, "sensor": device.read_sensor(name)}).encode())
            else:
                writer.write(_json_response(404, {"ok": False, "error": "not_found"}).encode())

        elif route == "/actions" and method == "GET":
            writer.write(_json_response(200, {"ok": True, "actions": list(action_registry.keys())}).encode())

        elif route.startswith("/actions/") and method == "POST":
            parts = route.strip("/").split("/")
            if len(parts) != 2:
                writer.write(_json_response(404, {"ok": False, "error": "not_found"}).encode())
            else:
                name = parts[1]
                handler = action_registry.get(name)
                if handler is None:
                    writer.write(_json_response(404, {"ok": False, "error": "action_not_found"}).encode())
                else:
                    result = handler(body)
                    writer.write(_json_response(200, result).encode())

        elif route == "/execute" and method == "POST":
            name = body.get("name")
            args = body.get("args") or {}
            handler = action_registry.get(name)
            if handler is None:
                writer.write(_json_response(404, {"ok": False, "error": "action_not_found"}).encode())
            else:
                result = handler(args)
                writer.write(_json_response(200, result).encode())

        else:
            writer.write(_json_response(404, {"ok": False, "error": "not_found"}).encode())

        await writer.drain()
        await writer.aclose()

    except Exception as exc:
        try:
            writer.write(_json_response(500, {"ok": False, "error": repr(exc)}).encode())
            await writer.drain()
        except Exception:
            pass
        try:
            await writer.aclose()
        except Exception:
            pass


async def start_server(device, action_registry, scheduler, program_scheduler):
    return await asyncio.start_server(
        lambda reader, writer: handle_client(reader, writer, device, action_registry, scheduler, program_scheduler),
        "0.0.0.0",
        getattr(config, "HTTP_PORT", 80),
    )
