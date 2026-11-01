"""Small recovery service. Independent of config.py and controller imports."""
import os
import time
import socket
import _thread
import network
import machine
try:
    import ujson as json
except ImportError:
    import json
try:
    import uhashlib as hashlib
    import ubinascii as binascii
except ImportError:
    import hashlib
    import binascii

MAX_FILE = 65536
PROTECTED = ('boot.py', 'main.py', 'recovery.py', 'recovery_config.json')
EDITABLE_CODE = ('controller.py', 'config.py', 'hardware.py', 'actions.py',
                 'http_server.py', 'scheduler.py', 'programs.py', 'time_utils.py')
STATE = {'controller': 'starting', 'error': None}


class RequestError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


def path_name(name, writing=False):
    if (not name or len(name) > 64 or name.startswith('.') or
            any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-. ' for c in name) or
            '..' in name or name.endswith('.tmp') or (writing and name.endswith('.bak'))):
        raise RequestError(400, 'invalid_filename')
    if name == 'recovery_config.json' or (writing and name in PROTECTED):
        raise RequestError(403, 'protected_file')
    if writing and name in ('jobs.json', 'programs.json'):
        raise RequestError(409, 'use_controller_api_for_live_state')
    # Do not allow a new socket.py/json.py/etc to shadow recovery dependencies.
    if writing and name not in EDITABLE_CODE and not name.endswith(('.txt', '.json')):
        raise RequestError(403, 'unsupported_file')
    return name


def digest(data):
    return binascii.hexlify(hashlib.sha256(data).digest()).decode()


def read_file(name):
    try:
        if os.stat(name)[6] > MAX_FILE:
            raise RequestError(413, 'file_too_large')
        with open(name, 'rb') as f:
            return f.read()
    except OSError:
        raise RequestError(404, 'file_not_found')


def install(name, data, expected):
    path_name(name, True)
    if not data or len(data) > MAX_FILE:
        raise RequestError(413, 'empty_or_large_file')
    if digest(data) != expected:
        raise RequestError(400, 'sha256_mismatch')
    if name.endswith('.py'):
        try:
            compile(data.decode('utf-8'), name, 'exec')
        except Exception as exc:
            raise RequestError(400, 'invalid_python: ' + str(exc))
    if name.endswith('.json'):
        try:
            json.loads(data.decode('utf-8'))
        except Exception:
            raise RequestError(400, 'invalid_json')
    # Never remove the destination before rename: LittleFS replaces it atomically.
    # Keep a backup before replacing, without moving the original out of the way.
    tmp = name + '.tmp'
    try:
        with open(tmp, 'wb') as f:
            f.write(data)
            f.flush()
        if digest(read_file(tmp)) != expected:
            raise RequestError(500, 'verification_failed')
        try:
            old = read_file(name)
        except RequestError as exc:
            if exc.status != 404:
                raise
        else:
            with open(name + '.bak', 'wb') as f:
                f.write(old)
                f.flush()
        os.rename(tmp, name)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return {'ok': True, 'file': name, 'sha256': expected, 'restart_required': True}


def send(conn, status, data, content_type='application/json', extra=''):
    if not isinstance(data, bytes):
        data = json.dumps(data).encode()
    header = ('HTTP/1.1 %s Response\r\nContent-Type: %s\r\nContent-Length: %s\r\n'
              'Connection: close\r\n%s\r\n') % (status, content_type, len(data), extra)
    conn.sendall(header.encode())
    conn.sendall(data)


