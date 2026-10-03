#!/usr/bin/env bash
# Quick CLI shortcut for fiduciary harness
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec uv run fiduciary "$@"
