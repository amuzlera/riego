from boot_manager import DEV_SLOT, STABLE_SLOT, get_state, set_active_slot
from server_utils import parse_query, send_response


def _status_payload():
    state = get_state()
    state["slots"] = [DEV_SLOT, STABLE_SLOT]
    return state


async def status(writer):
    send_response(writer, {"status": "ok", "firmware": _status_payload()})


async def slot(writer, query=""):
    params = parse_query(query)
    target = params.get("slot") or params.get("name")
    if not target:
        send_response(writer, {"error": "Falta parametro slot"}, "400 Bad Request")
        return

    try:
        state = set_active_slot(target)
        send_response(writer, {"status": "ok", "firmware": state})
    except Exception as e:
        send_response(writer, {"error": str(e)}, "400 Bad Request")
