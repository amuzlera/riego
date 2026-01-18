import sys
import io
import uasyncio as asyncio
import network, config, machine, time
from machine import WDT
from server_utils import log, log_and_send
from server import start_server
from task import riego_scheduler_loop
from time_utils import sync_time_from_ntp

TASK_FAILURES = {}

async def safe_task(name, coro, max_retries=3, failure_threshold=5, time_window=3600):
    """Ejecuta coro con reintentos. Si falla 5+ veces en 1 hora, abandona."""
    if name not in TASK_FAILURES:
        TASK_FAILURES[name] = []
    
    while True:
        retries = 0
        while retries < max_retries:
            try:
                await coro
                return
            except Exception as e:
                retries += 1
                current_time = time.time()
                
                # Limpiar fallos viejos
                TASK_FAILURES[name] = [t for t in TASK_FAILURES[name] if current_time - t < time_window]
                TASK_FAILURES[name].append(current_time)
                
                # Circuit breaker
                if len(TASK_FAILURES[name]) >= failure_threshold:
                    output = io.StringIO()
                    sys.print_exception(e, output)
                    tb_str = output.getvalue()
                    output.close()
                    log_and_send(f"⚠️ Tarea '{name}' falló {failure_threshold} veces en 1 hora. Abandonando.")
                    log_and_send(f"Traceback:\n{tb_str}")
                    return
                
                output = io.StringIO()
                sys.print_exception(e, output)
                tb_str = output.getvalue()
                output.close()
                log_and_send(f"Tarea '{name}' falló (intento {retries}/{max_retries}): {e}")
                log_and_send(f"Traceback:\n{tb_str}")
                
                if retries < max_retries:
                    await asyncio.sleep(5)
        
        # Agotó reintentos, espera y vuelve a intentar
        log_and_send(f"Tarea '{name}' agotó {max_retries} reintentos. Esperando 30s...")
        await asyncio.sleep(30)
        
WATCHDOG_TIMEOUT = 30

wdt = WDT(timeout=WATCHDOG_TIMEOUT * 1000)  # en ms
last_ok = time.time()

def heartbeat():
    global last_ok
    last_ok = time.time()

async def healthcheck():
    global last_ok
    while True:
        await asyncio.sleep(5)
        if time.time() - last_ok > 10:
            log("Healthcheck falló, reseteando...")
            machine.reset()
        wdt.feed()

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
    heartbeat()
    return ip

async def main():
    log("Iniciando sistema")

    await connect_wifi()

    log("Sincronizando hora con NTP...")
    t = sync_time_from_ntp()
    log(f"Hora actual: {t}")
    heartbeat()
    log_and_send(f"Última razón de reseteo: {machine.reset_cause()}")
    
    asyncio.create_task(safe_task("server", start_server()))
    asyncio.create_task(safe_task("riego_scheduler", riego_scheduler_loop(poll_s=5)))
    asyncio.create_task(safe_task("healthcheck", healthcheck()))

    while True:
        heartbeat()
        await asyncio.sleep(1)

async def safe_main():
    """Wrapper para main() que reinicia todo si falla."""
    while True:
        try:
            await main()
        except Exception as e:
            output = io.StringIO()
            sys.print_exception(e, output)
            tb_str = output.getvalue()
            output.close()
            
            log_and_send(f"❌ Main falló. El watchdog reseteará en {WATCHDOG_TIMEOUT}s...")
            log_and_send(f"Traceback:\n{tb_str}")
            await asyncio.sleep(WATCHDOG_TIMEOUT + 5)
            # El watchdog se encargará del reset

print("RUNNING MAIN")
asyncio.run(safe_main())

'''
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/ls.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/cat.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/upload.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/rm.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/__init__.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/server.py :
mpremote connect /dev/ttyUSB0 fs cp esp32/server_utils.py :
mpremote connect /dev/ttyUSB0 fs cp esp32/main.py :
mpremote connect /dev/ttyUSB0 fs cp esp32/task.py :
'''