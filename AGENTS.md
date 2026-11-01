# Contexto del repositorio: Riego v3

Documento de entrada para futuras sesiones. Leerlo antes de trabajar y actualizarlo
cuando cambien arquitectura, configuración o procedimientos relevantes.
Relevamiento: 2026-10-26, código local sobre commit `d0e71d1`.

## Actualización 2026-11-01: mantenimiento y hora (prioridad sobre el relevamiento)

- Instalado por USB y comprobado en el ESP32: mantenimiento HTTP en puerto 81,
  antes de importar la aplicación. API de riego conserva puerto 80.
- `boot.py` establece los seis relés físicos en OFF sin importar `config.py`;
  `main.py` es un lanzador protegido; `recovery.py` conecta Wi-Fi e inicia un hilo
  separado, después importa y ejecuta `controller.py` (antiguo `main.py`).
- El servicio no depende del ciclo asyncio del controlador. Errores Python de
  importación o ejecución dejan mantenimiento disponible y apagan los relés.
  Comparte VM/heap/hardware: no garantiza supervivencia a fallos nativos o red caída.
- Configuración independiente `esp32/recovery_config.json`, local e ignorada,
  con red, IP y copia de la misma API_KEY del controlador. Plantilla versionada.
- Endpoints de mantenimiento: `GET /health`, `GET /files`, `GET /files/{nombre}`,
  `PUT /files/{nombre}` (cuerpo crudo + SHA-256), `POST /reset`.
- Archivos de arranque/recuperación protegidos contra escritura Wi-Fi, al igual
  que módulos ajenos a la aplicación que podrían suplantar dependencias.
  `jobs.json`/`programs.json` se leen pero se modifican por API de riego.
- Escritura con temporal, validación de sintaxis/JSON, checksum, copia `.bak` y
  reemplazo sin borrar destino. No aplica código en caliente ni hace rollback
  automático. Limita archivos a 64 KiB. Solo nombres de la raíz.
- Cliente desde PC/servidor: `python tools/esp32_files.py list|health|reset`,
  `get nombre destino`, `put archivo-local nombre-remoto`. Lee clave local.
- Referencia completa y límites: `esp32/RECOVERY.md`. Pruebas locales en `tests/`;
  aceptación explícita en hardware: `tools/verify_recovery_hardware.py`.
- Respaldo previo USB en `.local-backups/pre-recovery-20261101/`, ignorado por Git;
  contiene secretos. Se conservaron los programas y jobs del dispositivo.
- Confirmado que el ESP32 tenía offset **+10800** pese al archivo local correcto.
  Se cargó `config.py` local con **-10800** (única diferencia con la configuración
  remota respaldada). El programa «Luces», zona6, diario 18:30–23:00, se conserva.
- El historial de sensores continúa modificándose por el servidor; no incluir
  esos cambios ajenos como parte del trabajo de recuperación.
- Verificaciones realizadas: 8 pruebas locales aprobadas; en hardware se probó
  fallo de importación y fallo dentro de un `main()` asyncio, leyendo/reparando
  por Wi-Fi y restaurando el controlador en ambos casos. Programas sin cambios.
  Archivos de arranque, recuperación y config descargados y comparados con el repo.
  Hora final: ESP32 `2026-11-01 13:02:32`, PC `13:02:33 -03`, offset `-10800`.

## Actualización: credenciales compartidas y editor web

- Por pedido del usuario se retiró la clave exclusiva de mantenimiento. Se usa
  la misma `API_KEY` del controlador; hoy está vacía y ambas APIs aceptan acceso
  sin autenticación. `recovery_config.json` conserva el valor de respaldo para
  cuando falle la importación del controlador; mantenerlo alineado si cambia.
- `app/files_api.py` es un proxy simple al mismo host del dispositivo, puerto 81.
  Usa `api_key` de su registro, calcula/verifica checksum y propaga errores.
  Rutas: `GET /devices/{name}/files`, `GET|PUT /devices/{name}/files/{filename}`,
  `POST /devices/{name}/maintenance/reset`. PUT JSON `{"content":"..."}`.
