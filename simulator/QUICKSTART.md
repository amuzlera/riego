# Simulator Quickstart

This project includes a local simulator for the ESP32 firmware under `simulator/`.

## Requirements

- Conda installed
- The `base` environment available
- Python available in that environment

## 1. Open a terminal in the repo root

```bash
cd /path/to/riegov2
```

## 2. Verify Conda

```bash
conda --version
conda info --envs
```

## 3. Run a fast syntax check

This compiles the simulator files and catches import/syntax problems early.

```bash
python3 -m compileall simulator
```

## 4. Start the simulator

```bash
python3 simulator/run.py
```

What starts:
- simulated ESP32 server on `http://127.0.0.1:80`

If you prefer to activate the environment first:

```bash
conda activate base
python simulator/run.py
```

Or launch the app + simulator together from the repo root:

```bash
./dev.sh
```

By default the simulator is published on `http://127.0.0.1:18080` to avoid conflicts with apps already using `8080`.

If you need another host port:

```bash
./start-dev.sh --target simulator --sim-port 18081 --open-browser
```

## 5. Smoke test

While the simulator is running, try:

```bash
curl -u admin:1234 http://127.0.0.1/ls
curl -u admin:1234 http://127.0.0.1/tail?filename=log.txt
```

## Files you will edit most often

- [esp32/config_riego.json](/home/amuzlera/project/riegov2/esp32/config_riego.json)
- [esp32/log.txt](/home/amuzlera/project/riegov2/esp32/log.txt)

## Notes

- The simulator uses in-memory relay state and prints pin changes to the console.
- Logs written by the firmware land in `esp32/log.txt`.
- The simulator imports the real code from `../esp32` without changing the firmware files.
