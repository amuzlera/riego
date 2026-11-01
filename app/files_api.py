"""Small proxy to the ESP32 maintenance service; uses the device API_KEY."""
import hashlib
import re

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .storage import store

router = APIRouter(prefix='/devices/{name}')
MAX_FILE_BYTES = 65536


class FileContent(BaseModel):
    content: str = Field(max_length=MAX_FILE_BYTES)


def _filename(filename):
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}', filename) or '..' in filename:
        raise HTTPException(400, 'invalid_filename')
    return filename


async def _request(name, method, path, content=None):
    device = store.get_device(name)
    if not device:
        raise HTTPException(404, 'device_not_found')
    if not device.get('enabled', True):
        raise HTTPException(409, 'device_disabled')
    base = httpx.URL(device['base_url']).copy_with(port=81, path=path, query=None, fragment=None)
    headers = {}
    if device.get('api_key'):
        headers['X-API-Key'] = device['api_key']
    if content is not None:
        headers['Content-Type'] = 'application/octet-stream'
        headers['X-Content-SHA256'] = hashlib.sha256(content).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            response = await client.request(method, base, headers=headers, content=content)
    except httpx.RequestError:
        raise HTTPException(502, 'maintenance_unreachable')
    if response.is_error:
        try:
            error = response.json().get('error', 'maintenance_error')
        except (ValueError, AttributeError):
            error = 'maintenance_error'
        raise HTTPException(response.status_code, error)
    return response


@router.get('/files')
async def list_files(name: str):
    return (await _request(name, 'GET', '/files')).json()


@router.get('/files/{filename}')
async def read_file(name: str, filename: str):
    response = await _request(name, 'GET', '/files/' + _filename(filename))
    if hashlib.sha256(response.content).hexdigest() != response.headers.get('X-Content-SHA256'):
        raise HTTPException(502, 'file_checksum_mismatch')
    try:
        content = response.content.decode('utf-8')
    except UnicodeError:
        raise HTTPException(422, 'file_is_not_utf8_text')
    return {'ok': True, 'filename': filename, 'content': content}


@router.put('/files/{filename}')
async def write_file(name: str, filename: str, payload: FileContent):
    content = payload.content.encode('utf-8')
    if not content or len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, 'empty_or_large_file')
    return (await _request(name, 'PUT', '/files/' + _filename(filename), content)).json()


@router.post('/maintenance/reset')
async def restart(name: str):
    return (await _request(name, 'POST', '/reset', b'')).json()
