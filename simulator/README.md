## ESP32 MicroPython Simulator

This folder contains a local simulator for the irrigation firmware.

What it provides:
- MicroPython-compatible stub modules: `machine`, `network`, `uasyncio`, `urequests`, `ujson`, `ubinascii`, `uos`, `dht`
- A runtime entrypoint that imports the real code from `../esp32`
- A writable device filesystem rooted at `../esp32`
- A sample `config_riego.json` for testing relays and valves

## Run locally

From the repository root:

```bash
cd simulator
python3 run.py
```

For the Conda-based workflow and smoke tests, see [QUICKSTART.md](./QUICKSTART.md).
For local development on Ubuntu, use `./dev.sh` from the repo root.
For production/real ESP32 mode on Ubuntu, use `./prod.sh` from the repo root.
The simulator is published on `http://127.0.0.1:18080` by default.

This starts:
- the simulated ESP32 server on `0.0.0.0:80`

## Run in Docker

```bash
cd simulator
docker compose up --build
```

Ports exposed by the container:
- `8080 -> 80` for the simulated device server

## Useful files

- `fixtures/config_riego.json`: seed irrigation config copied into the simulated device filesystem if missing
- `runtime/`: generated logs and mutable simulator state

## Notes

- The simulator does not emulate real GPIO or WiFi hardware. It records pin state changes in memory and prints them.
- The real firmware modules under `../esp32` are imported without modification.
