try:
    import ntptime
except ImportError:
    ntptime = None

try:
    import time
except ImportError:
    time = None


DEFAULT_TZ_OFFSET_SECONDS = 10800


def now_local(tz_offset_seconds=DEFAULT_TZ_OFFSET_SECONDS):
    if time is None:
        return None
    try:
        return time.localtime(time.time() + int(tz_offset_seconds))
    except Exception:
        return time.localtime()


def format_local_time(tz_offset_seconds=DEFAULT_TZ_OFFSET_SECONDS):
    local_time = now_local(tz_offset_seconds)
    if not local_time:
        return None

    try:
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            local_time[0],
            local_time[1],
            local_time[2],
            local_time[3],
            local_time[4],
            local_time[5],
        )
    except Exception:
        return None


def local_time_is_plausible(tz_offset_seconds=DEFAULT_TZ_OFFSET_SECONDS, minimum_year=2024):
    local_time = now_local(tz_offset_seconds)
    if not local_time:
        return False
    try:
        return int(local_time[0]) >= int(minimum_year)
    except Exception:
        return False


def sync_time_from_ntp(host="pool.ntp.org", tz_offset_seconds=DEFAULT_TZ_OFFSET_SECONDS):
    if ntptime is None or time is None:
        return None

    try:
        ntptime.host = host
        ntptime.settime()
        return now_local(tz_offset_seconds)
    except Exception as exc:
        print("No se pudo sincronizar NTP: {}".format(exc))
        return now_local(tz_offset_seconds)
