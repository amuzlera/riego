#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$REPO_ROOT/esp32"
PORT="${MPREMOTE_PORT:-/dev/ttyUSB0}"
DRY_RUN=0
CLEAN=0
MPREMOTE_CMD=()

usage() {
  cat <<'EOF'
Usage: ./flash-esp32.sh [--port /dev/ttyUSB0] [--clean] [--dry-run]

Copies the local esp32/ source tree to the MicroPython filesystem over USB.
Use --clean to remove the previous esp32 files before copying the new ones.
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
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --clean)
      CLEAN=1
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

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Source directory not found: $SRC_DIR" >&2
  exit 1
fi

run_mpremote() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '%q' "${MPREMOTE_CMD[0]}"
    for arg in "${MPREMOTE_CMD[@]:1}"; do
      printf ' %q' "$arg"
    done
    printf ' connect %q' "$PORT"
    shift
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  else
    "${MPREMOTE_CMD[@]}" connect "$PORT" "$@"
  fi
}

remove_remote_path() {
  local path="$1"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    run_mpremote fs rm -r "$path"
  else
    "${MPREMOTE_CMD[@]}" connect "$PORT" fs rm -r "$path" >/dev/null 2>&1 || true
  fi
}

clean_remote_tree() {
  echo "Cleaning remote esp32 files on $PORT"

  remove_remote_path "boot.py"
  remove_remote_path "main.py"
  remove_remote_path "config.py"
  remove_remote_path "config.example.py"
  remove_remote_path "config_riego.json"
  remove_remote_path "server.py"
  remove_remote_path "time_utils.py"
  remove_remote_path "server_utils.py"
  remove_remote_path "task.py"
  remove_remote_path "endpoints"
  remove_remote_path "utils"
}

ensure_remote_dir() {
  local dir="$1"
  local current=""
  local part
  IFS='/' read -r -a parts <<< "$dir"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    for part in "${parts[@]}"; do
      current="${current:+$current/}$part"
      run_mpremote fs mkdir "$current"
    done
    return
  fi

  for part in "${parts[@]}"; do
    current="${current:+$current/}$part"
    if ! "${MPREMOTE_CMD[@]}" connect "$PORT" fs ls "$current" >/dev/null 2>&1; then
      run_mpremote fs mkdir "$current"
    fi
  done
}

mapfile -t files < <(
  find "$SRC_DIR" -type f \
    ! -path '*/__pycache__/*' \
    ! -name '*.pyc' \
    ! -name 'log.txt' \
    ! -name '*.bin' \
    | sort
)

if [[ "${#files[@]}" -eq 0 ]]; then
  echo "No files found to sync under $SRC_DIR" >&2
  exit 1
fi

if [[ "$CLEAN" -eq 1 ]]; then
  clean_remote_tree
fi

declare -A seen_dirs=()

for file in "${files[@]}"; do
  rel_path="${file#"$SRC_DIR"/}"
  rel_dir="$(dirname "$rel_path")"

  if [[ "$rel_dir" != "." && -z "${seen_dirs[$rel_dir]:-}" ]]; then
    ensure_remote_dir "$rel_dir"
    seen_dirs["$rel_dir"]=1
  fi
done

echo "Syncing ${#files[@]} files to $PORT"

for file in "${files[@]}"; do
  rel_path="${file#"$SRC_DIR"/}"
  run_mpremote fs cp "$file" ":$rel_path"
done

echo "Done"
