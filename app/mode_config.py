"""
Configuración del modo de operación (direct vs remote).

direct: Llamadas van directo al ESP32 (comportamiento actual)
remote: Llamadas van vía servidor, placeholders por ahora
"""

import os
from enum import Enum

class Mode(str, Enum):
    DIRECT = "direct"
    REMOTE = "remote"

# Leer del ambiente o usar default "direct" (comportamiento actual)
CURRENT_MODE = os.getenv("RIEGO_MODE", "remote").lower()
if CURRENT_MODE not in [m.value for m in Mode]:
    CURRENT_MODE = Mode.DIRECT.value

def get_current_mode() -> str:
    """Devuelve el modo actual (direct o remote)"""
    return CURRENT_MODE

def is_direct_mode() -> bool:
    """True si estamos en modo directo"""
    return get_current_mode() == Mode.DIRECT.value

def is_remote_mode() -> bool:
    """True si estamos en modo remoto"""
    return get_current_mode() == Mode.REMOTE.value
