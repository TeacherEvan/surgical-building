#!/usr/bin/env bash
# install_surgical_building.sh — One-command installer for surgical-building across all agent harnesses.
#
# Targets:
#   - Hermes Agent:        ~/.hermes/skills/surgical-building/
#   - Gemini Antigravity:  ~/.gemini/antigravity-cli/skills/surgical-building/
#   - Cursor:              ~/.cursor/skills/surgical-building/ & ~/.cursor/rules/surgical-building.mdc
#   - OpenCode:            ~/.config/opencode/skills/surgical-building/
#
# Usage:
#   bash install_surgical_building.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="${PYTHON_EXEC:-python3}"

echo "=== Installing Surgical-Building Skill Package ==="
"$PYTHON_EXEC" "$SCRIPT_DIR/install_surgical_building.py" "$@"
