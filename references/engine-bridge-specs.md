# 4-Engine Geometry Pipeline & Coordinate Handshake Specifications

This document defines the interoperability, coordinate transforms, vertex budgets, and delivery formats across the 4 engines supported by `surgical-building`.

---

## 1. Coordinate System & Axis Conventions

All internal geometric representations conform to the **SI Metric Standard** ($1.0\text{ unit} = 1.000\text{ meter}$).

| Engine | Coordinate System | Up Vector | Forward Vector | Handedness | Export Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Blender 4.x (`bpy`)** | World Cartesian | $+Z$ | $-Y$ | Right-Handed | glTF 2.0 (`.glb`), FBX |
| **Build123d (B-Rep CAD)** | OpenCASCADE World | $+Z$ | $+Y$ | Right-Handed | STEP, STL, glTF |
| **Three.js (`r165+`)** | WebGL/WebGPU | $+Y$ | $-Z$ | Right-Handed | Web Canvas, React Three Fiber |
| **Godot 4.3 Engine** | SceneTree 3D | $+Y$ | $-Z$ | Right-Handed | `.tscn`, `.glb` CharacterBody3D |
| **Parametric SVG** | 2D Pixel Canvas | $+Y$ Down | $+X$ Right | Planar (2D) | SVG Vector Blueprint ($1\text{px} = 0.01\text{m}$) |

### glTF 2.0 Handshake Transform
When exporting from Blender or Build123d ($+Z\text{ Up}$) to Three.js or Godot ($+Y\text{ Up}$):
$$\begin{bmatrix} X_{\text{gltf}} \\ Y_{\text{gltf}} \\ Z_{\text{gltf}} \end{bmatrix} = \begin{bmatrix} 1 & 0 & 0 \\ 0 & 0 & 1 \\ 0 & -1 & 0 \end{bmatrix} \begin{bmatrix} X_{\text{source}} \\ Y_{\text{source}} \\ Z_{\text{source}} \end{bmatrix}$$
Standard glTF exporters in `bpy` handle this rotation natively when `--export_format='GLB'` is invoked.

---

## 2. Hard Geometric Limits & Quality Invariants

### 2.1 Blender Headless (`bpy`)
- **Invocation:** `blender -b -noaudio --threads 4 -P script.py`
- **Vertex Budget:** $\le 65,535$ vertices per single mesh buffer (ensures compatibility with 16-bit WebGL index buffers).
- **Topology:** $\ge 85\%$ quad faces on character meshes. Zero non-manifold edges (`BMEdge.is_manifold == True`).
- **Draco Compression:** Level 6 enabled on final `.glb` exports to minimize payload transfer size.

### 2.2 Three.js (`r165+`)
- **Draw Call Ceiling:** Max 100 draw calls per frame. Mandatory `THREE.InstancedMesh` for repeated furniture props.
- **Shadow Maps:** Capped at $2048 \times 2048$ resolution using `THREE.PCFSoftShadowMap`.
- **Texture Budgets:** Max $2048 \times 2048$ WebP textures; 8-bit sRGB color channels.

### 2.3 Parametric SVG (Floorplans & Cutouts)
- **Canvas:** `viewBox="0 0 2048 2048"`, scale $1\text{px} = 0.01\text{m}$ ($100\text{px} = 1.00\text{m}$).
- **Precision:** Coordinate points rounded to 2 decimal places ($0.01\text{m}$).
- **DOM Limit:** Maximum 1,200 SVG DOM nodes to ensure fluid 60 FPS rendering on mobile/tablet viewports.

### 2.4 Build123d (OpenCASCADE B-Rep CAD)
- **Kernel Tolerance:** $10^{-4}\text{m}$ ($0.1\text{mm}$).
- **Euler-Poincaré Formula Verification:** $\chi = V - E + F = 2(1 - g)$ where $g$ is genus (zero non-manifold self-intersections).
- **Fillet Safety:** $r_{\text{fillet}} \le 0.45 \times \min(E_{\text{adjacent}})$.
