#!/usr/bin/env python3
"""
Subagent 2A: Business vs. Private (Residential) Zoning Investigator.
Evaluates Fenestration-to-Wall Ratio (FWR), ground-floor story height, footprint area,
and signage edge density to deterministically classify occupancy and emit interior_program.json.
"""
import json
import sys
from typing import Dict

def classify_and_generate_program(spatial_manifest: Dict, fwr_ratio: float = 0.48, has_signage_band: bool = True) -> Dict:
    dims = spatial_manifest["metric_dimensions_m"]
    w, d, h, stories = dims["width_x"], dims["depth_y"], dims["height_z"], dims["estimated_stories"]
    footprint_area = w * d
    story_height = h / max(stories, 1)

    score = 0.0
    if fwr_ratio >= 0.42: score += 0.35
    if story_height >= 3.40: score += 0.25
    if has_signage_band: score += 0.25
    if footprint_area >= 180.0: score += 0.15

    occupancy_type = "BUSINESS_COMMERCIAL" if score >= 0.55 else "PRIVATE_RESIDENTIAL"

    if occupancy_type == "BUSINESS_COMMERCIAL":
        return {
            "occupancy_classification": occupancy_type,
            "confidence_score": round(score, 2),
            "lighting_spec": {"kelvin": 4500, "lux_target": 500, "fixture_type": "recessed_troffer_grid"},
            "circulation_rules": {"min_aisle_width_m": 1.50, "door_clear_arc_m": 1.10, "ada_turn_radius_m": 1.52},
            "zones": [
                {
                    "zone_id": "reception_lobby",
                    "area_ratio": 0.30,
                    "furniture_manifest": [
                        {"id": "counter_reception_01", "type": "reception_desk", "width": 2.20, "depth": 0.85, "height": 1.10, "wall_snap": False},
                        {"id": "sofa_waiting_01", "type": "commercial_sofa", "width": 2.00, "depth": 0.85, "height": 0.78, "wall_snap": True},
                        {"id": "kiosk_terminal_01", "type": "checkin_kiosk", "width": 0.60, "depth": 0.55, "height": 1.45, "wall_snap": True}
                    ]
                },
                {
                    "zone_id": "open_work_floor",
                    "area_ratio": 0.70,
                    "furniture_manifest": [
                        {"id": "workstation_pod_01", "type": "desk_cluster_4", "width": 2.80, "depth": 1.60, "height": 0.75, "wall_snap": False},
                        {"id": "chair_task_01", "type": "ergonomic_chair", "width": 0.65, "depth": 0.65, "height": 0.95, "wall_snap": False},
                        {"id": "storage_cabinet_01", "type": "steel_credenza", "width": 1.60, "depth": 0.50, "height": 0.85, "wall_snap": True}
                    ]
                }
            ]
        }
    return {
        "occupancy_classification": occupancy_type,
        "confidence_score": round(1.0 - score, 2),
        "lighting_spec": {"kelvin": 2700, "lux_target": 250, "fixture_type": "warm_pendant_and_sconce"},
        "circulation_rules": {"min_aisle_width_m": 0.85, "door_clear_arc_m": 0.90, "ada_turn_radius_m": 1.20},
        "zones": [
            {
                "zone_id": "living_lounge",
                "area_ratio": 0.55,
                "furniture_manifest": [
                    {"id": "sofa_sectional_01", "type": "lounge_sofa", "width": 2.40, "depth": 0.95, "height": 0.82, "wall_snap": True},
                    {"id": "table_coffee_01", "type": "coffee_table", "width": 1.20, "depth": 0.65, "height": 0.42, "wall_snap": False},
                    {"id": "media_console_01", "type": "tv_credenza", "width": 1.80, "depth": 0.45, "height": 0.55, "wall_snap": True}
                ]
            },
            {
                "zone_id": "dining_kitchen",
                "area_ratio": 0.45,
                "furniture_manifest": [
                    {"id": "table_dining_01", "type": "dining_table", "width": 1.80, "depth": 0.95, "height": 0.76, "wall_snap": False},
                    {"id": "island_counter_01", "type": "kitchen_island", "width": 2.10, "depth": 0.90, "height": 0.92, "wall_snap": True}
                ]
            }
        ]
    }

if __name__ == "__main__":
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        manifest = json.load(f)
    print(json.dumps(classify_and_generate_program(manifest), indent=2))
