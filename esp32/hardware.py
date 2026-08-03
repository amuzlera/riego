try:
    import ujson as json
except ImportError:
    import json

from machine import ADC, Pin


def _to_bool(value):
    return bool(value)


def _logical_to_raw(logical_value, active_low):
    if active_low:
        return 0 if logical_value else 1
    return 1 if logical_value else 0


def _raw_to_logical(raw_value, active_low):
    raw_value = 1 if raw_value else 0
    if active_low:
        return 0 if raw_value else 1
    return raw_value


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _coerce_state(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("1", "true", "on", "yes", "high"):
            return True
        if normalized in ("0", "false", "off", "no", "low"):
            return False
    raise ValueError("Valor de estado invalido: {}".format(value))


def _adc_atten_value(name):
    name = (name or "11db").lower()
    mapping = {
        "0db": getattr(ADC, "ATTN_0DB", None),
        "2.5db": getattr(ADC, "ATTN_2_5DB", None),
        "6db": getattr(ADC, "ATTN_6DB", None),
        "11db": getattr(ADC, "ATTN_11DB", None),
    }
    value = mapping.get(name)
    if value is None:
        value = mapping["11db"]
    return value


class OutputPin:
    def __init__(self, name, pin_num, active_low=False, default=False):
        self.name = name
        self.pin_num = _safe_int(pin_num)
        self.active_low = _to_bool(active_low)
        self.pin = Pin(self.pin_num, Pin.OUT)
        self.set(default)

    def set(self, logical_value):
        logical_value = bool(logical_value)
        self.pin.value(_logical_to_raw(logical_value, self.active_low))
        return self.state()

    def on(self):
        return self.set(True)

    def off(self):
        return self.set(False)

    def toggle(self):
        return self.set(not self.state())

    def raw(self):
        return 1 if self.pin.value() else 0

    def state(self):
        return _raw_to_logical(self.pin.value(), self.active_low)

    def as_dict(self):
        return {
            "name": self.name,
            "pin": self.pin_num,
            "active_low": self.active_low,
            "state": self.state(),
            "raw": self.raw(),
        }


class DigitalSensor:
    def __init__(self, name, pin_num, pull=None, invert=False):
        self.name = name
        self.pin_num = _safe_int(pin_num)
        self.invert = bool(invert)

        pull_map = {
            "up": getattr(Pin, "PULL_UP", None),
            "down": getattr(Pin, "PULL_DOWN", None),
        }
        pull_value = pull_map.get((pull or "").lower())

        if pull_value is None:
            self.pin = Pin(self.pin_num, Pin.IN)
        else:
            self.pin = Pin(self.pin_num, Pin.IN, pull=pull_value)

    def read(self):
        value = 1 if self.pin.value() else 0
        if self.invert:
            value = 0 if value else 1
        return value

    def as_dict(self):
        return {
            "name": self.name,
            "kind": "digital",
            "pin": self.pin_num,
            "value": self.read(),
        }


class AdcSensor:
    def __init__(self, name, pin_num, atten="11db"):
        self.name = name
        self.pin_num = _safe_int(pin_num)
        self.adc = ADC(Pin(self.pin_num))
        atten_value = _adc_atten_value(atten)
        if atten_value is not None:
            try:
                self.adc.atten(atten_value)
            except Exception:
                pass

    def read(self):
        return self.adc.read()

    def as_dict(self):
        return {
            "name": self.name,
            "kind": "adc",
            "pin": self.pin_num,
            "value": self.read(),
        }


class Dht11Sensor:
    def __init__(self, name, pin_num):
        self.name = name
        self.pin_num = _safe_int(pin_num)
        self.pin = Pin(self.pin_num)
        self.sensor = None

    def _ensure_sensor(self):
        if self.sensor is None:
            import dht

            self.sensor = dht.DHT11(self.pin)
        return self.sensor

    def read(self):
        sensor = self._ensure_sensor()
        sensor.measure()
        return {
            "temperature": sensor.temperature(),
            "humidity": sensor.humidity(),
        }

    def as_dict(self):
        values = self.read()
        return {
            "name": self.name,
            "kind": "dht11",
            "pin": self.pin_num,
            "temperature": values["temperature"],
            "humidity": values["humidity"],
        }


def build_sensor(name, cfg):
    kind = (cfg.get("kind") or "digital").lower()
    pin_num = cfg.get("pin")
    if kind == "dht11":
        return Dht11Sensor(name, pin_num)
    if kind == "adc":
        return AdcSensor(name, pin_num, cfg.get("atten", "11db"))
    return DigitalSensor(
        name,
        pin_num,
        pull=cfg.get("pull"),
        invert=cfg.get("invert", False),
    )


class Device:
    def __init__(self, pin_cfg, sensor_cfg):
        self.outputs = {}
        self.sensors = {}

        for name, cfg in (pin_cfg or {}).items():
            if cfg.get("mode", "out") != "out":
                continue
            self.outputs[name] = OutputPin(
                name=name,
                pin_num=cfg.get("pin"),
                active_low=cfg.get("active_low", False),
                default=cfg.get("default", False),
            )

        for name, cfg in (sensor_cfg or {}).items():
            self.sensors[name] = build_sensor(name, cfg)

    def list_outputs(self):
        result = {}
        for name, output in self.outputs.items():
            result[name] = output.as_dict()
        return result

    def list_sensors(self):
        result = {}
        for name, sensor in self.sensors.items():
            result[name] = sensor.as_dict()
        return result

    def get_output(self, name):
        if name not in self.outputs:
            raise KeyError("Salida inexistente: {}".format(name))
        return self.outputs[name]

    def get_sensor(self, name):
        if name not in self.sensors:
            raise KeyError("Sensor inexistente: {}".format(name))
        return self.sensors[name]

    def set_output(self, name, logical_value):
        return self.get_output(name).set(_coerce_state(logical_value))

    def on(self, name):
        return self.get_output(name).on()

    def off(self, name):
        return self.get_output(name).off()

    def toggle(self, name):
        return self.get_output(name).toggle()

    def read_sensor(self, name):
        sensor = self.get_sensor(name)
        payload = sensor.as_dict()
        return payload

    def read_all_sensors(self):
        return self.list_sensors()

    def all_off(self):
        for output in self.outputs.values():
            output.off()

    def status(self):
        return {
            "outputs": self.list_outputs(),
            "sensors": self.list_sensors(),
        }
