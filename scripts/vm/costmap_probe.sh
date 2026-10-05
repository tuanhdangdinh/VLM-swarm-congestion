#!/usr/bin/env bash
# One VM run of the costmap-source probe
# (docs/reports/2026-10-05-costmap-source-probe.md). Wraps
# scripts/vm/v2_final_run.sh, which owns every standing VM trap (pgrep-empty
# gate, pristine-config refusal, verbatim restore + rebuild + installed-md5
# check, `logs saved to` gate, mock-only backend), and adds, once Nav2 is live:
#   1. the live obstacle/inflation parameters of both costmaps (params.txt);
#   2. `ros2 bag record` (C++, mcap) of the scan, TF, odometry, M1 scene, raw
#      cmd_vel, the global costmap + updates and the probe's phase markers;
#   3. scripts/vm/costmap_probe.py: wait for the park, then per phase clear
#      the global costmap and hold still or rotate in place;
#   4. after the phases: stop the bag (SIGINT, so mcap finalises), export it
#      with scripts/vm/costmap_bag_export.py, and copy bag + export out --
#      all before fc_launch's cleanup restarts the container.
#
# Run as root (sudo) from the repo root on the VM.
#
# Env (on top of v2_final_run.sh's own):
#   LABEL     run directory name (required)
#   PARK      a | b -> OVERLAY=costmap_probe_<PARK> (robot_1's park goal)
#   PHASES    costmap_probe.py phase list
#   SCENARIO  default loop_map_preemption_probe_baseline (no blocker)
#   REC_SEC   default 900
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
CONTAINER="${CONTAINER:-vgu_ros}"
LABEL="${LABEL:?LABEL required}"
PARK="${PARK:?PARK required (a|b)}"
PHASES="${PHASES:?PHASES required}"
SCENARIO="${SCENARIO:-loop_map_preemption_probe_baseline}"
REC_SEC="${REC_SEC:-900}"
PROBE_TIMEOUT="${PROBE_TIMEOUT:-600}"
OUT_ROOT="${OUT_ROOT:-$REPO/data/logs/vm_runs/costmap_probe}"
OUT="$OUT_ROOT/$LABEL"
BAG="/tmp/cp_bag_${LABEL}"
EXPORT="/tmp/cp_export_${LABEL}.jsonl"
MARKS="/tmp/cp_phases_${LABEL}.jsonl"
ROS_ENV="source /opt/ros/jazzy/setup.bash && source /ws/ros2_ws/install/setup.bash && export FASTRTPS_DEFAULT_PROFILES_FILE=/ws/config/dds/fastdds.xml"
TOPICS="/robot_1/scan /tf /tf_static /robot_1/odom /perception/scene_state /robot_1/cmd_vel /robot_1/global_costmap/costmap /robot_1/global_costmap/costmap_updates /costmap_probe/phase"

log() { printf '[costmap-probe %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
dx() { docker exec -w /ws "$CONTAINER" bash -lc "$ROS_ENV && $1"; }

# Park goal in map minus the (-2.4, 0) spawn = the park in odom.
case "$PARK" in
  a) PARK_ODOM="0.85,0.0" ;;
  b) PARK_ODOM="2.7,1.2" ;;
  *) echo "ERROR: PARK must be a or b; got '${PARK}'" >&2; exit 1 ;;
esac

mkdir -p "$OUT"
LABEL="$LABEL" SCENARIO="$SCENARIO" OVERLAY="costmap_probe_${PARK}" MOCK="" \
  OUT_ROOT="$OUT_ROOT" REC_SEC="$REC_SEC" bash "$HERE/v2_final_run.sh" &
RUN_PID=$!

for _ in $(seq 1 240); do
  grep -q "Nav2 action servers live" "$OUT/launcher.log" 2>/dev/null && break
  kill -0 "$RUN_PID" 2>/dev/null || break
  sleep 3
done
if ! grep -q "Nav2 action servers live" "$OUT/launcher.log" 2>/dev/null; then
  log "WARNING: Nav2 readiness not seen; no probe"
  wait "$RUN_PID"
  exit 1
fi


docker exec "$CONTAINER" rm -rf "$BAG" "$EXPORT" "$MARKS"
docker exec -w /ws "$CONTAINER" bash -lc \
  "$ROS_ENV && exec ros2 bag record -s mcap -o $BAG $TOPICS" >"$OUT/bag_record.log" 2>&1 &
BAG_PID=$!
sleep 5
log "bag recorder started"

docker cp "$HERE/costmap_probe.py" "$CONTAINER":/tmp/costmap_probe.py
docker cp "$HERE/costmap_bag_export.py" "$CONTAINER":/tmp/costmap_bag_export.py
timeout "$((PROBE_TIMEOUT + 30))" docker exec -w /ws "$CONTAINER" bash -lc \
  "$ROS_ENV && python3 /tmp/costmap_probe.py $MARKS $PROBE_TIMEOUT '$PHASES' robot_1 $PARK_ODOM" \
  >"$OUT/probe_stderr.log" 2>&1 &
PROBE_PID=$!
log "probe started (PHASES=${PHASES})"

{
  for node in /robot_1/global_costmap/global_costmap /robot_1/local_costmap/local_costmap; do
    for p in obstacle_layer.scan.clearing obstacle_layer.scan.marking \
             obstacle_layer.scan.raytrace_max_range obstacle_layer.scan.obstacle_max_range \
             obstacle_layer.scan.inf_is_valid obstacle_layer.footprint_clearing_enabled \
             inflation_layer.inflation_radius footprint_padding update_frequency publish_frequency \
             always_send_full_costmap; do
      printf '%s %s: ' "$node" "$p"
      dx "ros2 param get $node $p" 2>&1 | tr '\n' ' '
      echo
    done
  done
  dx "ros2 service list | grep -i clear"
} >"$OUT/params.txt" 2>&1
log "params recorded ($(grep -c 'value is' "$OUT/params.txt") values)"

wait "$PROBE_PID"
log "probe exited rc=$?"

sleep 3
docker exec "$CONTAINER" pkill -INT -f "[r]os2 bag record"
for _ in $(seq 1 30); do kill -0 "$BAG_PID" 2>/dev/null || break; sleep 1; done
log "bag recorder stopped"
dx "python3 /tmp/costmap_bag_export.py $BAG $EXPORT robot_1" >"$OUT/export.log" 2>&1
log "export rc=$?"
docker cp "$CONTAINER":"$MARKS" "$OUT/phases.jsonl" 2>/dev/null || log "WARNING: no phase markers"
docker cp "$CONTAINER":"$EXPORT" "$OUT/export.jsonl" 2>/dev/null || log "WARNING: no export"
docker cp "$CONTAINER":"$BAG" "$OUT/bag" 2>/dev/null || log "WARNING: no bag"
log "copied: $(ls "$OUT" | tr '\n' ' ')"

wait "$RUN_PID"
log "v2_final_run exited rc=$?"
printf 'park=%s phases=%s\n' "$PARK" "$PHASES" >>"$OUT/CONDITION.txt"
chown -R ubuntu:ubuntu "$OUT" 2>/dev/null || true
log "done: $OUT"
