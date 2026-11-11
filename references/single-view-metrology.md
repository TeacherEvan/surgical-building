# Single-View Projective Metrology & Photogrammetry Reference

This document formalizes the single-view projective geometry pipeline implemented in `scripts/photogrammetry_investigator.py` for extracting metric 3D dimensional constraints from 2D imagery (e.g. Google Street View, aerial orthophotos, architectural photography).

---

## 1. Mathematical Formulation

### 1.1 Vanishing Point Formulation (Orthogonal Triad)
Given perspective projection with camera center $\mathbf{C}$ and intrinsic calibration matrix $\mathbf{K}$:

$$\mathbf{x} = \mathbf{K} [\mathbf{R} \mid \mathbf{t}] \mathbf{X}$$

Under zero skew and square pixels:

$$\mathbf{K} = \begin{bmatrix} f & 0 & u_0 \\ 0 & f & v_0 \\ 0 & 0 & 1 \end{bmatrix}$$

Assuming principal point $\mathbf{P}_c = (u_0, v_0) \approx (W/2, H/2)$, the orthogonality constraint for any two vanishing points $\mathbf{v}_i, \mathbf{v}_j$ corresponding to orthogonal scene directions $\mathbf{d}_i \perp \mathbf{d}_j$ states:

$$\mathbf{v}_i^T \mathbf{\omega} \mathbf{v}_j = 0$$

where $\mathbf{\omega} = (\mathbf{K}\mathbf{K}^T)^{-1}$ is the image of the absolute conic (IAC).

Expanding this constraint yields camera focal length $f$:

$$f = \sqrt{- (\mathbf{v}_x - \mathbf{P}_c) \cdot (\mathbf{v}_y - \mathbf{P}_c)}$$

### 1.2 Horizon Line Calibration
The horizon line $\mathbf{l}_h$ is the line joining the horizontal vanishing points:

$$\mathbf{l}_h = \mathbf{v}_x \times \mathbf{v}_y$$

For any ground point $\mathbf{b}$ and vertical point $\mathbf{t}$ aligned with the vertical vanishing point $\mathbf{v}_z$, their distance to the horizon provides projective invariant coordinates.

### 1.3 Cross-Ratio Height Estimation (Criminisi Invariant)
Given reference datum height $H_{\text{ref}}$ (e.g., standard door $2.10\text{m}$, commercial floor-to-floor $3.90\text{m}$) with base $\mathbf{b}_{\text{ref}}$ and top $\mathbf{t}_{\text{ref}}$, the metric height $H_x$ of an arbitrary vertical segment $(\mathbf{b}_x, \mathbf{t}_x)$ is given by the projective cross-ratio:

$$\frac{H_x}{H_{\text{ref}}} = \frac{\|\mathbf{t}_x - \mathbf{b}_x\| \cdot \|\mathbf{v}_z - \mathbf{t}_{\text{ref}}\|}{\|\mathbf{t}_{\text{ref}} - \mathbf{b}_{\text{ref}}\| \cdot \|\mathbf{v}_z - \mathbf{t}_x\|}$$

---

## 2. Real-World Metric Anchors & Datums

When resolving scale from images without lidar/EXIF metadata, lock calibration against the following real-world anchors:

| Physical Feature | Standard Metric Dimensions | Variance Tolerance |
| :--- | :--- | :--- |
| **Standard Entrance Door** | $2.10\text{m} \times 0.90\text{m}$ | $\pm 0.05\text{m}$ |
| **Standard Brick Course** | $0.065\text{m} (\text{H}) \times 0.215\text{m} (\text{L})$ | $\pm 0.005\text{m}$ |
| **Standard Stair Riser / Tread** | Riser: $0.17\text{m}$, Tread: $0.28\text{m}$ | $\pm 0.02\text{m}$ |
| **Commercial Story Height** | $3.60\text{m} - 4.20\text{m}$ (default: $3.90\text{m}$) | $\pm 0.20\text{m}$ |
| **Residential Story Height** | $2.70\text{m} - 3.00\text{m}$ (default: $2.85\text{m}$) | $\pm 0.15\text{m}$ |
| **Standard Traffic Lane** | $3.20\text{m} - 3.70\text{m}$ (default: $3.50\text{m}$) | $\pm 0.20\text{m}$ |
| **Standard Passenger Car Wheelbase** | $2.60\text{m} - 2.85\text{m}$ (default: $2.70\text{m}$) | $\pm 0.15\text{m}$ |
| **Guardrail / Handrail Height** | $1.05\text{m} - 1.10\text{m}$ (default: $1.07\text{m}$) | $\pm 0.03\text{m}$ |

---

## 3. Emitted Contract: `spatial_manifest.json`

The photogrammetry subagent outputs `spatial_manifest.json` conforming to `schemas/spatial_manifest.schema.json`:
- `metric_dimensions_m`: Width ($X$), Depth ($Y$), Height ($Z$), estimated stories.
- `camera_parameters`: Extracted focal length, pitch, yaw, roll.
- `fenestration`: Window grid arrays, sill height ($0.90\text{m}$ default), lintel height.
- `pbr_palette_srgb`: Dominant albedo hex colors, roughness, metalness values.
