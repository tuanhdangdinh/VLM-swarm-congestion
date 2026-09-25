#!/usr/bin/env bash
# Closed-loop demo WITH video, parameterized over the M2 reasoning backend.
# Retrieved from /tmp/gem_record_launch.sh (the recipe behind the live
# gemini_20260918_084649 run recorded in docs/implementation_notes.md, M2
# section), itself derived from /home/ubuntu/fc_record_launch.sh (run-H
# recipe, localization:=camera). Generalized here so any configured
# reasoning_backend_id can be exercised, not just `gemini`.
#
# Usage:
#   ./run_gemini_er2_demo.sh
#   ./run_gemini_er2_demo.sh --backend-id openai --rec-sec 300 --sim-sec 400
#   BACKEND_ID=openai ./run_gemini_er2_demo.sh
#
# Post-processing (manual — the recorder stamps a higher fps than it
# achieves under load, so raw playback runs fast; achieved fps only becomes
# known from the recorder's own exit line, hence this is not automated):
#   1. If --segment-frames split the output into annotated_000.mp4,
#      annotated_001.mp4, ..., concat them losslessly first:
#        ffmpeg -f concat -safe 0 \
#          -i <(for f in annotated_*.mp4; do echo "file '$PWD/$f'"; done) \
#          -c copy annotated_concat.mp4
#   2. Grep the recorder log for its exit line: `WROTE ... frames=<F>
#      secs=<S>` -> achieved_fps = F / S. The stamped fps is printed by this
#      script as "stamping fps=<FPS>" before the recorder starts.
#      ratio = stamped_fps / achieved_fps
#      (the 2026-09-18 live run measured stamped 8.289 vs achieved 3.941,
#      i.e. ratio 2.1033).
#   3. Re-time so wall-clock playback matches real elapsed time:
#        ffmpeg -i annotated_concat.mp4 -vf "setpts=<ratio>*PTS" \
#          -r <achieved_fps> annotated_retimed.mp4
set -euo pipefail

REPO=/home/ubuntu/vgu-vlm-swarm
CONTAINER=vgu_ros
BACKEND_ID="${BACKEND_ID:-gemini}"
REC_SEC="${REC_SEC:-1000}"
SIM_SEC="${SIM_SEC:-1200}"
STAMP=$(date -u +%Y%m%d_%H%M%S)

ORCH_CONFIG="${REPO}/ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
MAP=/ws/ros2_ws/install/share/swarm_simulation/maps/warehouse_map_head_on_deadlock.yaml

ISAAC_LOG=/tmp/gem_er2_${STAMP}_isaac.log
M1_LOG=/tmp/gem_er2_${STAMP}_m1.log
NAV2_R1_LOG=/tmp/gem_er2_${STAMP}_nav2_r1.log
NAV2_R2_LOG=/tmp/gem_er2_${STAMP}_nav2_r2.log
M4_LOG=/tmp/gem_er2_${STAMP}_m4.log
M5_LOG=/tmp/gem_er2_${STAMP}_m5.log
REC_LOG=/tmp/gem_er2_${STAMP}_rec.log
BUILD_LOG=/tmp/gem_er2_${STAMP}_build.log
REC_DIR_HOST="${REPO}/data/logs/gem_er2_run_${STAMP}"
REC_DIR_WS=/ws/data/logs/gem_er2_run_${STAMP}
REC_OUT="${REC_DIR_WS}/annotated.mp4"
TAIL_LOG="${REC_DIR_HOST}/tail_logs.txt"

ROS_SETUP='source /opt/ros/jazzy/setup.bash && source /ws/ros2_ws/install/setup.bash && export FASTRTPS_DEFAULT_PROFILES_FILE=/ws/config/dds/fastdds.xml && export PYTHONPATH=/ws:${PYTHONPATH:-}'

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-id) BACKEND_ID="$2"; shift 2 ;;
    --rec-sec) REC_SEC="$2"; shift 2 ;;
    --sim-sec) SIM_SEC="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

