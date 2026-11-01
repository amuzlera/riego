import hashlib
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import files_api

AsyncClient = httpx.AsyncClient


class FileProxyTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(files_api.router)
        self.client = TestClient(app)
        self.requests = []
        self.device_patch = patch.object(files_api.store, 'get_device', return_value={
            'name': 'test', 'base_url': 'http://192.168.1.50', 'api_key': '', 'enabled': True,
        })
        self.device_patch.start()
        self.addCleanup(self.device_patch.stop)

    def transport(self, handler):
        def record(request):
            self.requests.append(request)
            return handler(request)
        return patch.object(files_api.httpx, 'AsyncClient', side_effect=lambda **kwargs: AsyncClient(
            **kwargs, transport=httpx.MockTransport(record)))

    def test_read_checksum_and_no_extra_credentials(self):
        content = b'zone = 6\n'
        with self.transport(lambda _: httpx.Response(200, content=content, headers={
            'X-Content-SHA256': hashlib.sha256(content).hexdigest(),
        })):
            response = self.client.get('/devices/test/files/controller.py')
        self.assertEqual(response.json()['content'], content.decode())
        self.assertEqual(self.requests[0].url.port, 81)
        self.assertNotIn('x-api-key', self.requests[0].headers)

    def test_write_utf8_checksum_and_shared_credential(self):
        files_api.store.get_device.return_value['api_key'] = 'shared'
        content = 'label = "mañana"\n'
        with self.transport(lambda _: httpx.Response(200, json={'ok': True})):
            response = self.client.put('/devices/test/files/controller.py', json={'content': content})
        self.assertEqual(response.status_code, 200)
        req = self.requests[0]
        self.assertEqual(req.content, content.encode())
        self.assertEqual(req.headers['x-content-sha256'], hashlib.sha256(content.encode()).hexdigest())
        self.assertEqual(req.headers['x-api-key'], 'shared')

    def test_esp32_error_reaches_ui(self):
        with self.transport(lambda _: httpx.Response(400, json={'error': 'invalid_python'})):
            response = self.client.put('/devices/test/files/controller.py', json={'content': 'bad'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], 'invalid_python')

    def test_unicode_byte_limit_prevents_upload(self):
        response = self.client.put('/devices/test/files/controller.py', json={'content': 'á' * 40000})
        self.assertEqual(response.status_code, 413)
        self.assertFalse(self.requests)

    def test_corrupt_download_is_rejected(self):
        with self.transport(lambda _: httpx.Response(200, content=b'changed', headers={'X-Content-SHA256': 'wrong'})):
            response = self.client.get('/devices/test/files/controller.py')
        self.assertEqual(response.status_code, 502)

    def test_disabled_device_not_contacted(self):
        files_api.store.get_device.return_value['enabled'] = False
        response = self.client.get('/devices/test/files')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(self.requests)


if __name__ == '__main__':
    unittest.main()
