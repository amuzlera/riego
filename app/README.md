# Riego v3 - Backend

Backend Python para correr en la PC y hablar con el ESP32 por HTTP.

## Objetivo

- la PC decide la logica
- el ESP32 solo ejecuta acciones
- configuracion local en un JSON

## Estructura

- `main.py`: API FastAPI
- `esp32_client.py`: cliente HTTP al firmware
- `storage.py`: persistencia local de dispositivos
- `schemas.py`: modelos de entrada
- `devices.json.example`: plantilla de dispositivos
- `readings.json`: historial local de lecturas del sensor

## Configuracion

Copiar `devices.json.example` como `devices.json` o definir:

```bash
export RIEGO_DEVICES_FILE=/ruta/a/devices.json
export RIEGO_READINGS_FILE=/ruta/a/readings.json
export RIEGO_HTTP_TIMEOUT=5
```

La app levanta un poller en segundo plano que consulta `temp_humedad` cada 10 minutos y guarda la última lectura localmente.
En Docker, la persistencia queda en `riego/storage/devices.json` y `riego/storage/readings.json` del repo montados en `/data`.

## Ejecutar

```bash
cd riegov3
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Si querés correrlo desde otra carpeta, definí el `PYTHONPATH` apuntando a `riegov3`.

```bash
PYTHONPATH=/ruta/a/riegov3 python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API principal

- `GET /`
- `GET /devices`
- `POST /devices`
- `GET /devices/{name}/status`
- `GET /devices/{name}/pins`
- `POST /devices/{name}/pins/{pin}/on`
- `POST /devices/{name}/pins/{pin}/off`
- `POST /devices/{name}/pins/{pin}/toggle`
- `POST /devices/{name}/pins/{pin}/run_for`
- `POST /devices/{name}/pins/{pin}/set`
- `GET /devices/{name}/sensors`
- `GET /devices/{name}/sensors/{sensor}`
- `GET /devices/{name}/jobs`
- `GET /devices/{name}/environment`
- `GET /devices/{name}/programs`
- `POST /devices/{name}/programs`
- `PUT /devices/{name}/programs/{program_id}`
- `DELETE /devices/{name}/programs/{program_id}`
- `GET /devices/{name}/actions`
- `POST /devices/{name}/actions/{action}`
- `POST /devices/{name}/execute`

La UI web queda en `/` y toma los dispositivos desde `GET /devices`.

## Programador

Los programas semanales se crean por pin y aceptan:
- `days`: dias de la semana
- `periods`: una o mas franjas con `start` y `end`
- `enabled`
- `label`

Ese mismo formato se usa para guardar los programas en el ESP32.

## Ejemplo

Crear un dispositivo:

```bash
curl -X POST http://127.0.0.1:8000/devices \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "esp32-lab",
    "base_url": "http://192.168.1.50",
    "api_key": "cambia_esto",
    "description": "ESP32 principal",
    "enabled": true
  }'
```

Consultar estado:

```bash
curl http://127.0.0.1:8000/devices/esp32-lab/status
```

Guardar una lectura local del sensor:

```bash
curl http://127.0.0.1:8000/devices/esp32-lab/sensors/temp_humedad
```

Consultar la ultima lectura guardada:

```bash
curl http://127.0.0.1:8000/devices/esp32-lab/readings/latest?sensor=temp_humedad
```
