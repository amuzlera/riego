try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import network

import config
from actions import build_action_registry
from hardware import Device
from http_server import start_server
from scheduler import JobScheduler
from programs import WeeklyProgramScheduler
from time_utils import sync_time_from_ntp


async def main():
    device = Device(getattr(config, "PINS", {}), getattr(config, "SENSORS", {}))
    actions = build_action_registry(device)
    scheduler = JobScheduler(device)
    program_scheduler = WeeklyProgramScheduler(
        device,
        storage_path="programs.json",
        tz_offset_seconds=int(getattr(config, "TZ_OFFSET_SECONDS", -10800)),
    )

    wlan = network.WLAN(network.STA_IF)
    ip = wlan.ifconfig()[0]
    print("Device:", getattr(config, "DEVICE_NAME", "esp32"))
    print("IP:", ip)

    print("Syncing time from NTP...")
    sync_time_from_ntp(
        host=getattr(config, "NTP_HOST", "pool.ntp.org"),
        tz_offset_seconds=int(getattr(config, "TZ_OFFSET_SECONDS", -10800)),
    )

    scheduler.restore_pending_jobs()
    program_scheduler.reconcile()

    server = await start_server(device, actions, scheduler, program_scheduler)
    print("HTTP listening on port", getattr(config, "HTTP_PORT", 80))

    tasks = [
        asyncio.create_task(scheduler.loop(poll_s=1)),
        asyncio.create_task(program_scheduler.loop(poll_s=30)),
    ]

    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        device.all_off()
        server.close()
        await server.wait_closed()
