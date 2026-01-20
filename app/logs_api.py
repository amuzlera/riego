from fastapi import APIRouter, Query, Request
import requests
from datetime import datetime
from pathlib import Path
from requests.auth import HTTPBasicAuth
from .mode_config import is_remote_mode

router = APIRouter()


@router.post("/logs")
async def receive_logs(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}, 400
    
    log_data = payload.get("log", "")
    lines = [line for line in log_data.split("\n") if line.strip()]
    
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


async def _tail_log_remote(n: int = 20):
    """
    Devuelve el resultado del tail de log.txt directamente desde el ESP32.
    Modo REMOTE: consulta archivos locales del servidor (ESP32).
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

        return {"lines": lines}

    except requests.exceptions.RequestException as e:
        # Error de conexión o timeout
        return {"lines": [], "error": f"No se pudo conectar al ESP32: {e}"}
    except ValueError:
        # JSON malformado
        return {"lines": [], "error": "Respuesta inválida del ESP32"}


async def _tail_log_local(n: int = 30):
    """
    Devuelve las últimas n líneas de logs guardados localmente en el servidor.
    Los logs vienen del ESP32 que los envía regularmente vía POST /logs.
    Modo LOCAL: consulta logs guardados en el servidor.
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


@router.get("/logs/tail")
async def tail_log(n: int = Query(30, ge=1, le=500)):
    """
    Endpoint público que devuelve logs según RIEGO_MODE.
    
    - Si RIEGO_MODE=remote: consulta ESP32 directamente (/tail del ESP32)
    - Si RIEGO_MODE=direct: consulta archivos locales del servidor (guardados por POST /logs)
    """
    if is_remote_mode():
        # Remote: consultar ESP32 directamente
        return await _tail_log_remote(n)
    else:
        # Direct/Local: consultar archivos guardados
        return await _tail_log_local(n)