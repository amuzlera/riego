# Intentional async runtime failure for the opt-in hardware acceptance test.
import uasyncio as asyncio


async def main():
    await asyncio.sleep(0.1)
    raise RuntimeError('recovery acceptance test')
