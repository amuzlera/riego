import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'esp32' / 'recovery.py'
with patch.dict(sys.modules, {'network': types.ModuleType('network'), 'machine': types.ModuleType('machine')}):
    spec = importlib.util.spec_from_file_location('recovery', SOURCE)
    recovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def install(self, data, name='controller.py'):
        return recovery.install(name, data, hashlib.sha256(data).hexdigest())

    def test_atomic_replacement_and_backup(self):
        Path('controller.py').write_bytes(b'old = 1\n')
        self.install(b'new = 2\n')
        self.assertEqual(Path('controller.py').read_bytes(), b'new = 2\n')
        self.assertEqual(Path('controller.py.bak').read_bytes(), b'old = 1\n')
        self.assertFalse(Path('controller.py.tmp').exists())

    def test_bad_upload_preserves_original(self):
        Path('controller.py').write_bytes(b'old = 1\n')
        for content in (b'def broken(', b'\xff'):
            with self.assertRaises(recovery.RequestError):
                self.install(content)
        with self.assertRaises(recovery.RequestError):
            recovery.install('controller.py', b'x=1', 'wrong')
        self.assertEqual(Path('controller.py').read_bytes(), b'old = 1\n')

    def test_failed_rename_preserves_original(self):
        Path('controller.py').write_bytes(b'old = 1\n')
        with patch.object(recovery.os, 'rename', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                self.install(b'new = 2\n')
        self.assertEqual(Path('controller.py').read_bytes(), b'old = 1\n')
        self.assertFalse(Path('controller.py.tmp').exists())

    def test_protection_paths_and_live_state(self):
        for name in ('../config.py', '/config.py', 'x/y.py', 'config.py%00', 'main.py', 'boot.py', 'recovery.py', 'recovery_config.json', 'jobs.json', 'programs.json', 'socket.py', 'machine.mpy', 'json.py'):
            with self.assertRaises(recovery.RequestError, msg=name):
                self.install(b'x=1', name)

    def test_json_validation(self):
        with self.assertRaises(recovery.RequestError):
            self.install(b'{invalid', 'example.json')
        self.install(b'{"valid":true}', 'example.json')

    def request(self, raw, key='secret'):
        client, server = socket.socketpair()
        try:
            client.sendall(raw)
            client.shutdown(socket.SHUT_WR)
            result = recovery.request(server, key)
            server.shutdown(socket.SHUT_WR)
            return result, client.recv(100000)
        finally:
            client.close()
            server.close()

    def test_authenticated_read_and_health_after_controller_failure(self):
        Path('config.py').write_text('TZ_OFFSET_SECONDS = -10800\n')
        recovery.STATE.update(controller='failed', error='test import error')
        _, response = self.request(b'GET /health HTTP/1.1\r\nX-API-Key: secret\r\n\r\n')
        self.assertIn(b'failed', response)
        _, response = self.request(b'GET /files/config.py HTTP/1.1\r\nX-API-Key: secret\r\n\r\n')
        self.assertIn(b'TZ_OFFSET_SECONDS = -10800', response)
        self.assertIn(b'X-Content-SHA256:', response)
        with self.assertRaises(recovery.RequestError) as exc:
            self.request(b'GET /files/config.py HTTP/1.1\r\n\r\n')
        self.assertEqual(exc.exception.status, 401)

    def test_interrupted_upload_does_not_touch_original(self):
        Path('controller.py').write_bytes(b'old=1\n')
        with self.assertRaises(recovery.RequestError):
            self.request(b'PUT /files/controller.py HTTP/1.1\r\nX-API-Key: secret\r\nContent-Length: 20\r\n\r\nx=1')
        self.assertEqual(Path('controller.py').read_bytes(), b'old=1\n')

    def test_unicode_content_length(self):
        Path('test.py').write_text('label="Riego ma\u00f1ana"\n')
        _, response = self.request(b'GET /files/test.py HTTP/1.1\r\nX-API-Key: secret\r\n\r\n')
        headers, body = response.split(b'\r\n\r\n')
        self.assertIn(('Content-Length: %s' % len(body)).encode(), headers)

    def test_empty_key_disables_auth_like_controller(self):
        _, response = self.request(b'GET /health HTTP/1.1\r\n\r\n', key='')
        self.assertTrue(response.startswith(b'HTTP/1.1 200'))


if __name__ == '__main__':
    unittest.main()
