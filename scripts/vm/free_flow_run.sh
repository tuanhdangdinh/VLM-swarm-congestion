#!/usr/bin/env bash
# One solo-in-space free-flow harvest run (prereg-v2 spec, Foundations round
# adopted, METHOD RULED 2026-10-05): one robot traverses its cell's course
# ALONE on a generated variant (isaac/config/scenarios/free_flow/, built by
# scripts/make_free_flow_variants.py). Wraps scripts/vm/fc_launch.sh with the
# standing VM traps, as scripts/vm/v2_final_run.sh does:
#   - config files PRISTINE before the overlay (orchestrator.yaml 1f656533...,
#     config/rag.yaml e18c723c...), restored from verbatim backups with a
#     FRESH mtime, swarm_orchestrator rebuilt, source AND installed md5s
#     verified (RESTORE.txt);
#   - `pgrep -f run_simulation` EMPTY before the launch;
#   - the variant's USD must exist and be newer than its yaml (a yaml edit is
#     inert until the USD is rebuilt);
#   - mock backend, no decision file (MockBackend's default no-congestion
#     answer): zero API, and a free-flow run must dispatch nothing.
# The M5 overlay is the variant's one `initial_tasks` line (manifest.json,
# no start_delay_sec); Nav2 gets the parent cell's map (MAP_SCENARIO), which
# the variant's grid equals byte for byte.
#
# Short runs: the Isaac runner stops at the variant's own duration_sec
# (fc_launch's --duration-sec is a dead flag), but fc_launch tails M5 for
# REC_SEC regardless. Once Isaac has exited on its own, this driver ends that
# tail so fc_launch cleans up at once. REC_SEC stays a safety cap.
#
# Run as root (sudo) from the repo root on the VM.
#
# Env:
#   VARIANT    free-flow variant name (required), e.g. t2b_flow_ordering_ff_robot_3
#   LABEL      run directory name (default: VARIANT)
#   OUT_ROOT   output root (default data/logs/vm_runs/free_flow)
#   REC_SEC / SIM_SEC / SEED   passed to fc_launch (defaults 900 / 1000 / 42)
#   CONTAINER  default vgu_ros
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
CONTAINER="${CONTAINER:-vgu_ros}"
VARIANT="${VARIANT:?VARIANT required}"
LABEL="${LABEL:-$VARIANT}"
OUT_ROOT="${OUT_ROOT:-$REPO/data/logs/vm_runs/free_flow}"
REC_SEC="${REC_SEC:-900}"
SIM_SEC="${SIM_SEC:-1000}"
SEED="${SEED:-42}"
OUT="$OUT_ROOT/$LABEL"
ORCH="$REPO/ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
RAG="$REPO/config/rag.yaml"
INSTALLED=/ws/ros2_ws/install/share/swarm_orchestrator/config/orchestrator.yaml
PRISTINE_ORCH_MD5=1f656533a30a35882d57d0d64a57bd0d
PRISTINE_RAG_MD5=e18c723cff9cada3f320d564c2ecee5a
FF_DIR="$REPO/isaac/config/scenarios/free_flow"
VARIANT_YAML="$FF_DIR/${VARIANT}.yaml"
VARIANT_USD="$REPO/isaac/scenarios/${VARIANT}.usd"
BACKUP_DIR="/tmp/free_flow_backup_${LABEL}"

log() { printf '[free-flow %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
md5_of() { md5sum "$1" 2>/dev/null | awk '{print $1}'; }
manifest_field() {
  python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["variants"][sys.argv[2]][sys.argv[3]])' \
    "$FF_DIR/manifest.json" "$VARIANT" "$1"
}

mkdir -p "$OUT"
exec > >(tee -a "$OUT/driver.log") 2>&1

if [ ! -f "$VARIANT_YAML" ]; then
  log "REFUSING: no variant yaml ${VARIANT_YAML}"
  exit 1
fi
if [ ! -f "$VARIANT_USD" ] || [ ! "$VARIANT_USD" -nt "$VARIANT_YAML" ]; then
  log "REFUSING: ${VARIANT_USD} missing or older than its yaml (rebuild the USD)"
  exit 1
fi
PARENT="$(manifest_field parent)" || exit 1
MAP_SCENARIO="$(manifest_field map_scenario)" || exit 1
TASK_LINE="$(manifest_field m5_task_line)" || exit 1
log "variant=${VARIANT} parent=${PARENT} map=${MAP_SCENARIO} task=[${TASK_LINE}]"

if [ "$(md5_of "$ORCH")" != "$PRISTINE_ORCH_MD5" ] || [ "$(md5_of "$RAG")" != "$PRISTINE_RAG_MD5" ]; then
  log "REFUSING: config files are not pristine before the overlay"
  exit 1
fi

log "waiting for pgrep -f run_simulation to be EMPTY before launch"
WAITED=0
while pgrep -af '[r]un_simulation' >/dev/null 2>&1; do
  if [ "$WAITED" -ge 900 ]; then
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

printf '%s\n' "$TASK_LINE" >"$OUT/initial_tasks.txt"
python3 "$HERE/patch_initial_tasks.py" "$ORCH" --set "$OUT/initial_tasks.txt" || exit 1
cp "$ORCH" "$OUT/orchestrator.overlaid.yaml"

GT_DIR="$REPO/data/logs/simulation/${VARIANT}-seed${SEED}-rep000"
if [ -d "$GT_DIR" ]; then
  mv "$GT_DIR" "$OUT_ROOT/_rescued_$(basename "$GT_DIR")_$(date -u +%s)"
  log "moved a leftover ground-truth dir aside"
fi

