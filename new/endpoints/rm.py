import os
from server_utils import send_response, parse_query

async def handle(writer, query):
    params = parse_query(query)
    filename = params.get("filename")

    try:
        os.remove(filename)
        send_response(writer, {"status": "Archivo eliminado", "file": filename})
    except OSError as e:
        # incluye FileNotFoundError, PermissionError, etc.
        send_response(writer, {"error": f"No se pudo eliminar: {str(e)}"}, "404 Not Found")