log() { printf '[gem-er2-demo %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

docker_ros() {
  sudo docker exec -w /ws "$CONTAINER" bash -lc "$ROS_SETUP && $*"
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
  if [ -n "${PREV_BACKEND_ID:-}" ] && [ "${PREV_BACKEND_ID}" != "${BACKEND_ID}" ]; then
    log "restoring reasoning_backend_id: ${BACKEND_ID} -> ${PREV_BACKEND_ID}"
    sed -i "s/^reasoning_backend_id: .*/reasoning_backend_id: ${PREV_BACKEND_ID}/" "$ORCH_CONFIG"
    # Rebuild so the INSTALLED copy (what orchestrator.launch.py actually
    # loads via get_package_share_directory) matches the restored source —
    # a source-only revert would silently leave the VM's installed package
    # pointed at this run's backend for the next launch. This exact gap had
    # to be fixed by hand after the live gemini_20260918_084649 run.
    sudo docker exec -w /ws "$CONTAINER" bash -lc \
      "source /opt/ros/jazzy/setup.bash && cd ros2_ws && colcon build --merge-install --packages-select swarm_orchestrator" \
      >>"$BUILD_LOG" 2>&1
  fi

  log "cleanup: restarting container + killing Isaac"
  sudo docker restart "$CONTAINER" >/dev/null 2>&1 || true
  # Bracketed so the pattern doesn't match pkill's own argv/invoking command
  # line (an unbracketed "isaac.scripts.run_simulation" would match itself).
  sudo pkill -f "[i]saac.scripts.run_simulation" 2>/dev/null || true
  sudo pkill -f "[r]ecord_topic_video.py" 2>/dev/null || true
  sudo docker exec -w /ws "$CONTAINER" bash -lc "
    for f in ${M1_LOG} ${M5_LOG} ${M4_LOG} ${REC_LOG} ${NAV2_R1_LOG} ${NAV2_R2_LOG}; do
      echo \"===\$f===\"; tail -n 60 \"\$f\" 2>/dev/null || true
    done" >"$TAIL_LOG" 2>/dev/null || true
  {
    echo "===${ISAAC_LOG}==="
    tail -n 80 "$ISAAC_LOG" 2>/dev/null || true
    # BUILD_LOG is written on the HOST (the colcon build redirect is outside
    # the docker-exec command string), unlike the logs above which are
    # written inside the container — collect it separately or it is silently
    # missing from TAIL_LOG.
    echo "===${BUILD_LOG}==="
    tail -n 60 "$BUILD_LOG" 2>/dev/null || true
  } >>"$TAIL_LOG" 2>/dev/null || true
  sudo chown -R ubuntu:ubuntu "$REC_DIR_HOST" 2>/dev/null || true
  log "logs saved to ${TAIL_LOG}; recordings in ${REC_DIR_HOST}"
}
trap cleanup EXIT
# A bare `trap cleanup EXIT` alone would leave a Ctrl-C/dropped-SSH session
# waiting at the interrupted command instead of tearing down (INT/TERM/HUP
# resume execution unless the script itself exits) — on a ~20 min run that
# is the realistic way to abandon this script without the restore ever
# firing, so force an exit on those signals and let the EXIT trap fire once.
trap 'exit 130' INT TERM HUP

cd "$REPO"
log "restarting ROS container"
sudo docker restart "$CONTAINER" >/dev/null
sudo pkill -f "[i]saac.scripts.run_simulation" 2>/dev/null || true
sudo pkill -f "[r]ecord_topic_video.py" 2>/dev/null || true
sleep 2

sudo mkdir -p data/logs/m5_decisions data/logs/m5_frames data/logs/m5_scene "$REC_DIR_HOST"
sudo chmod 777 "$REC_DIR_HOST"
test -f "$REPO/scripts/record_topic_video.py" || { echo "recorder script missing on VM"; exit 1; }

# ── 1. Point M5 at BACKEND_ID (restored on exit) ────────────────────────────
PREV_BACKEND_ID=$(grep -m1 '^reasoning_backend_id:' "$ORCH_CONFIG" | awk '{print $2}')
if [ -z "$PREV_BACKEND_ID" ]; then
  echo "ERROR: could not read reasoning_backend_id from ${ORCH_CONFIG}" >&2
  exit 1
fi
log "reasoning_backend_id: ${PREV_BACKEND_ID} -> ${BACKEND_ID} (restored on exit)"
sed -i "s/^reasoning_backend_id: .*/reasoning_backend_id: ${BACKEND_ID}/" "$ORCH_CONFIG"

# orchestrator.launch.py loads the INSTALLED copy of orchestrator.yaml via
# get_package_share_directory, so the source edit above is inert until this
# package is rebuilt (plain `colcon build`, without --merge-install, errors
# in this workspace layout).
log "building swarm_orchestrator (merge-install) -> ${BUILD_LOG}"
sudo docker exec -w /ws "$CONTAINER" bash -lc \
  "source /opt/ros/jazzy/setup.bash && cd ros2_ws && colcon build --merge-install --packages-select swarm_orchestrator" \
  >"$BUILD_LOG" 2>&1

# ── 2. Isaac Sim ─────────────────────────────────────────────────────────────
log "starting Isaac Sim head_on_deadlock (headless, seed 42, ${SIM_SEC}s) -> ${ISAAC_LOG}"
# LD_LIBRARY_PATH is required: the isaacsim.ros2.core extension resolves its
# internal rclpy by itself, but the rmw/rcl C libraries must be on the path
# or the bridge fails with "ROS2 Bridge startup failed".
# sudo -H -u ubuntu: /home/ubuntu is mode 0750, so an SSH session under any
# other account fails with "python3: Permission denied" launching python.sh.
nohup sudo -H -u ubuntu env \
  ROS_DISTRO=jazzy \
  RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  LD_LIBRARY_PATH=/home/ubuntu/IsaacSim/exts/isaacsim.ros2.core/jazzy/lib \
  FASTRTPS_DEFAULT_PROFILES_FILE="$REPO/config/dds/fastdds.xml" \
  PYTHONPATH="$REPO" \
  /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.run_simulation \
    --scenario "$REPO/isaac/config/scenarios/head_on_deadlock.yaml" \
    --headless --seed 42 --duration-sec "$SIM_SEC" --topic-timeout-sec 180 \
  >"$ISAAC_LOG" 2>&1 &
log "Isaac PID $!"

wait_topic /camera/image_raw 300
docker_ros "timeout 60s ros2 topic echo --qos-reliability best_effort --once /camera/image_raw >/dev/null"
for robot in robot_1 robot_2; do
  wait_topic "/${robot}/odom" 120
  wait_topic "/${robot}/scan" 120
done
log "Isaac topics live"

# ── 3. M1 Perception (must start before Nav2: Nav2 uses camera localization) ─
log "starting M1 perception -> ${M1_LOG}"
sudo docker exec -d -w /ws "$CONTAINER" bash -lc \
  "$ROS_SETUP && ros2 launch swarm_perception perception.launch.py use_camera_node:=false >${M1_LOG} 2>&1"
wait_topic /perception/scene_state 90
wait_topic /perception/annotated_frame 90
log "M1 perception live"

# ── 4. Recorder (fps stamped from a live measurement; see header for re-timing) ─
HZ=$(docker_ros "timeout 12s ros2 topic hz /perception/annotated_frame 2>/dev/null | grep -m1 'average rate' | awk '{print \$3}'" || true)
FPS=${HZ:-9}
log "annotated_frame measured rate ${HZ:-unknown} Hz -> stamping fps=${FPS}, recording ${REC_SEC}s -> ${REC_OUT}"
sudo docker exec -d -w /ws "$CONTAINER" bash -lc \
  "$ROS_SETUP && python3 /ws/scripts/record_topic_video.py --topic /perception/annotated_frame --output ${REC_OUT} --duration-sec ${REC_SEC} --fps ${FPS} --qos best_effort --segment-frames 2000 >${REC_LOG} 2>&1"
sleep 3

# ── 5. Nav2 bringup (localization:=camera; map includes the aisle_barrier) ──
log "starting Nav2 robot_1 -> ${NAV2_R1_LOG}"
sudo docker exec -d -w /ws "$CONTAINER" bash -lc \
  "$ROS_SETUP && ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_1 x:=-1.5 y:=0.0 yaw:=0.0 start_map_server:=true localization:=camera map_yaml:=${MAP} >${NAV2_R1_LOG} 2>&1"
sleep 3
log "starting Nav2 robot_2 -> ${NAV2_R2_LOG}"
sudo docker exec -d -w /ws "$CONTAINER" bash -lc \
  "$ROS_SETUP && ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_2 x:=1.5 y:=0.0 yaw:=3.14159265 start_map_server:=false localization:=camera map_yaml:=${MAP} >${NAV2_R2_LOG} 2>&1"
wait_action /robot_1/navigate_to_pose 150
wait_action /robot_2/navigate_to_pose 150
log "Nav2 action servers live"

# ── 6. M4 Execution ──────────────────────────────────────────────────────────
log "starting M4 execution -> ${M4_LOG}"
sudo docker exec -d -w /ws "$CONTAINER" bash -lc \
  "$ROS_SETUP && ros2 launch swarm_execution execution.launch.py >${M4_LOG} 2>&1"
sleep 4

# ── 7. M5 Orchestrator (backend from BACKEND_ID) ────────────────────────────
# Source the key from /ws/.env inside the container rather than interpolating
# it into this command string — an inline API-key assignment lands in the
# docker-exec argv and is readable by every user on the host via `ps aux`
# for the whole life of the process.
log "starting M5 orchestrator (${BACKEND_ID} backend, CWD /ws) -> ${M5_LOG}"
sudo docker exec -d -w /ws "$CONTAINER" bash -lc \
  "$ROS_SETUP && set -a && source /ws/.env && set +a && export VGU_RUN_ID=${BACKEND_ID}_${STAMP} && ros2 launch swarm_orchestrator orchestrator.launch.py >${M5_LOG} 2>&1"
sleep 5
log "all components started — recording for ${REC_SEC}s while loop runs"

# ── 8. Monitor M5 decisions live ─────────────────────────────────────────────
log "--- M5 decisions will appear in ${REPO}/data/logs/m5_decisions/ ---"
log "--- tailing M5 log for live feedback ---"
# `sudo timeout`, not `timeout sudo`: an unprivileged timeout cannot signal
# the root-owned sudo child (EPERM), so the tail never dies and the script
# hangs here forever — the recording is never finalized and cleanup never runs.
sudo timeout $((REC_SEC - 10))s \
  docker exec -w /ws "$CONTAINER" bash -lc "tail -f ${M5_LOG}" 2>/dev/null || true

# ── 9. Wait for recorder to finish; recording is already on the bind mount ──
log "recorder window elapsed — recording lives on the host bind mount (no docker cp needed)"
sleep 10
sudo docker exec -w /ws "$CONTAINER" bash -lc "cat ${REC_LOG} 2>/dev/null || true"
sudo chown -R ubuntu:ubuntu "$REC_DIR_HOST" 2>/dev/null || true
ls -lh "$REC_DIR_HOST" || log "WARNING: recording directory not found at ${REC_DIR_HOST}"

# ── 10. Print M5 decision summary ───────────────────────────────────────────
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

log "done: ${REC_DIR_HOST} (stamped fps=${FPS}; see header for the ffmpeg re-timing post-step)"
