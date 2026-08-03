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


def build_action_registry(device):
    def all_off(payload):
        device.all_off()
        return {
            "ok": True,
            "action": "all_off",
            "outputs": device.list_outputs(),
        }

    def set_output(payload):
        name = payload.get("pin") or payload.get("name")
        value = payload.get("value")
        if name is None:
            raise ValueError("Falta 'pin' o 'name'")
        if value is None:
            raise ValueError("Falta 'value'")

        state = device.set_output(name, _coerce_state(value))
        return {
            "ok": True,
            "action": "set_output",
            "name": name,
            "state": state,
        }

    def set_output_by_name(payload):
        name = payload.get("name")
        state = payload.get("state")
        if name is None:
            raise ValueError("Falta 'name'")
        if state is None:
            raise ValueError("Falta 'state'")

        result = device.set_output(name, _coerce_state(state))
        return {
            "ok": True,
            "action": "set_output_by_name",
            "name": name,
            "state": result,
        }

    return {
        "all_off": all_off,
        "set_output": set_output,
        "set_output_by_name": set_output_by_name,
    }
