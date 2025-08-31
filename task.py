import machine
import time

LED_PIN = 4
led = machine.Pin(LED_PIN, machine.Pin.OUT)

print(f"task.py ejecutando: parpadeo LED por 10 ciclos en el pin {LED_PIN}")

for i in range(1):
    led.value(1)
    time.sleep(1)
    led.value(0)
    time.sleep(1)

print("task.py finalizado")
