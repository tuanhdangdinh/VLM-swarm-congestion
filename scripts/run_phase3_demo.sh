#!/usr/bin/env bash
# Phase 3 closed-loop demo: Isaac + M1 + Nav2 + M5 + M4 execution + recorder.
# The full M2->M3->M4->Nav2 loop: a head-on deadlock forms, M2 classifies it,
# M3 grounds yield, M4 issues backup, robot reverses, both reach goals.
#
# Usage:
#   ./run_phase3_demo.sh
#   ./run_phase3_demo.sh --rec-sec 90   # longer recording window
set -euo pipefail

REPO=/home/ubuntu/vgu-vlm-swarm
CONTAINER=vgu_ros
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REC_DURATION_SEC=80
OUT_CONTAINER="/tmp/phase3_demo_${STAMP}.mp4"
OUT_HOST="${REPO}/data/logs/recordings/phase3_demo_${STAMP}.mp4"
TAIL_LOG="${REPO}/data/logs/recordings/phase3_demo_${STAMP}_logs.txt"

ISAAC_LOG="/tmp/phase3_demo_${STAMP}_isaac.log"
M1_LOG="/tmp/phase3_demo_${STAMP}_m1.log"
M5_LOG="/tmp/phase3_demo_${STAMP}_m5.log"
M4_LOG="/tmp/phase3_demo_${STAMP}_m4.log"
NAV2_R1_LOG="/tmp/phase3_demo_${STAMP}_nav2_r1.log"
NAV2_R2_LOG="/tmp/phase3_demo_${STAMP}_nav2_r2.log"
REC_LOG="/tmp/phase3_demo_${STAMP}_record.log"

# Load API key from .env
if [ -f "$REPO/.env" ]; then
  set -a; source "$REPO/.env"; set +a
fi
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "ERROR: OPENAI_API_KEY not set" >&2
  exit 1
fi

ROS_SETUP='source /opt/ros/jazzy/setup.bash && source /ws/ros2_ws/install/setup.bash && for pkg in swarm_interfaces swarm_simulation swarm_perception swarm_execution swarm_orchestrator; do if [ -f /ws/ros2_ws/install/${pkg}/share/${pkg}/local_setup.bash ]; then source /ws/ros2_ws/install/${pkg}/share/${pkg}/local_setup.bash; fi; done && export FASTRTPS_DEFAULT_PROFILES_FILE=/ws/config/dds/fastdds.xml && export PYTHONPATH=/ws:${PYTHONPATH:-}'

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --rec-sec) REC_DURATION_SEC="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

