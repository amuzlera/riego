import time

# Días de la semana en español
SPANISH_WD = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5,
    "domingo": 6
}

DEFAULT_TZ = -3 * 3600  # UTC-3


def now_local(tz_offset=DEFAULT_TZ):
    """
    Devuelve struct_time en hora local (corrigiendo con tz_offset).
    """
    return time.localtime(time.time() + tz_offset)


def parse_hhmm_to_minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def minutes_since_midnight(t):
    """
    t: struct_time o similar
    """
    return t[3] * 60 + t[4]


def weekday_name_to_int(name: str):
    return SPANISH_WD.get(str(name).strip().lower())


# ----------------- FUTURO: sync de reloj -----------------

def sync_time_from_ntp(host="pool.ntp.org", tz_offset=DEFAULT_TZ):
    """
    Intenta sincronizar el RTC del ESP32 usando NTP.
    Requiere que la red esté conectada.
    """
    try:
        import ntptime
        ntptime.host = host
        ntptime.settime()  # ajusta RTC en UTC
        return now_local(tz_offset)
    except Exception as e:
        print("No se pudo sincronizar NTP:", e)
        return now_local(tz_offset)
