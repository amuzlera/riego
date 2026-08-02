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

For the USB flashing steps, see [USB-FLASH.md](/home/amuzlera/project/riegov2/riego/USB-FLASH.md).

## ESP32 failover

The ESP32 firmware now has two slots:

- `dev`: the mutable image you upload over WiFi
- `stable`: the fallback snapshot

The bootloader keeps a small boot-state file and switches back to `stable` after repeated failed boots from `dev`.
The firmware also runs a watchdog/heartbeat check, so a stalled main loop or scheduler can force a reset instead of hanging forever.

Useful endpoints:

- `GET /api/firmware/status`
- `POST /api/firmware/slot?slot=dev`
- `POST /api/firmware/slot?slot=stable`

To upload code into the fallback slot, send `slot=stable` to the ESP32 `/upload` endpoint. The root `boot.py` and `boot_manager.py` files are reserved and cannot be overwritten over WiFi.

## Manual simulator run

```bash
cd simulator
python3 run.py
```

The simulator listens on `http://127.0.0.1:18080` and the UI listens on `http://127.0.0.1:8001` when started through the launch script.
