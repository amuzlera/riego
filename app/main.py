import os
from urllib.parse import urlencode
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import httpx
from fastapi import FastAPI, Query, Body, Request, UploadFile

# === Config del ESP (igual que antes) ===
ESP_HOST = os.getenv("ESP_HOST", "http://192.168.0.50")
ESP_USER = os.getenv("ESP_USER", "admin")
ESP_PASS = os.getenv("ESP_PASS", "1234")
ESP_TIMEOUT = float(os.getenv("ESP_TIMEOUT", "5"))

app = FastAPI(title="Riego UI + ESP Proxy")

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

# ---------- (opcional) Proxy genérico /api/esp?cmd=xxx ----------


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

# ---------- Frontend ----------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")
# python -m uvicorn app.main:app --reload