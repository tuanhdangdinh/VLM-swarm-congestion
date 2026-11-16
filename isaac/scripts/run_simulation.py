"""CLI: run a scenario (delegates to runner.run_simulation).

Usage (Linux):
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.run_simulation \
        --scenario head_on_deadlock --headless --seed 42 --repetitions 3

Usage (Windows):
    %ISAAC_SIM_ROOT%\\python.bat -m isaac.scripts.run_simulation \
        --scenario head_on_deadlock --headless --seed 42 --repetitions 3
"""
import argparse
import os
import sys
from pathlib import Path

# fc_launch.sh passes the stop-flag path through `sudo ... env`, which keeps
# its DRY_RUN command line (and the goldens pinning it) unchanged.
STOP_FLAG_ENV = "VGU_ISAAC_STOP_FLAG"
# Opt-in GT config (e.g. config/gt/contact_logging_on.fragment.yaml); absent
# means gt_contact_logging.enabled is false, the pin's row schema.
GT_CONFIG_ENV = "VGU_ISAAC_GT_CONFIG"


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
    parser.add_argument("--stop-flag", type=Path,
                        default=os.environ.get(STOP_FLAG_ENV) or None,
                        help="File whose appearance stops the run early (GT "
                             "closed, manifest written with an aborted "
                             f"marker); defaults to ${STOP_FLAG_ENV}")
    parser.add_argument("--gt-config", type=Path,
                        default=os.environ.get(GT_CONFIG_ENV) or None,
                        help="YAML with a gt_contact_logging section (e.g. "
                             "config/gt/contact_logging_on.fragment.yaml); "
                             f"defaults to ${GT_CONFIG_ENV}, absent = off")
    args = parser.parse_args()

    if args.repetitions < 1:
        sys.exit("--repetitions must be >= 1")
    if args.duration_sec is not None and args.duration_sec <= 0:
        sys.exit("--duration-sec must be > 0")
    if args.seed is not None and args.seed < 0:
        sys.exit("--seed must be >= 0")
    if args.ros_domain_id is not None:
        os.environ["ROS_DOMAIN_ID"] = str(args.ros_domain_id)

    import yaml

    from isaac.vgu_sim.config import (
        ResolvedRunConfig,
        ScenarioConfig,
        load_gt_contact_logging_config,
    )
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
        gt_contact_logging=load_gt_contact_logging_config(args.gt_config),
    )
    print(f"gt_contact_logging.enabled={run_config.gt_contact_logging.enabled}",
          flush=True)

    from isaac.vgu_sim.runner import run_simulation
    results = run_simulation(run_config, stop_flag=args.stop_flag)

    failed = [r for r in results if not r.completed]
    if failed:
        for r in failed:
            print(f"FAIL rep={r.repetition}: {r.failure}", file=sys.stderr)
        sys.exit(1)

    print(f"All {len(results)} repetition(s) completed successfully.")


if __name__ == "__main__":
    main()
