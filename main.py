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

