import uasyncio as asyncio
import network
import config
from server_utils import log
from server import start_server
from task import riego_scheduler_loop
from time_utils import sync_time_from_ntp


async def connect_wifi():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        log("Conectando a WiFi...")
        sta_if.active(True)
        sta_if.connect(config.WIFI_SSID, config.WIFI_PASS)

        while not sta_if.isconnected():
            await asyncio.sleep(0.5)

    ip = sta_if.ifconfig()[0]
    log(f"Conectado a WiFi. IP: {ip}")
    return ip


async def main():
    log("Iniciando sistema")

    # --- WiFi ---
    await connect_wifi()

    # --- NTP Sync ---
    log("Sincronizando hora con NTP...")
    t = sync_time_from_ntp()
    log(f"Hora actual: {t}")

    # --- Tasks ---
    asyncio.create_task(start_server())
    asyncio.create_task(riego_scheduler_loop(
        "config_riego.json", poll_s=1, reload_s=3))

    while True:
        await asyncio.sleep(1)


print("RUNNING MAIN")
asyncio.run(main())


'''
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/ls.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/cat.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/upload.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/rm.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/__init__.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/server.py :
mpremote connect /dev/ttyUSB0 fs cp esp32/main.py :
'''
