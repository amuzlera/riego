import io
import sys

import uasyncio as asyncio

LAST_LOG_FILE = "last_log.txt"
BOOT_LOG_FILE = "log.txt"


def _write_boot_traceback(exc: BaseException):
    try:
        import traceback

        text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    except Exception:
        try:
            buf = io.StringIO()
            sys.print_exception(exc, buf)
            text = buf.getvalue()
        except Exception:
            text = repr(exc)

    try:
        for path in (BOOT_LOG_FILE, LAST_LOG_FILE):
            with open(path, "a") as f:
                f.write("BOOT ERROR\n")
                for line in text.splitlines():
                    f.write(line + "\n")
    except Exception:
        pass


async def _serve_only():
    from server import start_server

    await start_server()
    while True:
        await asyncio.sleep(1)


async def _main_loop():
    from server import start_server
    from server_utils import log, log_exception
    from task import riego_scheduler_loop

    log("Iniciando sistema")
    await start_server()

    try:
        from time_utils import sync_time_from_ntp

        t = sync_time_from_ntp()
        log(f"Hora actual: {t}")
    except Exception as e:
        log_exception("NTP sync failed", e)

    asyncio.create_task(riego_scheduler_loop(poll_s=5))

    while True:
        await asyncio.sleep(1)


async def _safe_start():
    while True:
        try:
            await _main_loop()
        except Exception as e:
            _write_boot_traceback(e)
            try:
                from server_utils import log_exception

                log_exception("main loop failed", e)
            except Exception:
                pass
            await asyncio.sleep(5)


def _boot():
    try:
        asyncio.run(_safe_start())
    except Exception as e:
        _write_boot_traceback(e)
        try:
            asyncio.run(_serve_only())
        except Exception as inner:
            _write_boot_traceback(inner)


print("RUNNING MAIN")
_boot()
