---
name: surgical-building
description: "Use when reconstructing 3D/2D architecture, Google Maps replicas, procedural interiors, or rigged characters from images using Blender, Three.js, SVG, and Build123d/Godot."
version: 2.1.0
author: "TeacherEvan, Hermes Agent"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    category: software-development
    tags: [3d-reconstruction, blender, threejs, photogrammetry, build123d, godot, svg, interior-design, character-rigging, spatial-manifest, sat-solver]
    related_skills: [plastic-surgery, surgical-implementation, surgical-orchestration, surgical-audit]
---

# SURGICAL-BUILDING: Autonomous 2D/3D Reconstruction & Spatial Orchestration Skill

## Auxiliary Resources

| File | Use |
| :--- | :--- |
| `references/single-view-metrology.md` | Single-view photogrammetry, vanishing point triad, Criminisi cross-ratio, and datum scale invariants |
| `references/sat-collision-energy-matrix.md` | Separating Axis Theorem (SAT), door-swing arc clearance, and $A^*$ navigable corridor solvers |
| `references/engine-bridge-specs.md` | Coordinate conversions ($+Z$ vs $+Y$), vertex budgets, glTF 2.0 handshake, and Draco compression |
| `schemas/spatial_manifest.schema.json` | JSON contract for extracted exterior geometry, camera parameters, and PBR palettes |
| `schemas/interior_program.schema.json` | JSON contract for commercial vs. residential zoning, room specs, and furniture manifests |
| `schemas/jobcard.schema.json` | Task card schema for dispatching sandboxed subagent workers |
| `schemas/debrief_payload.schema.json` | SHA-256 verified worker debrief payload and QA review reporting contract |

---

## 0. RUNTIME INVARIANTS & SYSTEM CONSTRAINTS
1. **Concurrency Ceiling:** Never spawn more than `MAX_CONCURRENCY = 2` subagents simultaneously. Headless Blender (`bpy`) and Build123d processes are capped at `2048 MB` RSS and `4 threads` (`OMP_NUM_THREADS=4`).
2. **Context Compaction Gate:** Monitor active context token usage. Trigger state compaction into `workspace/state_snapshot.json` if context exceeds `98,304 tokens`.
3. **Filesystem Sandbox:** Every subagent is strictly jailed via `realpath` verification (`runtime/surgical_sandbox.py`) to its designated subdirectory under `./workspace/job_<uuid>/`. Cross-folder writes outside `JobCard.allowed_write_paths` immediately abort the worker.
4. **Coordinate System & Units:**
   - **Metric Standard:** `1.0 unit = 1.000 meter` across all engines.
   - **Axis Convention:** Right-handed. Blender/Build123d use `+Z Up, -Y Forward`; glTF 2.0 exports automatically transform to `+Y Up, -Z Forward` for Three.js and Godot 4.x.
   - **Pivot Origin:** All structural shells and furniture props MUST have their local origin `(0, 0, 0)` at the bottom-center of their Axis-Aligned Bounding Box (`minZ = 0.000`).

---

## 1. THE UNIFIED 4-ENGINE GEOMETRY PIPELINE

| Stage | Engine | Role in Pipeline | Hard Technical Limits |
| :--- | :--- | :--- | :--- |
| **Stage A: 2D Vector Truth** | **Parametric SVG** | Orthographic floorplans, elevation blueprints, window/door cutouts, 2.5D character rigs | `viewBox="0 0 2048 2048"`; `1px = 0.01m`; coordinate precision `0.01`; max `1,200` DOM nodes; closed non-self-intersecting `<path>` loops (`shapely.is_valid == True`). |
| **Stage B: Exact B-Rep CAD** | **Build123d (OpenCASCADE)** | Extrudes SVG floorplans into watertight architectural shells, boolean window/door openings, and hard-surface furniture | Kernel tolerance `1e-4m`; Euler-Poincaré invariant $\chi = V - E + F = 2(1-g)$ verified; fillet radii $r \le 0.45 \times \min(E_{\text{adj}})$. |
| **Stage C: Organic, Rigging & Baking** | **Blender 4.x (`bpy`)** | Organic character topology, 52-bone humanoid rigging, procedural `FCurve` animations, UV unwrapping, PBR baking | `blender -b -noaudio --threads 4 -P script.py`; max `65,535` vertices/mesh; `>85%` quads on characters; zero non-manifold edges; Draco level `6`. |
| **Stage D: Real-Time Delivery** | **Three.js (`r165+`) / Godot 4.3** | Interactive WebGL/WebGPU scene compilation (`InstancedMesh`, BVH raycasting) or Godot `.tscn` `CharacterBody3D` | Max `100` draw calls/frame; shadow maps `2048x2048` (`PCFSoftShadowMap`); max texture `2048x2048` `.webp`. |

---

## 2. STATE MACHINE & MULTI-AGENT WORKFLOW

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

### PHASE 1: PHOTOGRAMMETRY & PERSPECTIVE CALIBRATION (MANDATORY FIRST PASS)
Before generating any 3D/2D geometry from a reference image (e.g., Google Maps, Street View, or concept art), execute `Subagent: Photogrammetry-Investigator` via `scripts/photogrammetry_investigator.py`:
1. **Vanishing Point & Camera Solver:**
   - Extract structural line segments via OpenCV LSD and compute 3 orthogonal vanishing points $V_x, V_y, V_z$ via RANSAC.
   - Compute camera focal length $f = \sqrt{-(V_x - P_c)\cdot(V_y - P_c)}$ and horizontal FOV.
