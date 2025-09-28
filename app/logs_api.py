# logs_api.py
from fastapi import APIRouter, Query
import requests
from requests.auth import HTTPBasicAuth

router = APIRouter()

# IP del ESP32
ESP32_IP = "http://192.168.0.50"  # reemplazar por la IP real
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
        return {"lines": r.text.splitlines()}

    except requests.exceptions.RequestException as e:
        # Error de conexión o timeout
        return {"lines": [], "error": f"No se pudo conectar al ESP32: {e}"}
    except ValueError:
        # JSON malformado
        return {"lines": [], "error": "Respuesta inválida del ESP32"}
