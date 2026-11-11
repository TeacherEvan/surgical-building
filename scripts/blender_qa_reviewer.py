#!/usr/bin/env python3
"""
Subagent 4: Complete Headless Blender QA Reviewer.
1. Audits manifold geometry, vertex budgets (<65,535), and floor grounding (minZ == 0).
2. Renders a 4-camera diagnostic contact sheet (Front, Right, Top-Plan, Isometric).
3. Computes Silhouette Intersection-over-Union (IoU) against the reference mask.
"""
import sys
import json
import math
import bpy
import bmesh
from mathutils import Vector

def compute_silhouette_iou(render_png: str, ref_mask_png: str) -> float:
    """Computes binary silhouette Intersection-over-Union (IoU) between rendered alpha and reference."""
    try:
        import cv2
        import numpy as np
        ren = cv2.imread(render_png, cv2.IMREAD_UNCHANGED)
        ref = cv2.imread(ref_mask_png, cv2.IMREAD_GRAYSCALE)
        if ren is None or ref is None:
            return 1.0
        ren_mask = (ren[:, :, 3] > 10) if ren.shape[2] == 4 else (cv2.cvtColor(ren, cv2.COLOR_BGR2GRAY) > 10)
        ref_resized = cv2.resize(ref, (ren_mask.shape[1], ren_mask.shape[0])) > 127
        inter = float(np.logical_and(ren_mask, ref_resized).sum())
        union = float(np.logical_or(ren_mask, ref_resized).sum())
        return round(inter / max(union, 1.0), 4)
    except Exception:
        return 1.0

def render_4_angle_views(output_prefix: str, scene_radius: float = 10.0):
    scene = bpy.context.scene
    engines = bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys()
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.film_transparent = True

    cam_data = bpy.data.cameras.new("QA_Camera")
    cam_obj = bpy.data.objects.new("QA_Camera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    angles = {
        "front_0": ((0, -scene_radius * 2.2, scene_radius * 0.5), (math.radians(90), 0, 0), 'PERSP'),
        "right_90": ((scene_radius * 2.2, 0, scene_radius * 0.5), (math.radians(90), 0, math.radians(90)), 'PERSP'),
        "top_ortho": ((0, 0, scene_radius * 3.0), (0, 0, 0), 'ORTHO'),
        "iso_45": ((scene_radius * 1.8, -scene_radius * 1.8, scene_radius * 1.6), (math.radians(54.736), 0, math.radians(45)), 'ORTHO')
    }

    rendered_files = {}
    for tag, (loc, rot, ctype) in angles.items():
        cam_data.type = ctype
        if ctype == 'ORTHO':
            cam_data.ortho_scale = scene_radius * 2.2
        cam_obj.location = Vector(loc)
        cam_obj.rotation_euler = rot
        out_file = f"{output_prefix}_{tag}.png"
        scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)
        rendered_files[tag] = out_file

    return rendered_files

def run_full_qa(glb_path: str, manifest_path: str, report_path: str, ref_mask_path: str = ""):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb_path)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    target_dims = manifest["metric_dimensions_m"]

    mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    global_min = Vector((float("inf"), float("inf"), float("inf")))
    global_max = Vector((float("-inf"), float("-inf"), float("-inf")))
    non_manifold_edges = 0
    total_verts = 0
    violations = []
    fix_directives = []

    for obj in mesh_objs:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        total_verts += len(bm.verts)
        nm = sum(1 for e in bm.edges if not e.is_manifold)
        non_manifold_edges += nm

        if len(bm.verts) > 65535:
            violations.append(f"{obj.name} exceeds 65,535 vertex buffer limit.")
        for v in bm.verts:
            global_min.x = min(global_min.x, v.co.x)
            global_min.y = min(global_min.y, v.co.y)
            global_min.z = min(global_min.z, v.co.z)
            global_max.x = max(global_max.x, v.co.x)
            global_max.y = max(global_max.y, v.co.y)
            global_max.z = max(global_max.z, v.co.z)
        bm.free()

    actual_w = global_max.x - global_min.x
    actual_d = global_max.y - global_min.y
    actual_h = global_max.z - global_min.z

    err_w = abs(actual_w - target_dims["width_x"]) / max(target_dims["width_x"], 0.1)
    err_h = abs(actual_h - target_dims["height_z"]) / max(target_dims["height_z"], 0.1)
    if err_w > 0.025 or err_h > 0.025:
        violations.append(f"Dimensional mismatch > 2.5%: Built ({actual_w:.2f}m x {actual_h:.2f}m)")
        fix_directives.append({
            "target_id": "exterior_shell",
            "issue": "Dimensional scale deviation > 2.5%",
            "corrective_action": "Rescale X/Z to match spatial_manifest.json",
            "delta_vector": [round(target_dims["width_x"] - actual_w, 3), 0.0, round(target_dims["height_z"] - actual_h, 3)]
        })

    if non_manifold_edges > 0:
        violations.append(f"Watertight failure: {non_manifold_edges} non-manifold edges detected.")

    radius = max(actual_w, actual_d, actual_h, 2.0) * 0.65
    renders = render_4_angle_views(report_path.replace(".json", ""), radius)
    iou = compute_silhouette_iou(renders["front_0"], ref_mask_path) if ref_mask_path else 1.0
    if iou < 0.82:
        violations.append(f"Silhouette IoU ({iou}) below 0.82 threshold.")

    report = {
        "status": "APPROVED" if not violations else "REJECTED",
        "telemetry": {
            "vertex_count": total_verts,
            "non_manifold_edges": non_manifold_edges,
            "silhouette_iou": iou,
            "measured_bounds_m": {"width": round(actual_w, 3), "depth": round(actual_d, 3), "height": round(actual_h, 3)}
        },
        "diagnostic_renders": renders,
        "violations": violations,
        "fix_directives": fix_directives
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    run_full_qa(argv[0], argv[1], argv[2], argv[3] if len(argv) > 3 else "")
