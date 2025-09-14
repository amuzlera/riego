import os
from server_utils import send_response, parse_query


def check_file_exist(path, writer):
    try:
        # Esto falla si el archivo no existe
        stat_info = os.stat(path)
    except OSError:
        send_response(writer, {"error": f"Archivo no encontrado: {path}"}, "404 Not Found")
        return

async def handle(writer, query):
    params = parse_query(query)
    filename = params.get("filename")
    if not filename:
        send_response(writer, {"error": "Falta parametro filename"}, "400 Bad Request")
        return

    check_file_exist(filename, writer)
    with open(filename) as f:
        content = f.read()
    send_response(writer, {"file": filename, "content": content})
