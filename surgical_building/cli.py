#!/usr/bin/env python3
"""
Command line interface for the surgical-building skill package.
"""
import argparse
import json
import sys
from pathlib import Path

from scripts.photogrammetry_investigator import compute_spatial_manifest, compute_spatial_manifest_analytical
from scripts.zone_classifier import classify_and_generate_program
from scripts.sat_layout_solver import solve_room_layout
from scripts.svg_to_build123d_shell import generate_svg_blueprint, build_parametric_shell_cad
from scripts.threejs_scene_compiler import compile_threejs_module
from scripts.blender_qa_reviewer import run_full_qa


def cmd_gate_a(args):
    """Outputs the Gate A Collaboration prompt for an exterior metrology manifest."""
    if args.manifest:
        with open(args.manifest, "r", encoding="utf-8") as f:
            m = json.load(f)
        dims = m["metric_dimensions_m"]
        w, d, h = dims["width_x"], dims["depth_y"], dims["height_z"]
    else:
        w, d, h = args.width, args.depth, args.height

    prompt = (
        f"Exterior projective metrology is locked ({w:.2f}m x {d:.2f}m x {h:.2f}m).\n"
        f"Should I improvise and construct the full interior layout and furnishings to the best of my capabilities?"
    )
    print(prompt)


def cmd_gate_b(args):
    """Outputs the Gate B Character intake prompt with recommended actions and platform examples."""
    prompt = (
        "=== 3D Character Reconstruction Intake ===\n"
        "1. Kinematics Query: Should the character be a static sculpt or rigged with a 52-bone skeletal armature capable of movement?\n"
        "2. Contextual Action Recommendations (30 FPS):\n"
        "   - Idle_Breathe (60f loop, thoracic wave)\n"
        "   - Locomotion_Run (24f loop, cyclic stride)\n"
        "   - Jump_Arc (36f one-shot, anticipation & landing compression)\n"
        "   - Action_Interact (48f one-shot, upper-body bone mask)\n"
        "3. Platform Target Examples:\n"
        "   - Option 1 (Next.js / Three.js WebGL): < 10,000 tris, single WebP atlas, Draco .glb, AnimationMixer state machine.\n"
        "   - Option 2 (Godot 4.x Native Game Engine): < 24,000 tris, SkeletonProfileHumanoid 52-bone rig, AnimationTree.\n"
        "   - Option 3 (2.5D SVG Cutout UI): Hierarchical vector bones with mathematical transform-origin pivots (60 FPS on edge devices).\n"
        "Which platform target would you like to build for?"
    )
    print(prompt)


def cmd_classify(args):
    with open(args.manifest, "r", encoding="utf-8") as f:
        m = json.load(f)
    res = classify_and_generate_program(m, fwr_ratio=args.fwr, has_signage_band=not args.no_signage)
    if args.output:
        Path(args.output).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"[OK] Saved interior program to {args.output}")
    else:
        print(json.dumps(res, indent=2))


def cmd_layout(args):
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    bounds = tuple(cfg.get("room_bounds", [0.0, 0.0, 6.0, 5.0]))
    door = tuple(cfg.get("door_pos", [0.9, 0.2, 0.95]))
    props = cfg.get("props", [])
    res = solve_room_layout(bounds, door, props, iterations=args.iterations)
    if args.output:
        Path(args.output).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"[OK] Saved layout placements to {args.output}")
    else:
        print(json.dumps(res, indent=2))


def cmd_blueprint(args):
    with open(args.manifest, "r", encoding="utf-8") as f:
        m = json.load(f)
    generate_svg_blueprint(m, args.output)
    print(f"[OK] Generated SVG blueprint: {args.output}")


def cmd_shell(args):
    with open(args.manifest, "r", encoding="utf-8") as f:
        m = json.load(f)
    build_parametric_shell_cad(m, args.output)
    print(f"[OK] Generated 3D CAD/STL shell: {args.output}")


def cmd_scene(args):
    with open(args.manifest, "r", encoding="utf-8") as mf:
        m = json.load(mf)
    with open(args.layout, "r", encoding="utf-8") as lf:
        l = json.load(lf)
    compile_threejs_module(m, l, args.output)
    print(f"[OK] Compiled Three.js scene: {args.output}")


def cmd_qa(args):
    rep = run_full_qa(args.mesh, args.manifest, args.report, args.mask if args.mask else "")
    print(json.dumps(rep, indent=2))


def main():
    parser = argparse.ArgumentParser(prog="surgical-building", description="Surgical-Building AI Agent Tool")
    sub = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # gate-a
    p_ga = sub.add_parser("gate-a", help="Output Gate A Interior Decision Prompt")
    p_ga.add_argument("--manifest", "-m", help="Path to spatial_manifest.json")
    p_ga.add_argument("--width", type=float, default=10.0, help="Width in meters")
    p_ga.add_argument("--depth", type=float, default=8.0, help="Depth in meters")
    p_ga.add_argument("--height", type=float, default=3.8, help="Height in meters")
    p_ga.set_defaults(func=cmd_gate_a)

    # gate-b
    p_gb = sub.add_parser("gate-b", help="Output Gate B Character Intake Prompt")
    p_gb.set_defaults(func=cmd_gate_b)

    # classify
    p_cl = sub.add_parser("classify", help="Commercial vs Residential zoning classifier")
    p_cl.add_argument("manifest", help="Path to spatial_manifest.json")
    p_cl.add_argument("--fwr", type=float, default=0.48, help="Fenestration-to-Wall Ratio")
    p_cl.add_argument("--no-signage", action="store_true", help="Set if building lacks commercial signage")
    p_cl.add_argument("--output", "-o", help="Optional output JSON path")
    p_cl.set_defaults(func=cmd_classify)

    # layout
    p_lay = sub.add_parser("layout", help="Solve SAT collision-free furniture layout")
    p_lay.add_argument("config", help="Path to layout config JSON (room_bounds, door_pos, props)")
    p_lay.add_argument("--iterations", type=int, default=3000, help="Annealing iterations")
    p_lay.add_argument("--output", "-o", help="Optional output JSON path")
    p_lay.set_defaults(func=cmd_layout)

    # blueprint
    p_bp = sub.add_parser("blueprint", help="Generate 2D SVG blueprint from manifest")
    p_bp.add_argument("manifest", help="Path to spatial_manifest.json")
    p_bp.add_argument("output", help="Output SVG path")
    p_bp.set_defaults(func=cmd_blueprint)

    # shell
    p_sh = sub.add_parser("shell", help="Generate watertight 3D CAD/STL shell from manifest")
    p_sh.add_argument("manifest", help="Path to spatial_manifest.json")
    p_sh.add_argument("output", help="Output STL path")
    p_sh.set_defaults(func=cmd_shell)

    # scene
    p_sc = sub.add_parser("scene", help="Compile Three.js scene module")
    p_sc.add_argument("manifest", help="Path to spatial_manifest.json")
    p_sc.add_argument("layout", help="Path to layout.json")
    p_sc.add_argument("output", help="Output TypeScript/JS file path")
    p_sc.set_defaults(func=cmd_scene)

    # qa
    p_qa = sub.add_parser("qa", help="Run geometric and dimensional QA review")
    p_qa.add_argument("mesh", help="Path to STL/OBJ/glTF mesh")
    p_qa.add_argument("manifest", help="Path to spatial_manifest.json")
    p_qa.add_argument("report", help="Output qa_debrief.json path")
    p_qa.add_argument("--mask", help="Optional reference silhouette mask PNG")
    p_qa.set_defaults(func=cmd_qa)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
