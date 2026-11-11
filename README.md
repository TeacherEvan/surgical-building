# Surgical-Building 🏛️📐🤖

[![CI](https://github.com/TeacherEvan/surgical-building/actions/workflows/ci.yml/badge.svg)](https://github.com/TeacherEvan/surgical-building/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Harness Support](https://img.shields.io/badge/Harness-Hermes%20%7C%20Antigravity%20%7C%20Cursor%20%7C%20OpenCode-blue)](https://github.com/TeacherEvan/surgical-building)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Conformance](https://img.shields.io/badge/Hermes%20Conformance-100%25%20PASS-brightgreen)](https://github.com/TeacherEvan/surgical-building)

> **Autonomous 2D/3D Architectural, Prop, and Skeletal Character Reconstruction Skill for AI Agents.**
> Part of the **Agent-Surgery-Skills** family.

---

## Overview

**Surgical-Building** provides an end-to-end, deterministic engineering skill for autonomous AI agents (Hermes Agent, Gemini Antigravity, Cursor, and OpenCode) to reconstruct watertight 3D buildings, procedural interiors, and fully rigged 3D characters directly from 2D images, Google Maps/Street View, or architectural blueprints.

Unlike loose generative prompt wrappers, **Surgical-Building** enforces:
- **Zero Hallucinated Dimensions:** Single-View Projective Metrology (Criminisi et al.) extracting vanishing points, horizon calibration, and metric datum scaling.
- **Unified 4-Engine Geometry Stack:** Parametric SVG, Build123d (OpenCASCADE B-Rep CAD), Blender Headless (`bpy`), and Three.js / Godot 4.3.
- **Collision-Free Procedural Interiors:** Separating Axis Theorem (SAT) on 2D Oriented Bounding Boxes (OBB), wall-normal snapping, door swing arc clearance, and $A^*$ navigable human walkways.
- **Interactive Collaboration Gates:** Hard stops prompting the user for interior improvisation decisions or character movement/platform selection before synthesis.
- **Headless QA Reviewer & Self-Healing Loop:** Multi-angle diagnostic contact sheets, non-manifold edge verification ($0$ tolerance), and Silhouette Intersection-over-Union ($\text{IoU} \ge 0.82$) with a 3-cycle circuit breaker.
- **Pure-Python Standard Library Resilience:** Zero-dependency analytical CSG and photogrammetric fallbacks so agents never fail when optional libraries (OpenCV, OpenCASCADE) are absent.
- **Blender MCP Integration:** First-class bridging for the live Blender Model Context Protocol server.

---

## The 4-Engine Geometry Pipeline

| Stage | Engine | Pipeline Role | Strict Limits & Performance Standards |
| :--- | :--- | :--- | :--- |
| **Stage A: 2D Vector Truth** | **Parametric SVG** | Orthographic floorplans, elevation blueprints, window/door cutouts, 2.5D character rigs | `viewBox="0 0 2048 2048"`; scale $1\text{px} = 0.01\text{m}$; coordinate precision $0.01$; max $1,200$ DOM nodes; non-self-intersecting loops. |
| **Stage B: Exact B-Rep CAD** | **Build123d (OpenCASCADE)** | Watertight architectural shells, boolean window/door cutouts, hard-surface furniture | Kernel tolerance $10^{-4}\text{m}$; Euler-Poincaré $\chi = V - E + F = 2(1-g)$ verified; fillet safety $r \le 0.45 \times \min(E_{\text{adj}})$. |
| **Stage C: Organic, Rigging & Baking** | **Blender 4.x (`bpy`)** | Organic character topology, 52-bone humanoid rigging, procedural `FCurve` animations, UV unwrapping, PBR baking | `blender -b -noaudio --threads 4 -P script.py`; max $65,535$ verts/mesh; $\ge 85\%$ quads on characters; zero non-manifold edges; Draco level 6. |
| **Stage D: Real-Time Delivery** | **Three.js (`r165+`) / Godot 4.3** | Interactive WebGL/WebGPU scene compilation (`InstancedMesh`, BVH raycasting) or Godot `.tscn` `CharacterBody3D` | Max $100$ draw calls/frame; shadow maps $2048 \times 2048$ (`PCFSoftShadowMap`); max texture $2048 \times 2048$ `.webp`. |

---

## State Machine & Multi-Agent Architecture

```
[Master Orchestrator Agent]
   │
   ├── Phase 1: [Photogrammetry & Perspective Subagent] (Image -> spatial_manifest.json)
   │
   ├── Phase 2: [Interactive Gatekeeper] (User Prompting: Interior Improv or Kinematics/Platform)
   │               ├── Gate A (Architecture): "Exterior calibrated. Improvise interior?"
   │               └── Gate B (Character): Pose vs Rig + 4 Tailored Actions + 3 Platform Examples
   │
   ├── Phase 3: Parallel Build Pool (MAX_CONCURRENCY = 2)
   │      ├── Branch A (Architecture):
   │      │      ├── [Subagent: Zone-Investigator] (Business vs Residential -> interior_program.json)
   │      │      ├── [Subagent: Furniture-Builder] (Origin-centered props + AABB bounds)
   │      │      └── [Subagent: Placement-Solver] (SAT OBB + Door Arcs + A* Walkway Solver)
   │      └── Branch B (Character):
   │             ├── [Subagent: Mesh-Topology] (Low/Mid poly + quad dominant topology)
   │             └── [Subagent: Character-Rigger] (52-bone armature + procedural NLA clips)
   │
   └── Phase 4: [Subagent: QA-Reviewer] (4-angle diagnostic render + IoU >= 0.82 + 3-cycle retry)
```

---

## Interactive Collaboration Gates

### Gate A: Architecture & Google Maps Replica Flow
1. **Telemetry Presentation:** Computes calibrated footprint dimensions $[W]\text{m} \times [D]\text{m}$, story height, and camera focal length.
2. **Mandatory Prompt:**
   > *"Exterior projective metrology is locked (`[W]m x [D]m x [H]m`). Should I improvise and construct the full interior layout and furnishings to the best of my capabilities?"*
3. **Branching:**
   - **No:** Proceed directly to watertight shell extrusion and Three.js/glTF compilation.
   - **Yes:** Trigger the 3-stage interior subagent pipeline (`Zone-Investigator` $\to$ `Furniture-Builder` $\to$ `Placement-Solver`).

### Gate B: 3D Character Reconstruction Flow
1. **Kinematics Query:** Static display sculpt vs. rigged skeletal armature capable of movement.
2. **Contextual Action Recommendations:** 4 tailored animations based on visual archetype:
   - `Idle_Breathe` ($60\text{f} @ 30\text{fps}$, looping thoracic wave)
   - `Locomotion_Run` ($24\text{f} @ 30\text{fps}$, counter-arm swing stride)
   - `Jump_Arc` ($36\text{f} @ 30\text{fps}$, anticipation, launch, landing compression)
   - `Action_Interact` / `Action_Consume` ($48\text{f} @ 30\text{fps}$, masked upper-body)
3. **Platform Selection & 3 Concrete Examples:**
   - **Next.js / Three.js Canvas:** $< 10,000$ tris, Draco `.glb`, WebP texture atlas, Three.js `AnimationMixer` state machine.
   - **Godot 4.x Indie Game Engine:** $< 24,000$ tris, rigged to 52-bone `SkeletonProfileHumanoid` for `AnimationTree` and `CapsuleShape3D`.
   - **2.5D SVG Interactive UI:** Hierarchical `<g id="bone_...">` vector cutout rig with mathematical `transform-origin` pivots for 60 FPS mobile rendering.

---

## Command Line Interface (CLI)

The package provides a unified CLI for agents and developers:

```bash
# Output Gate A collaboration prompt
python3 -m surgical_building gate-a --width 12.0 --depth 8.5 --height 4.2

# Output Gate B character intake prompt
python3 -m surgical_building gate-b

# Run commercial vs residential zoning classification
python3 -m surgical_building classify manifest.json -o interior_program.json

# Solve SAT collision-free furniture layout
python3 -m surgical_building layout config.json -o layout.json

# Generate 2D SVG blueprint
python3 -m surgical_building blueprint manifest.json blueprint.svg

# Generate 3D watertight CAD/STL shell
python3 -m surgical_building shell manifest.json shell.stl

# Compile Three.js scene module
python3 -m surgical_building scene manifest.json layout.json scene.ts

# Execute geometry & telemetry QA review
python3 -m surgical_building qa shell.stl manifest.json qa_debrief.json
```

---

## Installation & Harness Setup

Deploy to all local agent environments (`.hermes`, `gemini antigravity`, `cursor`, and `opencode`) with a single command:

```bash
# Clone the repository
git clone https://github.com/TeacherEvan/surgical-building.git
cd surgical-building

# Run installer (installs across all detected agent platforms and runs self-tests)
./install_surgical_building.sh
```

Or via Python:
```bash
python3 install_surgical_building.py
```

### Supported Installation Paths

| Platform | Deployment Target | Format |
| :--- | :--- | :--- |
| **Hermes Agent** | `~/.hermes/skills/surgical-building/` | Native Skill Directory (`SKILL.md`, scripts, schemas) |
| **Gemini Antigravity** | `~/.gemini/antigravity-cli/skills/surgical-building/` | Antigravity CLI Skill Bundle |
| **Cursor** | `~/.cursor/skills/surgical-building/`<br>`~/.cursor/rules/surgical-building.mdc` | Skill Package & Global MDC Rule |
| **OpenCode** | `~/.config/opencode/skills/surgical-building/` | OpenCode Skill Registry |

---

## Verification & Testing

Run the deterministic test suite:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Run the Hermes skill conformance gate:

```bash
python3 scripts/conform.py
```

To sync changes between the git repository and all local agent installs:

```bash
./scripts/sync-skill.sh check   # Verify sync status
./scripts/sync-skill.sh sync    # Push latest commits to all platforms
./scripts/sync-skill.sh verify  # Authoritative byte cross-check
```

---

## End-to-End Ground Truth Example

A verified reference implementation is provided in [`examples/google_maps_storefront/`](examples/google_maps_storefront/):
- `spatial_manifest.json`: Single-view photogrammetric calibration of a $12\text{m} \times 8.5\text{m} \times 4.2\text{m}$ retail building.
- `blueprint.svg`: Parametric 2D vector blueprint with entrance door arcs.
- `storefront_shell.stl`: Watertight 3D architectural shell with door/window openings.
- `interior_program.json`: Commercial retail zoning with lighting and circulation rules.
- `layout.json`: 100% collision-free SAT furniture layout with guaranteed $A^*$ walkway clearance.
- `scene.ts`: Three.js scene compiler output with instanced meshes and shadow maps.
- `qa_debrief.json`: Approved QA debrief report confirming 0 non-manifold edges.

---

## Repository Structure

```
surgical-building/
├── SKILL.md                          # Master skill definition & orchestration rules
├── README.md                         # Project documentation & engineering specs
├── LICENSE                           # MIT License
├── pyproject.toml                    # Standard Python package specification
├── install_surgical_building.py      # Cross-platform installer & test runner
├── install_surgical_building.sh      # Shell wrapper for one-command installation
├── .cursor/
│   └── rules/surgical-building.mdc   # Cursor rule for auto-activating the skill
├── surgical_building/                # Python package
│   ├── __init__.py
│   ├── __main__.py
│   └── cli.py                        # Unified command line tool
├── runtime/
│   └── surgical_sandbox.py           # Realpath sandbox, SHA-256 deduplication, & circuit breaker
├── schemas/
│   ├── spatial_manifest.schema.json  # Camera, dimension, & PBR palette contract
│   ├── interior_program.schema.json  # Zoning, room program, & furniture manifest
│   ├── jobcard.schema.json           # Subagent task dispatch envelope
│   └── debrief_payload.schema.json   # Subagent completion debrief & QA audit payload
├── scripts/
│   ├── photogrammetry_investigator.py# Single-view perspective & vanishing point solver
│   ├── zone_classifier.py            # Commercial vs. Residential zoning classifier
│   ├── sat_layout_solver.py          # SAT/OBB collision solver & A* walkway verifier
│   ├── svg_to_build123d_shell.py     # 2D SVG blueprint to 3D CAD shell generator
│   ├── threejs_scene_compiler.py     # Three.js (r165+) scene compiler
│   ├── blender_character_rigger.py   # Headless Blender 52-bone character rigger
│   ├── blender_qa_reviewer.py        # Headless QA reviewer & 4-angle contact sheet generator
│   ├── sync-skill.sh                 # Multi-platform sync & verification script
│   └── conform.py                    # Hermes Agent skill conformance checker
├── references/
│   ├── single-view-metrology.md      # Photogrammetric mathematical formulations
│   ├── sat-collision-energy-matrix.md# SAT collision & simulated annealing formulation
│   ├── engine-bridge-specs.md        # 4-engine coordinates, vertex limits, & glTF specs
│   └── blender-mcp-integration.md    # Live Blender MCP server tools & dual-mode execution
├── tests/
│   └── test_surgical_building.py     # 16 deterministic unit & integration tests
├── examples/
│   └── google_maps_storefront/       # Verified ground truth artifacts (STL, SVG, TS, JSON)
└── Docs/                             # Architectural design blueprints & concept notes
```

---

## License

MIT License. Copyright (c) 2026 TeacherEvan / Ewaldt Botha.
