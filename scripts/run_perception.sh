#!/usr/bin/env bash
set -euo pipefail

# Run M1 Perception & Robot ID Tracking module
#
# Usage:
#   ./scripts/run_perception.sh                    # Use hardware camera (default)
#   ./scripts/run_perception.sh --isaac-sim        # Use Isaac Sim bridge (skip camera_node)
#   ./scripts/run_perception.sh --help             # Show this help message
#
# Environment:
#   ROS2_DISTRO (optional): ROS2 distribution to source (default: jazzy)

ROS2_DISTRO="${ROS2_DISTRO:-jazzy}"
USE_CAMERA_NODE="true"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --isaac-sim)
            USE_CAMERA_NODE="false"
            echo "Using Isaac Sim bridge (camera_node disabled)"
            shift
            ;;
        --help)
            head -16 "$0" | tail -12
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            head -16 "$0" | tail -12
            exit 1
            ;;
    esac
done

# Source ROS2 and workspace
source /opt/ros/${ROS2_DISTRO}/setup.bash
source ros2_ws/install/setup.bash

# Launch M1 Perception
echo "Launching M1 Perception & Robot ID Tracking..."
echo "  use_camera_node: ${USE_CAMERA_NODE}"
echo ""

ros2 launch swarm_perception perception.launch.py use_camera_node:=${USE_CAMERA_NODE}
