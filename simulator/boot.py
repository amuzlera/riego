from pathlib import Path

from config import CONFIG_PATH
from machine import Pin

DEFAULT_SAFE_PINS = [19, 5, 18, 25, 26, 27]


def safe_high(pins):
    """Set relay pins to HIGH so active-low relays stay off."""
    for pin in pins:
        Pin(pin, Pin.OUT, value=1)


def _load_zone_pins():
    try:
        import json

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        zones = cfg.get("zones", {})
        return list(zones.values())
    except Exception:
        return []


try:
    zone_pins = _load_zone_pins()
    if zone_pins:
        safe_high(zone_pins)
    else:
        safe_high(DEFAULT_SAFE_PINS)
except Exception:
    safe_high(DEFAULT_SAFE_PINS)
