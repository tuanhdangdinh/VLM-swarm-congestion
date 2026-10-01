#!/usr/bin/env bash
# M1 y-extent verification probe (v2 build-order step 3,
# docs/superpowers/specs/2026-09-30-prereg-v2-design.md "Prerequisites" item
# 3 / docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md
# "Prereg-v2 Path"): confirms M1 tracks the composite `junction_clear`
# command's cross-pair recede endpoints (|y| ~= 1.2) before oracle design,
# using the two scenarios isaac/config/scenarios/m1_y_extent_probe_{a,b}.yaml
# (run A: the actual |y| = 1.2 requirement point, both signs, plus the
# already-verified |x| = 1.75 reference; run B: a stationary re-check of the
# verified |y| = 1.80 edge, a push to |y| = 2.0 inside the homography edge
# but outside the previously-verified band, and a cheap |x| = 2.4 bonus).
#
# Every run holds all four robots at spawn (orchestrator.yaml's
# `initial_tasks` rewritten with a huge `start_delay_sec`, so M5 never
# issues a Nav2 goal -- task_registry.py counts a pending assignment from
# load time) and forces BACKEND_ID=mock, so no VLM backend is ever called:
# this is a pure M1 tracking measurement, zero API spend. initial_tasks is
# restored byte-for-byte on exit (via patch_initial_tasks.py --restore),
# whatever the run's outcome, and the package is rebuilt so the restore
# reaches the installed copy too -- the pristine md5 is logged for the
# operator to compare against the recorded value
# (ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml: 1f656533a30a35882d57d0d64a57bd0d).
#
# Prerequisite (not run by this script): build + validate each scenario's
# USD and generate its map first, e.g. from the repo root on the VM host:
#   /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.build_scenario \
#     --config isaac/config/scenarios/m1_y_extent_probe_a.yaml
#   /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.validate_simulation \
#     --scenario isaac/scenarios/m1_y_extent_probe_a.usd
#   docker exec vgu_ros bash -lc \
#     "cd /ws && python3 -m isaac.scripts.generate_warehouse_map \
#        --out-dir ros2_ws/src/swarm_simulation/maps \
#        --scenario isaac/config/scenarios/m1_y_extent_probe_a.yaml"
#   docker exec -w /ws vgu_ros bash -lc \
#     "source /opt/ros/jazzy/setup.bash && cd ros2_ws && \
#      colcon build --merge-install --packages-select swarm_simulation"
# (repeat for _b). fc_launch.sh itself checks the map exists inside the
# container before anything expensive starts.
#
# Usage (on the VM, from the repo root):
#   bash scripts/vm/m1_y_extent_probe.sh a
#   bash scripts/vm/m1_y_extent_probe.sh b
#   REC_SEC=700 bash scripts/vm/m1_y_extent_probe.sh a
#
# Env: REC_SEC (default 650, passed to fc_launch.sh -- must comfortably
#   exceed Nav2 four-stack bring-up (NAV2_ACTIVE_TIMEOUT_SEC 240 worst case)
#   plus the scenario's own 120 s hold), SEED (default 42), CONTAINER
#   (default vgu_ros). Output: data/logs/vm_runs/y_extent_probe/<a|b>_<UTC
#   stamp>/{scenario.yaml,gt/,m5_scene.jsonl,launcher.log,restore_build.log}.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
CONTAINER="${CONTAINER:-vgu_ros}"
REC_SEC="${REC_SEC:-650}"
SEED="${SEED:-42}"
RUN="${1:?usage: m1_y_extent_probe.sh a|b}"

case "$RUN" in
  a) SCENARIO=m1_y_extent_probe_a ;;
  b) SCENARIO=m1_y_extent_probe_b ;;
  *) echo "ERROR: RUN must be 'a' or 'b'; got '${RUN}'" >&2; exit 1 ;;
esac

ORCH_CONFIG="$REPO/ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
BACKUP="/tmp/orchestrator.yaml.y_extent_probe_backup"
STAMP_NOW="$(date -u +%Y%m%d_%H%M%S)"
OUT="$REPO/data/logs/vm_runs/y_extent_probe/${RUN}_${STAMP_NOW}"
mkdir -p "$OUT"

log() { printf '[y-extent-probe %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

# All four robots held at spawn (goal == spawn, so a sent command -- none
# should ever be dispatched -- would still be a no-op) with
# start_delay_sec far beyond the scenario's 120 s duration_sec.
if [ "$RUN" = a ]; then
  BLOCK='  robot_1: { task: hold_position, goal: [-1.75, 0.0], start_delay_sec: 100000 }
  robot_2: { task: hold_position, goal: [1.75, 0.0], start_delay_sec: 100000 }
  robot_3: { task: hold_position, goal: [0.0, -1.2], start_delay_sec: 100000 }
  robot_4: { task: hold_position, goal: [0.0, 1.2], start_delay_sec: 100000 }'
else
  BLOCK='  robot_1: { task: hold_position, goal: [-2.4, 0.0], start_delay_sec: 100000 }
  robot_2: { task: hold_position, goal: [2.4, 0.0], start_delay_sec: 100000 }
  robot_3: { task: hold_position, goal: [0.0, -1.8], start_delay_sec: 100000 }
  robot_4: { task: hold_position, goal: [0.0, 2.0], start_delay_sec: 100000 }'
fi

PRISTINE_ORCH_MD5=1f656533a30a35882d57d0d64a57bd0d

cleanup() {
  set +e
  log "restoring orchestrator.yaml initial_tasks from ${BACKUP}"
  python3 "$HERE/patch_initial_tasks.py" "$ORCH_CONFIG" --restore "$BACKUP"
  # touch belt-and-suspenders the fresh-mtime guarantee patch_initial_tasks.py
  # --restore already provides (plain copy, not copy2): colcon's incremental
  # build skips re-copying a config file whose source mtime is NOT newer than
  # the package's last build output, silently leaving a stale installed copy
  # even though `colcon build` reports success (observed 2026-10-01 on this
  # exact probe -- the project's "never trust colcon exit codes" rule
  # applies to a post-run restore, not just a deploy).
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
printf '%s\n' "$BLOCK" >/tmp/y_extent_probe_block_"$RUN".txt
python3 "$HERE/patch_initial_tasks.py" "$ORCH_CONFIG" --set /tmp/y_extent_probe_block_"$RUN".txt

log "launching fc_launch.sh SCENARIO=${SCENARIO} BACKEND_ID=mock SEED=${SEED} REC_SEC=${REC_SEC}"
SCENARIO="$SCENARIO" BACKEND_ID=mock SEED="$SEED" REC_SEC="$REC_SEC" RECORD=0 \
  bash "$REPO/scripts/vm/fc_launch.sh" </dev/null 2>&1 | tee "$OUT/launcher.log"

# fc_launch.sh's own final "done: STAMP=..." line is NOT a reliable source:
# its stage-11 decision summary runs `ls -t m5_decisions/*.json | head -3`
# under `set -e -o pipefail`, which this project's m5_decisions/ directory
# (shared across every scenario ever run) will eventually accumulate more
# than 3 old files in -- SIGPIPE on `ls`'s write end then aborts the whole
# script before the done line prints (observed on run A, 2026-10-01: 9
# leftover files, done line never printed, yet the run itself completed
# cleanly). The M1-perception start line is unaffected and always present.
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
  # The scene log's filename is a random session_id (orchestrator_node.py:
  # uuid4().hex), not the fc_launch STAMP; the STAMP only appears inside
  # each record as run_id and in the M5 log's startup line
  # "session_id=<id> run_id=<STAMP>".
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
