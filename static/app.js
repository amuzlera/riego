const $ = (id) => document.getElementById(id);

// --- Consola ---
const out = $("out");
const runBtn = $("run");
const cmdInput = $("cmd");

// --- Logs ---
let running = false;
let intervalId = null;

const toggleBtn = document.getElementById("toggle");
const logbox = document.getElementById("logbox");

toggleBtn.addEventListener("click", () => {
  running = !running;
  toggleBtn.textContent = running ? "OFF" : "ON";

  if (running) {
    fetchLogs();
    intervalId = setInterval(fetchLogs, 30000); // cada 10s
  } else {
    clearInterval(intervalId);
  }
});

async function fetchLogs() {
  try {
    const res = await fetch("/api/logs/tail?n=20");
    const data = await res.json();
    console.log(data);
    logbox.textContent = data.lines.join("\n");
    logbox.scrollTop = logbox.scrollHeight;
  } catch (err) {
    console.error(err);
  }
}



async function exec() {
  const raw = cmdInput.value.trim();
  if (!raw) {
    out.textContent = "Ingresá un comando";
    return;
  }

  runBtn.disabled = true;
  out.textContent = "Consultando…";

  try {
    // dividir lo escrito en "comando" y "argumentos"
    const parts = raw.split(/\s+/);
    const cmd = parts[0];
    var arg = parts[1]; // solo el primero por ahora
    console.log(cmd, arg);
    arg = (typeof arg === "string" ? arg : "").replace(/\//g, "-_-");
    // special handling for zone commands
    if (cmd === "zone" || /^zona?\d+$/i.test(cmd)) {
      // body format: "zone1 on 3600" or if first token is 'zone', join remaining
      let bodyText = null;
      if (cmd === "zone") {
        bodyText = parts.slice(1).join(" ");
      } else {
        // e.g. "zone1 on 3600" -> keep as-is
        bodyText = parts.join(" ");
      }

      if (!bodyText || bodyText.trim().length === 0) {
        out.textContent = "Ingresá zona y acción, p.ej: 'zone1 on 3600'";
        runBtn.disabled = false;
        return;
      }

      console.log("→ POST /api/esp/zone", bodyText);
      const res = await fetch(`/api/esp/zone`, {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: bodyText
      });

      const ct = res.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        const data = await res.json();
        out.textContent = data.content ? data.content : JSON.stringify(data, null, 2);
      } else {
        out.textContent = await res.text();
      }
      runBtn.disabled = false;
      return;
    }

    let url = `/api/esp?cmd=${encodeURIComponent(cmd)}`;

    // mapear comandos con argumentos
    if (cmd === "cat" && arg) {
      url += `?filename=${encodeURIComponent(arg)}`;
    }
    if (cmd === "rm" && arg) {
      url += `?filename=${encodeURIComponent(arg)}`;
    }
    if (cmd === "ls" && arg) {
      url += `?filename=${encodeURIComponent(arg)}`;
    }
    if (cmd === "tail" && arg) {
      url += `?filename=${encodeURIComponent(arg)}`;
    }
    // ls no necesita argumentos

    console.log("→", url);

    const res = await fetch(url);
    const ct = res.headers.get("content-type") || "";

    if (ct.includes("application/json")) {
      const data = await res.json();
      if (data.content) {
        out.textContent = data.content;
        // si fue un cat que devolvió {file, content}, rellenar inputs de upload
        try {
          if (data.file && typeof data.content === 'string') {
            const filenameInput = $("filename");
            const filecontentInput = $("filecontent");
            if (filenameInput) filenameInput.value = data.file;
            if (filecontentInput) filecontentInput.value = data.content;
          }
        } catch (e) {
          console.warn('No se pudo auto-llenar upload:', e);
        }
      } else {
        out.textContent = JSON.stringify(data, null, 2);
      }
    } else {
      out.textContent = await res.text();
    }
  } catch (e) {
    out.textContent = `Error: ${e.message}`;
  } finally {
    runBtn.disabled = false;
  }
}

runBtn.addEventListener("click", exec);
cmdInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") exec();
});

// --- Upload ---
const uploadBtn = $("uploadBtn");
const uploadOut = $("uploadOut");

async function uploadFile() {
  var filename = $("filename").value.trim();
  const content = $("filecontent").value;
  if (!filename) {
    uploadOut.textContent = "Poné un nombre de archivo.";
    return;
  }
  filename = (typeof filename === "string" ? filename : "").replace(/\//g, "-_-");
  uploadBtn.disabled = true;
  uploadOut.textContent = "Subiendo…";

  try {
    // POST al endpoint del ESP32, mandando el contenido plano
    console.log(`/api/esp?cmd=upload&filename=${encodeURIComponent(filename)}`)
    const res = await fetch(`/api/esp?cmd=upload&filename=${encodeURIComponent(filename)}`, {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: content
    });

    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const data = await res.json();
      uploadOut.textContent = JSON.stringify(data, null, 2);
    } else {
      uploadOut.textContent = await res.text();
    }
  } catch (e) {
    uploadOut.textContent = `Error: ${e.message}`;
  } finally {
    uploadBtn.disabled = false;
  }
}

uploadBtn.addEventListener("click", uploadFile);
