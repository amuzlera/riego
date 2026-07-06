from __future__ import annotations

import os
import sys
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parent
REPO_ROOT = SIM_DIR.parent
ESP32_DIR = REPO_ROOT / "esp32"
sys.path.insert(0, str(SIM_DIR))
sys.path.insert(1, str(ESP32_DIR))

from config import CONFIG_PATH, FIXTURES_DIR, RUNTIME_DIR  # noqa: E402


def _ensure_seed_files():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    esp_config = Path(CONFIG_PATH)
    if not esp_config.exists():
        seed = FIXTURES_DIR / "config_riego.json"
        if seed.exists():
            esp_config.write_text(seed.read_text(encoding="utf-8"), encoding="utf-8")
    os.chdir(ESP32_DIR)


def main():
    _ensure_seed_files()
    import boot  # noqa: F401


if __name__ == "__main__":
    main()
