const $ = (id) => document.getElementById(id);

// --- Consola ---
const out = $("out");
const runBtn = $("run");
const cmdInput = $("cmd");

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

    arg = (typeof arg === "string" ? arg : "").replace(/\//g, "-_-");

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
    // ls no necesita argumentos

    console.log("→", url);

    const res = await fetch(url);
    const ct = res.headers.get("content-type") || "";

    if (ct.includes("application/json")) {
      const data = await res.json();
      if (data.content) {
        out.textContent = data.content;
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
