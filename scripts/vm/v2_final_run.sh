#!/usr/bin/env bash
# One VM run of the prereg-v2 final build wave (build-order step 8 phase 2
# loop-detour family + the step-9 visual pass). Wraps scripts/vm/fc_launch.sh
# with every standing VM trap, per run:
#   - Isaac Kit survives fc_launch's own cleanup by minutes: wait for
#     `pgrep -f run_simulation` to be EMPTY before launching (refuse after
#     420 s).
#   - The config files must be PRISTINE before the overlay (orchestrator.yaml
#     1f656533..., config/rag.yaml e18c723c...) and are restored from verbatim
#     backups afterwards with a FRESH mtime (plain copy + touch), then
#     swarm_orchestrator is rebuilt and the source AND installed copies are
#     md5-verified (RESTORE.txt).
#   - The run counts only when fc_launch printed its `logs saved to` line.
#   - Mock backend only: BACKEND_ID=mock always, MOCK_DECISION_FILE optional
#     (empty = the MockBackend's default no-congestion answer). Zero API.
#
# Run as root (sudo) from the repo root on the VM: the config dir is
# root-owned (the step-7b lesson).
#
# Env:
#   LABEL      run directory name (required)
#   SCENARIO   scenario name (required)
#   OVERLAY    scripts/vm/v2_overlay.py scene, or "none" (default none)
#   MOCK       repo-relative mock decision file (default empty)
#   OUT_ROOT   output root (default data/logs/vm_runs/loop_family)
#   SAMPLER    1 = run scripts/vm/loop_family_sampler.py on robot_1 (default 0)
#   RECORD     passed to fc_launch (default 0)
#   REC_SEC / SIM_SEC / SEED   passed to fc_launch (defaults 900 / 1000 / 42)
#   CONTAINER  default vgu_ros
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
CONTAINER="${CONTAINER:-vgu_ros}"
LABEL="${LABEL:?LABEL required}"
SCENARIO="${SCENARIO:?SCENARIO required}"
OVERLAY="${OVERLAY:-none}"
MOCK="${MOCK:-}"
OUT_ROOT="${OUT_ROOT:-$REPO/data/logs/vm_runs/loop_family}"
SAMPLER="${SAMPLER:-0}"
RECORD="${RECORD:-0}"
REC_SEC="${REC_SEC:-900}"
SIM_SEC="${SIM_SEC:-1000}"
SEED="${SEED:-42}"
OUT="$OUT_ROOT/$LABEL"
ORCH="$REPO/ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
RAG="$REPO/config/rag.yaml"
INSTALLED=/ws/ros2_ws/install/share/swarm_orchestrator/config/orchestrator.yaml
PRISTINE_ORCH_MD5=1f656533a30a35882d57d0d64a57bd0d
PRISTINE_RAG_MD5=e18c723cff9cada3f320d564c2ecee5a
BACKUP_DIR="/tmp/v2_final_backup_${LABEL}"

