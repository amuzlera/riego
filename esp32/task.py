import uasyncio as asyncio
import ujson as json
from machine import Pin
from server_utils import log
from time_utils import now_local

# ------------------ Helpers de día/tiempo ------------------

SPANISH_WD = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5,
    "domingo": 6
}


def parse_hhmm_to_minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def minutes_since_midnight(t):
    # t = time.localtime()
    return t[3] * 60 + t[4]

# ------------------ Carga y parsing de config ------------------


def _normalize_day_entries(entries):
    """
    entries: lista de objetos { "start": "HH:MM", "duration_min": int }
    Filtra inválidos y mapea a (start_min, duration_s)
    """
    norm = []
    if not isinstance(entries, list):
        return norm
    for obj in entries:
        try:
            start = obj.get("start")
            dur_m = int(obj.get("duration_min"))
            sm = parse_hhmm_to_minutes(start)
            if dur_m > 0:
                norm.append((sm, dur_m * 60))
        except Exception as e:
            log(e)
    return norm


def load_config(path):
    """
    Devuelve un dict con:
      zones: {name: pin}
      schedule: { wd_int: [(start_min, duration_s), ...] }
      policy: {mode, include?, multipliers?}
    """
    try:
        with open(path, "r") as f:
            raw = json.load(f)
    except Exception as e:
        log(f"Config: no se pudo leer: {e}")
        return {
            "zones": {},
            "schedule": {},
            "policy": {"mode": "all_same_time"}
        }

    zones = raw.get("zones", {})
    prog = raw.get("programed_times", {})
    policy = raw.get("policy", {"mode": "all_same_time"})

    schedule = {}
    for day_name, entries in prog.items():
        wd = SPANISH_WD.get(str(day_name).strip().lower())
        if wd is None:
            log(f"Config: día inválido:  {day_name}")
            continue
        day_list = _normalize_day_entries(entries)
        if day_list:
            schedule[wd] = sorted(day_list, key=lambda x: x[0])  # por hora
    return {
        "zones": zones,
        "schedule": schedule,
        "policy": policy
    }

# ------------------ Control de zonas ------------------


class ZonesController:
    def __init__(self, zones_map):
        """
        zones_map: {"zona1": pin, "zona2": pin, ...}
        """
        self.zones = {}
        for name, pin_num in zones_map.items():
            try:
                self.zones[name] = Pin(int(pin_num), Pin.OUT, value=0)
            except Exception as e:
                log(f'Pin inválido para, {name} : {pin_num}, {e}')

    def names(self):
        return list(self.zones.keys())

    def on(self, name):
        if name in self.zones:
            self.zones[name].value(1)

    def off(self, name):
        if name in self.zones:
            self.zones[name].value(0)

    def off_all(self):
        for p in self.zones.values():
            p.value(0)

# ------------------ Políticas ------------------


def resolve_policy(policy, zones_available, base_duration_s):
    """
    Retorna lista de (zona_name, duration_s) en orden de riego.
    """
    mode = (policy or {}).get("mode", "all_same_time")
    include = policy.get("include", None)
    multipliers = policy.get("multipliers", {})

    # 1) Zonas a incluir
    if include is None:
        selected = list(zones_available)  # todas
    else:
        selected = [z for z in include if z in zones_available]

    # 2) Duraciones
    plan = []
    if mode == "all_same_time" or mode == "only_zones":
        for z in selected:
            plan.append((z, base_duration_s))
    elif mode == "multipliers":
        for z in selected:
            k = multipliers.get(z, 1.0)
            dur = int(base_duration_s * float(k))
            if dur > 0:
                plan.append((z, dur))
    else:
        # fallback
        for z in selected:
            plan.append((z, base_duration_s))

    return plan

# ------------------ Scheduler ------------------


