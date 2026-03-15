#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: logs.sh"
  echo ""
  echo "Tail logs from all containers."
  echo ""
  echo "Options:"
  echo "  -h, --help  Show this help message"
  exit 0
fi

podman-compose logs -f
