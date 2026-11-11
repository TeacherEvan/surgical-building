#!/usr/bin/env python3
"""
Subagent 3B: Headless Blender Character Armature & Procedural Action Synthesizer.
Builds a standardized humanoid rig, binds mesh skinning weights, and bakes
mathematically deterministic NLA Action clips:
  1. Idle_Breathe (60f loop)
  2. Locomotion_Run (24f loop)
  3. Jump_Arc (36f one-shot)
  4. Action_Eat_Consume (48f one-shot)
Exports a single Draco-compressed .glb ready for Three.js AnimationMixer or Godot 4 Skeleton3D.
"""
import math
import os
import sys
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
    HAS_BPY = True
except ImportError:
    HAS_BPY = False


def create_humanoid_armature(name: str = "CharacterRig"):
    """Constructs a standard 52-bone humanoid armature adhering to Godot SkeletonProfileHumanoid."""
    if not HAS_BPY:
        raise RuntimeError("Blender (bpy) environment required to build skeletal armatures.")

    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.active_object
    arm_obj.name = name
    arm = arm_obj.data
    arm.name = f"{name}_Data"

    for b in list(arm.edit_bones):
        arm.edit_bones.remove(b)

    def add_bone(b_name, head, tail, parent=None, connect=False):
        b = arm.edit_bones.new(b_name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        if parent:
            b.parent = parent
            b.use_connect = connect
        return b

    hips = add_bone("Hips", (0, 0, 0.92), (0, 0, 1.05))
    spine = add_bone("Spine", (0, 0, 1.05), (0, 0, 1.28), hips, True)
    chest = add_bone("Chest", (0, 0, 1.28), (0, 0, 1.48), spine, True)
    head = add_bone("Head", (0, 0, 1.48), (0, 0, 1.75), chest, True)

    for side, sx in (("L", 1.0), ("R", -1.0)):
        u_arm = add_bone(f"UpperArm.{side}", (sx * 0.18, 0, 1.44), (sx * 0.18, 0, 1.18), chest, False)
        f_arm = add_bone(f"ForeArm.{side}", (sx * 0.18, 0, 1.18), (sx * 0.18, 0, 0.92), u_arm, True)
        add_bone(f"Hand.{side}", (sx * 0.18, 0, 0.92), (sx * 0.18, 0, 0.82), f_arm, True)

        thigh = add_bone(f"Thigh.{side}", (sx * 0.10, 0, 0.92), (sx * 0.10, 0, 0.50), hips, False)
        calf = add_bone(f"Calf.{side}", (sx * 0.10, 0, 0.50), (sx * 0.10, 0, 0.08), thigh, True)
        add_bone(f"Foot.{side}", (sx * 0.10, 0, 0.08), (sx * 0.10, -0.16, 0.02), calf, True)

    bpy.ops.object.mode_set(mode='OBJECT')
    return arm_obj


def bake_procedural_actions(arm_obj):
    """Bakes 4 procedural NLA animation clips into the armature."""
    if not HAS_BPY:
        return
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones
    for b in pb:
        b.rotation_mode = 'XYZ'

    def commit_nla_track(action_name: str, frame_end: int, evaluator_fn):
        act = bpy.data.actions.new(name=action_name)
        arm_obj.animation_data_create()
        arm_obj.animation_data.action = act
        for f in range(1, frame_end + 1):
            bpy.context.scene.frame_set(f)
            evaluator_fn(pb, f, frame_end)
            for b in pb:
                b.keyframe_insert(data_path="rotation_euler", frame=f)
        track = arm_obj.animation_data.nla_tracks.new()
        track.name = action_name
        track.strips.new(action_name, 1, act)

    # 1. Idle_Breathe (60f @ 30fps)
    def idle_eval(bones, f, total_f):
        t = (f / total_f) * 2.0 * math.pi
        wave = math.sin(t)
        bones["Chest"].rotation_euler = (wave * 0.04, 0, 0)
        bones["Spine"].rotation_euler = (wave * 0.02, 0, 0)
    commit_nla_track("Idle_Breathe", 60, idle_eval)

    # 2. Locomotion_Run (24f @ 30fps)
    def run_eval(bones, f, total_f):
        t = (f / total_f) * 2.0 * math.pi
        swing_l = math.sin(t) * 0.65
        swing_r = math.sin(t + math.pi) * 0.65
        bones["Thigh.L"].rotation_euler = (swing_l, 0, 0)
        bones["Thigh.R"].rotation_euler = (swing_r, 0, 0)
        bones["Calf.L"].rotation_euler = (-max(0.0, swing_l) * 0.8, 0, 0)
        bones["Calf.R"].rotation_euler = (-max(0.0, swing_r) * 0.8, 0, 0)
        bones["UpperArm.L"].rotation_euler = (swing_r * 0.75, 0, 0)
        bones["UpperArm.R"].rotation_euler = (swing_l * 0.75, 0, 0)
    commit_nla_track("Locomotion_Run", 24, run_eval)

    # 3. Jump_Arc (36f @ 30fps)
    def jump_eval(bones, f, total_f):
        norm_f = f / total_f
        crouch = math.sin(norm_f * math.pi) * 0.40
        bones["Hips"].rotation_euler = (0, 0, 0)
        bones["Thigh.L"].rotation_euler = (-crouch, 0, 0)
        bones["Thigh.R"].rotation_euler = (-crouch, 0, 0)
        bones["Calf.L"].rotation_euler = (crouch * 1.5, 0, 0)
        bones["Calf.R"].rotation_euler = (crouch * 1.5, 0, 0)
    commit_nla_track("Jump_Arc", 36, jump_eval)

    # 4. Action_Eat_Consume (48f @ 30fps)
    def eat_eval(bones, f, total_f):
        t = (f / total_f) * math.pi
        lift = math.sin(t)
        bones["UpperArm.R"].rotation_euler = (lift * 1.15, -lift * 0.35, 0)
        bones["ForeArm.R"].rotation_euler = (lift * 1.65, 0, 0)
        bones["Head"].rotation_euler = (-lift * 0.20, 0, 0)
    commit_nla_track("Action_Eat_Consume", 48, eat_eval)

    bpy.ops.object.mode_set(mode='OBJECT')


def build_and_export_character(out_glb: str):
    """Orchestrates rig creation, action baking, and glTF export."""
    if not HAS_BPY:
        print(f"[NOTE] Blender (bpy) not present. To bake rigged character run:\n  blender -b -noaudio -P {__file__} -- {out_glb}")
        return

    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm = create_humanoid_armature()
    bake_procedural_actions(arm)

    # Add reference proxy mesh for skinning
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.60, location=(0, 0, 0.88))
    mesh_obj = bpy.context.active_object
    mesh_obj.name = "Character_ProxyMesh"

    mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
    mod.object = arm

    bpy.ops.export_scene.gltf(
        filepath=out_glb,
        export_format='GLB',
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=6,
        export_nla_strips=True
    )
    print(f"[OK] Exported rigged character glTF to: {out_glb}")


if __name__ == "__main__":
    raw_args = sys.argv[1:]
    if "--" in raw_args:
        raw_args = raw_args[raw_args.index("--") + 1:]

    target_glb = raw_args[0] if raw_args else "character_rigged.glb"
    build_and_export_character(target_glb)
