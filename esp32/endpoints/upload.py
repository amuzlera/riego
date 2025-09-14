from server_utils import send_response, parse_query
import os

async def handle(reader, writer, query, headers):
    """
    Maneja la subida de archivo:
    - query: string con parámetros (ej. "filename=archivo.txt")
    - content: viene en el body
    """

    params = parse_query(query)
    print(params)
    filename = params.get("filename")
    if not filename:
        send_response(writer, {"error": "Falta parametro filename"}, "400 Bad Request")
        return
    # Evitar path traversal
    if ".." in filename or filename.startswith("/"):
        send_response(writer, {"error": "Ruta inválida"}, "400 Bad Request")
        return

    # Validar Content-Length
    content_length = int(headers.get("Content-Length", 0))
    if content_length == 0:
        send_response(writer, {"error": "Content-Length requerido"}, "411 Length Required")
        return

    try:
        # Crea el path si no existe
        mkdirs(filename)
        # Leer contenido en chunks y escribirlo
        with open(filename, "wb") as f:
            bytes_read = 0
            while bytes_read < content_length:
                chunk = await reader.read(min(512, content_length - bytes_read))
                if not chunk:
                    break
                f.write(chunk)
                bytes_read += len(chunk)

        send_response(writer, {"status": "Archivo guardado", "file": filename})

    except Exception as e:
        send_response(writer, {"error": f"No se pudo escribir {filename}: {repr(e)}"}, "500 Internal Server Error")


def mkdirs(full_path):
    """
    Crea recursivamente todas las carpetas necesarias en el path.
    path: "carpeta1/carpeta2/carpeta3"
    """
    parts = full_path.split("/")[:-1]
    current = ""
    for part in parts:
        if part:  # ignora partes vacías
            current += part + "/"
            try:
                os.mkdir(current)
            except OSError:
                # ya existe
                pass
