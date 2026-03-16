#!/usr/bin/env bash
set -euo pipefail

# Remote host to scp clips to. Override via env or edit defaults below.
REMOTE_USER="${CLIP_REMOTE_USER:-}"
REMOTE_HOST="${CLIP_REMOTE_HOST:-}"
REMOTE_DIR="${CLIP_REMOTE_DIR:-~/vad_clips}"

CLIP_DIR="${CLIP_DEBUG_DIR:-/home/arduino/vad_clips}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: fetch_clips.sh"
  echo ""
  echo "scp the last VAD debug clips from this board to a remote machine."
  echo ""
  echo "Configure via environment variables or .env:"
  echo "  CLIP_REMOTE_USER   SSH user on the remote machine"
  echo "  CLIP_REMOTE_HOST   Hostname or IP of the remote machine"
  echo "  CLIP_REMOTE_DIR    Destination directory (default: ~/vad_clips)"
  echo "  CLIP_DEBUG_DIR     Local clips directory (default: /home/arduino/vad_clips)"
  exit 0
fi

# Source .env from the project root if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -o allexport
  source "$ENV_FILE"
  set +o allexport
  REMOTE_USER="${CLIP_REMOTE_USER:-}"
  REMOTE_HOST="${CLIP_REMOTE_HOST:-}"
  REMOTE_DIR="${CLIP_REMOTE_DIR:-~/vad_clips}"
  CLIP_DIR="${CLIP_DEBUG_DIR:-/home/arduino/vad_clips}"
fi

if [[ -z "$REMOTE_USER" || -z "$REMOTE_HOST" ]]; then
  echo "Error: CLIP_REMOTE_USER and CLIP_REMOTE_HOST must be set in .env or environment." >&2
  exit 1
fi

if [[ ! -d "$CLIP_DIR" ]] || [[ -z "$(ls -A "$CLIP_DIR"/*.wav 2>/dev/null)" ]]; then
  echo "No clips found in $CLIP_DIR"
  exit 0
fi

echo "=== Copying clips from $CLIP_DIR to $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR ==="
ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_DIR"
scp "$CLIP_DIR"/*.wav "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"
echo "Done."
