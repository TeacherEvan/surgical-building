#!/usr/bin/env python3
"""
Installer & Verification Runner for the Surgical-Building Skill Package.
Deploys to:
  1. Hermes Agent:     ~/.hermes/skills/surgical-building
  2. Gemini Antigravity: ~/.gemini/antigravity-cli/skills/surgical-building, ~/.gemini/skills/, ~/.gemini/surgical/
  3. Cursor:           ~/.cursor/skills/surgical-building and ~/.cursor/rules/surgical-building.mdc
  4. OpenCode:         ~/.config/opencode/skills/surgical-building

Executes runtime self-tests on the SAT/A* layout solver and SHA-256 sandbox guard.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

CURSOR_RULE_CONTENT = """---
description: "Deterministic 2D-to-3D architectural, prop, and skeletal character reconstruction engine using Blender, Three.js, SVG, and Build123d."
alwaysApply: false
---

# Surgical-Building: Autonomous 2D/3D Reconstruction & Spatial Orchestration

When asked to construct, model, or reconstruct 3D/2D buildings, architecture, Google Maps replicas, procedural interiors, or rigged 3D characters from 2D images:

1. **Activate Surgical-Building Skill:** Load the full skill specification from `~/.cursor/skills/surgical-building/SKILL.md` or workspace rules.
2. **Never Guess Dimensions:** Execute `scripts/photogrammetry_investigator.py` to extract vanishing points ($V_x, V_y, V_z$), camera focal length, and metric anchors (doors $2.10m$, commercial stories $3.90m$, residential $2.85m$).
3. **Mandatory Interactive Collaboration Gate:**
   - **Architecture:** Pause after exterior metrology is locked and ask:
     > *"Exterior projective metrology is locked ([W]m x [D]m x [H]m). Should I improvise and construct the full interior layout and furnishings to the best of my capabilities?"*
   - **Character:** Ask whether static mesh or skeletal rig is required, recommend 4 tailored procedural actions (`Idle_Breathe`, `Locomotion_Run`, `Jump_Arc`, `Action_Interact`), and present 3 platform options (Three.js WebGL, Godot 4.x, or SVG 2.5D).
4. **Collision-Free Layouts:** Use `scripts/sat_layout_solver.py` to enforce zero SAT/OBB collision overlap, $0.95m$ door swing clearances, and continuous $A^*$ navigable paths (>= $0.85m$).
5. **Headless Verification:** Run `scripts/blender_qa_reviewer.py` to audit non-manifold edges ($0$), vertex bounds (<= $65,535$), and 4-angle diagnostic silhouette IoU (>= $0.82$).
"""

DEFAULT_TARGETS = [
    "~/.hermes/skills/surgical-building",
    "~/.config/opencode/skills/surgical-building",
    "~/.gemini/antigravity-cli/skills/surgical-building",
    "~/.gemini/skills/surgical-building",
    "~/.gemini/surgical/surgical-building",
    "~/.cursor/skills/surgical-building",
]

def install_to_directory(src_root: Path, dest_root: Path):
    dest_root.mkdir(parents=True, exist_ok=True)
    items_to_copy = ("SKILL.md", "README.md", "runtime", "schemas", "scripts", "references", "surgical_building", "examples")

    for item in items_to_copy:
        s = src_root / item
        d = dest_root / item
        if not s.exists():
            continue
        if s.is_dir():
            if d.exists():
                shutil.rmtree(d)
            shutil.copytree(s, d)
        elif s.is_file():
            shutil.copy2(s, d)

    scripts_dir = dest_root / "scripts"
    if scripts_dir.exists():
        for script in scripts_dir.glob("*.py"):
            script.chmod(0o755)
        for script in scripts_dir.glob("*.sh"):
            script.chmod(0o755)

def deploy_cursor_rule():
    rule_path = Path(os.path.expanduser("~/.cursor/rules/surgical-building.mdc")).resolve()
    rule_path.parent.mkdir(parents=True, exist_ok=True)
    rule_path.write_text(CURSOR_RULE_CONTENT, encoding="utf-8")
    print(f"[OK] Deployed Cursor rule to: {rule_path}")

def run_self_tests(skill_root: Path):
    print(">>> Running deterministic runtime & SAT/A* layout self-tests...")
    sandbox_script = skill_root / "runtime" / "surgical_sandbox.py"
    solver_script = skill_root / "scripts" / "sat_layout_solver.py"

    subprocess.run([sys.executable, str(sandbox_script)], check=True)
    subprocess.run([sys.executable, str(solver_script)], check=True)
    print("[OK] All deterministic runtime & SAT/A* layout self-tests passed.")

def main():
    parser = argparse.ArgumentParser(description="Install and verify surgical-building skill package.")
    parser.add_argument("--target", "-t", action="append", help="Custom install target directory (can specify multiple)")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running self-tests after installation")
    args = parser.parse_args()

    src_root = Path(__file__).resolve().parent
    targets = args.target if args.target else DEFAULT_TARGETS

    seen_real_paths = set()
    deployed_roots = []

    for target_str in targets:
        dest = Path(os.path.expanduser(target_str)).resolve()
        # Handle symlinks like ~/.config/opencode/skills -> ~/.hermes/skills
        real_dest = dest.resolve()
        if real_dest in seen_real_paths:
            print(f"[SKIP] Target already deployed (symlink/duplicate): {dest} -> {real_dest}")
            continue
        seen_real_paths.add(real_dest)

        install_to_directory(src_root, dest)
        deployed_roots.append(dest)
        print(f"[OK] Installed surgical-building to: {dest}")

    deploy_cursor_rule()

    if not args.skip_tests and deployed_roots:
        run_self_tests(deployed_roots[0])

    print("\n[SUCCESS] surgical-building successfully applied across all agent platforms:")
    print("  - .hermes:            ~/.hermes/skills/surgical-building")
    print("  - Gemini Antigravity: ~/.gemini/antigravity-cli/skills/surgical-building")
    print("  - Cursor:             ~/.cursor/skills/surgical-building & ~/.cursor/rules/surgical-building.mdc")
    print("  - OpenCode:           ~/.config/opencode/skills/surgical-building")

if __name__ == "__main__":
    main()
