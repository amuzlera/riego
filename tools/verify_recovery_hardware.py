"""Opt-in acceptance test: temporarily stops controller, always attempts restore."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import urllib.error
import argparse

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'esp32/recovery_config.json').read_text())
BASE = 'http://192.168.1.50:%s' % CFG['port']
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(path, data=None, method='GET', auth=True):
    headers = {'X-API-Key': CFG['api_key']} if auth else {}
    if method == 'PUT':
        headers['X-Content-SHA256'] = hashlib.sha256(data).hexdigest()
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with OPENER.open(req, timeout=10) as r:
        return r.read()


def wait_for(state):
    for _ in range(20):
        try:
            result = json.loads(request('/health'))
            if result['controller'] == state:
                print('Recovery reachable; controller:', state, flush=True)
                return result
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError('Controller did not reach ' + state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', action='store_true', help='Test async loop failure instead of import failure')
    args = parser.parse_args()
    original = (ROOT / 'esp32/controller.py').read_bytes()
    assert request('/files/controller.py') == original, 'Unexpected remote controller; refusing test'
    programs = request('/files/programs.json')
    for path in ('/health', '/files/config.py'):
        if not CFG.get('api_key'):
            request(path, auth=False)
            continue
        try:
            request(path, auth=False)
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError('Unauthenticated request accepted')
    print('Configured authentication behavior verified', flush=True)
    for name in ('main.py', '../config.py', 'recovery.py'):
        try:
            request('/files/' + name, b'x=1', 'PUT')
        except urllib.error.HTTPError as exc:
            assert exc.code in (400, 403)
        else:
            raise AssertionError('Protected write accepted')
    print('Protected writes rejected', flush=True)
    try:
        request('/files/controller.py', b'def invalid(', 'PUT')
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    else:
        raise AssertionError('Invalid syntax accepted')
    assert request('/files/controller.py') == original
    print('Invalid Python rejected without replacing file', flush=True)
    fixture = 'runtime_failing_controller.py' if args.runtime else 'failing_controller.py'
    failing = (ROOT / 'tests/fixtures' / fixture).read_bytes()
    try:
        request('/files/controller.py', failing, 'PUT')
        request('/reset', b'', 'POST')
        result = wait_for('failed')
        assert 'recovery acceptance test' in result['error']
        assert b'TZ_OFFSET_SECONDS = -10800' in request('/files/config.py')
        assert request('/files/controller.py') == failing
        print('File reads work after controller failure', flush=True)
    finally:
        request('/files/controller.py', original, 'PUT')
        request('/reset', b'', 'POST')
        wait_for('running')
    assert request('/files/controller.py') == original
    assert request('/files/programs.json') == programs
    print('Controller restored via Wi-Fi; saved programs unchanged', flush=True)


if __name__ == '__main__':
    main()
