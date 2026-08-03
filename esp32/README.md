# Riego v3 - ESP32

Firmware minimal para el ESP32.

Objetivo:
- conectar a Wi-Fi
- exponer HTTP simple
- prender/apagar pines
- ejecutar acciones locales
- leer sensores

## Archivos

- `main.py`: arranque del firmware
- `boot.py`: pone salidas en estado seguro al boot
- `config.py.example`: plantilla de configuracion
- `hardware.py`: registro de pines y sensores
- `actions.py`: acciones locales
- `http_server.py`: servidor HTTP y router

## Endpoints

- `GET /health`
- `GET /status`
- `GET /pins`
- `GET /pins/<nombre>`
- `POST /pins/<nombre>/on`
- `POST /pins/<nombre>/off`
- `POST /pins/<nombre>/toggle`
- `POST /pins/<nombre>/set` con JSON `{"value": 0|1}`
- `POST /pins/<nombre>/run_for` con JSON `{"seconds": 1200, "value": true}`
- `GET /sensors`
- `GET /sensors/<nombre>`
- `GET /jobs`
- `GET /environment`
- `GET /programs`
- `POST /programs`
- `PUT /programs/<id>`
- `DELETE /programs/<id>`
- `GET /actions`
- `POST /actions/<nombre>`
- `POST /execute` con JSON `{"name":"...", "args":{...}}`

## Autenticacion

Si `API_KEY` no esta vacio, el firmware acepta:
- `X-API-Key: <valor>`
- `Authorization: Bearer <valor>`

## Configuracion

Copiar `config.py.example` como `config.py` y ajustar:
- Wi-Fi
- `API_KEY`
- `NTP_HOST`
- `TZ_OFFSET_SECONDS`
- `PINS`
- `SENSORS`

El sensor `temp_humedad` expone temperatura y humedad usando `DHT11` en el pin `4`.

`GET /environment` devuelve temperatura, humedad y hora local del ESP32 en una sola respuesta.

Los programas semanales se guardan en `programs.json` y se evalúan localmente en el ESP32.
Cada programa usa:
- `pin`
- `days`
- `periods` con una o mas franjas `{"start":"HH:MM","end":"HH:MM"}`
- `enabled`
- `label`

Ejemplo:

```json
{
  "pin": "zona1",
  "days": [0, 1, 2, 3, 4, 5, 6],
  "periods": [
    { "start": "23:30", "end": "23:45" },
    { "start": "03:30", "end": "03:40" }
  ],
  "enabled": true,
  "label": "Riego general"
}
```

## Nota

Esta base no mete logica de riego compleja en el ESP32. El backend en la PC deberia decidir cuando y como disparar acciones.

`run_for` se resuelve localmente en el ESP32 con un solo scheduler interno, así el apagado no depende de Internet.
Los jobs quedan persistidos en `jobs.json` y se restauran al boot solo si el reloj del sistema tiene una hora válida.
