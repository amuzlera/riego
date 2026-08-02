import os
from server_utils import send_response, parse_query

async def handle(writer, query=""):
    params = parse_query(query)
    path = params.get("filename", ".") 

    try:
        files = os.listdir(path)
        send_response(writer, {"folder": path, "files": files})
    except Exception as e:
        send_response(writer, {"error": f"No se pudo listar '{path}': {repr(e)}"}, "400 Bad Request")
