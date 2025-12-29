import ujson as json
from boot import CONFIG_PATH
import uasyncio as asyncio
from server_utils import send_response, parse_query, log, send_logs
from machine import Pin




def load_zones_map():
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        return cfg.get("zones", {})
    except Exception as e:
        log(f"No se pudo leer {CONFIG_PATH}: {e}")
        return {}

_PINS = {}

async def change_zone(zone: str, action: str = "on", duration: int | None = None):
    action = action.lower()

    if zone.isdigit():
        zone = f"zona{zone}"

    zones_map = load_zones_map()
    if zone not in zones_map:
        raise ValueError(f"Zona '{zone}' no encontrada")

    try:
        pin_num = int(zones_map[zone])
    except Exception as e:
        raise ValueError(f"Pin inválido para {zone}: {e}")

    if pin_num not in _PINS:
        _PINS[pin_num] = Pin(pin_num, Pin.OUT, value=1)

    p = _PINS[pin_num]

    if action == "on":
        p.value(0)
        send_logs(f"Zona {zone} (pin {pin_num}) encendida")

        if duration and duration > 0:
            async def _delayed_off():
                await asyncio.sleep(duration)
                p.value(1)
                send_logs(f"Zona {zone} (pin {pin_num}) apagada por timeout")

            asyncio.create_task(_delayed_off())

    elif action == "off":
        p.value(1)
        send_logs(f"Zona {zone} (pin {pin_num}) apagada")

    else:
        raise ValueError(f"Action inválida: {action}")


async def handle(writer, query=""):
    """Parametros (query):
    - zone: nombre de la zona (ej. zona1) o número (entonces se busca zonaN)
    - action: 'on'|'off' (default 'on')
    - duration: segundos (opcional). Si se especifica y action='on', se apaga después.
    """
    params = parse_query(query)
    zone = params.get("zone")
    action = params.get("action")
    
    if not zone:
        send_response(writer, {"error": "Falta parametro zone"}, "400 Bad Request")
        return

    if isinstance(action, str):
        action = action.lower()
    else:
        action = "on"
    duration = params.get("duration")

    try:
        duration = int(duration) if duration is not None else None
    except Exception:
        duration = None

    try:
        asyncio.create_task(change_zone(zone, action, duration))
        send_response(writer, {"status": "ok", "zone": zone, "action": action, "duration": duration})
        return
    except Exception as e:
        send_response(writer, {"error": f"No se pudo encender {zone}: {e}"}, "500 Internal Server Error")
        return

