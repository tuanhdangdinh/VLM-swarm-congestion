"""CLI: write swarm_perception's calibration.yaml from the live CameraConfig.

Runs anywhere (pure math, no Isaac Sim required):

    python -m isaac.scripts.export_calibration
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from isaac.vgu_sim.calibration import build_calibration_dict
from isaac.vgu_sim.config import CameraConfig

DEFAULT_OUTPUT = Path("ros2_ws/src/swarm_perception/config/calibration.yaml")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export overhead-camera calibration.yaml")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = build_calibration_dict(CameraConfig())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=True)
    print(f"Calibration written to: {args.output}")


if __name__ == "__main__":
    main()
