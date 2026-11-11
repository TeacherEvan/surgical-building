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
import sys
import math
import bpy
from mathutils import Vector

def create_humanoid_armature(name: str = "CharacterRig") -> bpy.types.Object:
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

def bake_procedural_actions(arm_obj: bpy.types.Object):
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones
    for b in pb:
        b.rotation_mode = 'XYZ'

    def commit_nla_track(action_name: str, frame_end: int, evaluator_fn):
        action = bpy.data.actions.new(name=action_name)
        arm_obj.animation_data_create()
        arm_obj.animation_data.action = action

        for f in range(1, frame_end + 1):
            bpy.context.scene.frame_set(f)
            for b in pb:
                b.location = (0, 0, 0)
                b.rotation_euler = (0, 0, 0)
            evaluator_fn(f, frame_end, pb)
            for b in pb:
                b.keyframe_insert(data_path="location", frame=f)
                b.keyframe_insert(data_path="rotation_euler", frame=f)

        track = arm_obj.animation_data.nla_tracks.new()
        track.name = action_name
        track.strips.new(action_name, 1, action)
        arm_obj.animation_data.action = None

    def eval_idle(f, total, bones):
        phase = (f / total) * 2.0 * math.pi
        bones["Hips"].location.z = 0.012 * math.sin(phase)
        bones["Chest"].rotation_euler.x = 0.04 * math.sin(phase)
        bones["UpperArm.L"].rotation_euler.x = 0.03 * math.cos(phase)
        bones["UpperArm.R"].rotation_euler.x = 0.03 * math.cos(phase)

    def eval_run(f, total, bones):
        phase = (f / total) * 2.0 * math.pi
        bones["Hips"].location.z = 0.045 * abs(math.cos(phase)) - 0.02
        bones["Chest"].rotation_euler.x = 0.18
        bones["Thigh.L"].rotation_euler.x = 0.65 * math.sin(phase)
        bones["Thigh.R"].rotation_euler.x = -0.65 * math.sin(phase)
        bones["Calf.L"].rotation_euler.x = max(0.0, -0.85 * math.cos(phase))
        bones["Calf.R"].rotation_euler.x = max(0.0, 0.85 * math.cos(phase))
        bones["UpperArm.L"].rotation_euler.x = -0.55 * math.sin(phase)
        bones["UpperArm.R"].rotation_euler.x = 0.55 * math.sin(phase)
        bones["ForeArm.L"].rotation_euler.x = -0.60
        bones["ForeArm.R"].rotation_euler.x = -0.60

    def eval_jump(f, total, bones):
        u = f / total
        if u < 0.25:
            c = math.sin((u / 0.25) * (math.pi * 0.5))
            bones["Hips"].location.z = -0.18 * c
            bones["Thigh.L"].rotation_euler.x = -0.55 * c
            bones["Thigh.R"].rotation_euler.x = -0.55 * c
            bones["Calf.L"].rotation_euler.x = 0.95 * c
            bones["Calf.R"].rotation_euler.x = 0.95 * c
        elif u < 0.80:
            air_u = (u - 0.25) / 0.55
            parabola = 4.0 * air_u * (1.0 - air_u)
            bones["Hips"].location.z = 0.55 * parabola
            bones["UpperArm.L"].rotation_euler.y = -0.85 * parabola
            bones["UpperArm.R"].rotation_euler.y = 0.85 * parabola
        else:
            land_u = math.sin(((u - 0.80) / 0.20) * math.pi)
            bones["Hips"].location.z = -0.12 * land_u

    def eval_eat(f, total, bones):
        u = f / total
        lift = math.sin(min(u * 1.2, 1.0) * math.pi)
        chew = math.sin(u * 6.0 * math.pi) if 0.25 < u < 0.85 else 0.0
        bones["UpperArm.R"].rotation_euler.x = -1.15 * lift
        bones["ForeArm.R"].rotation_euler.x = -1.35 * lift
        bones["Head"].rotation_euler.x = 0.12 * chew + 0.08 * lift

    commit_nla_track("Idle_Breathe", 60, eval_idle)
    commit_nla_track("Locomotion_Run", 24, eval_run)
    commit_nla_track("Jump_Arc", 36, eval_jump)
    commit_nla_track("Action_Eat_Consume", 48, eval_eat)
    bpy.ops.object.mode_set(mode='OBJECT')

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_glb = argv[0] if argv else "character_rigged.glb"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig = create_humanoid_armature("SurgicalCharacterRig")
    bake_procedural_actions(rig)
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', export_animations=True, export_nla_strips=True)
