#!/usr/bin/env python3
"""
Generate dynamic_obstacle.usd on Windows Isaac Sim machine.

Run this in Isaac Sim's embedded Python environment:
  isaac_sim> python.bat path/to/scripts/generate_obstacle_windows.py

This ensures the USD file is created with Isaac Sim's exact Python environment
and any platform-specific extensions.
"""

from pathlib import Path
import sys


def generate_obstacle():
    """Generate obstacle using Isaac Sim's Python environment."""
    try:
        from pxr import Gf, Kind, Usd, UsdGeom, UsdPhysics
    except ImportError as e:
        print(f"ERROR: USD libraries not available. Run in Isaac Sim Python environment.")
        print(f"  {e}")
        sys.exit(1)

    # Output path - relative to vgu-vlm-swarm root
    output_dir = Path(__file__).parent.parent / "isaac" / "assets" / "obstacles"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "dynamic_obstacle.usd"

    print(f"Generating obstacle asset...")
    print(f"  Output: {output_path.relative_to(Path.cwd())}")

    stage = Usd.Stage.CreateNew(str(output_path))

    # Metadata
    stage.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetTimeCodesPerSecond(60.0)

    # Root assembly
    root = UsdGeom.Xform.Define(stage, "/Root")
    stage.SetDefaultPrim(root.GetPrim())
    root.GetPrim().SetMetadata("kind", Kind.Tokens.assembly)

    # Obstacle box: 0.3m × 0.3m × 0.5m (W × D × H)
    box = UsdGeom.Cube.Define(stage, "/Root/Obstacle")
    box.CreateSizeAttr(2.0)

    xform = UsdGeom.Xformable(box.GetPrim())
    xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 0.25))  # Height/2
    xform.AddScaleOp().Set(Gf.Vec3f(0.15, 0.15, 0.25))    # W/2, D/2, H/2

    # Physics: static collision
    UsdPhysics.CollisionAPI.Apply(box.GetPrim())

    box.GetPrim().SetMetadata("customData", {
        "obstacle_type": "box",
        "width_m": 0.3,
        "depth_m": 0.3,
        "height_m": 0.5,
        "generated_by": "generate_obstacle_windows.py",
    })

    stage.Save()

    print(f"✓ Generated: {output_path}")
    print(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"  Dimensions: 0.3m (W) × 0.3m (D) × 0.5m (H)")
    print(f"  Physics: Static collision enabled")


if __name__ == "__main__":
    generate_obstacle()
