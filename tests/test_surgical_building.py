#!/usr/bin/env python3
"""
Unit and integration test suite for surgical-building runtime, solvers, and schemas.
Runs via standard library unittest: `python3 -m unittest discover tests`
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from runtime.surgical_sandbox import SurgicalSandboxGuard
from scripts.sat_layout_solver import (
    OBB2D,
    sat_penetration_area,
    verify_a_star_corridor,
    solve_room_layout,
)
from scripts.zone_classifier import classify_and_generate_program
from scripts.svg_to_build123d_shell import (
    generate_svg_blueprint,
    build_parametric_shell_cad,
    build_parametric_shell_fallback_stl,
)
from scripts.threejs_scene_compiler import compile_threejs_module
from scripts.photogrammetry_investigator import (
    compute_spatial_manifest_analytical,
    compute_spatial_manifest,
)
from scripts.blender_qa_reviewer import run_full_qa, parse_stl_metrics
from scripts.conform import check as conform_check


class TestSchemas(unittest.TestCase):
    def test_all_schemas_valid_json(self):
        schema_dir = PROJECT_ROOT / "schemas"
        expected = [
            "spatial_manifest.schema.json",
            "interior_program.schema.json",
            "jobcard.schema.json",
            "debrief_payload.schema.json",
        ]
        for name in expected:
            path = schema_dir / name
            self.assertTrue(path.exists(), f"Schema file missing: {name}")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("type", data)
            self.assertEqual(data["type"], "object")
            self.assertIn("properties", data)


class TestSATLayoutSolver(unittest.TestCase):
    def test_obb_disjoint(self):
        b1 = OBB2D(id="b1", cx=1.0, cy=1.0, half_w=0.5, half_d=0.5, yaw=0.0)
        b2 = OBB2D(id="b2", cx=3.0, cy=1.0, half_w=0.5, half_d=0.5, yaw=0.0)
        overlap = sat_penetration_area(b1, b2)
        self.assertEqual(overlap, 0.0)

    def test_obb_overlapping(self):
        b1 = OBB2D(id="b1", cx=1.0, cy=1.0, half_w=0.5, half_d=0.5, yaw=0.0)
        b2 = OBB2D(id="b2", cx=1.4, cy=1.0, half_w=0.5, half_d=0.5, yaw=0.0)
        overlap = sat_penetration_area(b1, b2)
        self.assertGreater(overlap, 0.0)

    def test_obb_rotated_collision(self):
        b1 = OBB2D(id="b1", cx=2.0, cy=2.0, half_w=0.5, half_d=0.5, yaw=0.785398)
        b2 = OBB2D(id="b2", cx=2.5, cy=2.0, half_w=0.2, half_d=0.2, yaw=0.0)
        overlap = sat_penetration_area(b1, b2)
        self.assertGreater(overlap, 0.0)

    def test_solve_room_layout_executes(self):
        room_bounds = (0.0, 0.0, 6.0, 5.0)
        door_pos = (0.9, 0.2, 0.95)
        props = [
            {"id": "desk", "width": 1.4, "depth": 0.8, "wall_snap": True},
            {"id": "chair", "width": 0.6, "depth": 0.6, "wall_snap": False},
        ]
        res = solve_room_layout(room_bounds=room_bounds, door_pos=door_pos, props=props, iterations=500)
        self.assertIn("placements", res)
        self.assertEqual(len(res["placements"]), 2)
        self.assertTrue(res["collision_free"])
        for p in res["placements"]:
            self.assertIn("id", p)
            self.assertIn("position", p)
            self.assertIn("rotation_z_rad", p)


class TestSurgicalSandbox(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.guard = SurgicalSandboxGuard(workspace_root=self.temp_dir, max_revisions=3)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_allowed_write_path(self):
        allowed = ["job_123"]
        job_dir = Path(self.temp_dir) / "job_123"
        job_dir.mkdir(parents=True, exist_ok=True)
        target = str(job_dir / "output.json")
        verified = self.guard.verify_write_path(target, allowed)
        self.assertTrue(verified.is_relative_to(Path(self.temp_dir)))

    def test_directory_traversal_blocked(self):
        allowed = ["job_123"]
        malicious = os.path.join(self.temp_dir, "job_123", "..", "..", "escape.txt")
        with self.assertRaises(PermissionError):
            self.guard.verify_write_path(malicious, allowed)

    def test_circuit_breaker_revision_limit(self):
        role = "Placement-Solver"
        for i in range(3):
            payload = {"job_id": f"job_{i}", "status": "REJECTED", "cycle": i}
            self.guard.register_and_verify_debrief(role, payload)
        with self.assertRaises(RuntimeError) as ctx:
            self.guard.register_and_verify_debrief(role, {"job_id": "job_3", "status": "REJECTED", "cycle": 3})
        self.assertIn("Circuit Breaker Tripped", str(ctx.exception))

    def test_debrief_sha256_canonical_hashing_and_deduplication(self):
        payload1 = {"job_id": "job_01", "status": "APPROVED", "telemetry": {"val": 1.0}}
        payload2 = {"telemetry": {"val": 1.0}, "job_id": "job_01", "status": "APPROVED"}
        h1 = self.guard.register_and_verify_debrief("Worker1", payload1)
        self.assertTrue(h1)
        with self.assertRaises(RuntimeError) as ctx:
            self.guard.register_and_verify_debrief("Worker1", payload2)
        self.assertIn("Deduplication Halt", str(ctx.exception))


class TestZoneClassifier(unittest.TestCase):
    def test_commercial_classification(self):
        manifest = {
            "metric_dimensions_m": {
                "width_x": 18.0,
                "depth_y": 14.0,
                "height_z": 8.0,
                "estimated_stories": 2,
            }
        }
        res = classify_and_generate_program(manifest, fwr_ratio=0.55, has_signage_band=True)
        self.assertEqual(res["occupancy_classification"], "BUSINESS_COMMERCIAL")
        self.assertIn("lighting_spec", res)
        self.assertGreaterEqual(res["lighting_spec"]["kelvin"], 4000)

    def test_residential_classification(self):
        manifest = {
            "metric_dimensions_m": {
                "width_x": 8.0,
                "depth_y": 7.0,
                "height_z": 5.5,
                "estimated_stories": 2,
            }
        }
        res = classify_and_generate_program(manifest, fwr_ratio=0.25, has_signage_band=False)
        self.assertEqual(res["occupancy_classification"], "PRIVATE_RESIDENTIAL")
        self.assertIn("lighting_spec", res)
        self.assertLessEqual(res["lighting_spec"]["kelvin"], 3000)


class TestPhotogrammetry(unittest.TestCase):
    def test_analytical_fallback_manifest(self):
        res = compute_spatial_manifest_analytical(width_px=1920, height_px=1080)
        self.assertIn("metric_dimensions_m", res)
        self.assertIn("camera_telemetry", res)
        self.assertIn("vanishing_points", res["camera_telemetry"])
        dims = res["metric_dimensions_m"]
        self.assertGreater(dims["width_x"], 0)
        self.assertGreater(dims["height_z"], 0)


class TestWatertightCSGAndQA(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pure_python_stl_generation_and_qa_approval(self):
        manifest = {
            "metric_dimensions_m": {
                "width_x": 10.0,
                "depth_y": 8.0,
                "height_z": 3.8,
                "wall_thickness_ext": 0.24,
                "estimated_stories": 1,
            }
        }
        m_path = os.path.join(self.temp_dir, "manifest.json")
        stl_path = os.path.join(self.temp_dir, "shell.stl")
        report_path = os.path.join(self.temp_dir, "qa_debrief.json")
        Path(m_path).write_text(json.dumps(manifest), encoding="utf-8")

        build_parametric_shell_fallback_stl(manifest, stl_path)
        self.assertTrue(os.path.exists(stl_path))

        verts, tris, b_min, b_max = parse_stl_metrics(stl_path)
        self.assertGreater(tris, 0)
        self.assertAlmostEqual(b_max[0] - b_min[0], 10.0, places=1)
        self.assertAlmostEqual(b_max[1] - b_min[1], 8.0, places=1)
        self.assertAlmostEqual(b_max[2] - b_min[2], 3.8, places=1)

        rep = run_full_qa(stl_path, m_path, report_path)
        self.assertEqual(rep["status"], "APPROVED")
        self.assertEqual(rep["telemetry"]["non_manifold_edges"], 0)


class TestCompilers(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_svg_generation(self):
        manifest = {
            "metric_dimensions_m": {
                "width_x": 10.0,
                "depth_y": 8.0,
                "height_z": 3.8,
                "wall_thickness_ext": 0.22,
            }
        }
        out_svg = os.path.join(self.temp_dir, "blueprint.svg")
        generate_svg_blueprint(manifest, out_svg)
        self.assertTrue(os.path.exists(out_svg))
        content = Path(out_svg).read_text(encoding="utf-8")
        self.assertIn("<svg", content)
        self.assertIn("outer_footprint", content)

    def test_threejs_module_compilation(self):
        manifest = {
            "metric_dimensions_m": {
                "width_x": 10.0,
                "depth_y": 8.0,
                "height_z": 3.8,
            },
            "pbr_palette_srgb": ["#ffffff", "#333333"],
        }
        layout = {
            "placements": [
                {"id": "desk", "position": [2.0, 1.0, 0.0], "rotation_z_rad": 0.0}
            ]
        }
        out_ts = os.path.join(self.temp_dir, "scene.ts")
        compile_threejs_module(manifest, layout, out_ts)
        self.assertTrue(os.path.exists(out_ts))
        content = Path(out_ts).read_text(encoding="utf-8")
        self.assertIn("BUILDING_SPEC", content)
        self.assertIn("mountSurgicalScene", content)


class TestConformance(unittest.TestCase):
    def test_skill_passes_conformance(self):
        problems = conform_check(PROJECT_ROOT)
        self.assertEqual(problems, [], f"Conformance violations: {problems}")


if __name__ == "__main__":
    unittest.main()
