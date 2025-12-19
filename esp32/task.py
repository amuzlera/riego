import uasyncio as asyncio
import ujson as json
from machine import Pin
from server_utils import log, get_weather_multiplier, log_and_send, send_logs_batch
from time_utils import now_local
from boot import CONFIG_PATH

# ------------------ Helpers de día/tiempo ------------------
SPANISH_WD = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5,
    "domingo": 6
}


# ------------------ Loop principal ------------------

def parse_period_to_minutes(period_str):
    start, end = period_str.split("-")
    sh, sm = start.split(":")
    eh, em = end.split(":")
    return int(sh) * 60 + int(sm), int(eh) * 60 + int(em)


def create_today_plan(today):
    try:
        with open(CONFIG_PATH, "r") as f:
            raw = json.load(f)
        zones = raw.get("zones", {})
        today_plans = []
        for zone, plan in raw.get("programed_times", {}).items():
            days = [SPANISH_WD[d.strip().lower()] for d in plan.get(
                "days", [])] if isinstance(plan.get("days"), list) else []
            if today in days or "all" in plan.get("days", []):
                periods = [parse_period_to_minutes(
                    p) for p in plan.get("periods", [])]
                for p in periods:
                    today_plans.append({"zone": zone, "period": p})

        return sorted(today_plans, key=lambda x: x["period"][0]), zones
    except Exception as e:
        log(f"Config: no se pudo leer: {e}")
        return {}, {}

ZONE_PINS = {}


def get_pin(pin_num):
    if pin_num not in ZONE_PINS:
        ZONE_PINS[pin_num] = Pin(pin_num, Pin.OUT, value=1)
    return ZONE_PINS[pin_num]

async def async_job(zone_pin_num, zone, duration):
    pin = get_pin(zone_pin_num)
    log_and_send(f"Riego zona {zone} iniciado")
    try:
        pin.value(0)
        await asyncio.sleep(duration * 60)
    except Exception as e:
        log_and_send(f"Error en riego zona {zone}: {e}")
    finally:
        pin.value(1)
        log_and_send(f"Riego zona {zone} finalizado")



async def riego_scheduler_loop(poll_s=5):
    log("RUNNING riego_scheduler_loop")
    t = now_local()
    today = t[6]
    programed_times, zones = create_today_plan(today)
    first_plan_log = True
    while True:
        t = now_local()
        if today != t[6]:
            today = t[6]
            programed_times, zones = create_today_plan(today)
            log_and_send(f"Nuevo día {today}")
            first_plan_log = True
  #          send_logs_batch([f"Plan hoy: zona={p['zone']} {p['period'][0]}-{p['period'][1]}" for p in programed_times])

        if not programed_times:
            await asyncio.sleep(poll_s)
            continue

        current_minutes = t[3] * 60 + t[4]
        next_start = programed_times[0]["period"][0]
        next_end = programed_times[0]["period"][1]

        if abs(current_minutes - next_start) < 3 or first_plan_log:
            delta = max(0, next_start - current_minutes)
            log_and_send(f"next_start in {delta} minutes")
            first_plan_log = False

        if next_start <= current_minutes:

            if current_minutes >= next_end:
                log_and_send(f"Periodo {next_start}-{next_end} ya pasó, descartando")
                programed_times.pop(0)
                first_plan_log = True
                continue

            plan = programed_times.pop(0)
            zone_pin_num = zones.get(plan["zone"])

            log_and_send(
                f"Regando zona {plan['zone']} (pin {zone_pin_num}) de {plan['period'][0]} a {plan['period'][1]}")
            duration = plan["period"][1] - plan["period"][0]
            asyncio.create_task(async_job(zone_pin_num, plan['zone'], duration))

        await asyncio.sleep(poll_s)
