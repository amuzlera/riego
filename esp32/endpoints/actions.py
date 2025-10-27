import ujson as json
from boot import CONFIG_PATH
import uasyncio as asyncio
from server_utils import send_response, parse_query, log
from machine import Pin




def load_zones_map():
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        return cfg.get("zones", {})
    except Exception as e:
        log(f"No se pudo leer {CONFIG_PATH}: {e}")
        return {}


async def handle(writer, query=""):
    """Parametros (query):
    - zone: nombre de la zona (ej. zona1) o número (entonces se busca zonaN)
    - action: 'on'|'off' (default 'on')
    - duration: segundos (opcional). Si se especifica y action='on', se apaga después.
    """
    params = parse_query(query)
    zone = params.get("zone")
    action = params.get("action")
    if isinstance(action, str):
        action = action.lower()
    else:
        action = "on"
    duration = params.get("duration")

    if not zone:
        send_response(writer, {"error": "Falta parametro zone"}, "400 Bad Request")
        return

    # Permitir que pasen números simples (1..N) y convertir a zonaX
    if zone.isdigit():
        zone = f"zona{zone}"

    zones_map = load_zones_map()
    if zone not in zones_map:
        send_response(writer, {"error": f"Zona '{zone}' no encontrada en config"}, "404 Not Found")
        return

    try:
        pin_num = int(zones_map[zone])
    except Exception as e:
        send_response(writer, {"error": f"Pin inválido para {zone}: {e}"}, "500 Internal Server Error")
        return

    try:
        p = Pin(pin_num, Pin.OUT, value=1)
    except Exception as e:
        send_response(writer, {"error": f"No se pudo inicializar Pin {pin_num}: {e}"}, "500 Internal Server Error")
        return

    if action == "on":
        try:
            p.value(0)
            log(f"Endpoint: Zona {zone} (pin {pin_num}) encendida via /zone")
            if duration:
                # intenta parsear a entero
                try:
                    dur = int(duration)
                except Exception:
                    dur = None
                if dur and dur > 0:
                    # programar apagado sin bloquear
                    async def _delayed_off(pin, name, pin_n, s):
                        await asyncio.sleep(s)
                        try:
                            pin.value(1)
                            log(f"Endpoint: Zona {name} (pin {pin_n}) apagada por timeout")
                        except Exception as e:
                            log(f"Error apagando zona {name}: {e}")

                    asyncio.create_task(_delayed_off(p, zone, pin_num, dur))

            send_response(writer, {"status": "ok", "zone": zone, "action": "on", "pin": pin_num, "duration": duration})
            return
        except Exception as e:
            send_response(writer, {"error": f"No se pudo encender {zone}: {e}"}, "500 Internal Server Error")
            return

    elif action == "off":
        try:
            p.value(1)
            log(f"Endpoint: Zona {zone} (pin {pin_num}) apagada via /zone")
            send_response(writer, {"status": "ok", "zone": zone, "action": "off", "pin": pin_num})
            return
        except Exception as e:
            send_response(writer, {"error": f"No se pudo apagar {zone}: {e}"}, "500 Internal Server Error")
            return

    else:
        send_response(writer, {"error": f"Action inválida: {action}"}, "400 Bad Request")
