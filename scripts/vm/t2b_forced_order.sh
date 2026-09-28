#!/usr/bin/env bash
# T2b forced-order verification runs (battery design "T2b": scripted
# executions of both orders, n >= 2 seeds each, total time-to-goal from ground
# truth, the oracle order must win by >= 20%). Prepares nothing new on the VM:
# every run is an ordinary scripts/vm/fc_launch.sh mock run of the
# t2b_flow_ordering scenario with one arm's once-style decision script.
#
# Preamble: scripts/t2b_forced_order.py preflight must pass, or nothing runs.
# It checks the deployed tree for the T2b safety slice (pair-scoped clearing
# exemption 9c38042, ordered hold-until-last release 99f4699, first-passer
# guard 38868d2, one passer parser fc441d4) and the robot_3 hold-back
# (daa2558), by symbol and, in a git checkout, by ancestry; and M5/M3 for the
# T2b settings (initial_tasks with robot_3's start_delay_sec, the 1.0 m
# corridor, grounding.mode legacy). The alternative arm reverses robot_1
# toward the queued robot_3; it is safe only with both safety commits live.
#
# Per run (arms interleaved per seed, so drift hits both): any leftover
# ground-truth directory for the seed is moved aside first (Isaac names it
# <scenario>-seed<SEED>-rep000, the same for both arms), fc_launch runs with
# SEED and MOCK_DECISION_FILE, then the ground truth, component logs, the run's
# M5 decision artifacts and an uptime snapshot (three-robot load, report item
# 5) are collected into $OUT/<arm>_seed<SEED>/. At the end the runs are scored
# into $OUT/margin.json; writing the margin into the scenario is left to the
# operator (score --write-scenario) after a look at the per-run arrivals.
#
# Usage (on the VM, from the repo):
#   bash scripts/vm/t2b_forced_order.sh
#   SEEDS="42 43 44" REC_SEC=700 bash scripts/vm/t2b_forced_order.sh
# Env: SEEDS (default "42 43"), REC_SEC (default 600, passed to fc_launch),
#   OUT (default data/logs/vm_runs/t2b_forced_order/<UTC stamp>), PYTHON
#   (default python3; needs PyYAML), CONTAINER (default vgu_ros),
#   SETTLE_SEC (default 20, pause after Isaac exits between runs).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
HARNESS="$HERE/../t2b_forced_order.py"
PYTHON="${PYTHON:-python3}"
SEEDS="${SEEDS:-42 43}"
REC_SEC="${REC_SEC:-600}"
SETTLE_SEC="${SETTLE_SEC:-20}"
CONTAINER="${CONTAINER:-vgu_ros}"
SCENARIO=t2b_flow_ordering
OUT="${OUT:-$REPO/data/logs/vm_runs/t2b_forced_order/$(date -u +%Y%m%d_%H%M%S)}"

log() { printf '[t2b-forced %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

if ! "$PYTHON" "$HARNESS" preflight --repo "$REPO"; then
  echo "REFUSING TO RUN: preflight failed (see PREFLIGHT FAIL lines above)" >&2
  exit 1
fi

settle() {
  local i
  for i in $(seq 1 60); do
    pgrep -f "[i]saac.scripts.run_simulation" >/dev/null 2>&1 || break
    sleep 10
  done
  sleep "$SETTLE_SEC"
}

move() { mv "$1" "$2" 2>/dev/null || sudo mv "$1" "$2"; }

mkdir -p "$OUT"
SCORE_ARGS=()
PLAN="$("$PYTHON" "$HARNESS" plan --tsv --seeds $SEEDS)" || exit 1
while IFS=$'\t' read -r arm seed mock label; do
  [ -z "$arm" ] && continue
  run_dir="$OUT/$label"
  gt="$REPO/data/logs/simulation/${SCENARIO}-seed${seed}-rep000"
  mkdir -p "$run_dir"
  if [ -d "$gt" ]; then
    move "$gt" "$OUT/_rescued_$(basename "$gt")_$(date -u +%s)"
    log "moved a leftover ground-truth dir aside before ${label}"
  fi
  uptime >"$run_dir/uptime_start.txt" 2>&1 || true
  log "=== ${label}: arm=${arm} seed=${seed} mock=${mock} ==="
  SCENARIO="$SCENARIO" SEED="$seed" MOCK_DECISION_FILE="$mock" REC_SEC="$REC_SEC" \
    bash "$REPO/scripts/vm/fc_launch.sh" </dev/null 2>&1 | tee "$run_dir/launcher.log"
  uptime >"$run_dir/uptime_end.txt" 2>&1 || true
  stamp="$(grep -aoE 'fc_run_[0-9]{8}_[0-9]{6}' "$run_dir/launcher.log" | head -1 | sed 's/fc_run_//')"
  if [ -n "$stamp" ]; then
    for f in m5 m4 m1 nav2_r1 nav2_r2 nav2_r3; do
      sudo docker exec "$CONTAINER" bash -lc "cat /tmp/fc_${stamp}_${f}.log" </dev/null \
        >"$run_dir/${f}.log" 2>/dev/null || true
    done
    cp "/tmp/fc_${stamp}_isaac.log" "$run_dir/isaac.log" 2>/dev/null || true
    cp "$REPO/data/logs/fc_run_${stamp}/tail_logs.txt" "$run_dir/" 2>/dev/null || true
    mkdir -p "$run_dir/decisions"
    grep -l "\"run_id\": \"${stamp}\"" "$REPO"/data/logs/m5_decisions/*.json 2>/dev/null \
      | xargs -I{} cp {} "$run_dir/decisions/" 2>/dev/null || true
  fi
  printf 'arm=%s seed=%s mock=%s stamp=%s scenario=%s\n' \
    "$arm" "$seed" "$mock" "${stamp:-none}" "$SCENARIO" >"$run_dir/CONDITION.txt"
  if [ -f "$gt/ground_truth.jsonl" ]; then
    move "$gt" "$run_dir/gt"
    SCORE_ARGS+=(--run "${arm}:${run_dir}/gt")
    log "${label} collected to ${run_dir}"
  else
    echo "NO GT" >"$run_dir/NO_GT"
    log "WARNING: ${label} left no ground truth at ${gt}"
  fi
  settle
done <<<"$PLAN"

if [ "${#SCORE_ARGS[@]}" -eq 0 ]; then
  log "no run left ground truth; nothing to score"
  exit 1
fi
log "scoring -> ${OUT}/margin.json"
"$PYTHON" "$HARNESS" score "${SCORE_ARGS[@]}" --out "$OUT/margin.json"
