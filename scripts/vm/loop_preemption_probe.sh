#!/usr/bin/env bash
# Loop-map Nav2 pre-emption control smoke (v2 build-order step 8, Phase 1).
# docs/superpowers/specs/2026-09-30-prereg-v2-design.md, "(b) Loop map" ->
# "Risk"; geometry + design in docs/reports/2026-10-02-loop-preemption-smoke.md.
#
# Three runs, selected by $1:
#   baseline  - loop_map_preemption_probe_baseline (no blocker): confirms
#               Nav2 does not take the loop spuriously.
#   blocker   - loop_map_preemption_probe (partial blocker): the actual
#               go/no-go question -- does Nav2 self-detour through the loop?
#   coverage  - loop_map_m1_coverage_probe (both robots held stationary):
#               the bonus M1-visibility check, mirrors m1_y_extent_probe.sh.
#
# NEW standing trap this driver must respect (not yet fixed in fc_launch.sh
# itself): its cleanup trap logs "killing Isaac" but Isaac Kit can survive
# that pkill by 231-356 s. Before ANY (re)launch this script waits for
# `pgrep -f run_simulation` to return EMPTY first.
#
# baseline/blocker additionally run a positive control (send one
# compute_path_to_pose goal into the second aisle -- it must return a path
# through the N-S strip, proving the loop is genuinely in Nav2's map, not
# just in the YAML) and a continuous costmap/plan sampler
# (_vm_driver/loop_preemption_sampler.py, adapted from the t3a smoke's own
# sampler) for the FAIL signal: any /robot_1/plan pose with y > 0.6.
#
# Usage (on the VM, from the repo root):
#   bash scripts/vm/loop_preemption_probe.sh baseline
#   bash scripts/vm/loop_preemption_probe.sh blocker
#   bash scripts/vm/loop_preemption_probe.sh coverage
#
# Env: REC_SEC (default 420), SEED (default 42), CONTAINER (default vgu_ros).
# Output: data/logs/vm_runs/loop_preemption/<run>_<UTC stamp>/{scenario.yaml,
#   gt/,m5_scene.jsonl,launcher.log,control_goal.log,sampler.jsonl,
#   restore_build.log,m1.log,m5.log,nav2_r1.log,isaac.log}.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
CONTAINER="${CONTAINER:-vgu_ros}"
REC_SEC="${REC_SEC:-420}"
SEED="${SEED:-42}"
RUN="${1:?usage: loop_preemption_probe.sh baseline|blocker|coverage}"

case "$RUN" in
  baseline) SCENARIO=loop_map_preemption_probe_baseline ;;
  blocker)  SCENARIO=loop_map_preemption_probe ;;
  coverage) SCENARIO=loop_map_m1_coverage_probe ;;
  *) echo "ERROR: RUN must be baseline|blocker|coverage; got '${RUN}'" >&2; exit 1 ;;
esac

ORCH_CONFIG="$REPO/ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
BACKUP="/tmp/orchestrator.yaml.loop_preemption_backup"
STAMP_NOW="$(date -u +%Y%m%d_%H%M%S)"
OUT="$REPO/data/logs/vm_runs/loop_preemption/${RUN}_${STAMP_NOW}"
mkdir -p "$OUT"

log() { printf '[loop-preemption %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

PRISTINE_ORCH_MD5=1f656533a30a35882d57d0d64a57bd0d
PRISTINE_RAG_MD5=e18c723cff9cada3f320d564c2ecee5a
RAG_CONFIG="$REPO/config/rag.yaml"

# ── NEW trap: wait for the previous run's Isaac Kit to actually exit ────────
log "waiting for pgrep -f run_simulation to return EMPTY before (re)launch"
WAITED=0
while sudo pgrep -af '[r]un_simulation' >/dev/null 2>&1; do
  if [ "$WAITED" -ge 420 ]; then
    log "ERROR: run_simulation still alive after ${WAITED}s; refusing to launch"
    exit 1
  fi
  sleep 5
  WAITED=$((WAITED + 5))
done
log "confirmed empty after ${WAITED}s wait"

case "$RUN" in
  baseline|blocker)
    BLOCK="  robot_1: { task: cross_narrow_aisle, goal: [2.3, 0.0], start_delay_sec: 0 }"
    ;;
  coverage)
    BLOCK='  robot_1: { task: hold_position, goal: [1.2, 1.2], start_delay_sec: 100000 }
  robot_2: { task: hold_position, goal: [1.8, 1.0], start_delay_sec: 100000 }'
    ;;
esac

cleanup() {
  set +e
  if [ -n "${SAMPLER_PID:-}" ]; then
    kill "$SAMPLER_PID" 2>/dev/null
  fi
  log "restoring orchestrator.yaml initial_tasks from ${BACKUP}"
  python3 "$HERE/patch_initial_tasks.py" "$ORCH_CONFIG" --restore "$BACKUP"
  touch "$ORCH_CONFIG"
  sudo docker exec -w /ws "$CONTAINER" bash -lc \
    "source /opt/ros/jazzy/setup.bash && cd ros2_ws && colcon build --merge-install --packages-select swarm_orchestrator" \
    >"$OUT/restore_build.log" 2>&1
  SRC_MD5=$(md5sum "$ORCH_CONFIG" 2>/dev/null | awk '{print $1}')
  INSTALLED_MD5=$(sudo docker exec "$CONTAINER" md5sum /ws/ros2_ws/install/share/swarm_orchestrator/config/orchestrator.yaml 2>/dev/null | awk '{print $1}')
  RAG_MD5=$(md5sum "$RAG_CONFIG" 2>/dev/null | awk '{print $1}')
  log "orchestrator.yaml md5: src=${SRC_MD5} installed=${INSTALLED_MD5} (pristine ${PRISTINE_ORCH_MD5}); rag.yaml md5: ${RAG_MD5} (pristine ${PRISTINE_RAG_MD5})"
  if [ "$SRC_MD5" != "$PRISTINE_ORCH_MD5" ] || [ "$INSTALLED_MD5" != "$PRISTINE_ORCH_MD5" ] || [ "$RAG_MD5" != "$PRISTINE_RAG_MD5" ]; then
    log "RESTORE VERIFICATION FAILED -- fix by hand before any other scenario runs"
  else
    log "restore verified: all copies pristine"
  fi
}
trap cleanup EXIT

