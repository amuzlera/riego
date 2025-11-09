document.addEventListener('DOMContentLoaded', () => {
  const out = document.getElementById('out');

  function setOut(text) {
    out.textContent = text;
  }

  async function sendZone(zone, action, duration) {
    const params = new URLSearchParams({ zone: String(zone), action: String(action) });
    if (duration != null) params.set('duration', String(duration));
    const url = `/api/esp/zone?${params.toString()}`;
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
  }

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

      const result = await sendZone(zone, next, duration);
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
});
