import machine
import time

LED_PIN = 2
led = machine.Pin(LED_PIN, machine.Pin.OUT)

print("task.py ejecutando: parpadeo LED por 10 ciclos")

for i in range(10):
    led.value(1)
    time.sleep(1)
    led.value(0)
    time.sleep(1)

print("task.py finalizado")
