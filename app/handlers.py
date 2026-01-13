"""
Handlers para los modos direct (ESP32) y remote (servidor).
"""

from urllib.parse import urlencode
import httpx
from fastapi import Query
from fastapi.responses import JSONResponse, PlainTextResponse
import os

# === Config del ESP (igual que antes) ===
ESP_HOST = os.getenv("ESP_HOST", "http://192.168.0.50")
ESP_USER = os.getenv("ESP_USER", "admin")
ESP_PASS = os.getenv("ESP_PASS", "1234")
ESP_TIMEOUT = float(os.getenv("ESP_TIMEOUT", "5"))


async def _esp_get(path: str, params: dict | None = None):
    """Helper para GET al ESP32"""
    url = f"{ESP_HOST}{path}"
    if params:
        url += f"?{urlencode(params)}"
    auth = httpx.BasicAuth(ESP_USER, ESP_PASS)
    async with httpx.AsyncClient(timeout=ESP_TIMEOUT) as client:
        r = await client.get(url, auth=auth)
    return r


async def _esp_post(path: str, params: dict | None = None, data: str = ""):
    """Helper para POST al ESP32"""
    url = f"{ESP_HOST}{path}"
    if params:
        url += f"?{urlencode(params)}"
    auth = httpx.BasicAuth(ESP_USER, ESP_PASS)
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    async with httpx.AsyncClient(timeout=ESP_TIMEOUT) as client:
        r = await client.post(url, auth=auth, content=data.encode("utf-8"), headers=headers)
    return r


def _as_response(r: httpx.Response):
    """Convierte respuesta httpx a FastAPI response"""
    ctype = r.headers.get("content-type", "")
    if "application/json" in ctype:
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return PlainTextResponse(status_code=r.status_code, content=r.text)
    return PlainTextResponse(status_code=r.status_code, content=r.text)


# ============ HANDLERS DIRECT (ESP32) ============
class DirectHandlers:
    @staticmethod
    async def zone(zone: str, action: str, duration: int | None = None):
        """Envía comando de zona directo al ESP32"""
        params = {"zone": zone}
        if action:
            params["action"] = action
        if duration is not None:
            params["duration"] = str(duration)
        
        try:
            r = await _esp_get("/zone", params)
            return _as_response(r)
        except httpx.TimeoutException:
            return JSONResponse(status_code=504, content={"error": "timeout"})
        except httpx.RequestError as e:
            return JSONResponse(status_code=502, content={"error": str(e)})

    @staticmethod
    async def execute(code: str):
        """Ejecuta código directo en ESP32"""
        try:
            r = await _esp_get("/execute", {"code": code})
            return _as_response(r)
        except httpx.TimeoutException:
            return JSONResponse(status_code=504, content={"error": "timeout"})
        except httpx.RequestError as e:
            return JSONResponse(status_code=502, content={"error": str(e)})


# ============ HANDLERS REMOTE (Servidor) ============
class RemoteHandlers:
    @staticmethod
    async def zone(zone: str, action: str, duration: int | None = None):
        """
        Agrega una acción de zona al JSON de acciones.
        Se ejecuta cuando un botón es presionado en modo remote.
        
        Args:
            zone: Identificador de la zona (ej: "1", "2", "zona6", etc)
            action: "on" o "off"
            duration: Duración en segundos (opcional, default None)
        
        Returns: JSON con la acción agregada
        """
        import json
        import os
        
        if not action:
            return JSONResponse(
                status_code=400,
                content={"error": "action es requerido"}
            )
        
        # Normalizar la zona
        zone_str = str(zone).lower()
        if not zone_str.startswith("zona"):
            zone_str = f"zona{zone_str}"
        
        # Crear la acción
        new_action = {
            "type": "change_zone",
            "action_type": action.lower(),
            "zone": zone_str,
            "duration": duration if duration is not None else 0
        }
        
        try:
            # Leer acciones existentes
            actions_file = "app/actions.json"
            if os.path.exists(actions_file):
                with open(actions_file, "r") as f:
                    try:
                        actions = json.load(f)
                    except json.JSONDecodeError:
                        actions = []
            else:
                actions = []
            
            # Agregar nueva acción
            actions.append(new_action)
            
            # Guardar
            with open(actions_file, "w") as f:
                json.dump(actions, f, indent=2)
            
            return JSONResponse(
                status_code=200,
                content={
                    "mode": "remote",
                    "status": "success",
                    "message": f"Acción agregada: {zone_str} {action} ({duration}s)",
                    "action": new_action
                }
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": f"Error al guardar acción: {str(e)}"}
            )

    @staticmethod
    async def execute(code: str):
        """
        [PLACEHOLDER] Agrega una acción de ejecución de código al JSON.
        Por ahora devuelve un placeholder.
        Llenar según necesidad (guardar en DB, validar, etc).
        """
        return JSONResponse(
            status_code=200,
            content={
                "mode": "remote",
                "status": "placeholder",
                "code": code[:50] + "..." if len(code) > 50 else code,
                "message": "Remote code execution - placeholder, funcionalidad por implementar"
            }
        )


# ============ SELECTOR DE HANDLERS ============
def get_zone_handler():
    """Devuelve el handler correcto según el modo"""
    from .mode_config import is_remote_mode
    if is_remote_mode():
        return RemoteHandlers.zone
    return DirectHandlers.zone


def get_execute_handler():
    """Devuelve el handler correcto según el modo"""
    from .mode_config import is_remote_mode
    if is_remote_mode():
        return RemoteHandlers.execute
    return DirectHandlers.execute
