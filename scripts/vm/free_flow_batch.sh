#!/usr/bin/env bash
# Run scripts/vm/free_flow_run.sh once per variant, in order, stopping the
# batch at the first run whose RESTORE.txt is not `RESTORE OK` (a dirty config
# would mislabel every later run). Run as root (sudo nohup) from the repo
# root on the VM; the per-run driver keeps every standing VM trap.
#
# Env:
#   VARIANTS   space-separated free-flow variant names (required)
#   OUT_ROOT / REC_SEC / SEED   passed through to free_flow_run.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
VARIANTS="${VARIANTS:?VARIANTS required}"
OUT_ROOT="${OUT_ROOT:-$REPO/data/logs/vm_runs/free_flow}"

log() { printf '[free-flow-batch %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
mkdir -p "$OUT_ROOT"

for variant in $VARIANTS; do
  log "START ${variant}"
  VARIANT="$variant" OUT_ROOT="$OUT_ROOT" bash "$HERE/free_flow_run.sh" \
    >"$OUT_ROOT/${variant}.wrapper.log" 2>&1
  log "END ${variant} rc=$? $(tr '\n' ' ' <"$OUT_ROOT/${variant}/EVIDENCE.txt" 2>/dev/null)"
  if ! grep -q "RESTORE OK" "$OUT_ROOT/${variant}/RESTORE.txt" 2>/dev/null; then
    log "STOPPING: ${variant} did not restore cleanly"
    exit 1
  fi
done
log "BATCH DONE"
