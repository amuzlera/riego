const state = {
  devices: [],
  deviceName: null,
  pins: [],
  programs: [],
  activePrograms: {},
  editingProgramId: null,
};

const WEEK_DAYS = [
  { id: 0, short: "Lu", long: "Lunes" },
  { id: 1, short: "Ma", long: "Martes" },
  { id: 2, short: "Mi", long: "Miércoles" },
  { id: 3, short: "Ju", long: "Jueves" },
  { id: 4, short: "Vi", long: "Viernes" },
  { id: 5, short: "Sa", long: "Sábado" },
  { id: 6, short: "Do", long: "Domingo" },
];

const els = {
  status: document.getElementById("connectionStatus"),
  deviceSelect: document.getElementById("deviceSelect"),
  deviceUrl: document.getElementById("deviceUrl"),
  deviceDescription: document.getElementById("deviceDescription"),
  environmentButton: document.getElementById("environmentButton"),
  envTemperature: document.getElementById("envTemperature"),
  envHumidity: document.getElementById("envHumidity"),
  envTime: document.getElementById("envTime"),
  programsRefreshButton: document.getElementById("programsRefreshButton"),
  programForm: document.getElementById("programForm"),
  programId: document.getElementById("programId"),
  programPin: document.getElementById("programPin"),
  programLabel: document.getElementById("programLabel"),
  programEnabled: document.getElementById("programEnabled"),
  programDays: document.getElementById("programDays"),
  programPeriods: document.getElementById("programPeriods"),
  programAddPeriodButton: document.getElementById("programAddPeriodButton"),
  programCancelButton: document.getElementById("programCancelButton"),
  programSchedule: document.getElementById("programSchedule"),
  programsGrid: document.getElementById("programsGrid"),
  pinsGrid: document.getElementById("pinsGrid"),
  logBox: document.getElementById("logBox"),
  refreshButton: document.getElementById("refreshButton"),
};

function log(payload) {
  if (typeof payload === "string") {
    els.logBox.textContent = payload;
    return;
  }
  els.logBox.textContent = JSON.stringify(payload, null, 2);
}

function setStatus(text, kind = "idle") {
  els.status.textContent = text;
  els.status.dataset.kind = kind;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let data = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    data = { text: await response.text() };
  }

  if (!response.ok) {
    throw new Error(data?.detail || data?.error || data?.text || "request_failed");
  }

  return data;
}

function pinIsOn(pin) {
  if (typeof pin.state === "boolean") return pin.state;
  if (typeof pin.state === "number") return pin.state !== 0;
  return Boolean(pin.state);
}

function pinStateLabel(pin) {
  return pinIsOn(pin) ? "Activo" : "Inactivo";
}

function pinActionLabel(pin) {
  return pinIsOn(pin) ? "Apagar" : "Prender";
}

function normalizePeriods(program) {
  if (Array.isArray(program?.periods) && program.periods.length) {
    return program.periods.map((period) => ({
      start: period.start || "",
      end: period.end || "",
    }));
  }

  if (program?.start && program?.end) {
    return [{ start: program.start, end: program.end }];
  }

  return [];
}

function renderDevices() {
  els.deviceSelect.innerHTML = "";

  if (state.devices.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No hay dispositivos";
    els.deviceSelect.appendChild(option);
    els.deviceSelect.disabled = true;
    return;
  }

  els.deviceSelect.disabled = false;
  for (const device of state.devices) {
    const option = document.createElement("option");
    option.value = device.name;
    option.textContent = device.description ? `${device.name} - ${device.description}` : device.name;
    els.deviceSelect.appendChild(option);
  }

  if (!state.deviceName || !state.devices.some((d) => d.name === state.deviceName)) {
    state.deviceName = state.devices[0].name;
  }

  els.deviceSelect.value = state.deviceName;
}

function renderMeta(device) {
  els.deviceUrl.textContent = device?.base_url || "-";
  els.deviceDescription.textContent = device?.description || "-";
}

function renderProgramDayChecks() {
  els.programDays.innerHTML = WEEK_DAYS.map((day) => `
    <label class="day-check">
      <input type="checkbox" data-day-id="${day.id}" />
      <span>${day.short}</span>
    </label>
  `).join("");
}

