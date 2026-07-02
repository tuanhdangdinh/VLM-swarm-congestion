"""Static USD physics inspection for the M4 Phase 1 no-traction diagnosis.

Opens the built scenario stage with pxr.Usd (NO SimulationApp — fast, no GPU)
and reports the wheel/floor contact physics that determine whether spinning
wheels can move the base:

  - articulation root + whether it has a fixed base
  - wheel link prims: CollisionAPI present? collision children?
  - floor: CollisionAPI + any bound physics material
  - any UsdPhysics material prims and their friction coefficients

Usage on the host (no app needed):
    $ISAAC_SIM_ROOT/python.sh isaac/scripts/inspect_robot_physics.py [robot_1]
"""
from __future__ import annotations

import sys

from pxr import Usd, UsdGeom, UsdPhysics, UsdShade


def _world_z(prim: Usd.Prim) -> float | None:
    """World-frame Z (metres) of a prim's origin, or None if not xformable."""
    xf = UsdGeom.Xformable(prim)
    if not xf:
        return None
    m = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    return float(m.ExtractTranslation()[2])


def _world_bbox_z(prim: Usd.Prim) -> tuple[float, float] | None:
    """World-frame (min_z, max_z) of a prim's geometry extent, or None."""
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
    )
    box = cache.ComputeWorldBound(prim)
    rng = box.ComputeAlignedRange()
    if rng.IsEmpty():
        return None
    return float(rng.GetMin()[2]), float(rng.GetMax()[2])

from isaac.vgu_sim.config import RobotAssetConfig
from isaac.vgu_sim.paths import scenario_output_path

robot_id = sys.argv[1] if len(sys.argv) > 1 else "robot_1"
cfg = RobotAssetConfig()
stage_path = scenario_output_path("head_on_deadlock")
print(f"stage: {stage_path}")
stage = Usd.Stage.Open(str(stage_path))

print("\n== ARTICULATION ROOTS ==")
for p in stage.Traverse():
    if p.HasAPI(UsdPhysics.ArticulationRootAPI):
        # PhysX fixed-base lives in the physxArticulation schema attr.
        fb = p.GetAttribute("physxArticulation:fixedBase")
        print(f"  {p.GetPath()}  fixedBase={fb.Get() if fb else '<unset>'}")

print(f"\n== WHEEL LINKS (joints: {cfg.left_wheel_joint}, {cfg.right_wheel_joint}) ==")
# Wheel *link* bodies are usually named wheel_left_link / wheel_right_link;
# print any prim whose name contains 'wheel'.
for p in stage.Traverse():
    name = p.GetName()
    if "wheel" in name.lower():
        has_col = p.HasAPI(UsdPhysics.CollisionAPI)
        has_rb = p.HasAPI(UsdPhysics.RigidBodyAPI)
        kids_col = [c.GetName() for c in p.GetChildren()
                    if c.HasAPI(UsdPhysics.CollisionAPI)]
        print(f"  {p.GetPath()} ({p.GetTypeName()}) "
              f"collisionAPI={has_col} rigidBodyAPI={has_rb} "
              f"collision_children={kids_col}")

print("\n== FLOOR ==")
for path in ("/World/Environment/Floor",):
    fp = stage.GetPrimAtPath(path)
    if fp and fp.IsValid():
        has_col = fp.HasAPI(UsdPhysics.CollisionAPI)
        binding = UsdShade.MaterialBindingAPI(fp).GetDirectBinding(
            materialPurpose="physics")
        print(f"  {path} collisionAPI={has_col} "
              f"phys_material={binding.GetMaterialPath() if binding else None}")
    else:
        print(f"  {path} NOT FOUND")

print("\n== PHYSICS MATERIALS (UsdPhysics.MaterialAPI) ==")
found_mat = False
for p in stage.Traverse():
    if p.HasAPI(UsdPhysics.MaterialAPI):
        found_mat = True
        m = UsdPhysics.MaterialAPI(p)
        sf = m.GetStaticFrictionAttr().Get()
        df = m.GetDynamicFrictionAttr().Get()
        print(f"  {p.GetPath()} staticFriction={sf} dynamicFriction={df}")
if not found_mat:
    print("  <none — no physics materials authored anywhere in the stage>")

print("\n== WHEEL / FLOOR CONTACT GEOMETRY (world Z, metres) ==")
floor_prim = stage.GetPrimAtPath("/World/Environment/Floor")
floor_bbox = _world_bbox_z(floor_prim) if floor_prim and floor_prim.IsValid() else None
floor_top = floor_bbox[1] if floor_bbox else None
print(f"  floor bbox_z={floor_bbox} top={floor_top}")
for p in stage.Traverse():
    name = p.GetName()
    if "wheel" not in name.lower():
        continue
    # Report the wheel *collider* extents: the lowest point of the wheel's
    # collision geometry vs the floor top tells us if the tyre touches ground.
    cols = [p] if p.HasAPI(UsdPhysics.CollisionAPI) else [
        c for c in p.GetChildren() if c.HasAPI(UsdPhysics.CollisionAPI)
    ]
    for col in cols:
        bbox = _world_bbox_z(col)
        gap = (bbox[0] - floor_top) if (bbox and floor_top is not None) else None
        print(f"  {col.GetPath()} origin_z={_world_z(col)} "
              f"bbox_z={bbox} bottom_minus_floor={gap}")

print("\nINSPECT DONE")
