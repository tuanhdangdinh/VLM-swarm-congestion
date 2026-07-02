#!/usr/bin/env bash
# Run M6 Isaac Sim simulation.
# Usage: ISAAC_SIM_ROOT=~/IsaacSim ./scripts/run_simulation.sh --scenario isaac/config/scenarios/head_on_deadlock.yaml --headless --seed 42
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${ISAAC_SIM_ROOT:-}" ]]; then
    echo "ERROR: ISAAC_SIM_ROOT is not set. Point it at your Isaac Sim install." >&2
    exit 1
fi
if [[ ! -x "${ISAAC_SIM_ROOT}/python.sh" ]]; then
    echo "ERROR: ${ISAAC_SIM_ROOT}/python.sh not found or not executable." >&2
    exit 1
fi

# Do NOT source a host ROS install here. Isaac Sim's embedded Python is 3.12;
# host ROS distros are typically built for the system Python (e.g. 3.10), and
# putting their rclpy on the path breaks Isaac's ROS2 bridge with an ABI
# mismatch (ModuleNotFoundError: rclpy._rclpy_pybind11). Isaac's
# isaacsim.ros2.core extension bundles its own ABI-matched rclpy per distro
# and auto-loads it when no importable system rclpy is present.
export ROS_DISTRO="${ROS_DISTRO:-jazzy}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"

# UDP-only DDS profile. Without it FastDDS prefers shared-memory transport for
# same-host peers, which silently fails across the host/container boundary
# (separate /dev/shm): discovery works but no data flows, so consumers in the
# ROS2 container see the publishers yet receive nothing.
export FASTRTPS_DEFAULT_PROFILES_FILE="${FASTRTPS_DEFAULT_PROFILES_FILE:-${REPO}/config/dds/fastdds.xml}"

# Make the isaac/ package importable inside Isaac Sim's embedded Python.
export PYTHONPATH="${REPO}${PYTHONPATH:+:${PYTHONPATH}}"

# Isaac's bundled ROS2 C libraries for the chosen distro. Required: the
# extension resolves its internal rclpy Python package by itself, but the
# underlying rmw/rcl shared libraries must be on LD_LIBRARY_PATH or the
# bridge fails with "ROS2 Bridge startup failed" (verified 2026-07-02).
# Overridable for installs whose ext layout differs.
ISAAC_ROS2_LIB_DIR="${ISAAC_ROS2_LIB_DIR:-${ISAAC_SIM_ROOT}/exts/isaacsim.ros2.core/${ROS_DISTRO}/lib}"
if [[ ! -d "${ISAAC_ROS2_LIB_DIR}" ]]; then
    echo "ERROR: internal ROS2 lib dir not found: ${ISAAC_ROS2_LIB_DIR}" >&2
    echo "Set ISAAC_ROS2_LIB_DIR to your isaacsim.ros2.core/<distro>/lib directory." >&2
    exit 1
fi
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+${LD_LIBRARY_PATH}:}${ISAAC_ROS2_LIB_DIR}"

cd "${REPO}"
exec "${ISAAC_SIM_ROOT}/python.sh" -m isaac.scripts.run_simulation "$@"
