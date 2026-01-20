document.addEventListener('DOMContentLoaded', () => {
  const out = document.getElementById('out');

  function setOut(text) {
    out.textContent = text;
  }

  // ============ HANDLERS (agnóstico de modo) ============
  const handlers = {
    sendZone: async (zone, action, duration) => {
      const params = new URLSearchParams({ zone: String(zone), action: String(action) });
      if (duration != null) params.set('duration', String(duration));
      const url = `/api/zone?${params.toString()}`;
      setOut(`Enviando ${url} ...`);
      try {
        const res = await fetch(url, { method: 'POST' });
        const text = await res.text();
        let parsed;
        try { parsed = JSON.parse(text); }
        catch (_) { parsed = text; }
        setOut(`Respuesta (${res.status}): ` + (typeof parsed === 'string' ? parsed : JSON.stringify(parsed, null, 2)));
        return { ok: res.ok, status: res.status, body: parsed };
      } catch (err) {
        setOut('Error: ' + err.message);
        return { ok: false, error: err };
      }
    },

    executeCode: async (code) => {
      const encoded = encodeURIComponent(code);
      const url = `/api/execute?code=${encoded}`;
      setOut(`Ejecutando código...`);
      try {
        const res = await fetch(url, { method: 'GET' });
        const text = await res.text();
        let parsed;
        try { parsed = JSON.parse(text); }
        catch (_) { parsed = text; }
        setOut(`Respuesta (${res.status}): ` + (typeof parsed === 'string' ? parsed : JSON.stringify(parsed, null, 2)));
        return { ok: res.ok, status: res.status, body: parsed };
      } catch (err) {
        setOut('Error: ' + err.message);
        return { ok: false, error: err };
      }
    }
  };

  // Attach listeners to zone switches
  document.querySelectorAll('.zone-switch').forEach(btn => {
    // Initialize color
    const initState = btn.getAttribute('data-state') || 'off';
    updateButtonColor(btn, initState);

    btn.addEventListener('click', async () => {
      const zone = btn.getAttribute('data-zone');
      const current = btn.getAttribute('data-state') || 'off';
      const next = current === 'on' ? 'off' : 'on';

      // read duration for this zone
      const input = document.querySelector(`.zone-duration[data-zone="${zone}"]`);
      let duration = input ? parseInt(input.value, 10) : undefined;
      if (!Number.isFinite(duration) || duration <= 0) duration = undefined;

      // Optimistic UI update
      btn.textContent = `Zona ${zone}: ${next.toUpperCase()}`;
      btn.setAttribute('data-state', next);
      updateButtonColor(btn, next);
      btn.disabled = true;

      const result = await handlers.sendZone(zone, next, duration);
      btn.disabled = false;
      if (!result.ok) {
        // revert UI on failure
        const revert = current;
        btn.textContent = `Zona ${zone}: ${revert.toUpperCase()}`;
        btn.setAttribute('data-state', revert);
        updateButtonColor(btn, revert);
      }
    });
  });

  function updateButtonColor(btn, state) {
    if (state === 'on') {
      btn.style.background = '#16a34a'; // green
      btn.style.color = '#fff';
    } else {
      btn.style.background = '#dc2626'; // red
      btn.style.color = '#fff';
    }
  }

  document.getElementById('back').addEventListener('click', () => {
    window.location.href = '/';
  });

  // Execute code handler
  document.getElementById('execute-btn').addEventListener('click', async () => {
    const code = document.getElementById('code-input').value.trim();
    if (!code) {
      setOut('Error: Ingresa código para ejecutar');
      return;
    }

    const result = await handlers.executeCode(code);
  });

  // ============ RIEGO CONFIG MANAGEMENT ============
  let currentConfig = {
    tz_offset_seconds: 10800,
    zones: {},
    programed_times: []
  };

  function renderZones() {
    const container = document.getElementById('zones-container');
    container.innerHTML = '';
    Object.entries(currentConfig.zones).forEach(([name, gpio]) => {
      const div = document.createElement('div');
      div.style.display = 'flex';
      div.style.gap = '8px';
      div.style.alignItems = 'center';
      div.innerHTML = `
        <input type="text" value="${name}" placeholder="Nombre (ej: zona1)" class="zone-name" style="flex:1;padding:6px;border-radius:6px;border:1px solid #233;background:#0b1220;color:#e6eef8" />
        <input type="number" value="${gpio}" placeholder="GPIO" class="zone-gpio" style="width:80px;padding:6px;border-radius:6px;border:1px solid #233;background:#0b1220;color:#e6eef8" />
        <button class="remove-zone-btn" style="background:#dc2626;padding:6px 10px;font-size:0.85rem">✕</button>
      `;
      container.appendChild(div);
      div.querySelector('.remove-zone-btn').addEventListener('click', () => {
        delete currentConfig.zones[name];
        renderZones();
      });
    });
  }

  function renderSchedules() {
    const container = document.getElementById('schedules-container');
    container.innerHTML = '';
    currentConfig.programed_times.forEach((sched, idx) => {
      const div = document.createElement('div');
      div.style.background = '#0b1220';
      div.style.padding = '12px';
      div.style.borderRadius = '6px';
      div.style.border = '1px solid #233';
      const planStr = sched.plan.map(([z, dur]) => `${z}:${dur}`).join(', ');
      div.innerHTML = `
        <div style="display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap">
          <input type="time" value="${sched.start}" class="sched-time" style="padding:6px;border-radius:6px;border:1px solid #233;background:#0b1220;color:#e6eef8" />
          <input type="text" value="${sched.days.join(',')}" placeholder="Días (all o lun,mar,etc)" class="sched-days" style="flex:1;padding:6px;border-radius:6px;border:1px solid #233;background:#0b1220;color:#e6eef8" />
          <button class="remove-sched-btn" style="background:#dc2626;padding:6px 10px;font-size:0.85rem">✕</button>
        </div>
        <input type="text" value="${planStr}" placeholder="Plan (ej: zona1:15, zona2:20)" class="sched-plan" style="width:100%;padding:6px;border-radius:6px;border:1px solid #233;background:#0b1220;color:#e6eef8;box-sizing:border-box" />
      `;
      container.appendChild(div);
      div.querySelector('.remove-sched-btn').addEventListener('click', () => {
        currentConfig.programed_times.splice(idx, 1);
        renderSchedules();
      });
    });
  }

  document.getElementById('add-zone-btn').addEventListener('click', () => {
    const newName = `zona${Object.keys(currentConfig.zones).length + 1}`;
    currentConfig.zones[newName] = 0;
    renderZones();
  });

  document.getElementById('add-schedule-btn').addEventListener('click', () => {
    currentConfig.programed_times.push({
      start: '00:00',
      days: ['all'],
      plan: []
    });
    renderSchedules();
  });

  document.getElementById('load-config-btn').addEventListener('click', async () => {
    const statusDiv = document.getElementById('config-status');
    try {
      const res = await fetch('/api/config/riego');
      const data = await res.json();
      if (data.status === 'ok' && data.config) {
        currentConfig = data.config;
        renderZones();
        renderSchedules();
        statusDiv.textContent = '✓ Configuración cargada';
        statusDiv.style.color = '#16a34a';
      } else {
        statusDiv.textContent = '✗ Error al cargar: ' + (data.message || 'desconocido');
        statusDiv.style.color = '#dc2626';
      }
    } catch (err) {
      statusDiv.textContent = '✗ Error: ' + err.message;
      statusDiv.style.color = '#dc2626';
    }
  });

  document.getElementById('save-config-btn').addEventListener('click', async () => {
    const statusDiv = document.getElementById('config-status');
    try {
      // Actualizar zonas desde inputs
      const newZones = {};
      document.querySelectorAll('#zones-container > div').forEach(div => {
        const name = div.querySelector('.zone-name').value.trim();
        const gpio = parseInt(div.querySelector('.zone-gpio').value, 10);
        if (name && !isNaN(gpio)) {
          newZones[name] = gpio;
        }
      });
      currentConfig.zones = newZones;

      // Actualizar horarios desde inputs
      const newSchedules = [];
      document.querySelectorAll('#schedules-container > div').forEach(div => {
        const start = div.querySelector('.sched-time').value;
        const days = div.querySelector('.sched-days').value.split(',').map(d => d.trim()).filter(d => d);
        const planStr = div.querySelector('.sched-plan').value;
        const plan = planStr.split(',').map(item => {
          const [zone, dur] = item.trim().split(':');
          return [zone.trim(), parseInt(dur, 10)];
        }).filter(([z, d]) => z && !isNaN(d));
        
        if (start && days.length > 0 && plan.length > 0) {
          newSchedules.push({ start, days, plan });
        }
      });
      currentConfig.programed_times = newSchedules;

      // Enviar al servidor
      const res = await fetch('/api/config/riego', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentConfig)
      });
      const data = await res.json();
      if (data.status === 'ok') {
        statusDiv.textContent = '✓ Configuración guardada';
        statusDiv.style.color = '#16a34a';
      } else {
        statusDiv.textContent = '✗ Error al guardar: ' + (data.message || 'desconocido');
        statusDiv.style.color = '#dc2626';
      }
    } catch (err) {
      statusDiv.textContent = '✗ Error: ' + err.message;
      statusDiv.style.color = '#dc2626';
    }
  });

  document.getElementById('reset-config-btn').addEventListener('click', () => {
    currentConfig = {
      tz_offset_seconds: 10800,
      zones: {},
      programed_times: []
    };
    renderZones();
    renderSchedules();
    document.getElementById('config-status').textContent = '';
  });

  // Cargar configuración al abrir
  document.getElementById('load-config-btn').click();
});
