#!/usr/bin/env python3
"""
Subagent 2C: Deterministic Interior Furniture Placement Solver.
Uses Separating Axis Theorem (SAT) on 2D Oriented Bounding Boxes (OBB),
wall-normal snapping, door-arc exclusion, A* navigable corridor verification,
and Simulated Annealing energy minimization.
"""
import heapq
import json
import math
import random
import sys
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class OBB2D:
    id: str
    cx: float
    cy: float
    half_w: float
    half_d: float
    yaw: float
    wall_snap: bool = True

    def get_corners(self) -> List[Tuple[float, float]]:
        cos_a, sin_a = math.cos(self.yaw), math.sin(self.yaw)
        axes = [(cos_a, sin_a), (-sin_a, cos_a)]
        corners = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                px = self.cx + sx * self.half_w * axes[0][0] + sy * self.half_d * axes[1][0]
                py = self.cy + sx * self.half_w * axes[0][1] + sy * self.half_d * axes[1][1]
                corners.append((px, py))
        return corners


def sat_penetration_area(a: OBB2D, b: OBB2D) -> float:
    """Computes minimum penetration overlap between two 2D OBBs along 4 separating axes."""
    corners_a = a.get_corners()
    corners_b = b.get_corners()
    axes = [
        (math.cos(a.yaw), math.sin(a.yaw)),
        (-math.sin(a.yaw), math.cos(a.yaw)),
        (math.cos(b.yaw), math.sin(b.yaw)),
        (-math.sin(b.yaw), math.cos(b.yaw)),
    ]
    min_overlap = float("inf")
    for ax, ay in axes:
        proj_a = [x * ax + y * ay for x, y in corners_a]
        proj_b = [x * ax + y * ay for x, y in corners_b]
        overlap = min(max(proj_a), max(proj_b)) - max(min(proj_a), min(proj_b))
        if overlap <= 0.0:
            return 0.0
        min_overlap = min(min_overlap, overlap)
    return min_overlap


def verify_a_star_corridor(
    room_bounds: Tuple[float, float, float, float],
    items: List[OBB2D],
    start_xy: Tuple[float, float],
    goal_xy: Tuple[float, float],
    grid_res: float = 0.25
) -> bool:
    """Verifies a continuous navigable human walkway from doorway to room center using A*."""
    min_x, min_y, max_x, max_y = room_bounds
    nx = max(2, int((max_x - min_x) / grid_res))
    ny = max(2, int((max_y - min_y) / grid_res))

    def to_cell(x: float, y: float) -> Tuple[int, int]:
        ix = min(nx - 1, max(0, int((x - min_x) / grid_res)))
        iy = min(ny - 1, max(0, int((y - min_y) / grid_res)))
        return ix, iy

    start = to_cell(*start_xy)
    goal = to_cell(*goal_xy)
    open_heap = [(0.0, start)]
    visited = set()

    while open_heap:
        _, curr = heapq.heappop(open_heap)
        if curr == goal:
            return True
        if curr in visited:
            continue
        visited.add(curr)
        cx_m = min_x + (curr[0] + 0.5) * grid_res
        cy_m = min_y + (curr[1] + 0.5) * grid_res
        probe = OBB2D("walker", cx_m, cy_m, 0.35, 0.35, 0.0, False)
        if curr != start and any(sat_penetration_area(probe, it) > 0.0 for it in items):
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (curr[0] + dx, curr[1] + dy)
            if 0 <= nb[0] < nx and 0 <= nb[1] < ny and nb not in visited:
                h = math.hypot(nb[0] - goal[0], nb[1] - goal[1])
                heapq.heappush(open_heap, (h, nb))
    return False


