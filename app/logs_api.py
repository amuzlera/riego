# logs_api.py
from pydantic import BaseModel
from fastapi import APIRouter, Query
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pathlib import Path

router = APIRouter()


class LogPayload(BaseModel):
    logs: list[str] | None = None
    log: str | list[str] | None = None  # Aceptar ambos formatos


@router.post("/logs")
def receive_logs(payload: LogPayload):
    print("payload:", payload)
    
    # Aceptar ambos formatos: "logs" y "log"
    lines = payload.logs or []
    if payload.log:
        if isinstance(payload.log, str):
            lines = [payload.log]
        elif isinstance(payload.log, list):
            lines = payload.log
    
    if not lines:
        return {"status": "ok", "received_lines": 0}

    # Append lines to date-based log file
    today = datetime.now().strftime("%Y/%m/%d")
    log_file = Path(f"{today}.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Leer líneas existentes
    existing_lines = set()
    if log_file.exists():
        with open(log_file, "r") as f:
            existing_lines = set(f.read().splitlines())

    # Escribir solo líneas nuevas
    with open(log_file, "a") as f:
        for line in lines:
            if "/tail, filename=log.txt" not in line and line not in existing_lines:
                f.write(line + "\n")

    return {"status": "ok", "received_lines": len(lines)}


# IP del ESP32
ESP32_IP = "http://192.168.0.50"
ESP32_USER = "admin"
ESP32_PASS = "1234"


@router.get("/logs/tail")
async def tail_log(n: int = Query(20, ge=1, le=100)):
    """
    Devuelve el resultado del tail de log.txt directamente desde el ESP32.
    Solo se llama al endpoint del ESP32.
    """

    try:
        # Construimos la URL del ESP32
        esp_url = f"{ESP32_IP}/tail?filename=log.txt"

        print(esp_url)
        # Llamada HTTP al ESP32
        r = requests.get(
            f"{ESP32_IP}/tail?filename=log.txt",
            timeout=5,
            auth=HTTPBasicAuth(ESP32_USER, ESP32_PASS)
        )
        r.raise_for_status()

        lines = r.text.splitlines()

        # Append lines to date-based log file
        today = datetime.now().strftime("%Y/%m/%d")
        log_file = Path(f"{today}.log")
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Leer líneas existentes
        existing_lines = set()
        if log_file.exists():
            with open(log_file, "r") as f:
                existing_lines = set(f.read().splitlines())

        # Escribir solo líneas nuevas
        with open(log_file, "a") as f:
            for line in lines:
                if "/tail, filename=log.txt" not in line and line not in existing_lines:
                    f.write(line + "\n")

        return {"lines": lines}

    except requests.exceptions.RequestException as e:
        # Error de conexión o timeout
        return {"lines": [], "error": f"No se pudo conectar al ESP32: {e}"}
    except ValueError:
        # JSON malformado
        return {"lines": [], "error": "Respuesta inválida del ESP32"}