def request(conn, key):
    buf = b''
    while b'\r\n\r\n' not in buf:
        chunk = conn.recv(512)
        if not chunk:
            raise RequestError(400, 'incomplete_headers')
        buf += chunk
        if len(buf) > 4096:
            raise RequestError(413, 'headers_too_large')
    raw, body = buf.split(b'\r\n\r\n', 1)
    lines = raw.decode().split('\r\n')
    parts = lines[0].split()
    if len(parts) != 3:
        raise RequestError(400, 'invalid_request')
    method, path, _ = parts
    headers = {}
    for line in lines[1:]:
        if ':' not in line:
            raise RequestError(400, 'invalid_header')
        k, v = line.split(':', 1)
        k = k.lower()
        if k in headers:
            raise RequestError(400, 'duplicate_header')
        headers[k] = v.strip()
    if key and headers.get('x-api-key') != key and headers.get('authorization') != 'Bearer ' + key:
        raise RequestError(401, 'unauthorized')
    if 'transfer-encoding' in headers:
        raise RequestError(400, 'chunked_not_supported')
    if path == '/health' and method == 'GET':
        send(conn, 200, {'ok': True, 'controller': STATE['controller'], 'error': STATE['error']})
    elif path == '/files' and method == 'GET':
        files = []
        for name in os.listdir():
            if name != 'recovery_config.json' and not name.endswith('.tmp'):
                st = os.stat(name)
                if st[0] & 0x8000:
                    try:
                        path_name(name, True)
                        writable = True
                    except RequestError:
                        writable = False
                    files.append({'name': name, 'size': st[6], 'writable': writable})
        send(conn, 200, {'ok': True, 'files': files})
    elif path.startswith('/files/'):
        name = path_name(path[len('/files/'):], method == 'PUT')
        if method == 'GET':
            data = read_file(name)
            send(conn, 200, data, 'text/plain; charset=utf-8', 'X-Content-SHA256: %s\r\n' % digest(data))
        elif method == 'PUT':
            try:
                size = int(headers.get('content-length', '0'))
            except ValueError:
                raise RequestError(400, 'invalid_length')
            if size <= 0 or size > MAX_FILE:
                raise RequestError(413, 'empty_or_large_file')
            if len(body) > size:
                raise RequestError(400, 'invalid_length')
            while len(body) < size:
                chunk = conn.recv(min(1024, size - len(body)))
                if not chunk:
                    raise RequestError(400, 'incomplete_body')
                body += chunk
            send(conn, 200, install(name, body, headers.get('x-content-sha256', '')))
        else:
            raise RequestError(405, 'method_not_allowed')
    elif path == '/reset' and method == 'POST':
        send(conn, 200, {'ok': True, 'restarting': True})
        return True
    else:
        raise RequestError(404, 'not_found')
    return False


def serve(listener, wlan, cfg):
    while True:
        conn = None
        try:
            if not wlan.isconnected():
                try:
                    wlan.connect(cfg['wifi_ssid'], cfg['wifi_password'])
                except OSError:
                    pass
                time.sleep(2)
                continue
            conn, _ = listener.accept()
            conn.settimeout(5)
            reset = request(conn, cfg.get('api_key', ''))
            conn.close()
            conn = None
            if reset:
                time.sleep(0.3)
                machine.reset()
        except Exception as exc:
            if conn is not None:
                try:
                    send(conn, getattr(exc, 'status', 500), {'ok': False, 'error': getattr(exc, 'message', 'request_failed')})
                except Exception:
                    pass
        finally:
            if conn is not None:
                conn.close()


def run():
    with open('recovery_config.json') as f:
        cfg = json.loads(f.read())
    # Does not import editable config.py, even if it has a syntax/import error.
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if cfg.get('static_ifconfig'):
        wlan.ifconfig(tuple(cfg['static_ifconfig']))
    while not wlan.isconnected():
        try:
            wlan.connect(cfg['wifi_ssid'], cfg['wifi_password'])
        except OSError:
            pass
        for _ in range(30):
            if wlan.isconnected():
                break
            time.sleep(0.5)
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(('0.0.0.0', cfg.get('port', 81)))
    listener.listen(2)
    listener.settimeout(2)
    _thread.start_new_thread(serve, (listener, wlan, cfg))
    print('Recovery ready:', wlan.ifconfig()[0], cfg.get('port', 81))
    try:
        import controller
        # Use the controller's credential when its config can be imported.
        # The independent config only supplies a fallback for broken imports.
        import config
        cfg['api_key'] = getattr(config, 'API_KEY', '')
        try:
            import uasyncio as asyncio
        except ImportError:
            import asyncio
        STATE['controller'] = 'running'
        asyncio.run(controller.main())
        STATE['controller'] = 'stopped'
    except Exception as exc:
        STATE['controller'] = 'failed'
        STATE['error'] = repr(exc)
        print('Controller failed:', repr(exc))
    # On import/startup/runtime failure leave the physical relays OFF.
    try:
        from boot import safe_outputs
        safe_outputs()
    except Exception as exc:
        print('Safe output reset failed:', repr(exc))
    while True:
        time.sleep(1)
