#!/usr/bin/env bash
set -euo pipefail

source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --symlink-install
