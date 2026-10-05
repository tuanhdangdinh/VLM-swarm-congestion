#!/usr/bin/env bash
# One VM run of the follow_waypoints validation
# (docs/reports/2026-10-05-follow-waypoints-validation.md). Wraps
# scripts/vm/v2_final_run.sh, which owns every standing VM trap (pgrep-empty
# gate, pristine-config refusal, verbatim restore + rebuild + installed-md5
# check, `logs saved to` gate, mock-only backend), and adds the
# scripts/vm/waypoint_probe.py helper inside the container once Nav2 is live:
# one manual M5 analysis trigger at TRIGGER_X (the blocker-free map gives the
# progress detector nothing to fire on) plus full-rate command-chain
# recording. TRIGGER_X=none records only.
#
# Run as root (sudo) from the repo root on the VM.
#
# Env (on top of v2_final_run.sh's own):
#   LABEL, SCENARIO, OVERLAY, MOCK, SEED, REC_SEC, SIM_SEC  as v2_final_run.sh
#   TRIGGER_X   M1 x at which to trigger, or "none" (default -1.0)
#   PROBE       1 = run the probe (default 1)
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
CONTAINER="${CONTAINER:-vgu_ros}"
LABEL="${LABEL:?LABEL required}"
TRIGGER_X="${TRIGGER_X:--1.0}"
PROBE="${PROBE:-1}"
REC_SEC="${REC_SEC:-900}"
OUT_ROOT="${OUT_ROOT:-$REPO/data/logs/vm_runs/waypoints_validation}"
OUT="$OUT_ROOT/$LABEL"
PROBE_TMP="/tmp/waypoint_probe_${LABEL}.jsonl"

log() { printf '[wp-validate %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

mkdir -p "$OUT"
OUT_ROOT="$OUT_ROOT" REC_SEC="$REC_SEC" bash "$HERE/v2_final_run.sh" &
RUN_PID=$!

if [ "$PROBE" = "1" ]; then
  for _ in $(seq 1 240); do
    grep -q "Nav2 action servers live" "$OUT/launcher.log" 2>/dev/null && break
    kill -0 "$RUN_PID" 2>/dev/null || break
    sleep 3
  done
  if grep -q "Nav2 action servers live" "$OUT/launcher.log" 2>/dev/null; then
    docker exec "$CONTAINER" rm -f "$PROBE_TMP"
    docker cp "$HERE/waypoint_probe.py" "$CONTAINER":/tmp/waypoint_probe.py
    docker exec -w /ws "$CONTAINER" bash -lc \
      "source /opt/ros/jazzy/setup.bash && source /ws/ros2_ws/install/setup.bash && export FASTRTPS_DEFAULT_PROFILES_FILE=/ws/config/dds/fastdds.xml && python3 /tmp/waypoint_probe.py ${PROBE_TMP} $((REC_SEC - 30)) ${TRIGGER_X} robot_1" \
      >"$OUT/probe_stderr.log" 2>&1 &
    log "probe started (TRIGGER_X=${TRIGGER_X})"
  else
    log "WARNING: Nav2 readiness not seen; no probe"
  fi
fi

wait "$RUN_PID"
log "v2_final_run exited rc=$?"
if [ "$PROBE" = "1" ]; then
  docker cp "$CONTAINER":"$PROBE_TMP" "$OUT/probe.jsonl" 2>/dev/null \
    && log "probe output copied ($(wc -l <"$OUT/probe.jsonl") rows)" \
    || log "WARNING: no probe output"
fi
printf 'trigger_x=%s probe=%s\n' "$TRIGGER_X" "$PROBE" >>"$OUT/CONDITION.txt"
chown -R ubuntu:ubuntu "$OUT" 2>/dev/null || true
log "done: $OUT"
