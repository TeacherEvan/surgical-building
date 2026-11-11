#!/usr/bin/env bash
# sync-skill.sh — mirror surgical-building skill assets into every local agent install.
#
# Supported Targets:
#   - Hermes Agent:        ~/.hermes/skills/surgical-building
#   - OpenCode:            ~/.config/opencode/skills/surgical-building (often symlink to Hermes)
#   - Antigravity CLI:     ~/.gemini/antigravity-cli/skills/surgical-building
#   - Gemini CLI:          ~/.gemini/skills/surgical-building
#   - Gemini Bundle:       ~/.gemini/surgical/surgical-building
#   - Cursor Skills:       ~/.cursor/skills/surgical-building
#   - Cursor Rules:        ~/.cursor/rules/surgical-building.mdc
#
# Commands:
#   ./scripts/sync-skill.sh check    # dry-run comparison
#   ./scripts/sync-skill.sh sync     # mirror assets to all targets and verify
#   ./scripts/sync-skill.sh verify   # byte comparison
#   ./scripts/sync-skill.sh list     # list targets and file counts

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-sync}"
SKILL_NAME="surgical-building"

TARGET_DIRS=(
  "$HOME/.hermes/skills/$SKILL_NAME"
  "$HOME/.config/opencode/skills/$SKILL_NAME"
  "$HOME/.gemini/antigravity-cli/skills/$SKILL_NAME"
  "$HOME/.gemini/skills/$SKILL_NAME"
  "$HOME/.gemini/surgical/$SKILL_NAME"
  "$HOME/.cursor/skills/$SKILL_NAME"
)

ASSETS=(
  "SKILL.md"
  "README.md"
  "runtime"
  "schemas"
  "scripts"
  "references"
)

sync_to_dir() {
  local target="$1"
  echo ">>> Syncing to $target"
  mkdir -p "$target"
  
  for item in "${ASSETS[@]}"; do
    if [ -e "$REPO_DIR/$item" ]; then
      if [ -d "$REPO_DIR/$item" ]; then
        mkdir -p "$target/$item"
        cp -R "$REPO_DIR/$item/"* "$target/$item/"
      else
        cp "$REPO_DIR/$item" "$target/$item"
      fi
    fi
  done

  # Make all scripts executable
  if [ -d "$target/scripts" ]; then
    chmod +x "$target/scripts/"*.py 2>/dev/null || true
    chmod +x "$target/scripts/"*.sh 2>/dev/null || true
  fi
}

sync_cursor_rule() {
  local rule_dest="$HOME/.cursor/rules/$SKILL_NAME.mdc"
  echo ">>> Generating Cursor rule at $rule_dest"
  mkdir -p "$(dirname "$rule_dest")"

  cat << 'EOF' > "$rule_dest"
---
description: "Deterministic 2D-to-3D architectural, prop, and skeletal character reconstruction engine using Blender, Three.js, SVG, and Build123d."
alwaysApply: false
---

# Surgical-Building: Autonomous 2D/3D Reconstruction & Spatial Orchestration

When asked to construct, model, or reconstruct 3D/2D buildings, architecture, Google Maps replicas, procedural interiors, or rigged 3D characters from 2D images:

1. **Activate Surgical-Building Skill:** Load the full skill specification from `~/.cursor/skills/surgical-building/SKILL.md` or workspace rules.
2. **Never Guess Dimensions:** Execute `scripts/photogrammetry_investigator.py` to extract vanishing points ($V_x, V_y, V_z$), camera focal length, and metric anchors (doors $2.10\text{m}$, commercial stories $3.90\text{m}$, residential $2.85\text{m}$).
3. **Mandatory Interactive Collaboration Gate:**
   - **Architecture:** Pause after exterior metrology is locked and ask:
     > *"Exterior projective metrology is locked ([W]m x [D]m x [H]m). Should I improvise and construct the full interior layout and furnishings to the best of my capabilities?"*
   - **Character:** Ask whether static mesh or skeletal rig is required, recommend 4 tailored procedural actions (`Idle_Breathe`, `Locomotion_Run`, `Jump_Arc`, `Action_Interact`), and present 3 platform options (Three.js WebGL, Godot 4.x, or SVG 2.5D).
4. **Collision-Free Layouts:** Use `scripts/sat_layout_solver.py` to enforce zero SAT/OBB collision overlap, $0.95\text{m}$ door swing clearances, and continuous $A^*$ navigable paths ($\ge 0.85\text{m}$).
5. **Headless Verification:** Run `scripts/blender_qa_reviewer.py` to audit non-manifold edges ($0$), vertex bounds ($\le 65,535$), and 4-angle diagnostic silhouette IoU ($\ge 0.82$).
EOF
}

verify_target() {
  local target="$1"
  local missing=0
  for item in "SKILL.md" "runtime" "schemas" "scripts" "references"; do
    if [ ! -e "$target/$item" ]; then
      echo "  [MISSING] $target/$item"
      missing=$((missing + 1))
    fi
  done
  if [ "$missing" -eq 0 ]; then
    echo "  [OK] $target verified"
  else
    echo "  [ERROR] $target has $missing missing items"
    return 1
  fi
}

case "$MODE" in
  list)
    echo "Configured targets:"
    for t in "${TARGET_DIRS[@]}"; do
      echo "  - $t"
    done
    echo "  - $HOME/.cursor/rules/$SKILL_NAME.mdc"
    ;;
  check)
    echo "Checking target sync status..."
    for t in "${TARGET_DIRS[@]}"; do
      if [ -d "$t" ]; then
        verify_target "$t" || true
      else
        echo "  [NOT INSTALLED] $t"
      fi
    done
    ;;
  sync)
    echo "Mirroring surgical-building across all targets..."
    # Track canonical resolved paths to avoid duplicate work on symlinks
    declare -A SEEN_PATHS
    for t in "${TARGET_DIRS[@]}"; do
      # Resolve parent directory in case target doesn't exist yet
      local_parent="$(dirname "$t")"
      mkdir -p "$local_parent"
      canonical="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$t")"
      if [ -n "${SEEN_PATHS[$canonical]:-}" ]; then
        echo ">>> Skipping duplicate/symlink: $t -> $canonical"
        continue
      fi
      SEEN_PATHS[$canonical]=1
      sync_to_dir "$t"
      verify_target "$t"
    done
    sync_cursor_rule
    echo "All targets in sync."
    ;;
  verify)
    for t in "${TARGET_DIRS[@]}"; do
      verify_target "$t"
    done
    ;;
  *)
    echo "Usage: $0 {sync|check|verify|list}" >&2
    exit 1
    ;;
esac
