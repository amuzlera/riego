// Simple file editor, independent of the irrigation polling loop.
(() => {
  const byId = (id) => document.getElementById(id);
  const device = byId('deviceSelect');
  const select = byId('fileSelect');
  const original = byId('fileOriginal');
  const edited = byId('fileEdited');
  const message = byId('fileMessage');
  const refresh = byId('filesRefresh');
  const read = byId('fileRead');
  const send = byId('fileSend');
  const reset = byId('fileReset');
  let files = [];
  let loaded = null;
  let busy = false;

  function controls() {
    refresh.disabled = busy || !device.value;
    select.disabled = busy || !files.length;
    read.disabled = busy || !select.value;
    send.disabled = busy || !loaded || !loaded.writable;
    reset.disabled = busy || !device.value;
    edited.readOnly = busy || !loaded || !loaded.writable;
  }

  function clear() {
    loaded = null;
    original.value = '';
    edited.value = '';
    message.textContent = 'Elegí un archivo y presioná Leer.';
    controls();
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || 'Error de mantenimiento');
    return data;
  }

  function base(name = device.value) {
    if (!name) throw new Error('Seleccioná un dispositivo.');
    return `/devices/${encodeURIComponent(name)}`;
  }

  async function action(work) {
    busy = true;
    controls();
    try {
      await work();
    } catch (error) {
      message.textContent = `Error: ${error.message}`;
    } finally {
      busy = false;
      controls();
    }
  }

  refresh.addEventListener('click', () => action(async () => {
    const name = device.value;
    message.textContent = 'Consultando archivos…';
    const data = await api(`${base(name)}/files`);
    if (device.value !== name) return;
    files = data.files || [];
    select.replaceChildren();
    for (const file of files) {
      const option = document.createElement('option');
      option.value = file.name;
      option.textContent = `${file.name}${file.writable ? '' : ' (solo lectura)'}`;
      select.appendChild(option);
    }
    clear();
    if (!files.length) message.textContent = 'No hay archivos disponibles.';
  }));

  read.addEventListener('click', () => action(async () => {
    const name = device.value;
    const filename = select.value;
    message.textContent = 'Leyendo archivo…';
    const data = await api(`${base(name)}/files/${encodeURIComponent(filename)}`);
    if (device.value !== name || select.value !== filename) return;
    original.value = data.content;
    edited.value = data.content;
    loaded = { device: name, filename, writable: files.find((f) => f.name === filename)?.writable === true };
    message.textContent = loaded.writable ? 'Editá el contenido de la derecha y envialo al ESP32.' : 'Archivo protegido: solo lectura.';
  }));

  send.addEventListener('click', () => action(async () => {
    const target = loaded;
    if (!target || target.device !== device.value || target.filename !== select.value) return;
    const content = edited.value;
    const bytes = new TextEncoder().encode(content).length;
    if (!bytes || bytes > 65536) throw new Error('El archivo debe ocupar entre 1 byte y 64 KiB.');
    message.textContent = 'Enviando archivo…';
    await api(`${base(target.device)}/files/${encodeURIComponent(target.filename)}`, {
      method: 'PUT', body: JSON.stringify({ content }),
    });
    if (device.value !== target.device || loaded !== target) return;
    original.value = content;
    message.textContent = 'Archivo guardado. Reiniciá el ESP32 para aplicar los cambios.';
  }));

  reset.addEventListener('click', () => action(async () => {
    if (!window.confirm('¿Reiniciar el ESP32 para aplicar los archivos guardados?')) return;
    await api(`${base()}/maintenance/reset`, { method: 'POST' });
    message.textContent = 'Reinicio solicitado. Esperá unos segundos antes de volver a consultar.';
  }));

  select.addEventListener('change', clear);
  device.addEventListener('change', () => {
    files = [];
    select.replaceChildren();
    clear();
  });
  clear();
  // Initial device options are populated asynchronously by app.js.
  new MutationObserver(controls).observe(device, { childList: true });
})();
