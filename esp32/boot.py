try:
    from machine import Pin
    import config
except Exception:
    Pin = None
    config = None


def _logical_to_raw(logical_value, active_low):
    if active_low:
        return 0 if logical_value else 1
    return 1 if logical_value else 0


def _safe_start_outputs():
    if Pin is None or config is None:
        return

    pins = getattr(config, "PINS", {})
    for _, pin_cfg in pins.items():
        if pin_cfg.get("mode", "out") != "out":
            continue

        pin_num = pin_cfg.get("pin")
        if pin_num is None:
            continue

        active_low = bool(pin_cfg.get("active_low", False))
        default_state = bool(pin_cfg.get("default", False))

        pin = Pin(pin_num, Pin.OUT)
        pin.value(_logical_to_raw(default_state, active_low))


try:
    _safe_start_outputs()
except Exception:
    # El arranque no debe morir por un error de inicializacion.
    pass

