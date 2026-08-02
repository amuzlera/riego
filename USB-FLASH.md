# USB Flash Guide

Use this when you need to load the ESP32 code from your computer through USB.

## Requirements

- ESP32 connected by USB
- `mpremote` installed, or the `riego` Conda env available

## Quick start

```bash
conda activate riego
./flash-esp32.sh
```

If `conda activate` is not available, use:

```bash
conda run -n riego ./flash-esp32.sh
```

## See USB output

Open the live REPL over USB and watch `print()` output:

```bash
mpremote connect /dev/ttyUSB0 repl
```

If your board uses another port:

```bash
mpremote connect /dev/ttyUSB1 repl
```

Read the firmware logs stored on the device:

```bash
mpremote connect /dev/ttyUSB0 fs cat log.txt
mpremote connect /dev/ttyUSB0 fs cat last_log.txt
```

Reset the board from USB:

```bash
mpremote connect /dev/ttyUSB0 reset
```

## Flash commands

Flash to the default port:

```bash
./flash-esp32.sh
```

Flash to a specific USB port:

```bash
./flash-esp32.sh --port /dev/ttyUSB0
```

Flash and remove old device files first:

```bash
./flash-esp32.sh --clean
```

Preview the commands without writing:

```bash
./flash-esp32.sh --dry-run
```

## What gets copied

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

## Notes

- USB flashing is the safest way to do the first install on a blank or broken board.
- After that, the ESP32 can be managed over WiFi.