function renderProgramPinOptions() {
  const pinNames = Object.keys(state.pins || {});
  const currentValue = els.programPin.value;
  els.programPin.innerHTML = "";

  if (pinNames.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Sin pines";
    els.programPin.appendChild(option);
    els.programPin.disabled = true;
    return;
  }

  els.programPin.disabled = false;
  for (const pinName of pinNames) {
    const option = document.createElement("option");
    option.value = pinName;
    option.textContent = pinName;
    els.programPin.appendChild(option);
  }

  els.programPin.value = pinNames.includes(currentValue) ? currentValue : pinNames[0];
}

function createPeriodRow(period = {}) {
  const row = document.createElement("div");
  row.className = "period-row";
  row.innerHTML = `
    <label>
      <span class="meta-label">Inicio</span>
      <input class="input" type="time" data-period-start value="${period.start || "06:00"}" />
    </label>
    <label>
      <span class="meta-label">Fin</span>
      <input class="input" type="time" data-period-end value="${period.end || "06:20"}" />
    </label>
    <button type="button" class="button ghost period-remove">Quitar</button>
  `;
  return row;
}

function renderProgramPeriods(periods = []) {
  els.programPeriods.innerHTML = "";
  const rows = periods.length ? periods : [{ start: "06:00", end: "06:20" }];
  rows.forEach((period) => {
    els.programPeriods.appendChild(createPeriodRow(period));
  });
}

function clearProgramForm() {
  state.editingProgramId = null;
  els.programId.value = "";
  els.programLabel.value = "";
  els.programEnabled.checked = true;

  const dayChecks = els.programDays.querySelectorAll('input[type="checkbox"][data-day-id]');
  dayChecks.forEach((checkbox) => {
    checkbox.checked = true;
  });

  renderProgramPinOptions();
  renderProgramPeriods();
}

function fillProgramForm(program) {
  state.editingProgramId = program.id;
  els.programId.value = String(program.id);
  els.programPin.value = program.pin;
  els.programLabel.value = program.label || "";
  els.programEnabled.checked = Boolean(program.enabled);

  const selectedDays = new Set((program.days || []).map((day) => Number(day)));
  const dayChecks = els.programDays.querySelectorAll('input[type="checkbox"][data-day-id]');
  dayChecks.forEach((checkbox) => {
    checkbox.checked = selectedDays.has(Number(checkbox.dataset.dayId));
  });

  renderProgramPeriods(normalizePeriods(program));
}

function getSelectedProgramDays() {
  return Array.from(els.programDays.querySelectorAll('input[type="checkbox"][data-day-id]'))
    .filter((checkbox) => checkbox.checked)
    .map((checkbox) => Number(checkbox.dataset.dayId));
}

function getProgramPeriods() {
  return Array.from(els.programPeriods.querySelectorAll(".period-row")).map((row) => {
    const start = row.querySelector("[data-period-start]")?.value || "";
    const end = row.querySelector("[data-period-end]")?.value || "";
    return { start, end };
  }).filter((period) => period.start && period.end);
}

function dayNames(days) {
  const values = (days || []).map((day) => Number(day));
  return WEEK_DAYS.filter((day) => values.includes(day.id)).map((day) => day.short).join(", ");
}

function formatPeriods(periods) {
  const values = normalizePeriods({ periods });
  if (!values.length) return "Sin franjas";
  return values.map((period) => `${period.start} - ${period.end}`).join("<br />");
}

function timeToMinutes(value) {
  if (typeof value !== "string" || !value.includes(":")) return 0;
  const [hourText, minuteText] = value.split(":", 2);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return 0;
  return hour * 60 + minute;
}

function scheduleProgramsForDay(dayId) {
  const items = [];
  for (const program of state.programs) {
    const days = new Set((program.days || []).map((day) => Number(day)));
    if (!days.has(dayId)) continue;

    for (const period of normalizePeriods(program)) {
      items.push({
        id: program.id,
        label: program.label || program.pin,
        pin: program.pin,
        enabled: Boolean(program.enabled),
        start: period.start,
        end: period.end,
      });
    }
  }

  return items.sort((a, b) => timeToMinutes(a.start) - timeToMinutes(b.start));
}

