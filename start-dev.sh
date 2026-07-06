#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

TARGET="simulator"
ESP_HOST="http://127.0.0.1:18080"
ESP_USER="admin"
ESP_PASS="1234"
SIM_PORT="18080"
APP_PORT="8001"
OPEN_BROWSER=0
CONDA_BIN="${CONDA_BIN:-conda}"

usage() {
  cat <<'EOF'
Usage: ./start-dev.sh [--target simulator|real] [--esp-host URL] [--esp-user USER] [--esp-pass PASS] [--sim-port PORT] [--app-port PORT] [--open-browser]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="$2"
      shift 2
      ;;
    --target=*)
      TARGET="${1#*=}"
      shift
      ;;
    --esp-host)
      ESP_HOST="$2"
      shift 2
      ;;
    --esp-host=*)
      ESP_HOST="${1#*=}"
      shift
      ;;
    --esp-user)
      ESP_USER="$2"
      shift 2
      ;;
    --esp-user=*)
      ESP_USER="${1#*=}"
      shift
      ;;
    --esp-pass)
      ESP_PASS="$2"
      shift 2
      ;;
    --esp-pass=*)
      ESP_PASS="${1#*=}"
      shift
      ;;
    --sim-port)
      SIM_PORT="$2"
      shift 2
      ;;
    --sim-port=*)
      SIM_PORT="${1#*=}"
      shift
      ;;
    --app-port)
      APP_PORT="$2"
      shift 2
      ;;
    --app-port=*)
      APP_PORT="${1#*=}"
      shift
      ;;
    --open-browser)
      OPEN_BROWSER=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$TARGET" in
  simulator|real)
    ;;
  *)
    echo "Invalid target: $TARGET" >&2
    exit 1
    ;;
esac

if ! command -v "$CONDA_BIN" >/dev/null 2>&1; then
  echo "conda was not found on PATH." >&2
  exit 1
fi

if [[ "$TARGET" == "simulator" && "$ESP_HOST" == "http://127.0.0.1:18080" ]]; then
  ESP_HOST="http://127.0.0.1:${SIM_PORT}"
fi

SIM_COMPOSE_CMD=(docker compose -f simulator/docker-compose.yml up --build)
SIM_DOWN_CMD=(docker compose -f simulator/docker-compose.yml down)
APP_CMD=(
  "$CONDA_BIN"
  run
  --no-capture-output
  -n
  riego
  env
  ESP_HOST="$ESP_HOST"
  ESP_USER="$ESP_USER"
  ESP_PASS="$ESP_PASS"
  python
  -m
  uvicorn
  app.main:app
  --host
  0.0.0.0
  --port
  "$APP_PORT"
)

cleanup() {
  if [[ -n "${APP_PID:-}" ]] && kill -0 "$APP_PID" 2>/dev/null; then
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi

  if [[ -n "${SIM_PID:-}" ]] && kill -0 "$SIM_PID" 2>/dev/null; then
    kill "$SIM_PID" 2>/dev/null || true
    wait "$SIM_PID" 2>/dev/null || true
    "${SIM_DOWN_CMD[@]}" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting dev workflow for target: $TARGET"

if [[ "$TARGET" == "simulator" ]]; then
  export SIM_PORT
  "${SIM_COMPOSE_CMD[@]}" &
  SIM_PID=$!

  "${APP_CMD[@]}" &
  APP_PID=$!

  echo "Simulator: http://127.0.0.1:${SIM_PORT}"
  echo "App:        http://127.0.0.1:${APP_PORT}"
  echo "Press Ctrl-C to stop both processes."
else
  "${APP_CMD[@]}" &
  APP_PID=$!

  echo "Real ESP host: $ESP_HOST"
  echo "App:           http://127.0.0.1:${APP_PORT}"
  echo "Press Ctrl-C to stop the app."
fi

if [[ "$OPEN_BROWSER" -eq 1 ]]; then
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:${APP_PORT}/" >/dev/null 2>&1 || true
  else
    echo "xdg-open is not available; open http://127.0.0.1:${APP_PORT}/ manually."
  fi
fi

if [[ -n "${SIM_PID:-}" ]]; then
  wait -n "$APP_PID" "$SIM_PID"
else
  wait "$APP_PID"
fi
