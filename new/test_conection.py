import network
import urequests
import time

# Configura tus credenciales
import config

WIFI_SSID = config.WIFI_SSID
WIFI_PASS = config.WIFI_PASS
GITHUB_RAW_TASK = config.GITHUB_RAW_TASK
GITHUB_RAW_CONFIG = config.GITHUB_RAW_CONFIG


print(f"WIFI_SSID: {WIFI_SSID}")
print(f"WIFI_PASSWORD: {WIFI_PASS}")
# Conectar a WiFi
print("Conectando a WiFi...")
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect(WIFI_SSID, WIFI_PASS)

while not sta_if.isconnected():
    print(".", end="")
    time.sleep(1)

print("\nConectado! IP:", sta_if.ifconfig())

# Probar conexión HTTP
try:
    print("Haciendo request a https://raw.githubusercontent.com/amuzlera/riego/main/task.py...")
    r = urequests.get("https://raw.githubusercontent.com/amuzlera/riego/main/task.py")
    print("Status:", r.status_code)
    print("Contenido:", r.text[:100])  # Muestra primeros 100 chars
    r.close()
except Exception as e:
    print("Error en request:", e)
