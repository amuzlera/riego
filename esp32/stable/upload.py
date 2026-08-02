import os

from server_utils import parse_query, send_response

RESERVED_ROOT_FILES = {"boot.py", "boot_manager.py", "boot_state.json"}


def _normalize_relative_path(filename):
    filename = filename.replace("\\", "/").strip()
    if filename.startswith("./"):
        filename = filename[2:]
    while filename.startswith("/"):
        filename = filename[1:]
    return filename


def _is_path_safe(filename):
    filename = _normalize_relative_path(filename)
    if not filename or filename in (".", ".."):
        return False

    parts = filename.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False

    return True


def _resolve_target(filename, slot):
    filename = _normalize_relative_path(filename)
    slot = (slot or "dev").strip().lower()

    if not _is_path_safe(filename):
        raise ValueError("Ruta inválida")

    if slot == "stable":
        if filename in RESERVED_ROOT_FILES:
            raise ValueError("No se puede sobrescribir un archivo reservado")
        return "stable/" + filename

    if filename in RESERVED_ROOT_FILES:
        raise ValueError("No se puede sobrescribir un archivo reservado")
    if filename == "stable" or filename.startswith("stable/"):
        raise ValueError("Use slot=stable para escribir en la copia estable")
    return filename


def mkdirs(full_path):
    parts = full_path.split("/")[:-1]
    current = ""
    for part in parts:
        if part:
            current += part + "/"
            try:
                os.mkdir(current)
            except OSError:
                pass


async def handle(reader, writer, query, headers):
    params = parse_query(query)
    filename = params.get("filename")
    slot = params.get("slot", "dev")

    if not filename:
        send_response(writer, {"error": "Falta parametro filename"}, "400 Bad Request")
        return

    try:
        target = _resolve_target(filename, slot)
    except Exception as e:
        send_response(writer, {"error": str(e)}, "400 Bad Request")
        return

    content_length = int(headers.get("Content-Length", 0))
    if content_length == 0:
        send_response(writer, {"error": "Content-Length requerido"}, "411 Length Required")
        return

    try:
        mkdirs(target)
        with open(target, "wb") as f:
            bytes_read = 0
            while bytes_read < content_length:
                chunk = await reader.read(min(512, content_length - bytes_read))
                if not chunk:
                    break
                f.write(chunk)
                bytes_read += len(chunk)

        send_response(writer, {"status": "Archivo guardado", "file": target, "slot": slot})

    except Exception as e:
        send_response(writer, {"error": "No se pudo escribir {}: {}".format(target, repr(e))}, "500 Internal Server Error")
