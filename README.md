# Riego v2

Local irrigation UI and ESP32 firmware simulator.

## Ubuntu quick start

1. Install Python 3, `docker`, and `docker compose`.
2. Create the Conda environment named `riego` and install the app requirements from `app/requirements.txt`, for example:

```bash
conda create -n riego python=3.12
conda activate riego
python3 -m pip install -r app/requirements.txt
```
3. Start the simulator and UI:

```bash
./dev.sh
```

UI: http://127.0.0.1:8001

If you want to point the UI at a real ESP32 instead of the simulator:

```bash
./prod.sh --esp-host http://<esp32-ip>
```

## Manual simulator run

```bash
cd simulator
python3 run.py
```

The simulator listens on `http://127.0.0.1:18080` and the UI listens on `http://127.0.0.1:8001` when started through the launch script.
