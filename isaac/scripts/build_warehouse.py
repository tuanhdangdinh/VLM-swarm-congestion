# isaac/scripts/build_warehouse.py
"""CLI: build isaac/assets/warehouse/warehouse_base.usd.

Usage:
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.build_warehouse
"""
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build warehouse_base.usd")
    parser.add_argument("--output", default=None, type=Path)
    args = parser.parse_args()

    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "anti_aliasing": 0})

    try:
        import omni.kit.app
        omni.kit.app.get_app().update()

        from isaac.vgu_sim.config import CameraConfig, WarehouseConfig
        from isaac.vgu_sim.warehouse_builder import build_warehouse_asset
        from isaac.vgu_sim.paths import warehouse_asset_path

        output = args.output or warehouse_asset_path()
        output.parent.mkdir(parents=True, exist_ok=True)

        result = build_warehouse_asset(WarehouseConfig(), CameraConfig(), output)
        print(f"Warehouse written to: {result}")
    finally:
        app.close()


if __name__ == "__main__":
    main()
