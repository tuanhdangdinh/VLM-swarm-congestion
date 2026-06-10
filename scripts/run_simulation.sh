#!/usr/bin/env bash
# Run M6 Isaac Sim simulation.
# Usage: ./scripts/run_simulation.sh --scenario head_on_deadlock --headless --seed 42 --repetitions 3
set -euo pipefail

if [[ -z "${ISAAC_SIM_ROOT:-}" ]]; then
    echo "ERROR: ISAAC_SIM_ROOT is not set. Source your Isaac Sim environment first." >&2
    exit 1
fi
if [[ ! -x "${ISAAC_SIM_ROOT}/python.sh" ]]; then
    echo "ERROR: ${ISAAC_SIM_ROOT}/python.sh not found or not executable." >&2
    exit 1
fi

if [[ -f /opt/ros/jazzy/setup.bash ]]; then
    source /opt/ros/jazzy/setup.bash
else
    echo "ERROR: ROS 2 Jazzy not found at /opt/ros/jazzy/setup.bash." >&2
    exit 1
fi

if [[ -f ros2_ws/install/setup.bash ]]; then
    source ros2_ws/install/setup.bash
fi

exec "${ISAAC_SIM_ROOT}/python.sh" -m isaac.scripts.run_simulation "$@"
