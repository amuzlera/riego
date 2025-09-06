import machine
import uasyncio as asyncio

LED_PIN = 4
led = machine.Pin(LED_PIN, machine.Pin.OUT)

async def riego_loop():
    while True:
        print("Parpadeo LED")
        for i in range(3):
            led.value(1)
            await asyncio.sleep(1)
            led.value(0)
            await asyncio.sleep(1)
        await asyncio.sleep(10) 
