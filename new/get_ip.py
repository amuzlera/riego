import network
import config

sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect(config.WIFI_SSID, config.WIFI_PASS)

while not sta_if.isconnected():
    pass

print("Conectado a WiFi:", sta_if.ifconfig())