- `app/static/files.js` y sección «Archivos del ESP32»: listar, leer, contenido
  original y editable, enviar y reiniciar. Sin editor externo ni dependencias.
  Ediciones web se guardan en el ESP32, no automáticamente en el repo local.
- Despliegue confirmado: `/home/amuzlera/project/docker-compose.yml`, servicio
  `riego-backend`, contenedor `project-riego-backend-1`, puerto PC **8002** → 8001.
  Dispositivos e historial se montan desde `storage/` en `/data/`; no se necesitan
  mounts de claves adicionales. Actualizar con `docker compose up -d --build
  --no-deps riego-backend` desde `/home/amuzlera/project`.
- Pruebas actuales: 15 pruebas con unittest (6 de proxy y 9 de recuperación).
  El entorno Conda `riego` contiene FastAPI/httpx para ejecutarlas.

## Alcance y estado del relevamiento

- Proyecto local en `/home/amuzlera/project/riego`.
- Controlador físico ESP32 con MicroPython y UI/backend en esta misma PC.
- Se revisaron todos los archivos fuente, HTML, CSS, scripts, README, plantillas,
  configuración local y estructura del historial JSON. Los binarios `__pycache__`
  y los objetos internos de Git no son fuentes del proyecto.
- No se arrancaron servicios, instalaron dependencias, copiaron archivos al ESP32
  ni enviaron órdenes al hardware durante este relevamiento.
- No se verificó el despliegue activo: Docker no fue accesible desde el sandbox.
  Distinguir siempre configuración del repo de configuración efectiva del servidor.
- Ya había modificaciones locales en `storage/readings.json`; conservarlas.

## Arquitectura real

```text
Navegador
  └─ HTTP mismo origen → FastAPI en la PC
       ├─ / y /static → HTML + JavaScript + CSS
       ├─ JSON locales → dispositivos e historial de sensores
       └─ HTTP con httpx → ESP32 (configurado: 192.168.1.50:80)
                            ├─ GPIO / relés y DHT11
                            ├─ temporizadores persistidos en jobs.json
                            └─ programas semanales en programs.json
```

La PC administra dispositivos, sirve la UI, consulta sensores y reenvía órdenes.
Los programas semanales y los apagados temporizados se ejecutan **en el ESP32**;
no necesitan que la PC continúe encendida una vez configurados. El firmware sí
necesita conectarse a Wi-Fi durante su arranque antes de iniciar sus bucles.
No hay MQTT, base SQL, framework frontend ni compilación de assets.

## Mapa de archivos

| Archivo | Responsabilidad |
| --- | --- |
| `app/main.py` | FastAPI, rutas, proxy HTTP, ciclo de consulta de sensores |
| `app/esp32_client.py` | Cliente asíncrono hacia la API del ESP32 |
| `app/schemas.py` | Modelos Pydantic para dispositivos, pines, programas y acciones |
| `app/settings.py` | Rutas de persistencia y timeout por entorno |
| `app/storage.py` | `DeviceStore` y `SensorReadingStore`, persistencia JSON |
| `app/static/index.html` | Estructura de la UI en español |
| `app/static/app.js` | Estado en memoria, fetch, controles y vista semanal |
| `app/static/styles.css` | Tema oscuro, tarjetas y adaptación a móvil |
| `app/Dockerfile` | Imagen Python 3.12, Uvicorn en puerto 8001 |
| `app/requirements.txt` | fastapi, uvicorn[standard], httpx, pydantic sin versiones fijadas |
| `app/devices.json` | Dispositivos por defecto al ejecutar sin variables de entorno |
| `storage/devices.json` | Otra copia de configuración, destinada a persistencia Docker |
| `storage/readings.json` | Historial real de lecturas, versionado y mutable |
| `esp32/boot.py` | Inicialización temprana de salidas al estado configurado |
| `esp32/main.py` | Inicialización, Wi-Fi, NTP, restauración y bucles asíncronos |
| `esp32/config.py.example` | Plantilla de red, autenticación y hardware |
| `esp32/config.py` | Configuración local existente, ignorada por Git |
| `esp32/hardware.py` | Abstracciones de salidas y sensores digitales, ADC y DHT11 |
| `esp32/http_server.py` | Parser HTTP y router sobre uasyncio |
| `esp32/actions.py` | Registro de acciones locales permitidas |
| `esp32/scheduler.py` | Temporizadores `run_for`, persistencia y restauración |
| `esp32/programs.py` | CRUD y ejecución de programas semanales |
| `esp32/time_utils.py` | Sincronización NTP y conversión de hora local |
| `esp32/programs.json.example` | Estado inicial vacío del programador |
| `folder-copy.sh` | Copia recursiva al ESP32 usando mpremote |

