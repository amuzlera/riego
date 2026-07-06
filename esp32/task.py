import gc

import uasyncio as asyncio
import ujson as json
from machine import Pin

from config import CONFIG_PATH
from server_utils import log, log_and_send, log_exception
from time_utils import now_local

SPANISH_WD = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "miércoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "sábado": 5,
    "domingo": 6,
}

ZONE_PINS = {}
ZONES = {}


def parse_to_minutes(time_str):
    h, m = time_str.strip().split(":")
    return int(h) * 60 + int(m)


def _normalize_days(days):
    if days is None:
        return []
    if isinstance(days, str):
        return [days]
    if isinstance(days, list):
        return [d for d in days if isinstance(d, str)]
    return []


def _duration_minutes(start_str, end_str):
    start = parse_to_minutes(start_str)
    end = parse_to_minutes(end_str)
    duration = end - start
    if duration <= 0:
        duration += 24 * 60
    return duration


def _normalize_program_entry(program):
    if not isinstance(program, dict):
        return None

    start = program.get("start")
    plan = program.get("plan")
    days = _normalize_days(program.get("days", []))

    if start and isinstance(plan, list):
        return {
            "start": start,
            "days": days,
            "plan": [item for item in plan if isinstance(item, (list, tuple)) and len(item) >= 2],
        }

    periods = program.get("periods", [])
    zone = program.get("zone")
    if not zone or not isinstance(periods, list):
        return None

    normalized = []
    for period in periods:
        if not isinstance(period, str) or "-" not in period:
            continue
        start_str, end_str = period.split("-", 1)
        start_str = start_str.strip()
        end_str = end_str.strip()
        if not start_str or not end_str:
            continue
        normalized.append(
            {
                "start": start_str,
                "days": days,
                "plan": [[zone, _duration_minutes(start_str, end_str)]],
            }
        )
    return normalized


def normalize_programed_times(programed_times):
    normalized = []
    if isinstance(programed_times, dict):
        for zone, program in programed_times.items():
            if not isinstance(program, dict):
                continue
            periods = program.get("periods", [])
            days = program.get("days", [])
            if not isinstance(periods, list):
                continue
            for period in periods:
                if not isinstance(period, str) or "-" not in period:
                    continue
                start_str, end_str = period.split("-", 1)
                start_str = start_str.strip()
                end_str = end_str.strip()
                if not start_str or not end_str:
                    continue
                normalized.append(
                    {
                        "start": start_str,
                        "days": _normalize_days(days),
                        "plan": [[zone, _duration_minutes(start_str, end_str)]],
                    }
                )
        return normalized

    if isinstance(programed_times, list):
        for program in programed_times:
            if isinstance(program, dict):
                normalized_program = _normalize_program_entry(program)
                if normalized_program:
                    if isinstance(normalized_program, list):
                        normalized.extend(normalized_program)
                    else:
                        normalized.append(normalized_program)
        return normalized

    return normalized


def get_pin(zone):
    pin_num = ZONES.get(zone)
    if pin_num not in ZONE_PINS:
        ZONE_PINS[pin_num] = Pin(pin_num, Pin.OUT, value=1)
    return ZONE_PINS[pin_num]


def _load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error reading config: {e}")
        return {}


def get_programed_times():
    config = _load_config()
    if not config or "programed_times" not in config or "zones" not in config:
        return [], {}
    return normalize_programed_times(config.get("programed_times", [])), config.get("zones", {})


async def start_plan(plan):
    for zone, duration in plan:
        pin = get_pin(zone)
        log_and_send(f"Riego zona {zone} iniciado")
        try:
            pin.value(0)
            await asyncio.sleep(duration * 60)
        except Exception as e:
            log_exception(f"Error en riego zona {zone}", e)
        finally:
            try:
                pin.value(1)
            except Exception as e:
                log_exception(f"Error apagando zona {zone}", e)
            log_and_send(f"Riego zona {zone} finalizado")


def get_next_plan(programed_times, current_minutes):
    next_plans = []
    for p in programed_times:
        start = parse_to_minutes(p.get("start", "00:00"))
        if start > current_minutes:
            next_plans.append((start, p))
    if not next_plans:
        return "No hay planes programados"
    next_plan = sorted(next_plans, key=lambda x: x[0])[0][1]
    return f"{next_plan.get('start')} - Zonas: {len(next_plan.get('plan', []))}"


def log_temp_and_humidity():
    try:
        import dht
        from machine import Pin as MachinePin

        sensor = dht.DHT11(MachinePin(4))
        sensor.measure()
        temp = sensor.temperature()
        humidity = sensor.humidity()
        log_and_send(f"Temperatura: {temp}, Humedad: {humidity}")
    except Exception as e:
        log(f"Error leyendo DHT: {e}")


def _plan_key(program):
    plan = program.get("plan", [])
    days = program.get("days", [])
    return "{}|{}|{}".format(program.get("start", "00:00"), ",".join(days), repr(plan))


async def riego_scheduler_loop(poll_s=5):
    log("RUNNING riego_scheduler_loop")
    today = None
    executed_today = set()
    programed_times, zones = get_programed_times()
    ZONES.clear()
    ZONES.update(zones)

    while True:
        try:
            t = now_local()
            if today != t[6]:
                today = t[6]
                executed_today = set()
                programed_times, zones = get_programed_times()
                ZONES.clear()
                ZONES.update(zones)
                log_and_send(f"Nuevo día {today}")

            if not programed_times:
                await asyncio.sleep(poll_s)
                continue

            current_minutes = t[3] * 60 + t[4]
            for program in programed_times:
                days = program.get("days", [])
                if "all" not in days and today not in [SPANISH_WD.get(d.strip().lower()) for d in days]:
                    continue

                start = parse_to_minutes(program.get("start", "00:00"))
                key = _plan_key(program)
                if start <= current_minutes and key not in executed_today:
                    if current_minutes - start > 15:
                        log_and_send(
                            "Saltando plan iniciado a las {} (demasiado tarde)".format(program.get("start"))
                        )
                        executed_today.add(key)
                        continue

                    executed_today.add(key)
                    asyncio.create_task(start_plan(program.get("plan", [])))

            next_plan = get_next_plan(programed_times, current_minutes)
            log(f"Proximos riegos: {next_plan}")
            log_temp_and_humidity()
            gc.collect()
            await asyncio.sleep(poll_s)
        except Exception as e:
            log_exception("riego_scheduler_loop failed", e)
            gc.collect()
            await asyncio.sleep(poll_s)
