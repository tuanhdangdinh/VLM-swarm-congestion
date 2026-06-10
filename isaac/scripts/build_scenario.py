# isaac/scripts/build_scenario.py
"""CLI: build one scenario USD from its YAML config.

Usage (Linux):
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.build_scenario \
        --config isaac/config/scenarios/head_on_deadlock.yaml

Usage (Windows):
    %ISAAC_SIM_ROOT%\\python.bat -m isaac.scripts.build_scenario \
        --config isaac/config/scenarios/head_on_deadlock.yaml
"""
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build scenario USD")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()

    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "anti_aliasing": 0})

    try:
        import omni.kit.app
        omni.kit.app.get_app().update()

        import yaml
        from isaac.vgu_sim.config import ScenarioConfig
        from isaac.vgu_sim.paths import robot_asset_path, warehouse_asset_path, scenario_output_path
        from isaac.vgu_sim.scenario_builder import build_scenario_stage

        with open(args.config) as f:
            data = yaml.safe_load(f)
        config = ScenarioConfig.model_validate(data)

        output = scenario_output_path(config.name)
        output.parent.mkdir(parents=True, exist_ok=True)

        result = build_scenario_stage(
            config,
            warehouse_path=warehouse_asset_path(),
            robot_asset_path=robot_asset_path(),
            output_path=output,
        )
        print(f"Scenario written to: {result}")
    finally:
        app.close()


if __name__ == "__main__":
    main()
