try:
    import ujson as json
except Exception:
    import json

from machine import Pin

import boot_manager

CONFIG_PATH = "config_riego.json"
DEFAULT_SAFE_PINS = [19, 5, 18, 25, 26, 27]


def _write_boot_log(line):
    print(line)
    for path in ("log.txt", "last_log.txt"):
        try:
            with open(path, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass


def _start_new_boot_log():
    try:
        with open("last_log.txt", "w"):
            pass
    except Exception:
        pass


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


_start_new_boot_log()

try:
    zone_pins = _load_zone_pins()
    if zone_pins:
        safe_high(zone_pins)
        _write_boot_log("Relés activados HIGH en boot para las zonas: {}".format(zone_pins))
    else:
        safe_high(DEFAULT_SAFE_PINS)
        _write_boot_log("No se encontraron zonas en config, usando pines por defecto")
except Exception:
    safe_high(DEFAULT_SAFE_PINS)
    _write_boot_log("Fallo la inicialización segura de pines, usando defaults")

boot_manager.boot()
