from server_utils import send_response, parse_query, log
from machine import Pin
import ujson as json


def url_decode(s):
    """Decodifica una cadena URL encoded para MicroPython"""
    if not s:
        return s
    
    # Reemplazar %XX con caracteres
    result = []
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            try:
                hex_str = s[i+1:i+3]
                char_code = int(hex_str, 16)
                result.append(chr(char_code))
                i += 3
            except:
                result.append(s[i])
                i += 1
        elif s[i] == '+':
            result.append(' ')
            i += 1
        else:
            result.append(s[i])
            i += 1
    
    return ''.join(result)


async def handle(writer, query=""):
    """
    Ejecuta código Python en el ESP32.
    
    Parametros (query):
    - code: código Python a ejecutar (URL encoded)
    
    Ejemplo: /execute?code=pin=Pin(2,Pin.OUT)%0Apin.on()
    Retorna: {"result": salida, "error": null} o {"result": null, "error": mensaje}
    """
    params = parse_query(query)
    code = params.get("code")
    
    if not code:
        send_response(writer, {"error": "Falta parametro code"}, "400 Bad Request")
        return
    
    try:
        # Decodificar URL encoding
        code = url_decode(code)
        
        # Log del código recibido
        log(f"Received code: {code[:50]}...")
        
        # Crear un namespace seguro para ejecutar el código
        namespace = {
            "Pin": Pin,
            "print": print,
            "__name__": "__main__",
            "__builtins__": {},
        }
        
        # Capturar salida de print
        output = []
        last_result = None
        
        def safe_print(*args, **kwargs):
            output.append(" ".join(str(arg) for arg in args))
        
        namespace["print"] = safe_print
        
        # Ejecutar el código línea por línea para capturar el último resultado
        lines = code.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    last_result = eval(line, namespace)
                except:
                    # Si eval falla, intentar exec
                    exec(line, namespace)
        
        # Si hay output de print, usarlo; si no, retornar el último resultado
        if output:
            result = "\n".join(output)
        elif last_result is not None:
            result = str(last_result)
        else:
            result = "OK"
        
        log(f"Executed successfully")
        send_response(writer, {"result": result, "error": None})
        
    except SyntaxError as e:
        log(f"Syntax error: {e}")
        send_response(writer, {"result": None, "error": f"Syntax error: {str(e)}"}, "400 Bad Request")
    except Exception as e:
        log(f"Execution error: {e}")
        send_response(writer, {"result": None, "error": f"Error: {str(e)}"}, "400 Bad Request")
