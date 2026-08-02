try:
    import ujson as json
except Exception:
    import json

from machine import Pin
from server_utils import log, start_new_boot_log

CONFIG_PATH = "config_riego.json"
DEFAULT_SAFE_PINS = [19, 5, 18, 25, 26, 27]


def safe_high(pins):
    for p in pins:
        Pin(p, Pin.OUT, value=1)


def _load_zone_pins():
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        zones = cfg.get("zones", {})
        return list(zones.values())
    except Exception:
        return []


start_new_boot_log()

try:
    zone_pins = _load_zone_pins()
    if zone_pins:
        safe_high(zone_pins)
        log(f"Relés activados HIGH en boot para las zonas: {zone_pins}")
    else:
        safe_high(DEFAULT_SAFE_PINS)
        log("No se encontraron zonas en config, usando pines por defecto")
except Exception:
    safe_high(DEFAULT_SAFE_PINS)
