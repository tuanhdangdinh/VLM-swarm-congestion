# isaac/scripts/import_turtlebot3.py
"""CLI: import TurtleBot3 Burger URDF into isaac/assets/robots/.

Usage (Linux):
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.import_turtlebot3 \
        --urdf /path/to/turtlebot3_burger.urdf \
        --output-dir isaac/assets/robots \
        [--force]

Usage (Windows):
    %ISAAC_SIM_ROOT%\\python.bat -m isaac.scripts.import_turtlebot3 \
        --urdf C:\\path\\to\\turtlebot3_burger.urdf \
        --output-dir isaac\\assets\\robots \
        [--force]
"""
import argparse
import subprocess
import tempfile
from pathlib import Path


def _expand_xacro(xacro_path: Path) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".urdf", delete=False)
    subprocess.run(
        ["xacro", str(xacro_path), "-o", tmp.name],
        check=True,
    )
    return Path(tmp.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import TurtleBot3 Burger URDF")
    parser.add_argument("--urdf", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("isaac/assets/robots"), type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    urdf_path = args.urdf
    if urdf_path.suffix == ".xacro":
        urdf_path = _expand_xacro(urdf_path)

    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "anti_aliasing": 0})

    try:
        import omni.kit.app
        omni.kit.app.get_app().update()

        from isaac.vgu_sim.config import RobotAssetConfig
        from isaac.vgu_sim.robot_asset import import_turtlebot3

        config = RobotAssetConfig()
        result = import_turtlebot3(urdf_path, args.output_dir, config, force=args.force)
        print(f"Robot asset written to: {result}")
    finally:
        app.close()


if __name__ == "__main__":
    main()
