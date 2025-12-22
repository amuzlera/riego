import uasyncio as asyncio
import ujson as json
from machine import Pin
from server_utils import get_remote_config, log, get_weather_multiplier, log_and_send, send_logs
from time_utils import now_local
from config import CONFIG_PATH, SERVER_URL

# ------------------ Helpers de día/tiempo ------------------
SPANISH_WD = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5,
    "domingo": 6
}


def parse_to_minutes(time_str):
    h, m = time_str.strip().split(":")
    return int(h) * 60 + int(m)


ZONE_PINS = {}
ZONES = {}


def get_pin(zone):
    pin_num = ZONES.get(zone)
    if pin_num not in ZONE_PINS:
        ZONE_PINS[pin_num] = Pin(pin_num, Pin.OUT, value=1)
    return ZONE_PINS[pin_num]


def get_programed_times():
    try:
        config = get_remote_config()
        if not config or "programed_times" not in config or "zones" not in config:
            raise Exception("Configuración remota inválida")
        return config.get("programed_times", {}), config.get("zones", {})
    except Exception as e:
        log(f"Error getting remote config: {e}")
        
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        return config.get("programed_times", {}), config.get("zones", {})


async def start_plan(plan):
    for p in plan:
        zone, duration = p
        pin = get_pin(zone)
        log_and_send(f"Riego zona {zone} iniciado")
        try:
            pin.value(0)
            await asyncio.sleep(duration * 60)
        except Exception as e:
            log_and_send(f"Error en riego zona {zone}: {e}")
        finally:
            pin.value(1)
            log_and_send(f"Riego zona {zone} finalizado")


def get_next_plan(programed_times, current_minutes):
    next_plans = []
    for p in programed_times:
        start = parse_to_minutes(p.get("start", "00:00"))
        if start > current_minutes and p.get("status") != "done":
            next_plans.append((start, p))
    if not next_plans:
        return "No hay planes programados"
    next_plan = sorted(next_plans, key=lambda x: x[0])[0][1]
    return f"{next_plan.get('start')} - Zonas: {len(next_plan.get('plan', []))}"


async def riego_scheduler_loop(poll_s=5):
    log("RUNNING riego_scheduler_loop")
    t = now_local()
    today = t[6]
    programed_times, zones = get_programed_times()
    ZONES.clear()
    ZONES.update(zones)
    first_plan_log = True
    while True:
        t = now_local()
        if today != t[6]:
            today = t[6]
            programed_times, zones = get_programed_times()
            log_and_send(f"Nuevo día {today}")
            first_plan_log = True

        if not programed_times:
            await asyncio.sleep(poll_s)
            continue

        current_minutes = t[3] * 60 + t[4]
        for program in programed_times:
            days = program.get("days", [])
            if "all" in days or today in [SPANISH_WD[d.strip().lower()] for d in days]:
                start = parse_to_minutes(program.get("start", "00:00"))

                # Condicion para iniciar el plan
                if start <= current_minutes and program.get("status") != "done":
                    if current_minutes - start > 15:
                        log_and_send(
                            f"Saltando plan iniciado a las {program.get('start')} (demasiado tarde)")
                        program["status"] = "done"
                        continue

                    asyncio.create_task(start_plan(program.get("plan", [])))
                    program["status"] = "done"
                    first_plan_log = True

        if first_plan_log:
            next_plan = get_next_plan(programed_times, current_minutes)
            log_and_send(f"Proximos riegos: {next_plan}")
            first_plan_log = False

        await asyncio.sleep(poll_s)