def solve_room_layout(
    room_bounds: Tuple[float, float, float, float],
    door_pos: Tuple[float, float, float],
    props: List[Dict],
    iterations: int = 3000,
    seed: int = 42
) -> Dict:
    """Solves collision-free interior placement via Simulated Annealing + SAT + A* validation."""
    random.seed(seed)
    min_x, min_y, max_x, max_y = room_bounds
    door_obbs = [OBB2D("door_arc", door_pos[0], door_pos[1], door_pos[2], door_pos[2], 0.0, False)]
    room_center = ((min_x + max_x) * 0.5, (min_y + max_y) * 0.5)

    state: List[OBB2D] = []
    for p in props:
        hw = p["width"] * 0.5
        hd = p["depth"] * 0.5
        cx = random.uniform(min_x + hw + 0.2, max_x - hw - 0.2)
        cy = random.uniform(min_y + hd + 0.2, max_y - hd - 0.2)
        yaw = random.choice([0.0, math.pi * 0.5, math.pi, math.pi * 1.5])
        state.append(OBB2D(p["id"], cx, cy, hw, hd, yaw, p.get("wall_snap", True)))

    def compute_energy(items: List[OBB2D]) -> float:
        energy = 0.0
        for i, item in enumerate(items):
            for x, y in item.get_corners():
                if x < min_x: energy += (min_x - x) * 1e5
                if x > max_x: energy += (x - max_x) * 1e5
                if y < min_y: energy += (min_y - y) * 1e5
                if y > max_y: energy += (y - max_y) * 1e5
            for d_obb in door_obbs:
                energy += sat_penetration_area(item, d_obb) * 1e5
            for j in range(i + 1, len(items)):
                energy += sat_penetration_area(item, items[j]) * 1e5
            if item.wall_snap:
                dists = [
                    (abs((item.cx - item.half_d) - min_x), 0.0),
                    (abs((max_x - (item.cx + item.half_d))), math.pi),
                    (abs((item.cy - item.half_d) - min_y), math.pi * 0.5),
                    (abs((max_y - (item.cy + item.half_d))), math.pi * 1.5),
                ]
                nearest_dist, target_yaw = min(dists, key=lambda t: t[0])
                energy += nearest_dist * 25.0
                energy += abs(math.atan2(math.sin(item.yaw - target_yaw), math.cos(item.yaw - target_yaw))) * 40.0
        return energy

    current_e = compute_energy(state)
    temp = 100.0
    for _ in range(iterations):
        idx = random.randrange(len(state))
        old_item = state[idx]
        step = max(0.02, temp * 0.01)
        new_cx = max(min_x + old_item.half_w, min(max_x - old_item.half_w, old_item.cx + random.uniform(-step, step)))
        new_cy = max(min_y + old_item.half_d, min(max_y - old_item.half_d, old_item.cy + random.uniform(-step, step)))
        new_yaw = old_item.yaw if random.random() > 0.2 else random.choice([0.0, math.pi * 0.5, math.pi, math.pi * 1.5])
        state[idx] = OBB2D(old_item.id, new_cx, new_cy, old_item.half_w, old_item.half_d, new_yaw, old_item.wall_snap)

        cand_e = compute_energy(state)
        if cand_e < current_e or random.random() < math.exp((current_e - cand_e) / max(temp, 1e-4)):
            current_e = cand_e
        else:
            state[idx] = old_item
        temp *= 0.995

    walkway_ok = verify_a_star_corridor(room_bounds, state, (door_pos[0], door_pos[1]), room_center)
    return {
        "final_energy": round(current_e, 4),
        "collision_free": current_e < 1000.0,
        "a_star_walkway_valid": walkway_ok,
        "placements": [
            {"id": s.id, "position": [round(s.cx, 3), round(s.cy, 3), 0.0], "rotation_z_rad": round(s.yaw, 4)}
            for s in state
        ]
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] not in ("-h", "--help"):
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bounds = tuple(cfg.get("room_bounds", [0.0, 0.0, 6.0, 5.0]))
        door = tuple(cfg.get("door_pos", [0.9, 0.2, 0.95]))
        props_list = cfg.get("props", [])
        result = solve_room_layout(bounds, door, props_list)
        print(json.dumps(result, indent=2))
    else:
        sample_props = [
            {"id": "reception_desk", "width": 1.8, "depth": 0.8, "wall_snap": False},
            {"id": "sofa_wait_01", "width": 2.1, "depth": 0.9, "wall_snap": True},
            {"id": "cabinet_file_01", "width": 1.0, "depth": 0.5, "wall_snap": True},
        ]
        print(json.dumps(solve_room_layout((0.0, 0.0, 5.5, 4.2), (0.9, 0.2, 0.95), sample_props), indent=2))