log "launching fc_launch SCENARIO=${VARIANT} MAP_SCENARIO=${MAP_SCENARIO} REC_SEC=${REC_SEC}"
SCENARIO="$VARIANT" MAP_SCENARIO="$MAP_SCENARIO" BACKEND_ID=mock MOCK_DECISION_FILE="" \
  SEED="$SEED" REC_SEC="$REC_SEC" SIM_SEC="$SIM_SEC" RECORD=0 \
  bash "$REPO/scripts/vm/fc_launch.sh" </dev/null >"$OUT/launcher.log" 2>&1 &
FC_PID=$!

# The installed overlay, once fc_launch's own swarm_orchestrator build is done
# (its "scenario validated" line follows that build).
for _ in $(seq 1 120); do
  grep -q "scenario validated" "$OUT/launcher.log" 2>/dev/null && break
  kill -0 "$FC_PID" 2>/dev/null || break
  sleep 2
done
docker exec "$CONTAINER" bash -lc "grep -A3 '^initial_tasks:' $INSTALLED" >"$OUT/installed_initial_tasks.txt" 2>&1
log "installed initial_tasks: $(tr '\n' ' ' <"$OUT/installed_initial_tasks.txt")"

for _ in $(seq 1 300); do
  grep -q "all components started" "$OUT/launcher.log" 2>/dev/null && break
  kill -0 "$FC_PID" 2>/dev/null || break
  sleep 3
done
STAMP="$(grep -aoE '/tmp/fc_[0-9]{8}_[0-9]{6}_m5\.log' "$OUT/launcher.log" | head -1 | sed -E 's#/tmp/fc_([0-9]{8}_[0-9]{6})_m5\.log#\1#')"
log "fc_launch stamp: ${STAMP:-UNKNOWN}"

while kill -0 "$FC_PID" 2>/dev/null; do
  if ! pgrep -af '[r]un_simulation' >/dev/null 2>&1; then
    log "Isaac exited on its own; ending fc_launch's M5 tail"
    echo "isaac_exited_utc=$(date -u +%H:%M:%S)" >"$OUT/ISAAC_EXIT.txt"
    if [ -n "$STAMP" ]; then
      pkill -TERM -f "[t]ail -f /tmp/fc_${STAMP}_m5.log" 2>/dev/null
    fi
    break
  fi
  sleep 5
done

wait "$FC_PID"
log "fc_launch exited rc=$?"

if grep -q "logs saved to" "$OUT/launcher.log"; then
  echo "GATE OK: logs saved to present" >"$OUT/GATE.txt"
else
  echo "GATE FAILED: no 'logs saved to' line" >"$OUT/GATE.txt"
fi
cat "$OUT/GATE.txt"

if [ -d "$GT_DIR" ]; then mv "$GT_DIR" "$OUT/gt"; log "ground truth -> $OUT/gt"; else log "WARNING: no ground truth"; fi
cp "$VARIANT_YAML" "$OUT/scenario.yaml"
if [ -n "$STAMP" ]; then
  for f in m1 m4 m5 nav2_r1 nav2_r2 nav2_r3 nav2_r4; do
    docker exec "$CONTAINER" bash -lc "cat /tmp/fc_${STAMP}_${f}.log" </dev/null >"$OUT/${f}.log" 2>/dev/null || rm -f "$OUT/${f}.log"
    [ -s "$OUT/${f}.log" ] || rm -f "$OUT/${f}.log"
  done
  cp "/tmp/fc_${STAMP}_isaac.log" "$OUT/isaac.log" 2>/dev/null || true
  mkdir -p "$OUT/decisions"
  grep -l "\"run_id\": \"${STAMP}\"" "$REPO"/data/logs/m5_decisions/*.json 2>/dev/null \
    | xargs -I{} cp {} "$OUT/decisions/" 2>/dev/null || true
  SESSION_ID="$(grep -aoE "session_id=[0-9a-f]+ run_id=${STAMP}" "$OUT/m5.log" 2>/dev/null | head -1 | sed -E 's/session_id=([0-9a-f]+).*/\1/')"
  if [ -n "$SESSION_ID" ] && [ -f "$REPO/data/logs/m5_scene/${SESSION_ID}.jsonl" ]; then
    cp "$REPO/data/logs/m5_scene/${SESSION_ID}.jsonl" "$OUT/m5_scene.jsonl"
  fi
fi

{
  echo "m5_log_lines=$(wc -l <"$OUT/m5.log" 2>/dev/null || echo 0)"
  echo "m5_accepted_arrivals=$(grep -cE 'arrived at base goal|arrival accepted late' "$OUT/m5.log" 2>/dev/null || echo 0)"
  echo "m5_rejected_arrivals=$(grep -c 'arrival rejected' "$OUT/m5.log" 2>/dev/null || echo 0)"
  echo "decision_files=$(find "$OUT/decisions" -name '*.json' 2>/dev/null | wc -l)"
  echo "gt_completed=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1])).get("completed"))' "$OUT/gt/run_manifest.json" 2>/dev/null || echo missing)"
  echo "jump_back_warnings=$(grep -c 'jump back in time' "$OUT/m1.log" "$OUT/nav2_r"*.log 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')"
} | tee "$OUT/EVIDENCE.txt"

printf 'label=%s variant=%s parent=%s map=%s stamp=%s seed=%s rec_sec=%s\n' \
  "$LABEL" "$VARIANT" "$PARENT" "$MAP_SCENARIO" "${STAMP:-none}" "$SEED" "$REC_SEC" \
  >"$OUT/CONDITION.txt"
chown -R ubuntu:ubuntu "$OUT" 2>/dev/null || true
log "done: $OUT"