`README.md`, `app/README.md` y `esp32/README.md` aportan instrucciones históricas,
pero algunas afirmaciones quedaron desactualizadas; el código es la referencia.

## Hardware y configuración local

Configuración observada en el archivo local y en la plantilla:

| Salida lógica | GPIO |
| --- | --- |
| zona1 | 19 |
| zona2 | 5 |
| zona3 | 18 |
| zona4 | 25 |
| zona5 | 26 |
| zona6 | 27 |

- Todas las zonas son salidas `active_low=True`, `default=False`.
  Activar una zona significa escribir 0 físico; desactivarla, 1.
  La API distingue `state` lógico de `raw` físico.
- Sensor `temp_humedad`: DHT11 en GPIO 4, temperatura y humedad ambiental.
  No se observa sensor de humedad de suelo en la configuración actual.
- Nombre de firmware: `riego-esp32`. Nombre en backend: `esp32-lab`.
- IP estática configurada: `192.168.1.50`, máscara `255.255.255.0`,
  gateway `192.168.1.1`, DNS `8.8.8.8`; puerto HTTP 80.
- Wi-Fi: timeout de conexión 15 s. NTP: `pool.ntp.org` al arrancar.
- Offset local: `-10800` segundos (Buenos Aires, UTC−3).
- No copiar credenciales Wi-Fi ni claves a documentación o respuestas.
  La plantilla versionada también contiene valores de Wi-Fi; tratarlos con cuidado.
- Los JSON de dispositivos observados apuntan a `http://192.168.1.50`,
  con dispositivo habilitado y API key vacía.

## Backend y persistencia

Variables leídas al importar `app/settings.py`:

| Variable | Valor por defecto |
| --- | --- |
| `RIEGO_DEVICES_FILE` | `app/devices.json` |
| `RIEGO_READINGS_FILE` | `app/readings.json` |
| `RIEGO_HTTP_TIMEOUT` | `5` segundos |

`storage/` **no se selecciona automáticamente**. La documentación del backend
describe montarlo en `/data` para Docker, pero este repo no contiene Compose ni
una definición del montaje o de esas variables. Comprobar el despliegue externo
antes de asumir puertos publicados, volúmenes o integración con cdashboard.

Los dispositivos se guardan como diccionario indexado por nombre, con `name`,
`base_url`, `api_key`, `description` y `enabled`. POST hace upsert.
Las lecturas se organizan como `{dispositivo: {sensor: [lecturas]}}`.
Cada lectura tiene `temperature`, `humidity`, `data`, `recorded_at`, `device`
y `sensor`. Se conservan como máximo 500 entradas por dispositivo/sensor.
`recorded_at` usa la zona horaria de la PC/contenedor; no la del ESP32.
El historial observado tenía 500 entradas de `esp32-lab/temp_humedad`.

Al iniciar FastAPI se consulta una vez a cada dispositivo habilitado; luego un
poller consulta `temp_humedad` cada 600 s. Las consultas son secuenciales y los
fallos se omiten. GET de sensor individual y de ambiente también intentan guardar
lecturas. La ruta de última lectura consulta disco sin contactar al ESP32.
Los stores se instancian al importar el módulo y crean directorios si hace falta.

## API

Backend local:

