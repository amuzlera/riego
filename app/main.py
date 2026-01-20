import os
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
from fastapi import FastAPI, Query, Body, Request, UploadFile

from app.actions import get_actions_router, get_config_router, get_actions_router
from app.handlers import get_zone_handler, get_execute_handler, _esp_get, _esp_post, _as_response
from app.mode_config import get_current_mode
from .logs_api import router as logs_router
from .wheater import weather_router


# === Config del ESP (igual que antes) ===
ESP_HOST = os.getenv("ESP_HOST", "http://192.168.0.50")
ESP_USER = os.getenv("ESP_USER", "admin")
ESP_PASS = os.getenv("ESP_PASS", "1234")
ESP_TIMEOUT = float(os.getenv("ESP_TIMEOUT", "5"))

app = FastAPI(title="Riego UI + ESP Proxy")
app.include_router(logs_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(get_actions_router, prefix="/api")
app.include_router(get_config_router, prefix="/api")
app.include_router(get_actions_router, prefix="/api")

# Los helpers están ahora en app/handlers.py

# ---------- API del ESP: endpoints específicos ----------


@app.get("/api/esp/get_actions")
async def esp_get_actions():
    """
    GET {ESP_HOST}/ls
    Devuelve {"files": [...]} según tu firmware.
    """
    try:
        r = await _esp_get("/ls")
        return _as_response(r)
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "timeout"})
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.get("/api/esp/ls")
async def esp_ls():
    """
    GET {ESP_HOST}/ls
    Devuelve {"files": [...]} según tu firmware.
    """
    try:
        r = await _esp_get("/ls")
        return _as_response(r)
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "timeout"})
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.get("/api/esp/cat")
async def esp_cat(file: str = Query(..., description="Nombre de archivo")):
    """
    GET {ESP_HOST}/cat?file=<nombre>
    Devuelve {"file": "...", "content": "..."} o error JSON.
    """
    try:
        r = await _esp_get("/cat", {"file": file})
        return _as_response(r)
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "timeout"})
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.post("/upload")
async def upload_file(data: UploadFile):
    filename = data.filename
    content = data.content
    # guardar en disco, por ej:
    with open(filename, "w") as f:
        f.write(content)
    return {"status": "Archivo guardado", "file": filename}


@app.post("/api/esp/rm")
async def esp_rm(file: str = Query(..., description="Nombre de archivo a eliminar")):
    """
    Tu firmware acepta /rm (sin restricción de método).
    Usamos POST desde la API para acciones destructivas.
    Internamente hace GET {ESP_HOST}/rm?file=<nombre>.
    """
    try:
        # podríamos usar GET directo porque tu firmware lo maneja así
        r = await _esp_get("/rm", {"file": file})
        return _as_response(r)
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "timeout"})
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.api_route("/api/esp", methods=["GET", "POST"])
async def esp_exec(
    request: Request,
    cmd: str = Query(..., description="Comando para el ESP32"),
    filename: str | None = Query(None, description="Nombre de archivo"),
    body: str = Body("", media_type="text/plain")
):
    try:
        if request.method == "GET":
            # Ej: /api/esp?cmd=ls
            r = await _esp_get(f"/{cmd}", {"file": filename} if filename else None)
        else:
            # Ej: /api/esp?cmd=upload&filename=main.py
            r = await _esp_post(f"/{cmd}", {"filename": filename} if filename else None, data=body)

        return _as_response(r)

    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "timeout"})
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.post("/api/zone")
async def api_zone(request: Request, body: str = Body("", media_type="text/plain"),
                   zone: str | None = Query(None), action: str | None = Query(None),
                   duration: int | None = Query(None)):
    """
    Control de zonas con modo dinámico (direct o remote).
    Según RIEGO_MODE, usa handlers de DirectHandlers o RemoteHandlers.

    Formatos aceptados:
      - Body corto: "zone1 on 3600" (zona, action, duration opcional)
      - Query params: zone=<zona>, action=on|off, duration=<s>
    """
    # Priorizar query params si están presentes
    z = zone
    a = action
    d = duration

    # Si no vienen en query, intentar parsear el body corto
    if not z and body:
        first = body.splitlines()[0].strip()
        if first:
            parts = first.split()
            if len(parts) >= 1:
                z = parts[0]
            if len(parts) >= 2:
                a = parts[1]
            if len(parts) >= 3:
                try:
                    d = int(parts[2])
                except Exception:
                    d = None

    if not z:
        return JSONResponse(status_code=400, content={"error": "zone requerido"})

    # Obtener el handler correcto (direct o remote)
    handler = get_zone_handler()
    return await handler(z, a or "", d)


@app.get("/api/execute")
async def api_execute(code: str = Query(..., description="Código a ejecutar")):
    """
    Ejecuta código con modo dinámico (direct o remote).
    Según RIEGO_MODE, usa handlers de DirectHandlers o RemoteHandlers.

    Ejemplos:
      - /api/execute?code=pin=Pin(2,Pin.IN)%0Aprint(pin.value())
    """
    handler = get_execute_handler()
    return await handler(code)

# ---------- Frontend ----------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/config/mode")
async def get_mode():
    """Devuelve el modo actual de operación (direct o remote)"""
    return JSONResponse(content={"mode": get_current_mode()})


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/control_panel")
def control_panel():
    """Sirve la página Control Panel (static/control_panel.html)"""
    return FileResponse("static/control_panel.html")
# python -m uvicorn app.main:app --reload
# python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# On EC2 instance:
# ssh -i "am-server-keypair.pem" ubuntu@ec2-56-124-102-170.sa-east-1.compute.amazonaws.com
# http://56.124.102.170:8000
