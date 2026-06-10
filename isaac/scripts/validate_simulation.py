# isaac/scripts/validate_simulation.py
"""CLI: validate a scenario USD.

Usage (Linux):
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.validate_simulation \
        --scenario isaac/scenarios/head_on_deadlock.usd

Usage (Windows):
    %ISAAC_SIM_ROOT%\\python.bat -m isaac.scripts.validate_simulation \
        --scenario isaac/scenarios/head_on_deadlock.usd
"""
import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate scenario USD")
    parser.add_argument("--scenario", required=True, type=Path)
    args = parser.parse_args()

    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "anti_aliasing": 0})

    try:
        import omni.kit.app
        omni.kit.app.get_app().update()

        from isaac.vgu_sim.validation import validate_scenario_stage, ValidationError

        try:
            validate_scenario_stage(args.scenario)
            print(f"PASS: {args.scenario}")
        except ValidationError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            sys.exit(1)
    finally:
        app.close()


if __name__ == "__main__":
    main()
