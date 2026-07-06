# ESP32 Flashing

This script syncs the local `esp32/` tree to a MicroPython ESP32 over USB with `mpremote`.

## Prerequisites

- The `riego` Conda environment should be available.
- `mpremote` must be on `PATH`.
- The board should be connected over USB, usually as `/dev/ttyUSB0`.

If you want to run it explicitly from the Conda env:

```bash
conda activate riego
./flash-esp32.sh
```

Or:

```bash
conda run -n riego ./flash-esp32.sh
```

## Usage

```bash
./flash-esp32.sh
./flash-esp32.sh --port /dev/ttyUSB0
./flash-esp32.sh --clean
./flash-esp32.sh --dry-run
```

## Network Address

The firmware uses a fixed WiFi IP in `esp32/server.py`, and `prod.sh` defaults to the same host.

If you change the ESP32 IP in firmware, keep `prod.sh` aligned with the same address.

## Clean Mode

`--clean` removes the previous ESP32 source files and directories before copying the new version.
Use it when you want the device filesystem to match the local `esp32/` tree as closely as possible.

The script copies:

- `boot.py`
- `main.py`
- `config.py`
- `config.example.py`
- `config_riego.json`
- `server.py`
- `time_utils.py`
- `server_utils.py`
- `task.py`
- `endpoints/`
- `utils/`