- `GET /`: UI; `GET /health`: salud de FastAPI; `/static`: assets.
- `GET|POST /devices`; `GET|PATCH|DELETE /devices/{name}`.
- Bajo `/devices/{name}` se reenvían las rutas del firmware listadas abajo.
- Adicional: `GET /devices/{name}/readings/latest?sensor=temp_humedad`.
- Dispositivo ausente: 404; deshabilitado al operarlo: 409;
  error de transporte hacia ESP32: 502 `esp32_unreachable`.
- Sin autenticación propia del backend. Las respuestas de dispositivos incluyen
  su `api_key`; considerar esto al cambiar el acceso a la UI/API.

Firmware (sin el prefijo `/devices/{name}`):

- `GET /health`, `/status`, `/pins`, `/pins/{pin}`.
- `POST /pins/{pin}/on|off|toggle|set|run_for`.
- `set`: `{"value": true}`; `run_for`: `{"seconds": 1200, "value": true}`.
- `GET /sensors`, `/sensors/{sensor}`, `/environment`, `/jobs`.
- `GET|POST /programs`; `PUT|DELETE /programs/{id}`.
- `GET /actions`; `POST /actions/{action}`; `POST /execute`.
- Acciones registradas: `all_off`, `set_output`, `set_output_by_name`.
  `/execute` busca una acción en ese registro; no evalúa código arbitrario.
- `/environment` mide el DHT11 y devuelve también hora local del ESP32.
- Si `API_KEY` tiene valor, se exige `X-API-Key` o `Authorization: Bearer`.
  El cliente de la PC envía ambos encabezados cuando tiene clave configurada.
- En backend, las acciones reciben `{"payload": {...}}`; `execute` recibe
  `{"name": "...", "args": {...}}`.

## Temporizadores y programas semanales

`JobScheduler` mantiene un job por pin. `run_for` aplica el valor inmediatamente,
reemplaza el job anterior y persiste en `jobs.json`; al vencer siempre apaga.
El bucle revisa vencimientos cada segundo. Guarda tiempos monotónicos y epoch.
Al arrancar carga los jobs como pendientes y busca restaurar los no vencidos
solo si considera plausible el epoch (`>= 1700000000`).

`WeeklyProgramScheduler` persiste `next_id` y programas en `programs.json`.
Formato de creación habitual:

```json
{
  "pin": "zona1",
  "days": [0, 2, 4],
  "periods": [{"start": "06:00", "end": "06:20"}],
  "enabled": true,
  "label": "Riego mañana"
}
```

Días 0=lunes a 6=domingo. Se admite más de una franja, cruce de medianoche,
formato legado `start`/`end` y franjas string `HH:MM-HH:MM`.
El firmware admite además nombres de días; el backend tipa los días como enteros.
Inicio inclusivo y fin exclusivo; inicio y fin iguales son inválidos.
Al cruzar medianoche, el día seleccionado corresponde al inicio de la franja.
Se evalúa al arrancar y cada 30 s, si el año local es al menos 2024.
Las franjas superpuestas usan contadores por pin para mantenerlo encendido hasta
que termine la última. Crear/editar/borrar no reconcilia inmediatamente: depende
del próximo ciclo. Jobs y programas no tienen coordinación entre sí.

## Comportamiento de la UI

- JavaScript directo, sin npm ni herramientas de build; fetch al mismo origen.
- Selector de dispositivo, control de zonas, encendido por minutos (20 por
  defecto), formulario CRUD de programas y resumen semanal por día.
- La UI convierte minutos a segundos antes de enviar `run_for`.
- Consulta pines cada 5 s; reconstruye tarjetas e inputs en cada respuesta.
- Los programas se consultan al cargar, cambiar dispositivo, actualizar o guardar;
  su indicador de ejecución no tiene actualización periódica propia.
- «Consultar sensor» obtiene **la última lectura persistida en la PC** mediante
  `/readings/latest`; no fuerza una medición ni consulta `/environment`.
- La hora que muestra ese botón es `recorded_at` formateada por el navegador.
- Al iniciar, ambiente queda en guiones hasta consultar. El cronograma lista las
  franjas por día de inicio; no divide visualmente los cruces de medianoche.

