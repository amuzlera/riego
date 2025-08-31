import machine
import time

LED_PIN = 2  # Cambiá si usás otro pin
led = machine.Pin(LED_PIN, machine.Pin.OUT)

print("task.py ejecutando: parpadeo LED")

while True:
    led.value(1)
    time.sleep(1)
    led.value(0)
    time.sleep(1)