log() { printf '[v2-final %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
md5_of() { md5sum "$1" 2>/dev/null | awk '{print $1}'; }

mkdir -p "$OUT"
exec > >(tee -a "$OUT/driver.log") 2>&1

if [ "$(md5_of "$ORCH")" != "$PRISTINE_ORCH_MD5" ] || [ "$(md5_of "$RAG")" != "$PRISTINE_RAG_MD5" ]; then
  log "REFUSING: config files are not pristine before the overlay"
  exit 1
fi

log "waiting for pgrep -f run_simulation to be EMPTY before launch"
WAITED=0
while pgrep -af '[r]un_simulation' >/dev/null 2>&1; do
  if [ "$WAITED" -ge 420 ]; then
    log "ERROR: run_simulation still alive after ${WAITED}s; refusing to launch"
    exit 1
  fi
  sleep 5
  WAITED=$((WAITED + 5))
done
log "confirmed empty after ${WAITED}s"

mkdir -p "$BACKUP_DIR"
cp -p "$ORCH" "$BACKUP_DIR/orchestrator.yaml"
cp -p "$RAG" "$BACKUP_DIR/rag.yaml"

restore() {
  set +e
  if [ -n "${SAMPLER_PID:-}" ]; then kill "$SAMPLER_PID" 2>/dev/null; fi
  cp "$BACKUP_DIR/orchestrator.yaml" "$ORCH" && touch "$ORCH"
  cp "$BACKUP_DIR/rag.yaml" "$RAG" && touch "$RAG"
  docker exec -w /ws "$CONTAINER" bash -lc \
    "source /opt/ros/jazzy/setup.bash && cd ros2_ws && colcon build --merge-install --packages-select swarm_orchestrator" \
    >"$OUT/restore_build.log" 2>&1
  local src inst rag
  src=$(md5_of "$ORCH")
  inst=$(docker exec "$CONTAINER" md5sum "$INSTALLED" 2>/dev/null | awk '{print $1}')
  rag=$(md5_of "$RAG")
  {
    echo "orchestrator.yaml src=${src} installed=${inst} (pristine ${PRISTINE_ORCH_MD5})"
    echo "rag.yaml src=${rag} (pristine ${PRISTINE_RAG_MD5})"
    if [ "$src" = "$PRISTINE_ORCH_MD5" ] && [ "$inst" = "$PRISTINE_ORCH_MD5" ] && [ "$rag" = "$PRISTINE_RAG_MD5" ]; then
      echo "RESTORE OK"
    else
      echo "RESTORE FAILED -- fix by hand before any other run"
    fi
  } | tee "$OUT/RESTORE.txt"
}
trap restore EXIT

if [ "$OVERLAY" != "none" ]; then
  python3 "$HERE/v2_overlay.py" --orchestrator "$ORCH" --rag "$RAG" "$OVERLAY" || exit 1
fi
cp "$ORCH" "$OUT/orchestrator.overlaid.yaml"
cp "$RAG" "$OUT/rag.overlaid.yaml"

GT_DIR="$REPO/data/logs/simulation/${SCENARIO}-seed${SEED}-rep000"
if [ -d "$GT_DIR" ]; then
  mv "$GT_DIR" "$OUT_ROOT/_rescued_$(basename "$GT_DIR")_$(date -u +%s)"
  log "moved a leftover ground-truth dir aside"
fi

log "launching fc_launch SCENARIO=${SCENARIO} MOCK=${MOCK:-<default>} REC_SEC=${REC_SEC} SIM_SEC=${SIM_SEC} RECORD=${RECORD}"
SCENARIO="$SCENARIO" BACKEND_ID=mock MOCK_DECISION_FILE="$MOCK" SEED="$SEED" \
  REC_SEC="$REC_SEC" SIM_SEC="$SIM_SEC" RECORD="$RECORD" \
  bash "$REPO/scripts/vm/fc_launch.sh" </dev/null >"$OUT/launcher.log" 2>&1 &
FC_PID=$!

if [ "$SAMPLER" = "1" ]; then
  for _ in $(seq 1 200); do
    grep -q "Nav2 action servers live" "$OUT/launcher.log" 2>/dev/null && break
    sleep 3
  done
  if grep -q "Nav2 action servers live" "$OUT/launcher.log" 2>/dev/null; then
    docker cp "$HERE/loop_family_sampler.py" "$CONTAINER":/tmp/loop_family_sampler.py
    docker exec -w /ws "$CONTAINER" bash -lc \
      "source /opt/ros/jazzy/setup.bash && source /ws/ros2_ws/install/setup.bash && export FASTRTPS_DEFAULT_PROFILES_FILE=/ws/config/dds/fastdds.xml && python3 /tmp/loop_family_sampler.py /tmp/loop_family_sampler_${LABEL}.jsonl $((REC_SEC - 30))" \
      >"$OUT/sampler_stderr.log" 2>&1 &
    SAMPLER_PID=$!
    log "sampler started"
  else
    log "WARNING: Nav2 readiness not seen; no sampler"
  fi
fi

wait "$FC_PID"
log "fc_launch exited rc=$?"
if [ -n "${SAMPLER_PID:-}" ]; then
  wait "$SAMPLER_PID" 2>/dev/null
  docker cp "$CONTAINER":/tmp/loop_family_sampler_${LABEL}.jsonl "$OUT/sampler.jsonl" 2>/dev/null \
    && log "sampler output copied" || log "WARNING: no sampler output"
  SAMPLER_PID=""
fi

if grep -q "logs saved to" "$OUT/launcher.log"; then
  echo "GATE OK: logs saved to present" >"$OUT/GATE.txt"
else
  echo "GATE FAILED: no 'logs saved to' line" >"$OUT/GATE.txt"
fi
cat "$OUT/GATE.txt"

STAMP="$(grep -aoE 'STAMP=[0-9]{8}_[0-9]{6}' "$OUT/launcher.log" | head -1 | sed 's/STAMP=//')"
[ -z "$STAMP" ] && STAMP="$(grep -aoE '/tmp/fc_[0-9]{8}_[0-9]{6}_m1\.log' "$OUT/launcher.log" | head -1 | sed -E 's#.*/fc_([0-9]{8}_[0-9]{6})_m1\.log#\1#')"
log "fc_launch stamp: ${STAMP:-UNKNOWN}"
if [ -d "$GT_DIR" ]; then mv "$GT_DIR" "$OUT/gt"; log "ground truth -> $OUT/gt"; else log "WARNING: no ground truth"; fi
cp "$REPO/isaac/config/scenarios/${SCENARIO}.yaml" "$OUT/scenario.yaml"
if [ -n "$STAMP" ]; then
  for f in m1 m4 m5 nav2_r1 nav2_r2 nav2_r3 nav2_r4; do
    docker exec "$CONTAINER" bash -lc "cat /tmp/fc_${STAMP}_${f}.log" </dev/null >"$OUT/${f}.log" 2>/dev/null || rm -f "$OUT/${f}.log"
  done
  cp "/tmp/fc_${STAMP}_isaac.log" "$OUT/isaac.log" 2>/dev/null || true
  REC_DIR="$REPO/data/logs/fc_run_${STAMP}"
  [ -d "$REC_DIR" ] && cp -r "$REC_DIR" "$OUT/fc_run" 2>/dev/null
  mkdir -p "$OUT/decisions"
  grep -l "\"run_id\": \"${STAMP}\"" "$REPO"/data/logs/m5_decisions/*.json 2>/dev/null \
    | xargs -I{} cp {} "$OUT/decisions/" 2>/dev/null || true
  SESSION_ID="$(grep -aoE "session_id=[0-9a-f]+ run_id=${STAMP}" "$OUT/m5.log" 2>/dev/null | head -1 | sed -E 's/session_id=([0-9a-f]+).*/\1/')"
  if [ -n "$SESSION_ID" ] && [ -f "$REPO/data/logs/m5_scene/${SESSION_ID}.jsonl" ]; then
    cp "$REPO/data/logs/m5_scene/${SESSION_ID}.jsonl" "$OUT/m5_scene.jsonl"
    log "M1 scene log copied (session ${SESSION_ID})"
  else
    log "WARNING: no m5_scene log for session ${SESSION_ID:-UNKNOWN}"
  fi
  if [ -n "$SESSION_ID" ] && [ -d "$REPO/data/logs/m5_frames" ]; then
    mkdir -p "$OUT/frames"
    find "$REPO/data/logs/m5_frames" -maxdepth 2 -newer "$OUT/orchestrator.overlaid.yaml" -type f \
      -exec cp {} "$OUT/frames/" \; 2>/dev/null || true
  fi
fi
printf 'label=%s scenario=%s overlay=%s mock=%s stamp=%s seed=%s rec_sec=%s sim_sec=%s\n' \
  "$LABEL" "$SCENARIO" "$OVERLAY" "${MOCK:-default}" "${STAMP:-none}" "$SEED" "$REC_SEC" "$SIM_SEC" \
  >"$OUT/CONDITION.txt"
chown -R ubuntu:ubuntu "$OUT" 2>/dev/null || true
log "done: $OUT"