log() { printf '[phase3-demo %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

docker_ros() {
  sudo docker exec "$CONTAINER" bash -lc "$ROS_SETUP && $*"
}

wait_topic() {
  local topic="$1" timeout="${2:-120}"
  log "waiting for publisher: ${topic}"
  docker_ros "timeout ${timeout}s bash -lc 'until ros2 topic list 2>/dev/null | grep -qx ${topic}; do sleep 1; done'"
}

wait_action() {
  local action="$1" timeout="${2:-150}"
  log "waiting for action server: ${action}"
  docker_ros "timeout ${timeout}s bash -lc 'until ros2 action list 2>/dev/null | grep -qx ${action}; do sleep 1; done'"
}

cleanup() {
  set +e
  log "cleanup: restarting container + killing Isaac"
  sudo docker restart "$CONTAINER" >/dev/null 2>&1 || true
  for p in $(ps -eo pid=,args= | awk '/isaac[.]scripts[.]run_simulation/ {print $1}'); do
    sudo kill -9 "$p" 2>/dev/null || true
  done
  # Collect tail logs
  sudo docker exec "$CONTAINER" bash -lc "
    for f in ${M1_LOG} ${M5_LOG} ${M4_LOG} ${REC_LOG} ${NAV2_R1_LOG} ${NAV2_R2_LOG}; do
      echo \"===\$f===\"; tail -n 60 \"\$f\" 2>/dev/null || true
    done" >"$TAIL_LOG" 2>/dev/null || true
  {
    echo "===${ISAAC_LOG}==="
    tail -n 80 "$ISAAC_LOG" 2>/dev/null || true
  } >>"$TAIL_LOG" 2>/dev/null || true
  sudo chown ubuntu:ubuntu "$TAIL_LOG" "$OUT_HOST" 2>/dev/null || true
  log "logs saved to ${TAIL_LOG}"
}
trap cleanup EXIT

cd "$REPO"
mkdir -p data/logs/recordings data/logs/m5_decisions data/logs/m5_frames

# ── 0. Clean old processes ─────────────────────────────────────────────────
log "restarting ROS container"
sudo docker restart "$CONTAINER" >/dev/null
for p in $(ps -eo pid=,args= | awk '/isaac[.]scripts[.]run_simulation|record_camera[.]py/ {print $1}'); do
  sudo kill -9 "$p" 2>/dev/null || true
done

# ── 1. Isaac Sim ────────────────────────────────────────────────────────────
log "starting Isaac Sim head_on_deadlock (headless) → ${ISAAC_LOG}"
# LD_LIBRARY_PATH is required: the isaacsim.ros2.core extension resolves its
# internal rclpy by itself, but the rmw/rcl C libraries must be on the path
# or the bridge fails with "ROS2 Bridge startup failed".
nohup sudo -H -u ubuntu env \
  ROS_DISTRO=jazzy \
  RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  LD_LIBRARY_PATH=/home/ubuntu/IsaacSim/exts/isaacsim.ros2.core/jazzy/lib \
  FASTRTPS_DEFAULT_PROFILES_FILE="$REPO/config/dds/fastdds.xml" \
  PYTHONPATH="$REPO" \
  /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.run_simulation \
    --scenario "$REPO/isaac/config/scenarios/head_on_deadlock.yaml" \
    --headless --seed 42 --duration-sec 280 --topic-timeout-sec 120 \
  >"$ISAAC_LOG" 2>&1 &
ISAAC_PID=$!
log "Isaac PID ${ISAAC_PID}"

# ── 2. Wait for Isaac topics ─────────────────────────────────────────────────
wait_topic /camera/image_raw 180
docker_ros "timeout 60s ros2 topic echo --qos-reliability best_effort --once /camera/image_raw >/dev/null"
for robot in robot_1 robot_2; do
  wait_topic "/${robot}/odom" 120
  wait_topic "/${robot}/scan" 120
done
log "Isaac topics live"

# ── 3. M1 Perception ─────────────────────────────────────────────────────────
log "starting M1 perception → ${M1_LOG}"
sudo docker exec -d "$CONTAINER" bash -lc \
  "$ROS_SETUP && ros2 launch swarm_perception perception.launch.py \
   use_camera_node:=false expected_robot_ids:=robot_1,robot_2 \
   >${M1_LOG} 2>&1"
wait_topic /perception/scene_state 90
wait_topic /perception/annotated_frame 90
log "M1 perception live"

# ── 4. M1 Annotated-frame recorder ───────────────────────────────────────────
log "starting M1 recorder (${REC_DURATION_SEC}s) → ${OUT_CONTAINER}"
sudo docker exec -d "$CONTAINER" bash -lc \
  "$ROS_SETUP && python3 /ws/record_camera.py \
   /perception/annotated_frame ${OUT_CONTAINER} ${REC_DURATION_SEC} \
   >${REC_LOG} 2>&1"
sleep 3

# ── 5. Nav2 bringup ───────────────────────────────────────────────────────────
log "starting Nav2 robot_1 → ${NAV2_R1_LOG}"
# x/y/yaw MUST equal the spawn poses in isaac/config/scenarios/head_on_deadlock.yaml: they define the static map->odom transform.
sudo docker exec -d "$CONTAINER" bash -lc \
  "$ROS_SETUP && ros2 launch swarm_simulation nav2_robot.launch.py \
   robot_id:=robot_1 x:=-1.5 y:=0.0 yaw:=0.0 start_map_server:=true \
   >${NAV2_R1_LOG} 2>&1"
sleep 3
log "starting Nav2 robot_2 → ${NAV2_R2_LOG}"
sudo docker exec -d "$CONTAINER" bash -lc \
  "$ROS_SETUP && ros2 launch swarm_simulation nav2_robot.launch.py \
   robot_id:=robot_2 x:=1.5 y:=0.0 yaw:=3.14159265 start_map_server:=false \
   >${NAV2_R2_LOG} 2>&1"

wait_action /robot_1/navigate_to_pose 150
wait_action /robot_2/navigate_to_pose 150
log "Nav2 action servers live"

# ── 6. M4 Execution (command_bus + coordination_client + safety_monitor) ───────
log "starting M4 execution stack → ${M4_LOG}"
sudo docker exec -d "$CONTAINER" bash -lc \
  "$ROS_SETUP && ros2 launch swarm_execution execution.launch.py \
   >${M4_LOG} 2>&1"
sleep 4

# ── 7. M5 Orchestrator (owns task registry + triggers M2→M3 pipeline) ─────────
# Source the key from /ws/.env inside the container rather than interpolating
# it into this command string — an inline OPENAI_API_KEY=... lands in the
# docker-exec argv and is readable by every user on the host via `ps aux`
# for the whole life of the process.
log "starting M5 orchestrator (openai backend) → ${M5_LOG}"
sudo docker exec -d "$CONTAINER" bash -lc \
  "$ROS_SETUP && set -a && source /ws/.env && set +a && \
   ros2 launch swarm_orchestrator orchestrator.launch.py \
   >${M5_LOG} 2>&1"
sleep 5

log "all components started — recording for ${REC_DURATION_SEC}s while loop runs"

# ── 8. Monitor M5 decisions live ─────────────────────────────────────────────
log "--- M5 decisions will appear in ${REPO}/data/logs/m5_decisions/ ---"
log "--- tailing M5 log for live feedback ---"
# Stream M5 log for ~60s while recording runs
# `sudo timeout`, not `timeout sudo`: an unprivileged timeout cannot signal
# the root-owned sudo child (EPERM), so the tail never dies and the script
# hangs here forever — the video is never copied and cleanup never runs.
sudo timeout $((REC_DURATION_SEC - 10))s \
  docker exec "$CONTAINER" bash -lc "tail -f ${M5_LOG}" 2>/dev/null || true

# ── 9. Wait for recorder, then copy out ──────────────────────────────────────
log "recorder window elapsed — copying video"
sleep 10
sudo docker exec "$CONTAINER" bash -lc "cat ${REC_LOG} 2>/dev/null || true"
sudo docker cp "$CONTAINER:${OUT_CONTAINER}" "$OUT_HOST" 2>/dev/null || true
sudo chown ubuntu:ubuntu "$OUT_HOST" 2>/dev/null || true

if [ -f "$OUT_HOST" ]; then
  ls -lh "$OUT_HOST"
else
  log "WARNING: output video not found at ${OUT_HOST}"
fi

# ── 10. Print M5 decision summary ──────────────────────────────────────────
log "=== M5 decision summary ==="
ls -lt "$REPO/data/logs/m5_decisions/" | head -10
latest_dec=$(ls -t "$REPO/data/logs/m5_decisions/"*.json 2>/dev/null | head -3)
for f in $latest_dec; do
  echo "--- $f ---"
  python3 -c "
import json, sys
d = json.load(open('$f'))
print('  terminal_stage:', d.get('terminal_stage'))
print('  grounded:', d.get('grounded_command_present'))
print('  strategy:', d.get('decision', {}).get('strategy') if d.get('decision') else 'none')
print('  failure:', d.get('failure_reason'))
" 2>/dev/null || cat "$f" | head -10
done

log "done: ${OUT_HOST}"
