# Mantenimiento por Wi-Fi

Instalado y verificado en el ESP32 el 2026-11-01. IP actual: `192.168.1.50`.
La API de riego sigue en puerto 80; mantenimiento usa el **81**.

## Arranque y recuperación

1. `boot.py` apaga físicamente los seis relés (GPIO 19, 5, 18, 25, 26, 27,
   activos en bajo). No importa la configuración editable. Si se cambia el
   cableado o la polaridad, este archivo también debe actualizarse por USB.
2. `main.py` es un lanzador mínimo hacia `recovery.run()`.
3. `recovery.py` lee `recovery_config.json`, conecta Wi-Fi y levanta un servidor
   HTTP en un hilo separado, antes de importar el controlador.
4. Importa `controller.py` y ejecuta su `main()` asíncrono. Allí vive el código
   antes ubicado en `main.py`: hardware, NTP, API de riego y schedulers.
5. Si falla la importación o la ejecución del controlador, se apagan los relés,
   se conserva el error en memoria y mantenimiento sigue funcionando. No hay
   reinicio automático del controlador: reparar archivos y llamar a `/reset`.

Una escritura de código/configuración se aplica **al reiniciar**, no en caliente.
El cambio de signo a `TZ_OFFSET_SECONDS = -10800` se cargó desde `config.py` local.
Los programas y jobs existentes se conservaron.

Este aislamiento cubre errores Python del controlador y de su ciclo asyncio;
no constituye aislamiento de procesos. Ambos hilos comparten MicroPython, heap
y sistema de archivos. Un fallo nativo, agotamiento extremo de recursos, corte
eléctrico, problemas de Wi-Fi o código que cierre/reconfigure la red pueden
impedir el acceso. El servicio no ejecuta código subido antes del reinicio.

## Configuración y clave

`recovery_config.json` contiene red, IP, puerto y una copia de respaldo de la
misma `API_KEY` que usa el controlador. Existe una plantilla versionada.
La copia local está ignorada por Git y tiene permisos 600.

Por pedido del usuario, **no hay una credencial independiente**. Actualmente
`API_KEY` está vacía tanto en el controlador como en mantenimiento, por lo que
ambos permiten acceso sin autenticación en la red local. Si se configura una
clave, ambos aceptan `X-API-Key` o `Authorization: Bearer` con el mismo valor.
Al importar correctamente el controlador, mantenimiento toma `config.API_KEY`;
si falla la importación usa la copia de `recovery_config.json`. Al cambiar
credenciales, mantener esa copia alineada para conservar el mismo acceso durante
una recuperación.

La red de mantenimiento sigue siendo independiente de `config.py`: un error en
ese archivo no impide conectar Wi-Fi. Cambios de red de mantenimiento requieren
USB. No se puede consultar `recovery_config.json` por HTTP porque contiene datos
de Wi-Fi. Se usa HTTP local, sin TLS.

## Endpoints (puerto 81)

| Método/ruta | Resultado |
| --- | --- |
| `GET /health` | Estado `starting/running/failed/stopped` del controlador y último error |
| `GET /files` | Archivos de la raíz con tamaño y permiso de escritura |
| `GET /files/config.py` | Contenido crudo UTF-8 y header `X-Content-SHA256` |
| `PUT /files/controller.py` | Reemplazo con cuerpo crudo, `Content-Length` y `X-Content-SHA256` |
| `POST /reset` | Responde y reinicia el ESP32 para aplicar los cambios |

Se admiten nombres simples en la raíz, sin directorios, escapes URL ni `..`.
Se pueden modificar los módulos de aplicación `controller.py`, `config.py`,
`hardware.py`, `actions.py`, `http_server.py`, `scheduler.py`, `programs.py`,
`time_utils.py`, además de archivos `.txt` y `.json` no reservados.
No se permiten nuevos módulos arbitrarios que puedan suplantar dependencias del
servicio, ni archivos `.mpy`.

`boot.py`, `main.py`, `recovery.py` y `recovery_config.json` están protegidos contra
escritura por Wi-Fi: se actualizan por USB. Los tres primeros se pueden leer;
la configuración secreta de recuperación no. `jobs.json` y `programs.json` son
consultables, pero su escritura requiere la API de riego en puerto 80 para evitar
conflictos con el estado en memoria de los schedulers.

## Cómo actualizar desde esta PC o servidor

Desde la raíz del repositorio, usando Python estándar, sin instalar paquetes:

```bash
python tools/esp32_files.py health
python tools/esp32_files.py list
python tools/esp32_files.py get controller.py /tmp/controller-remoto.py
# Editar primero el archivo del proyecto local y luego subirlo:
python tools/esp32_files.py put esp32/controller.py controller.py
python tools/esp32_files.py reset
python tools/esp32_files.py health
```

El cliente lee la clave local sin imprimirla y verifica SHA-256 de las descargas.
Para otra máquina/IP se puede usar `--host` y `--config` antes del subcomando.
Una respuesta `failed` permite leer el error, corregir el archivo local, subirlo
y reiniciar de nuevo. No requiere que FastAPI de la PC esté funcionando.
La UI del backend local incluye una sección «Archivos del ESP32», con selector,
contenido remoto a la izquierda y texto editable a la derecha. «Enviar al ESP32»
guarda el archivo y «Reiniciar ESP32» aplica los cambios. Los archivos protegidos
se muestran en modo solo lectura. El backend reenvía al puerto 81 y utiliza la
misma `api_key` del dispositivo; no requiere un secreto adicional ni nuevos mounts.
La edición web modifica el archivo remoto; no escribe automáticamente el código
en el checkout local del proyecto.

## Protección frente a cargas fallidas

- Máximo 64 KiB por archivo, cabeceras limitadas y timeout de socket de 5 s.
- Rechaza cuerpos incompletos, longitud inválida y checksum incorrecto.
- Compila `.py` sin ejecutarlo para comprobar sintaxis, y valida `.json`.
- Escribe un temporal `.tmp`, lo verifica y guarda una copia previa `.bak`.
- Reemplaza con `os.rename` sin borrar primero el destino (verificado en el
  filesystem del equipo). Un temporal incompleto no se importa al arrancar.
- `.bak` se puede descargar con GET; para restaurar se sube su contenido al
  nombre original. Es la versión anterior, no una garantía de versión funcional.
- El reemplazo es por archivo: no hay transacción para conjuntos de archivos,
  rollback automático ni protección ante dos ediciones simultáneas del usuario.

## Reproducción y verificaciones

Antes de instalar se guardó un respaldo USB local, ignorado por Git, en
`.local-backups/pre-recovery-20261101/` (incluye configuración sensible).
Para una instalación nueva, copiar dependencias/configuración antes del lanzador
`main.py` y `boot.py`, y reiniciar al terminar. No sobrescribir `programs.json`
ni `jobs.json` con plantillas. `folder-copy.sh` sigue siendo una copia completa;
para un cambio de aplicación individual conviene usar el cliente Wi-Fi.

Pruebas locales sin hardware:

```bash
python -m unittest discover -s tests -v
```

Prueba explícita de recuperación en hardware (interrumpe temporalmente el
controlador y procura restaurarlo en `finally`; no ejecutar como test ordinario):

```bash
python tools/verify_recovery_hardware.py
python tools/verify_recovery_hardware.py --runtime
```

Comprueba autenticación, archivos protegidos, rechazo de sintaxis inválida,
lectura y reparación por Wi-Fi con controlador fallando, recuperación tras
reiniciar y conservación de programas. Mantener USB disponible durante pruebas.