function renderSchedule() {
  if (!els.programSchedule) return;

  els.programSchedule.innerHTML = "";

  for (const day of WEEK_DAYS) {
    const items = scheduleProgramsForDay(day.id);
    const dayCard = document.createElement("div");
    dayCard.className = "schedule-day";
    dayCard.innerHTML = `
      <div class="schedule-day-head">
        <div class="schedule-day-title">${day.long}</div>
        <div class="schedule-day-count">${items.length} franja${items.length === 1 ? "" : "s"}</div>
      </div>
    `;

    if (items.length === 0) {
      const empty = document.createElement("div");
      empty.className = "schedule-item";
      empty.innerHTML = `
        <div class="schedule-item-title">Sin programas</div>
        <div class="schedule-item-meta">No hay riegos configurados para este día.</div>
      `;
      dayCard.appendChild(empty);
    } else {
      for (const item of items) {
        const entry = document.createElement("div");
        entry.className = "schedule-item";
        entry.innerHTML = `
          <div class="schedule-item-title">${item.label}</div>
          <div class="schedule-item-meta">
            ${item.pin}<br />
            ${item.start} - ${item.end}${item.enabled ? "" : "<br />Pausado"}
          </div>
        `;
        dayCard.appendChild(entry);
      }
    }

    els.programSchedule.appendChild(dayCard);
  }
}

function isProgramActive(program) {
  const prefix = `${program.id}:`;
  return Object.keys(state.activePrograms || {}).some((key) => key.startsWith(prefix));
}

function renderPrograms(payload) {
  state.programs = payload?.programs || [];
  state.activePrograms = payload?.active || {};
  renderSchedule();

  els.programsGrid.innerHTML = "";

  if (state.programs.length === 0) {
    els.programsGrid.innerHTML = `
      <div class="program-card">
        <div class="program-card-head">
          <div>
            <div class="pin-name">Sin programas</div>
            <div class="program-meta">Todavía no hay reglas semanales cargadas.</div>
          </div>
        </div>
      </div>
    `;
    return;
  }

  for (const program of state.programs) {
    const active = isProgramActive(program);
    const enabled = Boolean(program.enabled);
    const card = document.createElement("div");
    card.className = "program-card";
    card.innerHTML = `
      <div class="program-card-head">
        <div>
          <div class="pin-name">${program.label || program.pin}</div>
          <div class="program-meta">
            Pin: ${program.pin}<br />
            Días: ${dayNames(program.days) || "Sin días"}
            <div class="program-periods">${formatPeriods(program.periods)}</div>
          </div>
        </div>
        <div class="program-badges">
          <span class="badge ${enabled ? "ok" : "warn"}">${enabled ? "Activo" : "Pausado"}</span>
          <span class="badge ${active ? "ok" : "warn"}">${active ? "Ejecutando" : "Libre"}</span>
        </div>
      </div>
      <div class="program-card-actions">
        <button class="button muted" data-program-action="edit" data-program-id="${program.id}">Editar</button>
        <button class="button ghost" data-program-action="delete" data-program-id="${program.id}">Borrar</button>
      </div>
    `;
    els.programsGrid.appendChild(card);
  }
}

function renderEnvironment(data) {
  els.envTemperature.textContent =
    data && data.temperature !== undefined && data.temperature !== null
      ? `${data.temperature} °C`
      : "-";
  els.envHumidity.textContent =
    data && data.humidity !== undefined && data.humidity !== null
      ? `${data.humidity} %`
      : "-";
  els.envTime.textContent = data?.time || "-";
}

