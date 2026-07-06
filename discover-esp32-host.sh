#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${MPREMOTE_PORT:-/dev/ttyUSB0}"

usage() {
  cat <<'EOF'
Usage: ./discover-esp32-host.sh [--port /dev/ttyUSB0]

Prints the current ESP32 HTTP host as a full http:// URL.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="$2"
      shift 2
      ;;
    --port=*)
      PORT="${1#*=}"
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

if command -v mpremote >/dev/null 2>&1; then
  MPREMOTE_CMD=(mpremote)
elif command -v conda >/dev/null 2>&1; then
  MPREMOTE_CMD=(conda run --no-capture-output -n riego mpremote)
else
  echo "mpremote was not found on PATH, and conda is unavailable." >&2
  exit 1
fi

ip="$(
  "${MPREMOTE_CMD[@]}" connect "$PORT" exec "import network; print(network.WLAN(network.STA_IF).ifconfig()[0])" \
    | awk 'NF { line=$0 } END { print line }'
)"

if [[ -z "$ip" ]]; then
  echo "Could not discover ESP32 IP." >&2
  exit 1
fi

printf 'http://%s\n' "$ip"
