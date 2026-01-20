"""
API para gestionar config_riego.json
GET /config/riego - obtiene la configuración actual
POST /config/riego - guarda la configuración
"""

from fastapi import APIRouter, Body
from pathlib import Path
import json

router = APIRouter()

CONFIG_FILE = Path("app/config_riego.json")


@router.get("/config/riego")
async def get_riego_config():
    """Obtiene la configuración actual de riego"""
    try:
        if not CONFIG_FILE.exists():
            return {
                "status": "error",
                "message": "Archivo de configuración no encontrado",
                "config": None
            }
        
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        
        return {
            "status": "ok",
            "config": config
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "config": None
        }


@router.post("/config/riego")
async def save_riego_config(config: dict = Body(...)):
    """Guarda la configuración de riego"""
    try:
        # Validar estructura básica
        if "zones" not in config or "programed_times" not in config:
            return {
                "status": "error",
                "message": "Configuración incompleta. Se requieren 'zones' y 'programed_times'",
                "saved": False
            }
        
        # Asegurar que existe el directorio
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Escribir la configuración
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        
        return {
            "status": "ok",
            "message": "Configuración guardada exitosamente",
            "saved": True,
            "config": config
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "saved": False
        }
