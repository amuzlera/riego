import asyncio
from config import SERVER_URL
from endpoints.actions import change_zone
import urequests
from server_utils import send_logs



def get_actions():
    url = f"{SERVER_URL}/api/get_actions"
    r = urequests.get(url)
    data = r.json()
    r.close()
    return data

def execute_remote_actions():
    for act in get_actions():
        if act.get("type") != "change_zone":
            continue

        try:
            zone = act.get("zone")
            action_type = act.get("action_type", "on")

            try:
                duration = int(act.get("duration")) if act.get("duration") is not None else None
            except Exception:
                duration = None

            asyncio.create_task(change_zone(zone, action_type, duration))

            send_logs(f"Remote action: {zone} -> {action_type} ({duration}s)")
            
        except Exception as e:
            send_logs(f"Failed to execute remote action {act}: {e}")
