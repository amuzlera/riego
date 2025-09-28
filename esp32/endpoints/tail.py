import os
from server_utils import send_response, parse_query


def check_file_exist(path, writer):
    try:
        os.stat(path)  # falla si no existe
    except OSError:
        send_response(writer, {"error": f"Archivo no encontrado: {path}"}, "404 Not Found")
        return False
    return True


def tail(filename, n=20):
    """Devuelve las últimas n líneas de un archivo de texto (MicroPython)."""
    with open(filename, "rb") as f:
        f.seek(0, 2)   # ir al final
        pos = f.tell()
        lines = []
        buf = bytearray()

        while pos > 0 and len(lines) < n:
            pos -= 1
            f.seek(pos)
            c = f.read(1)
            if c == b"\n":
                if buf:
                    # convertir buffer invertido a string
                    lines.append(bytes(reversed(buf)).decode())
                    buf = bytearray()
            else:
                buf.append(c[0])  # guardamos el byte

        # último fragmento si no terminaba en \n
        if buf:
            lines.append(bytes(reversed(buf)).decode())

    return list(reversed(lines))



async def handle(writer, query):
    params = parse_query(query)
    filename = params.get("filename")
    if not filename:
        send_response(writer, {"error": "Falta parametro filename"}, "400 Bad Request")
        return

    n = int(params.get("n", 20))  # por defecto 20
    if not check_file_exist(filename, writer):
        return

    try:
        lines = tail(filename, n)
        out = "\n".join(lines)
        send_response(writer, out)
    except Exception as e:
        send_response(writer, {"error": str(e)}, "500 Internal Server Error")
