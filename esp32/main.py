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


async def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    static_ifconfig = getattr(config, "STATIC_IFCONFIG", None)
    if static_ifconfig:
        wlan.ifconfig(static_ifconfig)

    if not wlan.isconnected():
        ssid = getattr(config, "WIFI_SSID", "")
        password = getattr(config, "WIFI_PASSWORD", "")
        if not ssid:
            raise RuntimeError("Falta WIFI_SSID en config.py")

        wlan.connect(ssid, password)

        timeout_seconds = int(getattr(config, "WIFI_TIMEOUT_SECONDS", 15))
        for _ in range(timeout_seconds * 10):
            if wlan.isconnected():
                break
            await asyncio.sleep(0.1)

    if not wlan.isconnected():
        raise RuntimeError("No se pudo conectar al WiFi")

    return wlan


async def main():
    device = Device(getattr(config, "PINS", {}), getattr(config, "SENSORS", {}))
    actions = build_action_registry(device)
    scheduler = JobScheduler(device)
    program_scheduler = WeeklyProgramScheduler(
        device,
        storage_path="programs.json",
        tz_offset_seconds=int(getattr(config, "TZ_OFFSET_SECONDS", 10800)),
    )

    wlan = await connect_wifi()
    ip = wlan.ifconfig()[0]
    print("Device:", getattr(config, "DEVICE_NAME", "esp32"))
    print("IP:", ip)

    print("Syncing time from NTP...")
    sync_time_from_ntp(
        host=getattr(config, "NTP_HOST", "pool.ntp.org"),
        tz_offset_seconds=int(getattr(config, "TZ_OFFSET_SECONDS", 10800)),
    )

    scheduler.restore_pending_jobs()
    program_scheduler.reconcile()

    server = await start_server(device, actions, scheduler, program_scheduler)
    print("HTTP listening on port", getattr(config, "HTTP_PORT", 80))

    asyncio.create_task(scheduler.loop(poll_s=1))
    asyncio.create_task(program_scheduler.loop(poll_s=30))

    try:
        while True:
            await asyncio.sleep(1)
    finally:
        server.close()
        await server.wait_closed()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
