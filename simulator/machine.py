from __future__ import annotations

import time
from dataclasses import dataclass, field

PWRON_RESET = 0
HARD_RESET = 1
WDT_RESET = 2
DEEPSLEEP_RESET = 3
SOFT_RESET = 4

IN = 0
OUT = 1

_reset_cause = PWRON_RESET


@dataclass
class _PinState:
    pin_id: int
    mode: int | None = None
    value: int = 1
    history: list[tuple[float, int]] = field(default_factory=list)

    def set_value(self, new_value: int) -> int:
        self.value = int(new_value)
        self.history.append((time.time(), self.value))
        print(f"[sim-pin] pin {self.pin_id} -> {self.value}")
        return self.value


PIN_STATES: dict[int, _PinState] = {}


class Pin:
    OUT = OUT
    IN = IN

    def __init__(self, pin_id, mode=None, value=1):
        self.pin_id = int(pin_id)
        self.mode = mode
        state = PIN_STATES.get(self.pin_id)
        if state is None:
            state = _PinState(self.pin_id, mode=mode, value=int(value))
            state.history.append((time.time(), int(value)))
            PIN_STATES[self.pin_id] = state
        else:
            state.mode = mode
            state.set_value(value)
        self._state = state

    def value(self, new_value=None):
        if new_value is None:
            return self._state.value
        return self._state.set_value(new_value)

    def on(self):
        return self.value(1)

    def off(self):
        return self.value(0)


class WDT:
    def __init__(self, timeout=0):
        self.timeout = timeout

    def feed(self):
        return None


def reset():
    global _reset_cause
    _reset_cause = SOFT_RESET
    print("[sim-machine] reset requested")


def reset_cause():
    return _reset_cause


def unique_id():
    return b"SIM-ESP32"
