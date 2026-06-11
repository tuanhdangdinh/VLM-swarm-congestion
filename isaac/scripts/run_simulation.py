"""CLI: run a scenario (delegates to runner.run_simulation).

Usage (Linux):
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.run_simulation \
        --scenario head_on_deadlock --headless --seed 42 --repetitions 3

Usage (Windows):
    %ISAAC_SIM_ROOT%\\python.bat -m isaac.scripts.run_simulation \
        --scenario head_on_deadlock --headless --seed 42 --repetitions 3
"""
import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Isaac Sim scenario")
    parser.add_argument("--scenario", required=True,
                        help="Scenario name or path to YAML config")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--duration-sec", type=float, default=None)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--output-dir", type=Path,
                        default=Path("data/logs/simulation"))
    parser.add_argument("--ros-domain-id", type=int, default=None)
    parser.add_argument("--topic-timeout-sec", type=float, default=15.0)
    args = parser.parse_args()

    if args.repetitions < 1:
        sys.exit("--repetitions must be >= 1")
    if args.duration_sec is not None and args.duration_sec <= 0:
        sys.exit("--duration-sec must be > 0")
    if args.seed is not None and args.seed < 0:
        sys.exit("--seed must be >= 0")
    if args.ros_domain_id is not None:
        import os
        os.environ["ROS_DOMAIN_ID"] = str(args.ros_domain_id)

    import yaml

    from isaac.vgu_sim.config import ResolvedRunConfig, ScenarioConfig
    from isaac.vgu_sim.paths import scenario_config_path, scenario_output_path

    scenario_arg = args.scenario
    cfg_path = (Path(scenario_arg) if scenario_arg.endswith(".yaml")
                else scenario_config_path(scenario_arg))
    if not cfg_path.exists():
        sys.exit(f"Scenario config not found: {cfg_path}")

    with open(cfg_path) as f:
        raw = yaml.safe_load(f)

    if args.seed is not None:
        raw["seed"] = args.seed
    scenario = ScenarioConfig.model_validate(raw)

    run_config = ResolvedRunConfig(
        scenario_path=scenario_output_path(scenario.name),
        scenario=scenario,
        headless=args.headless,
        repetitions=args.repetitions,
        output_dir=args.output_dir,
        topic_timeout_sec=args.topic_timeout_sec,
        ros_domain_id=args.ros_domain_id,
    )

    from isaac.vgu_sim.runner import run_simulation
    results = run_simulation(run_config)

    failed = [r for r in results if not r.completed]
    if failed:
        for r in failed:
            print(f"FAIL rep={r.repetition}: {r.failure}", file=sys.stderr)
        sys.exit(1)

    print(f"All {len(results)} repetition(s) completed successfully.")


if __name__ == "__main__":
    main()
