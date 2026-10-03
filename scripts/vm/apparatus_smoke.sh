#!/usr/bin/env bash
# One VM run of the prompt-apparatus smoke (2026-10-04,
# docs/reports/2026-10-04-visual-apparatus.md). Mock backend only, zero API.
#
# Wraps scripts/vm/v2_final_run.sh (every standing VM trap: pristine
# orchestrator/rag md5 gate, the run_simulation-empty wait, verbatim restore
# with fresh mtime + installed-copy md5 check). On top of it, ANNOTATION=1
# switches M1's overlays on for this one run: swarm_perception's
# config/annotation.yaml gets `metric_grid: true` and `motion_trails: true`,
# swarm_perception is rebuilt, and the INSTALLED copy is md5-verified
# against the edited source before launch. On exit the shipped all-off file
# is restored (plain copy + touch), rebuilt, and the installed copy is
# md5-verified against it (ANNOTATION_RESTORE.txt).
#
# Run as root (sudo) from the repo root on the VM.
#
# Env:
#   LABEL       run directory name (required)
#   OVERLAY     v2_overlay.py scene (apparatus_annotation | apparatus_votes)
#   MOCK        repo-relative scripted mock decision file
#   ANNOTATION  1 = M1 grid + trails on for this run (default 0)
#   SNAPSHOTS   passed to v2_final_run.sh (default = ANNOTATION)
#   SCENARIO    default head_on_asymmetric_w0p2_eopen_bshort_o0
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../.." && pwd)}"
CONTAINER="${CONTAINER:-vgu_ros}"
LABEL="${LABEL:?LABEL required}"
OVERLAY="${OVERLAY:?OVERLAY required}"
MOCK="${MOCK:-}"
ANNOTATION="${ANNOTATION:-0}"
SNAPSHOTS="${SNAPSHOTS:-$ANNOTATION}"
SCENARIO="${SCENARIO:-head_on_asymmetric_w0p2_eopen_bshort_o0}"
OUT_ROOT="$REPO/data/logs/vm_runs/apparatus_smoke"
OUT="$OUT_ROOT/$LABEL"
ANN="$REPO/ros2_ws/src/swarm_perception/config/annotation.yaml"
ANN_INSTALLED=/ws/ros2_ws/install/share/swarm_perception/config/annotation.yaml
BACKUP="/tmp/apparatus_smoke_annotation_${LABEL}.yaml"

log() { printf '[apparatus-smoke %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
md5_of() { md5sum "$1" 2>/dev/null | awk '{print $1}'; }
installed_md5() { docker exec "$CONTAINER" md5sum "$ANN_INSTALLED" 2>/dev/null | awk '{print $1}'; }
build_perception() {
  docker exec -w /ws "$CONTAINER" bash -lc \
    "source /opt/ros/jazzy/setup.bash && cd ros2_ws && colcon build --merge-install --packages-select swarm_perception" \
    >"$1" 2>&1
}

mkdir -p "$OUT"
SHIPPED_MD5="$(md5_of "$ANN")"
if grep -qE '^  (metric_grid|motion_trails): true' "$ANN"; then
  log "REFUSING: annotation.yaml is not the shipped all-off file"
  exit 1
fi

restore_annotation() {
  set +e
  if [ "$ANNOTATION" = "1" ] && [ -f "$BACKUP" ]; then
    cp "$BACKUP" "$ANN" && touch "$ANN"
    build_perception "$OUT/annotation_restore_build.log"
  fi
  local src inst
  src="$(md5_of "$ANN")"
  inst="$(installed_md5)"
  {
    echo "annotation.yaml src=${src} installed=${inst} (shipped ${SHIPPED_MD5})"
    if [ "$src" = "$SHIPPED_MD5" ] && [ "$inst" = "$SHIPPED_MD5" ]; then
      echo "ANNOTATION RESTORE OK"
    else
      echo "ANNOTATION RESTORE FAILED -- fix by hand before any other run"
    fi
  } | tee "$OUT/ANNOTATION_RESTORE.txt"
}
trap restore_annotation EXIT

if [ "$ANNOTATION" = "1" ]; then
  cp -p "$ANN" "$BACKUP"
  sed -i -E 's/^  (metric_grid|motion_trails): false$/  \1: true/' "$ANN"
  touch "$ANN"
  build_perception "$OUT/annotation_on_build.log"
  if [ "$(installed_md5)" != "$(md5_of "$ANN")" ] || ! grep -qE '^  metric_grid: true' "$ANN"; then
    log "ERROR: installed annotation.yaml does not match the flags-on source; refusing to launch"
    exit 1
  fi
  cp "$ANN" "$OUT/annotation.on.yaml"
  log "M1 overlays ON (installed md5 $(installed_md5))"
fi

LABEL="$LABEL" SCENARIO="$SCENARIO" OVERLAY="$OVERLAY" MOCK="$MOCK" OUT_ROOT="$OUT_ROOT" \
  SNAPSHOTS="$SNAPSHOTS" bash "$HERE/v2_final_run.sh"
log "v2_final_run exited rc=$?"