## Ejecución y carga de firmware

Ejemplo de ejecución manual desde la raíz, con dependencias ya instaladas:

```bash
cd /home/amuzlera/project/riego
RIEGO_DEVICES_FILE="$PWD/storage/devices.json" \
RIEGO_READINGS_FILE="$PWD/storage/readings.json" \
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Ese arranque inicia consultas al sensor y escritura del historial. El README usa
8000 y el nombre antiguo `riegov3`; el Dockerfile usa 8001. No asumir que alguno
sea el puerto actualmente publicado. El contexto de build del Dockerfile es `app/`.

Para copiar firmware cuando una tarea lo requiera:

```bash
./folder-copy.sh ./esp32
# Otro puerto serial:
MPREMOTE_PORT=/dev/ttyUSB1 ./folder-copy.sh ./esp32
```

El script usa `mpremote` de PATH o `conda run -n riego mpremote`, con puerto
por defecto `/dev/ttyUSB0`. Copia recursivamente, primero archivos comunes,
después `main.py` y al final `boot.py`. Omite cachés, `.pyc`, `log.txt` y `.bin`;
también copia README, ejemplos y `config.py` si están presentes. No limpia
archivos remotos sobrantes ni implementa un reinicio final explícito.

## Hallazgos para futuras tareas (sin corregir en este relevamiento)

1. `app/main.py` usa `response.ok` en las rutas de sensor individual y ambiente.
   Ese atributo corresponde a requests; httpx usa `is_success`/`is_error`.
   Revisar estas rutas: pueden fallar antes de guardar/devolver la respuesta.
   El poller usa `is_error` y no pasa por esa misma condición.
2. Al restaurar jobs se conservan `expires_at_ms` de antes del reinicio: no se
   recalculan desde el tiempo epoch restante. Verificar expiración tras reinicios.
   Verificar también la base epoch del firmware MicroPython concreto antes de
   confiar en el umbral fijo de plausibilidad.
3. Órdenes manuales y `all_off` no cancelan jobs ni programas. El programador
   semanal solo actúa al entrar/salir de ventanas, no impone el estado cada ciclo.
   Un apagado manual puede mantenerse durante una ventana y un job puede apagar
   una zona que un programa aún considera activa. No existe prioridad explícita.
4. Las lecturas DHT11 no tienen caché; `/status` y `/sensors` también miden.
   Un fallo del sensor puede hacer fallar la respuesta completa de estado.
5. Persistencia PC: escritura directa del JSON, sin reemplazo atómico;
   dispositivos sin lock y lecturas con lock únicamente por proceso.
   Evitar asumir soporte seguro para varios workers escritores.
6. Hay interpolación de campos en `innerHTML` en la UI, sin escape general.
   Revisarlo si se amplían entradas o exposición de la aplicación.
7. README desactualizados sobre dónde reside la lógica, rutas, lectura ambiental
   y despliegue. No hay suite de tests ni configuración de CI en este árbol.

## Criterios para continuar trabajando

- Revisar `git status` al comenzar y conservar cambios ajenos y datos históricos.
- Mantener separación entre código CPython de la PC y MicroPython del ESP32;
  no introducir dependencias CPython en firmware sin comprobar compatibilidad.
- Tratar GPIO, polaridad y estados de arranque como configuración de hardware real.
- Una revisión documental no requiere activar relés, flashear ni reiniciar equipos.
  Para tareas de operación, usar el alcance autorizado por el usuario.
- Para verificaciones sin hardware, preferir análisis estático y dobles de
  `machine`, `network`, tiempo y transporte HTTP. No arrancar la app como prueba
  inocua: su startup consulta equipos y escribe datos.
- Confirmar montaje/variables del servidor antes de editar una de las dos copias
  de `devices.json`. Mantener secretos fuera de nuevos documentos y commits.
- Actualizar este documento cuando cambien los hechos descritos; los hallazgos
  son observaciones del código, no fallos reproducidos en el dispositivo.