2. **Datum-Anchored Cross-Ratio Scaling:**
   - Lock metric scale (`meters_per_pixel` at reference plane) against known real-world invariants:
     - Standard Entrance Door: `2.10m (H) x 0.90m (W)`
     - Standard Brick Course: `0.065m (H) x 0.215m (W)`
     - Guardrail / Handrail: `1.07m (H)`
     - Standard Traffic Lane: `3.50m`
     - Commercial Story Height: `3.90m` | Residential Story Height: `2.85m`
3. **Emit `spatial_manifest.json`:** Validate against `schemas/spatial_manifest.schema.json`.

---

### PHASE 2: INTERACTIVE COLLABORATION GATES (HARD STOP)
Once `spatial_manifest.json` (for architecture) or initial silhouette telemetry (for characters) is generated, the Master Orchestrator MUST pause and prompt the user before spawning Phase 3 synthesis workers.

#### GATE A: Architectural / Google Maps Replica Flow
1. Present calibrated exterior telemetry (`Footprint: [W]m x [D]m | Height: [H]m | Stories: [N] | Focal Length: [f]px`).
2. **Mandatory Prompt:**
   > *"Exterior projective metrology is locked (`[W]m x [D]m x [H]m`). Should I improvise and construct the full interior layout and furnishings to the best of my capabilities?"*
3. **Branching Execution:**
   - **If User says NO:** Run `scripts/svg_to_build123d_shell.py` -> `scripts/threejs_scene_compiler.py` -> Phase 4 QA.
   - **If User says YES:** Spawn the **3-Stage Interior Subagent Pipeline**:
     - **Worker 1 (`Subagent: Zone-Investigator`):** Runs `scripts/zone_classifier.py` to evaluate Fenestration-to-Wall Ratio (FWR), signage bands, story height, and footprint area. Classifies occupancy as `BUSINESS_COMMERCIAL` or `PRIVATE_RESIDENTIAL` and outputs `interior_program.json`.
     - **Worker 2 (`Subagent: Furniture-Builder`):** Generates origin-centered (`minZ = 0.000`) 3D props for every manifest item in `interior_program.json` using Build123d/Blender.
     - **Worker 3 (`Subagent: Placement-Solver`):** Runs `scripts/sat_layout_solver.py` using Oriented Bounding Boxes (OBB), Separating Axis Theorem (SAT) collision penalties, wall-normal snapping, `0.95m` door-swing arc exclusions, and $A^*$ pathfinding to guarantee navigable walkways (`>= 0.85m` residential, `>= 1.50m` commercial).

#### GATE B: 3D Character Reconstruction Flow
When the user requests a 3D character from an image or prompt, pause and output this 3-part interactive intake:
1. **Kinematics Query:** Ask whether the character should be a static sculpt or rigged with a skeletal armature for movement.
2. **Contextual Action Recommendations:** Recommend **4 tailored procedural animations** based on visual archetype:
   - `Idle_Breathe` (`60 frames @ 30fps`, looping thoracic/pelvis wave)
   - `Locomotion_Run` (`24 frames @ 30fps`, looping cyclic stride with counter-arm swing)
   - `Jump_Arc` (`36 frames @ 30fps`, anticipation crouch, parabolic launch, landing absorption)
   - `Action_Eat_Consume` or `Action_Interact` (`48 frames @ 30fps`, upper-body bone mask)
3. **Platform Target & 3 Concrete Portfolio-Matched Examples:** Ask which platform the character will be deployed on, providing 3 concrete examples aligned with existing engineering workflows:
   - **Example 1 — Next.js / Three.js WebGL Survival & Simulation Canvas:** `< 10,000 tris`, single `2048x2048` WebP atlas, Draco `.glb` with embedded `THREE.AnimationClip` tracks driven by a tick-based simulation state machine.
   - **Example 2 — Godot 4.x Indie Game Engine (`.glb` + `.tscn` CharacterBody3D):** `< 24,000 tris`, rigged to the 52-bone Godot `SkeletonProfileHumanoid` map for immediate `AnimationTree` blending and `CapsuleShape3D` collision.
   - **Example 3 — Lightweight 2.5D Parametric SVG Educational Rig:** Hierarchical `<g id="bone_...">` vector cutout rig with mathematical `transform-origin` pivots (`< 150 KB` payload, 60 FPS on ARM64 tablets and Intel N95 mini-PCs).

---

### PHASE 3: PARALLEL SYNTHESIS & SANDBOX ENFORCEMENT
1. Dispatch workers using `schemas/jobcard.schema.json` (max 2 parallel processes).
2. Validate every worker output via `runtime/surgical_sandbox.py` and `schemas/debrief_payload.schema.json`.

---

### PHASE 4: AUTONOMOUS QA REVIEWER & SELF-HEALING LOOP
Execute `Subagent: QA-Reviewer` via `scripts/blender_qa_reviewer.py`:
1. **Mesh & Layout Telemetry:** Verify `non_manifold_edges == 0`, `vertex_count <= 65535`, `floating_objects == 0` (`|minZ| <= 0.005m`), and dimensional error `<= 2.5%` against `spatial_manifest.json`.
2. **4-Angle Diagnostic Render & Silhouette IoU:** Render `front_0`, `right_90`, `top_ortho`, and `iso_45` views at `1024x1024` and compute Silhouette Intersection-over-Union (`IoU >= 0.82` against reference mask).
3. **Self-Healing Retry Loop (Max 3 Cycles):** If `status == "REJECTED"`, route the generated `fix_directives` back to the responsible subagent. Halt after 3 failed cycles.
