import os
from urllib.parse import urlencode
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import httpx
from fastapi import FastAPI, Query, Body, Request, UploadFile
from .logs_api import router as logs_router
from .wheater import weather_router


# === Config del ESP (igual que antes) ===
ESP_HOST = os.getenv("ESP_HOST", "http://192.168.0.50")
ESP_USER = os.getenv("ESP_USER", "admin")
ESP_PASS = os.getenv("ESP_PASS", "1234")
ESP_TIMEOUT = float(os.getenv("ESP_TIMEOUT", "5"))

app = FastAPI(title="Riego UI + ESP Proxy")
app.include_router(logs_router, prefix="/api")  # <- esto pone /api/logs/tail
app.include_router(weather_router, prefix="/api")

# ---------- helpers ----------


async def _esp_get(path: str, params: dict | None = None):
    url = f"{ESP_HOST}{path}"
    if params:
        url += f"?{urlencode(params)}"
    auth = httpx.BasicAuth(ESP_USER, ESP_PASS)
    async with httpx.AsyncClient(timeout=ESP_TIMEOUT) as client:
        r = await client.get(url, auth=auth)
    return r


async def _esp_post(path: str, params: dict | None = None, data: str = ""):
    url = f"{ESP_HOST}{path}"
    if params:
        url += f"?{urlencode(params)}"
    auth = httpx.BasicAuth(ESP_USER, ESP_PASS)
    # El firmware que compartiste lee el body como texto (no JSON)
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    async with httpx.AsyncClient(timeout=ESP_TIMEOUT) as client:
        r = await client.post(url, auth=auth, content=data.encode("utf-8"), headers=headers)
    return r


def _as_response(r: httpx.Response):
    # Tu firmware devuelve JSON en todas las rutas -> lo pasamos tal cual
    ctype = r.headers.get("content-type", "")
    if "application/json" in ctype:
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return PlainTextResponse(status_code=r.status_code, content=r.text)
    return PlainTextResponse(status_code=r.status_code, content=r.text)

# ---------- API del ESP: endpoints específicos ----------


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



@app.post("/api/esp/zone")
async def esp_zone(request: Request, body: str = Body("", media_type="text/plain"),
                   zone: str | None = Query(None), action: str | None = Query(None),
                   duration: int | None = Query(None)):
    """
    Proxy para encender/apagar zonas del ESP.
    Formatos aceptados:
      - Body corto: "zone1 on 3600" (zona, action, duration opcional)
      - Query params: zone=<zona>, action=on|off, duration=<s>

    Reenvía a {ESP_HOST}/zone?zone=...&action=...&duration=...
    """
    # Priorizar query params si están presentes
    z = zone
    a = action
    d = duration

    # Si no vienen en query, intentar parsear el body corto
    if not z and body:
        # body puede venir con newline; tomamos la primera linea
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

    try:
        # Usamos GET porque el firmware acepta GET para /zone (como otros endpoints)
        r = await _esp_get("/zone", params)
        return _as_response(r)
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "timeout"})
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"error": str(e)})


@app.get("/api/esp/execute")
async def esp_execute(code: str = Query(..., description="Código Python a ejecutar en ESP32")):
    """
    Ejecuta código Python en el ESP32.
    
    Ejemplos:
      - /api/esp/execute?code=pin=Pin(2,Pin.IN)%0Aprint(pin.value())
      - /api/esp/execute?code=print(machine.freq())
    
    Retorna: {"result": "salida", "error": null}
    """
    try:
        r = await _esp_get("/execute", {"code": code})
        return _as_response(r)
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "timeout"})
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"error": str(e)})

# ---------- Frontend ----------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")



@app.get("/control_panel")
def control_panel():
    """Sirve la página Control Panel (static/control_panel.html)"""
    return FileResponse("static/control_panel.html")
# python -m uvicorn app.main:app --reload
# python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
