from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .esp32_client import Esp32Client
from .schemas import (
    ActionRequest,
    DeviceCreate,
    DeviceUpdate,
    ExecuteRequest,
    PinSetRequest,
    ProgramCreate,
    ProgramUpdate,
    RunForRequest,
)
from .storage import store


app = FastAPI(title="Riego v3 Backend")
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _ensure_device(name: str) -> dict:
    device = store.get_device(name)
    if not device:
        raise HTTPException(status_code=404, detail="device_not_found")
    if not device.get("enabled", True):
        raise HTTPException(status_code=409, detail="device_disabled")
    return device


def _response_from_httpx(response) -> JSONResponse:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            return JSONResponse(status_code=response.status_code, content=response.json())
        except Exception:
            pass
    return JSONResponse(
        status_code=response.status_code,
        content={"ok": False, "text": response.text},
    )


def _offline_response(device: dict, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "ok": False,
            "error": "esp32_unreachable",
            "device": device.get("name"),
            "base_url": device.get("base_url"),
            "detail": str(exc),
        },
    )


def _model_payload(model):
    dump = getattr(model, "model_dump", None)
    if dump is not None:
        return dump()
    return model.dict()


@app.get("/")
def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        "ok": True,
        "service": "riego-v3-backend",
        "devices": [d["name"] for d in store.list_devices()],
    }


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/devices")
def list_devices():
    return {"ok": True, "devices": store.list_devices()}


@app.post("/devices")
def create_device(payload: DeviceCreate):
    device = store.upsert_device(_model_payload(payload))
    return {"ok": True, "device": device}


@app.get("/devices/{name}")
def get_device(name: str):
    device = store.get_device(name)
    if not device:
        raise HTTPException(status_code=404, detail="device_not_found")
    return {"ok": True, "device": device}


@app.patch("/devices/{name}")
def update_device(name: str, payload: DeviceUpdate):
    try:
        device = store.patch_device(name, _model_payload(payload))
    except KeyError:
        raise HTTPException(status_code=404, detail="device_not_found")
    return {"ok": True, "device": device}


@app.delete("/devices/{name}")
def delete_device(name: str):
    try:
        store.delete_device(name)
    except KeyError:
        raise HTTPException(status_code=404, detail="device_not_found")
    return {"ok": True}


@app.get("/devices/{name}/health")
async def device_health(name: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).health()
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.get("/devices/{name}/status")
async def device_status(name: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).status()
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.get("/devices/{name}/pins")
async def device_pins(name: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).list_pins()
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.get("/devices/{name}/pins/{pin}")
async def device_pin(name: str, pin: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).get_pin(pin)
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.post("/devices/{name}/pins/{pin}/on")
async def device_pin_on(name: str, pin: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).pin_on(pin)
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.post("/devices/{name}/pins/{pin}/off")
async def device_pin_off(name: str, pin: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).pin_off(pin)
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.post("/devices/{name}/pins/{pin}/toggle")
async def device_pin_toggle(name: str, pin: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).pin_toggle(pin)
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.post("/devices/{name}/pins/{pin}/run_for")
async def device_pin_run_for(name: str, pin: str, payload: RunForRequest):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).pin_run_for(pin, payload.seconds, payload.value)
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.post("/devices/{name}/pins/{pin}/set")
async def device_pin_set(name: str, pin: str, payload: PinSetRequest):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).set_pin(pin, payload.value)
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.get("/devices/{name}/sensors")
async def device_sensors(name: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).list_sensors()
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.get("/devices/{name}/sensors/{sensor}")
async def device_sensor(name: str, sensor: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).get_sensor(sensor)
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.get("/devices/{name}/actions")
async def device_actions(name: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).list_actions()
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.get("/devices/{name}/jobs")
async def device_jobs(name: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).list_jobs()
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.get("/devices/{name}/environment")
async def device_environment(name: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).environment()
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.get("/devices/{name}/programs")
async def device_programs(name: str):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).list_programs()
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.post("/devices/{name}/programs")
async def device_program_create(name: str, payload: ProgramCreate):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).create_program(_model_payload(payload))
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.put("/devices/{name}/programs/{program_id}")
async def device_program_update(name: str, program_id: int, payload: ProgramUpdate):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).update_program(program_id, _model_payload(payload))
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.delete("/devices/{name}/programs/{program_id}")
async def device_program_delete(name: str, program_id: int):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).delete_program(program_id)
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.post("/devices/{name}/actions/{action}")
async def device_action(name: str, action: str, payload: ActionRequest):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).run_action(action, payload.payload)
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)


@app.post("/devices/{name}/execute")
async def device_execute(name: str, payload: ExecuteRequest):
    device = _ensure_device(name)
    try:
        response = await Esp32Client(device).execute(payload.name, payload.args)
        return _response_from_httpx(response)
    except httpx.RequestError as exc:
        return _offline_response(device, exc)
