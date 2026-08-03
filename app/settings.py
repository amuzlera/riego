from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = Path(os.getenv("RIEGO_DEVICES_FILE", BASE_DIR / "devices.json"))
DEFAULT_TIMEOUT = float(os.getenv("RIEGO_HTTP_TIMEOUT", "5"))

