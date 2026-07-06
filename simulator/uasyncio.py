from __future__ import annotations

import asyncio as _asyncio

CancelledError = _asyncio.CancelledError
TimeoutError = _asyncio.TimeoutError
Event = _asyncio.Event
Lock = _asyncio.Lock
Queue = _asyncio.Queue


async def sleep(seconds):
    return await _asyncio.sleep(seconds)


async def sleep_ms(milliseconds):
    return await _asyncio.sleep(milliseconds / 1000.0)


def create_task(coro):
    return _asyncio.create_task(coro)


def gather(*args, **kwargs):
    return _asyncio.gather(*args, **kwargs)


def run(coro):
    return _asyncio.run(coro)


async def start_server(client_connected_cb, host, port, *args, **kwargs):
    async def _wrapped(reader, writer):
        await client_connected_cb(reader, _WriterAdapter(writer))

    return await _asyncio.start_server(_wrapped, host, port, *args, **kwargs)


class _WriterAdapter:
    def __init__(self, writer):
        self._writer = writer

    def write(self, data):
        return self._writer.write(data)

    async def drain(self):
        return await self._writer.drain()

    async def aclose(self):
        self._writer.close()
        try:
            await self._writer.wait_closed()
        except Exception:
            pass

    def close(self):
        self._writer.close()

    def __getattr__(self, name):
        return getattr(self._writer, name)
