from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Body

from .handlers import proxy_post

router = APIRouter()

CONFIG_FILE = Path("app/config_riego.json")


@router.get("/config/riego")
async def get_riego_config():
    try:
        if not CONFIG_FILE.exists():
            return {
                "status": "error",
                "message": "Archivo de configuración no encontrado",
                "config": None,
            }

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        return {"status": "ok", "config": config}
    except Exception as e:
        return {"status": "error", "message": str(e), "config": None}


@router.post("/config/riego")
async def save_riego_config(config: dict = Body(...)):
    try:
        if "zones" not in config or "programed_times" not in config:
            return {
                "status": "error",
                "message": "Configuración incompleta. Se requieren 'zones' y 'programed_times'",
                "saved": False,
            }

        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

        sync_error = None
        try:
            payload = json.dumps(config, indent=4)
            response = await proxy_post("/upload", {"filename": "config_riego.json"}, data=payload)
            if getattr(response, "status_code", 500) >= 400:
                sync_error = f"device sync failed ({response.status_code})"
        except Exception as e:
            sync_error = str(e)

        return {
            "status": "ok",
            "message": "Configuración guardada exitosamente",
            "saved": True,
            "synced": sync_error is None,
            "sync_error": sync_error,
            "config": config,
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "saved": False}
