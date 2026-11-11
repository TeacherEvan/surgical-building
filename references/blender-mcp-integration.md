# Blender MCP Integration Guide

This reference explains how AI agents (Hermes Agent, Gemini Antigravity, Cursor, and OpenCode) interface with Blender using the `blender` Model Context Protocol (MCP) server.

---

## 1. Dual-Mode Architecture: Headless vs. Live MCP

`surgical-building` supports two execution modalities for Blender:

```
                      ┌──────────────────────────────────────────────┐
                      │            Master Orchestrator               │
                      └──────────────────────┬───────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
          [Mode 1: Headless CLI]                      [Mode 2: Live MCP Session]
       `blender -b -noaudio -P script.py`            `mcp_blender_execute_blender_code`
                       │                                           │
          • Isolated batch execution                  • Real-time interactive feedback
          • Automated CI / sandbox                    • Visual validation via `look`
          • Draco `.glb` file export                  • Direct scene graph manipulation
```

---

## 2. Available Blender MCP Tools

| MCP Tool Name | Function | Use in `surgical-building` |
| :--- | :--- | :--- |
| `get_addon_status` | Returns connection status of the Blender addon | Preflight check before dispatching Blender subagents |
| `get_scene_info` | Inspects active objects, meshes, materials, and hierarchy | Validating object names, AABB bounds, and vertex counts |
| `execute_blender_code` | Executes arbitrary Python (`bpy`) in the live Blender process | Rigging 52-bone armature, baking procedural NLA clips, boolean cuts |
| `look` | Captures camera viewport render | Headless visual audit and silhouette IoU verification |
| `generate_3d` | Generates 3D meshes from text/image briefs | Quick generation of specialized decorative props |
| `search_assets` / `import_asset` | Queries and loads modular asset kits | Ingesting standardized commercial/residential furniture kits |

---

## 3. Standard MCP Execution Patterns

### 3.1 Preflight Handshake
Before running Blender operations, verify the addon connection:
```json
{
  "ServerName": "blender",
  "ToolName": "get_addon_status",
  "Arguments": {}
}
```

### 3.2 Executing Procedural Armature & Action Synthesis
Send the rigger script directly to the live session:
```python
code = """
import bpy
from mathutils import Vector

# Run character armature construction
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
arm = bpy.context.active_object
arm.name = "Surgical_Humanoid"
"""
# Dispatch via call_mcp_tool(ServerName="blender", ToolName="execute_blender_code", Arguments={"code": code})
```

### 3.3 Visual Verification with `look`
Capture diagnostic angles without writing to disk manually:
```json
{
  "ServerName": "blender",
  "ToolName": "look",
  "Arguments": {
    "camera_name": "QA_Camera",
    "resolution": [1024, 1024]
  }
}
```

---

## 4. Fallback Matrix

If the `blender` MCP server is not active or fails the handshake:
1. Fall back automatically to headless execution via `scripts/blender_qa_reviewer.py` (`blender -b -noaudio -P ...`).
2. If Blender is not installed on the host system, the runtime executes the pure-Python STL/OBJ geometric analyzer and emits the canonical `debrief_payload.schema.json` without failing.
