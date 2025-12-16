# logs_api.py
from pydantic import BaseModel
from fastapi import APIRouter, Query, Request
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pathlib import Path

router = APIRouter()


class LogPayload(BaseModel):
    logs: list[str] | None = None
    log: str | list[str] | None = None  # Aceptar ambos formatos


@router.post("/logs")
async def receive_logs(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        # Si no es JSON válido, intentar como texto
        body = await request.body()
        print(f"ERROR parsing JSON: {e}")
        print(f"RAW BODY: {body}")
        return {"status": "error", "error": str(e)}, 400
    
    import json
    print("RAW PAYLOAD:", json.dumps(payload, default=str, ensure_ascii=False))
    print("payload:", payload)
    
    # Aceptar ambos formatos: "logs" y "log"
    lines = []
    if payload.get("log"):
        log_data = payload.get("log")
        if isinstance(log_data, str):
            # Si es un string compacto con múltiples líneas, dividirlo
            lines = [line for line in log_data.split("\n") if line.strip()]
        elif isinstance(log_data, list):
            lines = log_data
    else:
        lines = payload.get("logs") or []
    
    # Aplanar la lista en caso de que haya listas anidadas
    flat_lines = []
    for item in lines:
        if isinstance(item, list):
            flat_lines.extend(item)
        else:
            flat_lines.append(str(item))
    lines = flat_lines
    
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
            line_str = str(line)
            if "/tail, filename=log.txt" not in line_str and line_str not in existing_lines:
                f.write(line_str + "\n")

    return {"status": "ok", "received_lines": len(lines)}


# IP del ESP32
ESP32_IP = "http://192.168.0.50"
ESP32_USER = "admin"
ESP32_PASS = "1234"


@router.get("/logs/tail")
async def tail_log(n: int = Query(20, ge=1, le=500)):
    """
    Devuelve las últimas n líneas de logs guardados localmente en el servidor.
    Los logs vienen del ESP32 que los envía regularmente vía POST /logs.
    """
    try:
        # Usar el log de hoy
        today = datetime.now().strftime("%Y/%m/%d")
        log_file = Path(f"{today}.log")
        
        if not log_file.exists():
            return {"lines": [], "file": str(log_file), "count": 0}
        
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        # Devolver las últimas n líneas
        last_lines = all_lines[-n:] if len(all_lines) > n else all_lines
        # Remover saltos de línea
        last_lines = [line.rstrip("\n") for line in last_lines]
        
        return {
            "lines": last_lines,
            "file": str(log_file),
            "count": len(last_lines),
            "total": len(all_lines)
        }
    except Exception as e:
        return {"error": str(e), "lines": []}, 400
