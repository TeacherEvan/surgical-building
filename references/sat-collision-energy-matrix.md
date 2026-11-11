# SAT Collision Layout Solver & Spatial Energy Optimization

This document outlines the Separating Axis Theorem (SAT) collision checking, Simulated Annealing layout optimization, and $A^*$ walkway clearance verification implemented in `scripts/sat_layout_solver.py`.

---

## 1. 2D Oriented Bounding Box (OBB) & SAT

Each furniture prop or room obstacle $i$ is modeled as a 2D Oriented Bounding Box in the ground plane ($XY$):
$$\text{OBB}_i = \{ \mathbf{c}_i, \mathbf{u}_i, \mathbf{v}_i, h_{w,i}, h_{d,i} \}$$
where $\mathbf{c}_i = (x_i, y_i)$ is center position, $\mathbf{u}_i = (\cos\theta_i, \sin\theta_i)$, $\mathbf{v}_i = (-\sin\theta_i, \cos\theta_i)$, and $h_{w,i}, h_{d,i}$ are half-width and half-depth.

### 1.1 Separating Axis Theorem (SAT)
Two convex polygons $A$ and $B$ are disjoint if and only if there exists a separating axis $\mathbf{n}$ upon which their 1D projections do not overlap:

$$\text{Overlap}(\mathbf{n}) = (r_A + r_B) - |\mathbf{n} \cdot (\mathbf{c}_B - \mathbf{c}_A)|$$

where $r_A, r_B$ are the projected radii along unit axis $\mathbf{n}$. If $\text{Overlap}(\mathbf{n}) \le 0$ for ANY of the 4 candidate normal axes (the face normals of $A$ and $B$), the objects do not collide.

---

## 2. Global Energy Objective Function

During interior furnishing layout synthesis, placement subagents solve a constrained energy minimization problem:

$$E(\mathbf{X}) = w_{\text{coll}} E_{\text{collision}} + w_{\text{wall}} E_{\text{wall\_snap}} + w_{\text{door}} E_{\text{door\_clear}} + w_{\text{walk}} E_{\text{nav\_corridor}}$$

### 2.1 Hard Constraints & Penalty Weights
- **$w_{\text{coll}} = 10^5$ (Collision Overlap):** Hard constraint. Zero overlap permitted between any two props ($δ_{ij} = 0.000\text{m}$).
- **$w_{\text{door}} = 5 \times 10^4$ (Door Swing Arc Clearance):** Disallows any prop geometry within $0.95\text{m}$ radius of room door hinges.
- **$w_{\text{walk}} = 2 \times 10^4$ ($A^*$ Navigable Walkway Guarantee):** Continuous corridor of width $\ge 0.85\text{m}$ (residential) or $\ge 1.50\text{m}$ (commercial) connecting all doors and functional zones.
- **$w_{\text{wall}} = 15.0$ (Wall Normal Snapping):** Encourages desks, sofas, and cabinets to align parallel/flush against room perimeter walls ($gap \approx 0.01\text{m}$).

---

## 3. Simulated Annealing Schedule

- Initial Temperature $T_0 = 100.0$
- Minimum Temperature $T_{\min} = 0.01$
- Cooling Factor $\alpha = 0.995$
- Max Iterations: $2,500$
- Acceptance Probability: $P(\Delta E) = \exp(-\Delta E / T)$ for uphill steps ($\Delta E > 0$).