python3 "$HERE/patch_initial_tasks.py" "$ORCH_CONFIG" --backup "$BACKUP"
printf '%s\n' "$BLOCK" >/tmp/loop_preemption_block_"$RUN".txt
python3 "$HERE/patch_initial_tasks.py" "$ORCH_CONFIG" --set /tmp/loop_preemption_block_"$RUN".txt

log "launching fc_launch.sh (background) SCENARIO=${SCENARIO} BACKEND_ID=mock SEED=${SEED} REC_SEC=${REC_SEC}"
SCENARIO="$SCENARIO" BACKEND_ID=mock SEED="$SEED" REC_SEC="$REC_SEC" RECORD=0 \
  bash "$REPO/scripts/vm/fc_launch.sh" </dev/null >"$OUT/launcher.log" 2>&1 &
FC_PID=$!

if [ "$RUN" != "coverage" ]; then
  # Wait for the Nav2 action server to come up (fc_launch logs it), then run
  # the positive control + start the sampler. Bounded by NAV2_ACTIVE_TIMEOUT_SEC
  # (240s) plus bring-up margin.
  log "waiting up to 260s for '/robot_1/navigate_to_pose' action server"
  READY=0
  for i in $(seq 1 130); do
    if grep -q "Nav2 action servers live" "$OUT/launcher.log" 2>/dev/null; then
      READY=1
      break
    fi
    sleep 2
  done
  if [ "$READY" = "1" ]; then
    log "Nav2 action server up; running positive control: compute_path_to_pose into the second aisle (1.2, 1.2)"
    sudo docker exec -w /ws "$CONTAINER" bash -lc \
      "source /opt/ros/jazzy/setup.bash && source /ws/ros2_ws/install/setup.bash && timeout 20s ros2 action send_goal /robot_1/compute_path_to_pose nav2_msgs/action/ComputePathToPose \"{goal: {header: {frame_id: map}, pose: {position: {x: 1.2, y: 1.2, z: 0.0}, orientation: {w: 1.0}}}}\" --feedback" \
      >"$OUT/control_goal.log" 2>&1
    log "positive control result saved to $OUT/control_goal.log"

    log "starting costmap/plan sampler for $((REC_SEC - 20))s -> $OUT/sampler.jsonl"
    sudo docker cp "$REPO/data/logs/vm_runs/loop_preemption/_vm_driver/loop_preemption_sampler.py" "$CONTAINER":/tmp/loop_preemption_sampler.py
    sudo docker exec -w /ws "$CONTAINER" bash -lc \
      "source /opt/ros/jazzy/setup.bash && source /ws/ros2_ws/install/setup.bash && python3 /tmp/loop_preemption_sampler.py /tmp/loop_preemption_sampler_${RUN}.jsonl $((REC_SEC - 20))" \
      >"$OUT/sampler_stderr.log" 2>&1 &
    SAMPLER_PID=$!
  else
    log "WARNING: Nav2 action server readiness not confirmed in launcher.log within budget; skipping positive control + sampler"
  fi
fi

log "waiting for fc_launch.sh (pid $FC_PID) to finish"
wait "$FC_PID"
FC_RC=$?
log "fc_launch.sh exited rc=${FC_RC}"

if [ -n "${SAMPLER_PID:-}" ]; then
  wait "$SAMPLER_PID" 2>/dev/null
  sudo docker cp "$CONTAINER":/tmp/loop_preemption_sampler_${RUN}.jsonl "$OUT/sampler.jsonl" 2>/dev/null \
    && log "copied sampler output -> $OUT/sampler.jsonl" \
    || log "WARNING: no sampler output copied"
fi

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
    fi
  fi
  sudo docker exec "$CONTAINER" bash -lc "cat /tmp/fc_${STAMP}_m5.log" </dev/null >"$OUT/m5.log" 2>/dev/null || true
  sudo docker exec "$CONTAINER" bash -lc "cat /tmp/fc_${STAMP}_m1.log" </dev/null >"$OUT/m1.log" 2>/dev/null || true
  sudo docker exec "$CONTAINER" bash -lc "cat /tmp/fc_${STAMP}_nav2_r1.log" </dev/null >"$OUT/nav2_r1.log" 2>/dev/null || true
  cp "/tmp/fc_${STAMP}_isaac.log" "$OUT/isaac.log" 2>/dev/null || true

  log "checking m5_decisions/ for any dispatch (should be unchanged -- mock stays silent)"
  ls -t "$REPO/data/logs/m5_decisions/" 2>/dev/null | head -3 >"$OUT/newest_m5_decisions.txt"
  grep -ac "dispatch" "$OUT/m5.log" >"$OUT/m5_dispatch_count.txt" 2>/dev/null || echo 0 >"$OUT/m5_dispatch_count.txt"
fi

cp "$REPO/isaac/config/scenarios/${SCENARIO}.yaml" "$OUT/scenario.yaml"
log "done: outputs in $OUT"
