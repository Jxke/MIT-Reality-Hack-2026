#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: status.sh"
  echo ""
  echo "Display status of containers and networks."
  echo ""
  echo "Options:"
  echo "  -h, --help  Show this help message"
  exit 0
fi

echo "=== arduino-router ==="
systemctl is-active arduino-router 2>/dev/null || true

echo ""
echo "=== Containers ==="
podman-compose ps

echo ""
echo "=== Networks ==="
podman network ls

# echo ""
# echo "=== Volumes ==="
# podman volume ls
