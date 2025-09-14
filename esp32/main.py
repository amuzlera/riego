import uasyncio as asyncio
from server import start_server
from task import riego_loop


async def main():
    
    asyncio.create_task(start_server())   # tu endpoint HTTP
    asyncio.create_task(riego_loop())     # tu loop de riego
    while True:
        await asyncio.sleep(1)

print("RUNING MAIN")
asyncio.run(main())

# mpremote connect /dev/ttyUSB0

'''
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/ls.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/cat.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/upload.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/rm.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/endpoints/__init__.py :endpoints/
mpremote connect /dev/ttyUSB0 fs cp esp32/server.py :
mpremote connect /dev/ttyUSB0 fs cp esp32/main.py :

'''
