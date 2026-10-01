#!/usr/bin/env bash
# M1 robot_1/(-1.75, 0) STALE root-cause probe (docs/reports/
# 2026-10-01-m1-y-extent-verification.md "Registered risk"; this task's
# report is docs/reports/2026-10-01-robot1-stale-rootcause.md). Two short
# mock-backend runs discriminate the hypothesis space:
#
#   swap  -- isaac/config/scenarios/m1_stale_rootcause_probe_swap.yaml:
#            robot_1/robot_2 spawn positions exchanged (marker_id stays
#            bound to robot_id per ScenarioConfig's validator, so swapping
#            positions is how marker identity is isolated). Follows the
#            dropout to the marker (hypothesis 2) or to the position
#            (hypothesis 1/4).
#   nudge -- isaac/config/scenarios/m1_stale_rootcause_probe_nudge.yaml:
#            robot_1 (marker 1) moved 0.10 m off the failing x to -1.65 --
#            the candidate scene-level fix for IB10 -- plus a bonus
#            far-side nudge on robot_2/marker 2 to +1.85.
#   goalpose -- isaac/config/scenarios/m1_stale_rootcause_probe_goalpose.yaml:
#            all four robots held at their intersection_bottleneck.yaml GOAL
#            positions, all at yaw 0 (Nav2's actual arrival orientation,
#            since cross_intersection goals are plain [x, y] lists ->
#            command_bus_node.py defaults yaw to 0.0) -- closes the gap the
#            swap run left open (marker 1 was only tested at (+1.75, 0,
#            yaw PI) there, not the real arrival yaw 0; N-S arrival poses
#            were never tested at yaw 0 either).
#   yieldpark -- isaac/config/scenarios/m1_stale_rootcause_probe_yieldpark.yaml:
#            robot_1/robot_2 held at the REAL single-yield park pose a
#            junction yielder gets, computed directly from
#            reasoning/rag/maneuver_geometry.py's derive_backup_distance
#            against tests/unit/test_intersection_bottleneck_scenario.py's
#            own IB10 ground-truth standoff frame (not the scenario header's
#            north-south-only "1.7 m clearance binds" note, which does not
#            establish the east-west yielder's park point -- that clearance
#            is computed per-yielder from its own real offsets to the
#            crossing robots, not a fixed geometric constant shared across
#            axes). Closes the gap review flagged: an IB10 yield parks a
#            robot for the whole maneuver, not just the transient
#            pre-departure window the goalpose run covered.
#
# Modeled directly on scripts/vm/m1_y_extent_probe.sh (same mechanism:
# rewrite orchestrator.yaml's initial_tasks to a 100000 s start_delay hold
# for all four robots so M5 never dispatches a Nav2 goal, force
# BACKEND_ID=mock so this is zero API spend, restore byte-for-byte on exit
# regardless of outcome). Not a generalization of that script -- kept
# separate so this task's scope stays out of the frozen y-extent probe.
#
# Prerequisite (not run by this script): build + validate each scenario's
# USD and generate its map first, e.g. from the repo root on the VM host:
#   /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.build_scenario \
#     --config isaac/config/scenarios/m1_stale_rootcause_probe_swap.yaml
#   /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.validate_simulation \
#     --scenario isaac/scenarios/m1_stale_rootcause_probe_swap.usd
#   docker exec vgu_ros bash -lc \
#     "cd /ws && python3 -m isaac.scripts.generate_warehouse_map \
#        --out-dir ros2_ws/src/swarm_simulation/maps \
#        --scenario isaac/config/scenarios/m1_stale_rootcause_probe_swap.yaml"
#   docker exec -w /ws vgu_ros bash -lc \
#     "source /opt/ros/jazzy/setup.bash && cd ros2_ws && \
#      colcon build --merge-install --packages-select swarm_simulation"
# (repeat for _nudge). fc_launch.sh itself checks the map exists inside the
# container before anything expensive starts.
#
# Usage (on the VM, from the repo root):
#   bash scripts/vm/m1_stale_rootcause_probe.sh swap
#   bash scripts/vm/m1_stale_rootcause_probe.sh nudge
#   bash scripts/vm/m1_stale_rootcause_probe.sh goalpose
#   bash scripts/vm/m1_stale_rootcause_probe.sh yieldpark
#
# Env: REC_SEC (default 650), SEED (default 42), CONTAINER (default
#   vgu_ros). Output: data/logs/vm_runs/stale_rootcause/<swap|nudge|
#   goalpose|yieldpark>_<UTC stamp>/{scenario.yaml,gt/,m5_scene.jsonl,
#   launcher.log,restore_build.log}.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
CONTAINER="${CONTAINER:-vgu_ros}"
REC_SEC="${REC_SEC:-650}"
SEED="${SEED:-42}"
RUN="${1:?usage: m1_stale_rootcause_probe.sh swap|nudge|goalpose|yieldpark}"

