import json
from machine import Pin

CONFIG_PATH = "config_riego.json"

def safe_high(pins):
    """Inicializa cada pin en HIGH para relé activo LOW"""
    for p in pins:
        Pin(p, Pin.OUT, value=1)


DEFAULT_SAFE_PINS = [19,5,18,25,26,27]

try:
    from server_utils import log
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    
    zone_pins = list(cfg.get("zones", {}).values())
    if zone_pins:
        safe_high(zone_pins)
        log(f"Relés activados HIGH en boot para las zonas: {zone_pins}")
    else:
        safe_high(DEFAULT_SAFE_PINS)
        log("No se encontraron zonas en config, usando pines por defecto")
except Exception as e:
    safe_high(DEFAULT_SAFE_PINS)
    print("Error leyendo config.json en boot.py:", e)
    log(f"Error leyendo config.json en boot.py:, {e}")