class ProgramScheduler:
    def __init__(self, zones_ctrl):
        self.zc = zones_ctrl
        self._lock = asyncio.Lock()
        self._already_run_keys = set()  # "YYYYMMDD-wd-start_min"

    def _make_key(self, t, wd, start_min):
        y, mo, d = t[0], t[1], t[2]
        return "{}{:02d}{:02d}-{}-{}".format(y, mo, d, wd, start_min)

    async def run_program(self, plan):
        """
        plan: lista de (zona_name, duration_s) para ejecutar secuencialmente.
        Usa lock para serializar con otros programas solapados.
        """
        async with self._lock:
            try:
                for name, dur in plan:
                    log(f">> Riego {name} por {dur} s")
                    self.zc.on(name)
                    await asyncio.sleep(dur)
                    self.zc.off(name)
                log("<< Programa finalizado")
            finally:
                self.zc.off_all()

    async def tick(self, schedule, policy):
        """
        Chequea si algún evento debe dispararse "ahora".
        Retorna plan si debe disparar, o None si no.
        """
        t = now_local()
        wd = t[6]
        minute_now = minutes_since_midnight(t)

        day_list = schedule.get(wd, [])
        for start_min, duration_s in day_list:
            # Disparo exacto cuando coincide el minuto (tolerancia de 0..59s)
            # clave por fecha + minuto de inicio
            key = self._make_key(t, wd, start_min)
            if start_min == minute_now and key not in self._already_run_keys:
                self._already_run_keys.add(key)
                plan = resolve_policy(policy, self.zc.names(), duration_s)
                return plan
        return None

# ------------------ Próximo evento ------------------


def next_event_in(schedule):
    """
    Devuelve segundos hasta el próximo evento programado
    (o None si no hay nada futuro).
    """
    t = now_local()
    wd_now = t[6]
    min_now = minutes_since_midnight(t)

    best_delta = None
    for delta_day in range(0, 7):  # mirar la semana completa
        wd = (wd_now + delta_day) % 7
        if wd not in schedule:
            continue
        for start_min, _ in schedule[wd]:
            abs_min_now = wd_now * 1440 + min_now
            abs_min_evt = wd * 1440 + start_min + delta_day * 1440
            delta = abs_min_evt - abs_min_now
            if delta < 0:
                continue
            sec = delta * 60
            if best_delta is None or sec < best_delta:
                best_delta = sec
    return best_delta

# ------------------ Loop principal ------------------


async def riego_scheduler_loop(config_path, poll_s=1, reload_s=3):
    """
    - Relee config cada 'reload_s' segundos.
    - Chequea disparos cada 'poll_s' segundos.
    - Ejecuta programas secuencialmente, aplicando la política.
    - Loguea hora actual y tiempo hasta el próximo evento (1 vez por minuto).
    """
    print("RUNNING riego_scheduler_loop")
    last_cfg_text = None
    cfg = load_config(config_path)
    zc = ZonesController(cfg["zones"] or {"zona1": 4})  # fallback a LED pin 4
    sched = ProgramScheduler(zc)

    schedule = cfg["schedule"]
    policy = cfg["policy"]

    reload_acc = 0
    last_reported_min = None  # throttle: log una vez por minuto restante

    while True:
        # Reload periódico
        if reload_s and reload_acc <= 0:
            try:
                with open(config_path, "r") as f:
                    cfg_text = f.read()
            except Exception as e:
                log(e)
                cfg_text = None
            if cfg_text and cfg_text != last_cfg_text:
                try:
                    cfg = json.loads(cfg_text)
                    zc = ZonesController(cfg.get("zones", zc.zones))
                    schedule = load_config(config_path)["schedule"]
                    policy = cfg.get("policy", policy)
                    # reinicia estado de ejecución
                    sched = ProgramScheduler(zc)
                    log("Config recargada.")
                    last_cfg_text = cfg_text
                    # forzar log inmediato del próximo evento
                    last_reported_min = None
                except Exception as e:
                    log(f"Error parseando config: {e}")
            reload_acc = reload_s

        # Tick de programación
        plan = await sched.tick(schedule, policy)
        if plan:
            # Lanza el programa sin bloquear el loop de polling
            asyncio.create_task(sched.run_program(plan))
            # al disparar, forzamos logeo del próximo evento en el siguiente ciclo
            last_reported_min = None

        # ---- Log de hora y countdown al próximo evento (1 vez por minuto) ----
        tnow = now_local()
        wait_s = next_event_in(schedule)
        if wait_s is None:
            if last_reported_min != "none":
                log("No hay ejecuciones futuras programadas")
                last_reported_min = "none"
        else:
            remaining_min = wait_s // 60
            if remaining_min != last_reported_min:
                hh = wait_s // 3600
                mm = (wait_s % 3600) // 60
                ss = wait_s % 60
                log("Tiempo hasta la proxima ejecucion: {}h {}m {}s".format(hh, mm, ss))
                last_reported_min = remaining_min

        await asyncio.sleep(poll_s)
        if reload_acc:
            reload_acc -= poll_s
