#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: start.sh [--rebuild]"
  echo ""
  echo "Start all containers in detached mode."
  echo ""
  echo "Options:"
  echo "  --rebuild   Rebuild images before starting"
  echo "  -h, --help  Show this help message"
  exit 0
fi

BUILD_FLAG=""
if [[ "${1:-}" == "--rebuild" ]]; then
  BUILD_FLAG="--build"
fi


podman-compose up --force-recreate $BUILD_FLAG -d
