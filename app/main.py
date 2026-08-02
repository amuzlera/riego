from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.boot_log_archive import capture_boot_log, watch_boot_logs
from app.actions import get_actions_router, get_config_router
from app.handlers import proxy_get, proxy_post
from app.logs_api import router as logs_router
from app.riego_config_api import router as riego_config_router
from app.wheater import weather_router

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Riego UI")
app.include_router(logs_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(get_actions_router, prefix="/api")
app.include_router(get_config_router, prefix="/api")
app.include_router(riego_config_router, prefix="/api")


@app.on_event("startup")
async def capture_esp32_boot_log_on_startup():
    await capture_boot_log()
    asyncio.create_task(watch_boot_logs())


@app.api_route("/api/esp", methods=["GET", "POST"])
async def esp_exec(
    request: Request,
    cmd: str = Query(..., description="Comando para el ESP32"),
    filename: str | None = Query(None, description="Nombre de archivo"),
    body: str = Body("", media_type="text/plain"),
):
    if request.method == "GET":
        params = {"filename": filename} if filename else None
        return await proxy_get(f"/{cmd}", params)

    params = {"filename": filename} if filename else None
    return await proxy_post(f"/{cmd}", params, data=body)


@app.get("/api/esp/ls")
async def esp_ls(filename: str | None = Query(None, description="Carpeta opcional")):
    return await proxy_get("/ls", {"filename": filename} if filename else None)


@app.get("/api/esp/cat")
async def esp_cat(
    filename: str | None = Query(None, description="Nombre de archivo"),
    file: str | None = Query(None, description="Compatibilidad legacy"),
):
    target = filename or file
    return await proxy_get("/cat", {"filename": target} if target else None)


@app.post("/api/esp/rm")
async def esp_rm(
    filename: str | None = Query(None, description="Nombre de archivo a eliminar"),
    file: str | None = Query(None, description="Compatibilidad legacy"),
):
    target = filename or file
    return await proxy_get("/rm", {"filename": target} if target else None)


@app.post("/api/zone")
async def api_zone(
    request: Request,
    body: str = Body("", media_type="text/plain"),
    zone: str | None = Query(None),
    action: str | None = Query(None),
    duration: int | None = Query(None),
):
    z = zone
    a = action
    d = duration

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

    params = {"zone": z}
    if a:
        params["action"] = a
    if d is not None:
        params["duration"] = str(d)
    return await proxy_get("/zone", params)


@app.get("/api/execute")
async def api_execute(code: str = Query(..., description="Código a ejecutar")):
    return await proxy_get("/execute", {"code": code})


@app.get("/api/firmware/status")
async def firmware_status():
    return await proxy_get("/firmware/status")


@app.post("/api/firmware/slot")
async def firmware_slot(slot: str = Query(..., description="Slot a activar: dev o stable")):
    return await proxy_post("/firmware/slot", {"slot": slot})


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/config/mode")
async def get_mode():
    return JSONResponse(content={"mode": "local-only"})


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/control_panel")
def control_panel():
    return FileResponse(STATIC_DIR / "control_panel.html")