case "$RUN" in
  swap)      SCENARIO=m1_stale_rootcause_probe_swap ;;
  nudge)     SCENARIO=m1_stale_rootcause_probe_nudge ;;
  goalpose)  SCENARIO=m1_stale_rootcause_probe_goalpose ;;
  yieldpark) SCENARIO=m1_stale_rootcause_probe_yieldpark ;;
  *) echo "ERROR: RUN must be 'swap', 'nudge', 'goalpose', or 'yieldpark'; got '${RUN}'" >&2; exit 1 ;;
esac

ORCH_CONFIG="$REPO/ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
BACKUP="/tmp/orchestrator.yaml.stale_rootcause_probe_backup"
STAMP_NOW="$(date -u +%Y%m%d_%H%M%S)"
OUT="$REPO/data/logs/vm_runs/stale_rootcause/${RUN}_${STAMP_NOW}"
mkdir -p "$OUT"

log() { printf '[stale-rootcause-probe %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

if [ "$RUN" = swap ]; then
  BLOCK='  robot_1: { task: hold_position, goal: [1.75, 0.0], start_delay_sec: 100000 }
  robot_2: { task: hold_position, goal: [-1.75, 0.0], start_delay_sec: 100000 }
  robot_3: { task: hold_position, goal: [0.0, -1.2], start_delay_sec: 100000 }
  robot_4: { task: hold_position, goal: [0.0, 1.2], start_delay_sec: 100000 }'
elif [ "$RUN" = nudge ]; then
  BLOCK='  robot_1: { task: hold_position, goal: [-1.65, 0.0], start_delay_sec: 100000 }
  robot_2: { task: hold_position, goal: [1.85, 0.0], start_delay_sec: 100000 }
  robot_3: { task: hold_position, goal: [0.0, -1.2], start_delay_sec: 100000 }
  robot_4: { task: hold_position, goal: [0.0, 1.2], start_delay_sec: 100000 }'
elif [ "$RUN" = goalpose ]; then
  BLOCK='  robot_1: { task: hold_position, goal: [1.75, 0.0], start_delay_sec: 100000 }
  robot_2: { task: hold_position, goal: [-1.75, 0.0], start_delay_sec: 100000 }
  robot_3: { task: hold_position, goal: [0.0, 1.75], start_delay_sec: 100000 }
  robot_4: { task: hold_position, goal: [0.0, -1.75], start_delay_sec: 100000 }'
else
  BLOCK='  robot_1: { task: hold_position, goal: [-1.37, 0.359], start_delay_sec: 100000 }
  robot_2: { task: hold_position, goal: [1.481, -0.344], start_delay_sec: 100000 }
  robot_3: { task: hold_position, goal: [0.0, -1.2], start_delay_sec: 100000 }
  robot_4: { task: hold_position, goal: [0.0, 1.2], start_delay_sec: 100000 }'
fi

PRISTINE_ORCH_MD5=1f656533a30a35882d57d0d64a57bd0d

cleanup() {
  set +e
  log "restoring orchestrator.yaml initial_tasks from ${BACKUP}"
  python3 "$HERE/patch_initial_tasks.py" "$ORCH_CONFIG" --restore "$BACKUP"
  # Plain copy + explicit touch, not copy2: colcon's incremental build skips
  # re-copying a config file whose source mtime is not newer than the
  # package's last build output (m1_y_extent_probe.sh hit this exact trap
  # 2026-10-01; patch_initial_tasks.py --restore already avoids copy2, this
  # touch is belt-and-suspenders).
  touch "$ORCH_CONFIG"
  sudo docker exec -w /ws "$CONTAINER" bash -lc \
    "source /opt/ros/jazzy/setup.bash && cd ros2_ws && colcon build --merge-install --packages-select swarm_orchestrator" \
    >"$OUT/restore_build.log" 2>&1
  SRC_MD5=$(md5sum "$ORCH_CONFIG" 2>/dev/null | awk '{print $1}')
  INSTALLED_MD5=$(sudo docker exec "$CONTAINER" md5sum /ws/ros2_ws/install/share/swarm_orchestrator/config/orchestrator.yaml 2>/dev/null | awk '{print $1}')
  log "orchestrator.yaml md5 after restore: src=${SRC_MD5} installed=${INSTALLED_MD5} (pristine ${PRISTINE_ORCH_MD5})"
  if [ "$SRC_MD5" != "$PRISTINE_ORCH_MD5" ] || [ "$INSTALLED_MD5" != "$PRISTINE_ORCH_MD5" ]; then
    log "RESTORE VERIFICATION FAILED -- orchestrator.yaml is NOT pristine; fix by hand before any other scenario runs"
  else
    log "restore verified: both copies pristine"
  fi
}
trap cleanup EXIT

python3 "$HERE/patch_initial_tasks.py" "$ORCH_CONFIG" --backup "$BACKUP"
printf '%s\n' "$BLOCK" >/tmp/stale_rootcause_probe_block_"$RUN".txt
python3 "$HERE/patch_initial_tasks.py" "$ORCH_CONFIG" --set /tmp/stale_rootcause_probe_block_"$RUN".txt

log "launching fc_launch.sh SCENARIO=${SCENARIO} BACKEND_ID=mock SEED=${SEED} REC_SEC=${REC_SEC}"
SCENARIO="$SCENARIO" BACKEND_ID=mock SEED="$SEED" REC_SEC="$REC_SEC" RECORD=0 \
  bash "$REPO/scripts/vm/fc_launch.sh" </dev/null 2>&1 | tee "$OUT/launcher.log"

# Same stamp-extraction caveat as m1_y_extent_probe.sh: fc_launch.sh's own
# "done: STAMP=..." line can be lost to a SIGPIPE in its decision-summary
# stage once m5_decisions/ accumulates more than 3 files; the M1-perception
# start line is unaffected and always present.
STAMP="$(grep -aoE '/tmp/fc_[0-9]{8}_[0-9]{6}_m1\.log' "$OUT/launcher.log" | head -1 | sed -E 's#.*/fc_([0-9]{8}_[0-9]{6})_m1\.log#\1#')"
log "fc_launch run stamp: ${STAMP:-UNKNOWN}"

GT_DIR="$REPO/data/logs/simulation/${SCENARIO}-seed${SEED}-rep000"
if [ -d "$GT_DIR" ]; then
  cp -r "$GT_DIR" "$OUT/gt"
  log "copied ground truth -> $OUT/gt"
else
  log "WARNING: no ground-truth dir at $GT_DIR"
fi

if [ -n "${STAMP:-}" ]; then
  SESSION_ID="$(sudo docker exec "$CONTAINER" grep -aoE "session_id=[0-9a-f]+ run_id=${STAMP}" "/tmp/fc_${STAMP}_m5.log" 2>/dev/null | head -1 | sed -E 's/session_id=([0-9a-f]+).*/\1/')"
  log "M5 session_id: ${SESSION_ID:-UNKNOWN}"
  if [ -n "${SESSION_ID:-}" ]; then
    SCENE_SRC="$REPO/data/logs/m5_scene/${SESSION_ID}.jsonl"
    if [ -f "$SCENE_SRC" ]; then
      cp "$SCENE_SRC" "$OUT/m5_scene.jsonl"
      log "copied M1 scene log -> $OUT/m5_scene.jsonl"
    else
      log "WARNING: no m5_scene log at $SCENE_SRC"
    fi
  fi
  sudo docker exec "$CONTAINER" bash -lc "cat /tmp/fc_${STAMP}_m5.log" </dev/null >"$OUT/m5.log" 2>/dev/null || true
  sudo docker exec "$CONTAINER" bash -lc "cat /tmp/fc_${STAMP}_m1.log" </dev/null >"$OUT/m1.log" 2>/dev/null || true
  cp "/tmp/fc_${STAMP}_isaac.log" "$OUT/isaac.log" 2>/dev/null || true
fi

cp "$REPO/isaac/config/scenarios/${SCENARIO}.yaml" "$OUT/scenario.yaml"
log "done: outputs in $OUT"
