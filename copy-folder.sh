#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: ./copy-folder.sh <source-dir> [esp-path]" >&2
  exit 1
fi

SRC_DIR="$1"
ESP_PATH="${2:-.}"
PORT="${MPREMOTE_PORT:-/dev/ttyUSB0}"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Source directory not found: $SRC_DIR" >&2
  exit 1
fi

if command -v mpremote >/dev/null 2>&1; then
  MPREMOTE_CMD=(mpremote)
elif command -v conda >/dev/null 2>&1; then
  MPREMOTE_CMD=(conda run --no-capture-output -n riego mpremote)
else
  echo "mpremote was not found on PATH, and conda is unavailable." >&2
  exit 1
fi

run_mpremote() {
  "${MPREMOTE_CMD[@]}" connect "$PORT" "$@"
}

ensure_remote_dir() {
  local dir="$1"
  local current=""
  local part
  IFS='/' read -r -a parts <<< "$dir"

  for part in "${parts[@]}"; do
    [[ -z "$part" ]] && continue
    current="${current:+$current/}$part"
    run_mpremote fs mkdir "$current" >/dev/null 2>&1 || true
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
  echo "No files found to copy under $SRC_DIR" >&2
  exit 1
fi

ordered_files=()
main_files=()
boot_files=()
for file in "${files[@]}"; do
  case "$(basename "$file")" in
    boot.py)
      boot_files+=("$file")
      ;;
    main.py)
      main_files+=("$file")
      ;;
    *)
      ordered_files+=("$file")
      ;;
  esac
done
files=("${ordered_files[@]}" "${main_files[@]}" "${boot_files[@]}")

echo "Copying ${#files[@]} files from $SRC_DIR to $ESP_PATH on $PORT"

for file in "${files[@]}"; do
  rel_path="${file#"$SRC_DIR"/}"
  rel_dir="$(dirname "$rel_path")"

  if [[ "$ESP_PATH" == "." ]]; then
    remote_path="$rel_path"
  else
    remote_path="$ESP_PATH/$rel_path"
  fi

  if [[ "$rel_dir" != "." ]]; then
    if [[ "$ESP_PATH" == "." ]]; then
      ensure_remote_dir "$rel_dir"
    else
      ensure_remote_dir "$ESP_PATH/$rel_dir"
    fi
  fi

  run_mpremote fs cp "$file" ":$remote_path"
done

echo "Done"