function renderPins(pinsResponse) {
  const pins = pinsResponse?.pins || {};
  const entries = Object.entries(pins);

  els.pinsGrid.innerHTML = "";

  if (entries.length === 0) {
    els.pinsGrid.innerHTML = `
      <div class="card">
        <div class="pin-name">Sin pines</div>
        <div class="pin-meta">No hay salidas definidas en este dispositivo.</div>
      </div>
    `;
    return;
  }

  for (const [name, pin] of entries) {
    const on = pinIsOn(pin);
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="card-head">
        <div>
          <div class="pin-name">${name}</div>
          <div class="pin-meta">GPIO ${pin.pin}${pin.active_low ? " · relé inverso" : " · relé directo"}</div>
        </div>
        <span class="pill ${on ? "on" : "off"}">${pinStateLabel(pin)}</span>
      </div>
      <div class="card-actions">
        <button class="button toggle" data-action="toggle" data-pin="${name}">${pinActionLabel(pin)}</button>
      </div>
      <div class="runfor-row">
        <input class="duration" type="number" min="1" step="1" value="20" data-duration-for="${name}" />
        <span class="duration-unit">min</span>
        <button class="button ghost" data-action="run_for" data-pin="${name}">Encender</button>
      </div>
    `;
    els.pinsGrid.appendChild(card);
  }
}

async function loadDevices() {
  setStatus("Cargando dispositivos...");
  const data = await api("/devices");
  state.devices = data.devices || [];
  renderDevices();

  const selected = state.devices.find((d) => d.name === state.deviceName) || state.devices[0];
  if (!selected) {
    renderMeta(null);
    renderPins({ pins: {} });
    setStatus("No hay dispositivos configurados", "idle");
    return;
  }

  renderMeta(selected);
  await loadPins();
  await loadPrograms();
}

async function loadPins() {
  if (!state.deviceName) return;
  setStatus(`Conectando a ${state.deviceName}...`);
  const data = await api(`/devices/${encodeURIComponent(state.deviceName)}/pins`);
  state.pins = data.pins || {};
  renderPins(data);
  renderProgramPinOptions();
  setStatus(`Conectado a ${state.deviceName}`, "ok");
}

async function loadPrograms() {
  if (!state.deviceName) return;
  const data = await api(`/devices/${encodeURIComponent(state.deviceName)}/programs`);
  renderPrograms(data);
}

async function togglePin(pin, action) {
  if (!state.deviceName) return;

  const label =
    action === "toggle" ? "Cambiando" :
    action === "on" ? "Prendiendo" :
    action === "off" ? "Apagando" :
    "Consultando";
  setStatus(`${label} ${pin}...`);

  const endpoint =
    action === "toggle"
      ? `/devices/${encodeURIComponent(state.deviceName)}/pins/${encodeURIComponent(pin)}/toggle`
      : action === "on"
      ? `/devices/${encodeURIComponent(state.deviceName)}/pins/${encodeURIComponent(pin)}/on`
      : action === "off"
        ? `/devices/${encodeURIComponent(state.deviceName)}/pins/${encodeURIComponent(pin)}/off`
        : `/devices/${encodeURIComponent(state.deviceName)}/pins/${encodeURIComponent(pin)}`;

  const data = action === "refresh" ? await api(endpoint) : await api(endpoint, { method: "POST" });
  log(data);
  await loadPins();
}

async function runForPin(pin, minutes) {
  if (!state.deviceName) return;

  const seconds = Math.max(1, Math.round(Number(minutes || 0) * 60));
  setStatus(`Programando ${pin} por ${minutes} min...`);

  const data = await api(
    `/devices/${encodeURIComponent(state.deviceName)}/pins/${encodeURIComponent(pin)}/run_for`,
    {
      method: "POST",
      body: JSON.stringify({ seconds, value: true }),
    }
  );
  log(data);
  await loadPins();
}

async function loadEnvironment() {
  if (!state.deviceName) return;

  setStatus(`Consultando sensor de ${state.deviceName}...`);
  const data = await api(`/devices/${encodeURIComponent(state.deviceName)}/environment`);
  renderEnvironment(data);
  log(data);
  setStatus(`Ambiente actualizado en ${state.deviceName}`, "ok");
}

async function saveProgram(event) {
  event.preventDefault();
  if (!state.deviceName) return;

  const periods = getProgramPeriods();
  const payload = {
    pin: els.programPin.value,
    label: els.programLabel.value.trim(),
    enabled: els.programEnabled.checked,
    days: getSelectedProgramDays(),
    periods,
  };

  if (!payload.pin) {
    throw new Error("Falta seleccionar un pin");
  }
  if (!payload.days.length) {
    throw new Error("Tenés que seleccionar al menos un día");
  }
  if (!payload.periods.length) {
    throw new Error("Tenés que agregar al menos una franja");
  }
  for (const period of payload.periods) {
    if (!period.start || !period.end) {
      throw new Error("Todas las franjas deben tener inicio y fin");
    }
    if (period.start === period.end) {
      throw new Error("Inicio y fin no pueden ser iguales");
    }
  }

  const programId = els.programId.value ? Number(els.programId.value) : null;
  const pathBase = `/devices/${encodeURIComponent(state.deviceName)}/programs`;

  if (programId) {
    await api(`${pathBase}/${programId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    setStatus("Programa actualizado", "ok");
  } else {
    await api(pathBase, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setStatus("Programa creado", "ok");
  }

  clearProgramForm();
  await loadPrograms();
}

async function deleteProgram(programId) {
  await api(`/devices/${encodeURIComponent(state.deviceName)}/programs/${programId}`, {
    method: "DELETE",
  });
  setStatus("Programa borrado", "ok");
  if (String(els.programId.value) === String(programId)) {
    clearProgramForm();
  }
  await loadPrograms();
}

els.deviceSelect.addEventListener("change", async () => {
  state.deviceName = els.deviceSelect.value;
  const device = state.devices.find((d) => d.name === state.deviceName);
  renderMeta(device);
  await loadPins();
  await loadPrograms();
});

els.refreshButton.addEventListener("click", async () => {
  await loadDevices();
});

els.programsRefreshButton.addEventListener("click", async () => {
  try {
    await loadPrograms();
  } catch (error) {
    setStatus("Error actualizando programas", "error");
    log({ error: error.message });
  }
});

els.environmentButton.addEventListener("click", async () => {
  try {
    await loadEnvironment();
  } catch (error) {
    setStatus("Error consultando sensor", "error");
    log({ error: error.message });
  }
});

els.programAddPeriodButton.addEventListener("click", () => {
  els.programPeriods.appendChild(createPeriodRow());
});

els.programPeriods.addEventListener("click", (event) => {
  const button = event.target.closest("button.period-remove");
  if (!button) return;

  const row = button.closest(".period-row");
  if (!row) return;

  row.remove();
  if (els.programPeriods.querySelectorAll(".period-row").length === 0) {
    els.programPeriods.appendChild(createPeriodRow());
  }
});

els.programForm.addEventListener("submit", async (event) => {
  try {
    await saveProgram(event);
  } catch (error) {
    setStatus("Error guardando programa", "error");
    log({ error: error.message });
  }
});

els.programCancelButton.addEventListener("click", () => {
  clearProgramForm();
});

els.programsGrid.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-program-action][data-program-id]");
  if (!button) return;

  const programId = Number(button.dataset.programId);
  const action = button.dataset.programAction;
  const program = state.programs.find((item) => Number(item.id) === programId);

  if (action === "edit") {
    if (program) {
      fillProgramForm(program);
      setStatus(`Editando programa ${program.id}`, "idle");
    }
    return;
  }

  if (action === "delete") {
    const ok = window.confirm("Borrar este programa?");
    if (!ok) return;
    try {
      await deleteProgram(programId);
    } catch (error) {
      setStatus("Error borrando programa", "error");
      log({ error: error.message });
    }
  }
});

els.pinsGrid.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action][data-pin]");
  if (!button) return;
  const { action, pin } = button.dataset;
  try {
    if (action === "run_for") {
      const durationInput = document.querySelector(`[data-duration-for="${pin}"]`);
      await runForPin(pin, durationInput ? durationInput.value : 20);
    } else {
      await togglePin(pin, action);
    }
  } catch (error) {
    setStatus("Error", "error");
    log({ error: error.message });
  }
});

async function init() {
  try {
    renderProgramDayChecks();
    clearProgramForm();
    const devices = await api("/devices");
    state.devices = devices.devices || [];
    renderDevices();
    await loadDevices();
    renderEnvironment(null);

    setInterval(async () => {
      if (state.deviceName) {
        try {
          await loadPins();
        } catch (error) {
          setStatus("Sin respuesta del ESP32", "error");
          log({ error: error.message });
        }
      }
    }, 5000);
  } catch (error) {
    setStatus("Error inicializando UI", "error");
    log({ error: error.message });
  }
}

init();
