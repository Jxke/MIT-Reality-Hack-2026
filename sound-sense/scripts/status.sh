#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "=== Containers ==="
podman-compose ps

echo ""
echo "=== Networks ==="
podman network ls

echo ""
echo "=== Volumes ==="
podman volume ls
