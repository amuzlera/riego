#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESP_HOST="${ESP_HOST:-http://192.168.1.50}"

exec "$DIR/start-dev.sh" --target real --esp-host "$ESP_HOST" --open-browser "$@"
