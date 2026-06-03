#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-dev.txt

if [ -f /opt/ros/humble/setup.bash ]; then
  echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
fi
