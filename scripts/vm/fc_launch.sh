#!/usr/bin/env bash
# Scenario-parametrised closed-loop launch for the head_on_asymmetric family
# (and any other isaac/config/scenarios/*.yaml scenario).
#
# Ported from scripts/run_gemini_er2_demo.sh (feat/gemini-er2-backend, 265
# lines), itself derived from /home/ubuntu/fc_record_launch.sh (the run-H
# recipe behind the live gemini_20260918_084649 run). Same six-stage bring-up
# order (Isaac -> topics -> M1 -> Nav2 per robot -> M4 -> M5), `localization:=camera`,
# `-w /ws` on every `docker exec`, the OpenAI key sourced inside the
# container (never interpolated into a docker-exec argv), per-run logs
# collected on exit, and the reasoning_backend_id rewrite-then-restore
# mechanism (with `trap cleanup EXIT` + `trap 'exit 130' INT TERM HUP` so a
# Ctrl-C or dropped SSH still restores it).
#
# Generalized here for the family work:
#   - SCENARIO selects the Isaac scenario yaml and Nav2 map (instead of the
#     hardcoded head_on_deadlock scenario/map).
#   - Nav2 spawn poses are read from the scenario yaml (instead of hardcoded
#     x:=-1.5 / x:=1.5), and every stage that is per robot loops over the
#     scenario's robots in robot-number order: the spawn parse, the Isaac
#     odom/scan waits, one Nav2 stack each (the first one starts the shared
#     map server), the action-server waits and the Nav2 log collection. A
#     two-robot scenario runs exactly the commands the old fixed robot_1 /
#     robot_2 stages ran (tests/unit/test_fc_launch_dry_run.py pins the
#     DRY_RUN output against goldens recorded before the loop).
#   - MOCK_DECISION_FILE forces the mock reasoning backend and makes it
#     replay a scripted decision, for forced-mock runs that prove the
#     family's frozen `oracle:` block against both yielder orders.
#   - RECORD=0|1 gates the recorder stage. The ported script always
#     recorded; this script defaults to not recording so the family's mock
#     runs (short, high-volume) don't pay the recorder's overhead.
#   - DRY_RUN=1 prints every external command (docker/sudo/Isaac/sleep)
#     instead of running it, so the script can be sanity-checked without a
#     VM. Scenario-yaml parsing still actually runs in DRY_RUN, using the
#     host python3 directly instead of going through docker_ros (which
#     needs a live container), so the printed commands carry real values.
#   - Isaac stop flag (2026-10-07 shutdown-timing ruling): Kit catches and
#     swallows SIGTERM, so cleanup's pkill never stopped an aborted run's
#     Isaac — it re-parented to PID 1 and simulated its full horizon (trap
#     16). Isaac now gets a per-run flag path (VGU_ISAAC_STOP_FLAG); the
#     runner polls it in its loops and, once it exists, exits normally (GT
#     closed, manifest written with completed=false + aborted=true, ~1 s
#     close()). Cleanup touches it ONLY on an abort (exit before stage 9
#     finished); a normal exit — including the REC_SEC cap firing while a
#     4-robot Isaac still runs — leaves Isaac to finish its horizon exactly
#     as before. SIGINT is deliberately not used: SimulationApp's handler
#     skips the manifest write. The pkill stays as defense in depth, and so
#     must every caller's `pgrep -f run_simulation` EMPTY relaunch gate.
#   - MODALITY guard (final whole-branch review, Finding 2): unlike
#     reasoning_backend_id above, this script never sets prompt_static_obstacles
#     itself — an operator flips it by hand in orchestrator.yaml before an ON
#     run. A snapshot/restore mirroring the backend-id mechanism cannot catch
#     an ON run that aborts before the operator clears the flag by hand
#     (Ctrl-C, dropped SSH, crash): the script would only know what IT set,
#     not that the flag was already dirty on entry. So instead this script
#     refuses to start whenever prompt_static_obstacles is already true in
#     ORCH_CONFIG unless MODALITY=on confirms that is intended (and the
#     reverse: MODALITY=on with the flag not true is also refused), and it
#     always prints the modality state it found — so a labelled OFF run is
#     never silently an ON run, and every run's log records the condition.
#
# Usage:
#   ./fc_launch.sh
#   SCENARIO=head_on_asymmetric_w0p2_eopen_o0 ./fc_launch.sh
#   MOCK_DECISION_FILE=config/mock_decisions/head_on_yield.json ./fc_launch.sh
#   RECORD=1 REC_SEC=300 ./fc_launch.sh
#   DRY_RUN=1 SCENARIO=head_on_deadlock ./fc_launch.sh
#   MODALITY=on ./fc_launch.sh   # confirms prompt_static_obstacles: true is intended
#
# Env vars:
#   SCENARIO              Scenario name (default head_on_deadlock). Resolved
#                          as isaac/config/scenarios/$SCENARIO.yaml (legacy),
#                          else isaac/config/scenarios/family/$SCENARIO.yaml
#                          (generated), else isaac/config/scenarios/free_flow/
#                          $SCENARIO.yaml (generated solo free-flow variants),
#                          else this script exits 1 naming every path tried.
#                          MAP is derived as
#                          warehouse_map_${MAP_SCENARIO:-$SCENARIO}.yaml (a
#                          free-flow variant passes its parent cell as
#                          MAP_SCENARIO) and is checked to
#                          exist inside the container before Isaac Sim
#                          starts (stage 2), not just before Nav2 — a
#                          missing/misnamed map should fail in about a
#                          second, not after minutes of GPU bring-up.
#   BACKEND_ID             Reasoning backend (default openai). Forced to
#                          "mock" whenever MOCK_DECISION_FILE is set (see
#                          below) — VGU_MOCK_DECISION_FILE is only consulted
#                          by the backend factory when reasoning_backend_id
#                          is "mock". Switched the same way the ported
#                          script switches backends: by rewriting
#                          reasoning_backend_id in
#                          ros2_ws/src/swarm_orchestrator/config/
#                          orchestrator.yaml, rebuilding swarm_orchestrator
#                          so the *installed* copy matches, and restoring the
#                          original value (and rebuilding again) on exit.
#   MOCK_DECISION_FILE     Optional path to a scripted VLM decision JSON,
#                          e.g. config/mock_decisions/head_on_yield.json.
#                          Give it repo-relative (M5 runs with cwd /ws
#                          inside the container, so a repo-relative path
#                          resolves correctly there) or as an absolute host
#                          path under $REPO. Exported into M5's launch
#                          environment as VGU_MOCK_DECISION_FILE — the exact
#                          variable reasoning/vlm/backend_factory.py's
#                          build_backend() reads for backend_id == "mock"
#                          (see that function's docstring: unset/empty keeps
#                          MockBackend's default no-congestion answer).
#   MOCK_ECHO              1 selects the echo mock (prereg-v3 A12(i),
#                          APPARATUS ONLY, never a scored arm): each
#                          decision names the prompt's stalled robots so M3
#                          grounding runs without an API. Forces BACKEND_ID
#                          to "mock" like MOCK_DECISION_FILE, and refuses to
#                          start with it set too. Exported as VGU_MOCK_ECHO;
#                          MOCK_ECHO_TYPE / MOCK_ECHO_STRATEGY (default
#                          deadlock / yield) as VGU_MOCK_ECHO_TYPE /
#                          VGU_MOCK_ECHO_STRATEGY. Artifacts carry
#                          diagnostics.mock_mode = "echo".
#   MOCK_RETREAT_CHOICE_FILE
#                          Optional stage-2 mock script, e.g.
#                          config/mock_decisions/retreat_choice_b.json,
#                          path rules as MOCK_DECISION_FILE. Exported as
#                          VGU_MOCK_RETREAT_CHOICE_FILE, which the mock
#                          backend reads for the stage-2 retreat letter
#                          (reasoning/vlm/backend_factory.py). Unset leaves
#                          it unset, so a mock run's stage 2 is skipped and
#                          recorded as skip_reason=no_backend.
#   RECORD                 0|1 (default 0). 1 enables the recorder stage
#                          (annotated_frame -> REC_OUT) exactly as in the
#                          ported script; 0 skips it entirely.
#   REC_SEC / SIM_SEC       Recording / Isaac duration seconds (default
#                          1000 / 1200). REC_SEC also CAPS how long stage 9
#                          tails the M5 log, independent of RECORD: the tail
#                          ends ISAAC_EXIT_GRACE_SEC after the Isaac process
#                          exits, or at REC_SEC - 10 s, whichever is first
#                          (Option B, 2026-10-07 shutdown-timing ruling; the
#                          fixed tail used to idle ~238 s after a head-on
#                          Isaac had exited). SIM_SEC is inert: the runner
#                          never reads --duration-sec; the scenario yaml's
#                          duration_sec sets Isaac's lifetime.
#   ISAAC_EXIT_GRACE_SEC   Seconds the M5 tail keeps running after Isaac
#                          exits (default 10), so M5 writes in flight at that
#                          moment can land before cleanup restarts the
#                          container.
#   ISAAC_STOP_WAIT_SEC    Abort path only: how long cleanup waits for Isaac
#                          to honor its stop flag before the (defense-in-
#                          depth) pkill (default 60).
#   NAV2_ACTIVE_TIMEOUT_SEC
#                          Nav2 lifecycle-gate budget in seconds (default
#                          240, sized on <= 4 stacks). Raise for 5-stack
#                          scenarios (S1 run line: 360).
#   NAV2_LAUNCH_STAGGER_SEC
#                          Settle sleep before each Nav2 stack after the
#                          first (default 3, the pre-loop fixed value; the
#                          two-robot goldens pin it). Env-overridable for
#                          long 5-stack bring-ups. Parallel mode only.
#   NAV2_BRINGUP_MODE      parallel|sequential (default parallel, the
#                          behavior every run before 2026-10-11 used).
#                          sequential (prereg-v3 A23 infra wave, a HARNESS
#                          change: no Nav2 or lifecycle parameter changes)
#                          launches stack k+1 only once stack k's
#                          lifecycle_manager_navigation reports "Managed
#                          nodes are active" in its OWN log. Parallel
#                          bring-up aborted 9/16 five-stack launches at
#                          stagger 6: every abort hit a stack whose
#                          activation/configure overlapped another stack's
#                          startup (bond window = bond_timeout/2 = 2 s,
#                          get_state's hard-coded 2 s timeout), and a stack
#                          brought up alone takes ~6-11 s, so sequential
#                          costs about what parallel does. After the loop a
#                          health gate also requires every stack's LAST
#                          active line to follow any "CRITICAL FAILURE"
#                          (bond heartbeat loss) line, waiting up to
#                          NAV2_HEALTH_GRACE_SEC for a respawn re-activation.
#   NAV2_STACK_ACTIVE_TIMEOUT_SEC
#                          Sequential mode: per-stack budget from its launch
#                          to active (default 180; 120 until prereg-v3 A32,
#                          owner ruling R3 2026-10-21, after E24/E25 aborted
#                          at 120 s on the asia-northeast1-a host).
#   NAV2_HEALTH_GRACE_SEC  Sequential mode: how long the post-loop health
#                          gate waits for a stack that went down after
#                          activation to come back (default 45).
#   BRINGUP_ONLY           1 = bring-up validation: skip the backend rewrite
#                          (orchestrator.yaml is never touched), run Isaac,
#                          M1 and every Nav2 stack through the lifecycle
#                          gates, hold BRINGUP_HOLD_SEC (default 0), re-run
#                          the health check, log "BRINGUP_ONLY PASS" and
#                          exit 0 through the abort cleanup (Isaac stop
#                          flag). M4/M5 never start, so no API is called.
#   REC_STOP_WAIT_SEC      RECORD=1 only: how long stage 10 waits for the
#                          recorder to exit after its SIGTERM stop request,
#                          i.e. for the mp4 trailer to be written, before
#                          cleanup's container restart (default 30).
#   SEED                   Isaac --seed (default 42, the value every run so far
#                          used). Also names the ground-truth directory
#                          (data/logs/simulation/<scenario>-seed<SEED>-rep000).
#   DRY_RUN                 1 prints every external command instead of
#                          executing it (see above).
#   MODALITY               on|<unset> (default unset). Confirms an ON run of
#                          the static-obstacle prompt modality: required when
#                          prompt_static_obstacles: true is already set in
#                          ORCH_CONFIG (the script never sets this flag
#                          itself; the operator does, by hand), and refused
#                          when it is NOT set but prompt_static_obstacles is
#                          not true. Either mismatch aborts before anything
#                          expensive starts (see the MODALITY guard note
#                          above). The resolved state is always printed.
#
# Recorder fps re-timing caveat (unchanged from the ported script — read
# before using RECORD=1 recordings): the recorder stamps a higher fps than
# it achieves under load, so raw playback runs fast; achieved fps only
# becomes known from the recorder's own exit line, hence this is not
# automated. Post-processing:
#   1. If --segment-frames split the output into annotated_000.mp4,
#      annotated_001.mp4, ..., concat them losslessly first:
#        ffmpeg -f concat -safe 0 \
#          -i <(for f in annotated_*.mp4; do echo "file '$PWD/$f'"; done) \
#          -c copy annotated_concat.mp4
#   2. Grep the recorder log for its exit line: `WROTE ... frames=<F>
#      secs=<S>` -> achieved_fps = F / S. The stamped fps is printed by this
#      script as "stamping fps=<FPS>" before the recorder starts.
#      ratio = stamped_fps / achieved_fps
#   3. Re-time so wall-clock playback matches real elapsed time:
#        ffmpeg -i annotated_concat.mp4 -vf "setpts=<ratio>*PTS" \
#          -r <achieved_fps> annotated_retimed.mp4
set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
CONTAINER="${CONTAINER:-vgu_ros}"
SCENARIO="${SCENARIO:-head_on_deadlock}"
BACKEND_ID="${BACKEND_ID:-openai}"
MOCK_DECISION_FILE="${MOCK_DECISION_FILE:-}"
MOCK_RETREAT_CHOICE_FILE="${MOCK_RETREAT_CHOICE_FILE:-}"
MOCK_ECHO="${MOCK_ECHO:-}"
MOCK_ECHO_TYPE="${MOCK_ECHO_TYPE:-}"
MOCK_ECHO_STRATEGY="${MOCK_ECHO_STRATEGY:-}"
MODALITY="${MODALITY:-}"
RECORD="${RECORD:-0}"
REC_SEC="${REC_SEC:-1000}"
SIM_SEC="${SIM_SEC:-1200}"
SEED="${SEED:-42}"
ISAAC_EXIT_GRACE_SEC="${ISAAC_EXIT_GRACE_SEC:-10}"
ISAAC_STOP_WAIT_SEC="${ISAAC_STOP_WAIT_SEC:-60}"
REC_STOP_WAIT_SEC="${REC_STOP_WAIT_SEC:-30}"
ISAAC_POLL_SEC=2
BRINGUP_ONLY="${BRINGUP_ONLY:-0}"
BRINGUP_HOLD_SEC="${BRINGUP_HOLD_SEC:-0}"
case "${NAV2_BRINGUP_MODE:-parallel}" in
  parallel|sequential) ;;
  *) echo "ERROR: NAV2_BRINGUP_MODE='${NAV2_BRINGUP_MODE}' is not parallel|sequential" >&2; exit 2 ;;
esac
STAMP=$(date -u +%Y%m%d_%H%M%S)

# Sourced from this script's own directory, not $REPO: tests point REPO at a
# scratch tree that has no scripts/.
# shellcheck source=scripts/vm/isaac_lifecycle.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/isaac_lifecycle.sh"

# MOCK_DECISION_FILE only takes effect via the "mock" backend, so setting it
# selects that backend regardless of BACKEND_ID's default/inherited value.
if [ -n "$MOCK_DECISION_FILE" ]; then
  BACKEND_ID=mock
fi
# Same for the echo mock; the backend factory refuses both at once, so fail
# here before any GPU bring-up instead of when M5 starts.
if [ -n "$MOCK_ECHO" ] && [ "$MOCK_ECHO" != "0" ]; then
  if [ -n "$MOCK_DECISION_FILE" ]; then
    echo "MOCK_ECHO and MOCK_DECISION_FILE are mutually exclusive" >&2
    exit 2
  fi
  BACKEND_ID=mock
fi

log() { printf '[fc-launch %s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

# Executes a plain argv command normally, or just logs it under DRY_RUN.
# Only for commands with no shell operators (redirection, &&, backgrounding)
# — those get their own DRY_RUN branch below since "$@" can't carry them.
xrun() {
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY_RUN] $*"
  else
    "$@"
  fi
}

# Same as xrun, but tolerates a non-zero exit (pkill/chown return non-zero
# when there's nothing to act on, which under `set -e` would otherwise abort
# a clean run — mirrors the ported script's own `... 2>/dev/null || true`
# guards on these exact commands).
xrun_soft() {
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY_RUN] $*"
  else
    "$@" 2>/dev/null || true
  fi
}

# ── Resolve SCENARIO -> scenario yaml (legacy, then family) + MAP ──────────
SCENARIO_YAML_LEGACY="$REPO/isaac/config/scenarios/${SCENARIO}.yaml"
SCENARIO_YAML_FAMILY="$REPO/isaac/config/scenarios/family/${SCENARIO}.yaml"
SCENARIO_YAML_FREE_FLOW="$REPO/isaac/config/scenarios/free_flow/${SCENARIO}.yaml"
if [ -f "$SCENARIO_YAML_LEGACY" ]; then
  SCENARIO_YAML_HOST="$SCENARIO_YAML_LEGACY"
elif [ -f "$SCENARIO_YAML_FAMILY" ]; then
  SCENARIO_YAML_HOST="$SCENARIO_YAML_FAMILY"
elif [ -f "$SCENARIO_YAML_FREE_FLOW" ]; then
  SCENARIO_YAML_HOST="$SCENARIO_YAML_FREE_FLOW"
else
  echo "ERROR: scenario '${SCENARIO}' not found; tried:" >&2
  echo "  ${SCENARIO_YAML_LEGACY}" >&2
  echo "  ${SCENARIO_YAML_FAMILY}" >&2
  echo "  ${SCENARIO_YAML_FREE_FLOW}" >&2
  exit 1
fi
# Container-side path for parsing the yaml inside the container (real runs):
# $REPO is bind-mounted at /ws in $CONTAINER regardless of its host path.
SCENARIO_YAML_CONTAINER="/ws${SCENARIO_YAML_HOST#"$REPO"}"

# A solo free-flow variant reuses its parent cell's map, whose grid it equals
# byte for byte (tests/unit/test_free_flow_variants.py): no variant map is
# installed.
MAP_SCENARIO="${MAP_SCENARIO:-$SCENARIO}"
MAP="/ws/ros2_ws/install/share/swarm_simulation/maps/warehouse_map_${MAP_SCENARIO}.yaml"

# MOCK_DECISION_FILE -> the path M5 (cwd /ws inside the container) should
# read. A repo-relative path is passed through unchanged (it already
# resolves under /ws); a host path under $REPO is rewritten to its /ws
# equivalent.
MOCK_DECISION_FILE_CONTAINER=""
if [ -n "$MOCK_DECISION_FILE" ]; then
  case "$MOCK_DECISION_FILE" in
    "$REPO"/*) MOCK_DECISION_FILE_CONTAINER="/ws${MOCK_DECISION_FILE#"$REPO"}" ;;
    *) MOCK_DECISION_FILE_CONTAINER="$MOCK_DECISION_FILE" ;;
  esac
fi

MOCK_RETREAT_CHOICE_FILE_CONTAINER=""
if [ -n "$MOCK_RETREAT_CHOICE_FILE" ]; then
  case "$MOCK_RETREAT_CHOICE_FILE" in
    "$REPO"/*) MOCK_RETREAT_CHOICE_FILE_CONTAINER="/ws${MOCK_RETREAT_CHOICE_FILE#"$REPO"}" ;;
    *) MOCK_RETREAT_CHOICE_FILE_CONTAINER="$MOCK_RETREAT_CHOICE_FILE" ;;
  esac
fi

ORCH_CONFIG="${REPO}/ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"

# ── Guard: an ON prompt_static_obstacles left set by an aborted prior run
#    must not silently mislabel this run (final whole-branch review,
#    Finding 2). Unlike BACKEND_ID below, this script never sets
#    prompt_static_obstacles itself — the operator flips it by hand in
#    ORCH_CONFIG before an intentional ON run — so a snapshot/restore
#    mirroring the BACKEND_ID mechanism cannot catch this: the script would
#    only know what IT set, not that the flag was already dirty on entry.
#    Instead, refuse to start on a mismatch between the installed flag and
#    the operator's declared intent (MODALITY=on). Pure host-file read, no
#    docker/sudo involved, so this holds under DRY_RUN too, and it runs
#    before `trap cleanup EXIT` is installed below so a refusal here is a
#    plain exit — it never restarts the container or touches the log dirs. ──
if [ -n "$MODALITY" ] && [ "$MODALITY" != "on" ]; then
  echo "ERROR: MODALITY='${MODALITY}' is not recognized; the only accepted" >&2
  echo "  value is 'on' (confirms an intentional ON run). Leave it unset for" >&2
  echo "  an OFF run." >&2
  exit 1
fi
OBSTACLE_MODALITY=$(grep -m1 '^prompt_static_obstacles:' "$ORCH_CONFIG" | awk '{print $2}' || true)
if [ -z "$OBSTACLE_MODALITY" ]; then
  echo "ERROR: could not read prompt_static_obstacles from ${ORCH_CONFIG}" >&2
  exit 1
fi
if [ "$OBSTACLE_MODALITY" = "true" ] && [ "$MODALITY" != "on" ]; then
  echo "ERROR: prompt_static_obstacles: true is already set in ${ORCH_CONFIG}." >&2
  echo "  A prior ON run likely aborted (Ctrl-C, dropped SSH, crash) before the" >&2
  echo "  operator restored it by hand. Confirm an intentional ON run with" >&2
  echo "  MODALITY=on, or clear the flag first:" >&2
  echo "    sed -i 's/^prompt_static_obstacles: .*/prompt_static_obstacles: false/' ${ORCH_CONFIG}" >&2
  exit 1
fi
if [ "$OBSTACLE_MODALITY" != "true" ] && [ "$MODALITY" = "on" ]; then
  echo "ERROR: MODALITY=on was requested but prompt_static_obstacles is not true" >&2
  echo "  in ${ORCH_CONFIG}. Set prompt_static_obstacles: true there first, or drop" >&2
  echo "  MODALITY=on for an OFF run." >&2
  exit 1
fi
log "obstacle modality: prompt_static_obstacles=${OBSTACLE_MODALITY} (MODALITY=${MODALITY:-<unset>})"

ISAAC_LOG=/tmp/fc_${STAMP}_isaac.log
# Host path (Isaac runs on the host, not in the container). Touched by
# cleanup on an abort only; see the stop-flag note in the header.
ISAAC_STOP_FLAG=/tmp/fc_${STAMP}_isaac.stop
# The `sudo` wrapper's PID ($! of the launch): python.sh runs Kit's python as
# a child (no exec), so the wrapper lives exactly as long as Isaac does.
ISAAC_PID=""
# 1 once stage 9 (the M5 tail) has finished; cleanup reads an exit before
# that as an abort. Not the exit status: every normal cycle exits 141 (the
# stage-11 `ls | head` SIGPIPE under pipefail).
TAIL_STAGE_DONE=0
ISAAC_STOP_REQUESTED=0
M1_LOG=/tmp/fc_${STAMP}_m1.log
# One Nav2 log per robot, named by robot number (robot_3 -> nav2_r3); filled
# in once the scenario's robots are parsed (stage 2).
NAV2_LOGS=""
nav2_log_of() { printf '/tmp/fc_%s_nav2_r%s.log' "$STAMP" "${1#robot_}"; }
M4_LOG=/tmp/fc_${STAMP}_m4.log
M5_LOG=/tmp/fc_${STAMP}_m5.log
REC_LOG=/tmp/fc_${STAMP}_rec.log
BUILD_LOG=/tmp/fc_${STAMP}_build.log
REC_DIR_HOST="${REPO}/data/logs/fc_run_${STAMP}"
REC_DIR_WS=/ws/data/logs/fc_run_${STAMP}
REC_OUT="${REC_DIR_WS}/annotated.mp4"
TAIL_LOG="${REC_DIR_HOST}/tail_logs.txt"

ROS_SETUP='source /opt/ros/jazzy/setup.bash && source /ws/ros2_ws/install/setup.bash && export FASTRTPS_DEFAULT_PROFILES_FILE=/ws/config/dds/fastdds.xml && export PYTHONPATH=/ws:${PYTHONPATH:-}'

# Reads robot_id/spawn.x/spawn.y/spawn.yaw_rad from the scenario yaml, one
# line per robot in robot-number order (robot_1 first: it starts the map
# server, as the fixed two-robot stages did). Single source of truth for both
# the DRY_RUN (host python3) and real (parsed inside the container, which is
# guaranteed to have pyyaml) paths.
SPAWN_PARSE_PY_SRC=$(cat <<'PY'
import sys
import yaml

data = yaml.safe_load(open(sys.argv[1]))
robots = sorted(data["robots"], key=lambda robot: int(robot["robot_id"].split("_")[1]))
for robot in robots:
    spawn = robot["spawn"]
    print(robot["robot_id"], spawn["x"], spawn["y"], spawn["yaw_rad"])
PY
)

docker_ros() {
  if [ "$DRY_RUN" = "1" ]; then
    # >&2: docker_ros is captured via $(...) at one call site (the recorder's
    # HZ measurement) — a stdout log line here would land IN that variable.
    log "[DRY_RUN] docker exec -w /ws ${CONTAINER} bash -lc \"\$ROS_SETUP && $*\"" >&2
    return 0
  fi
  sudo docker exec -w /ws "$CONTAINER" bash -lc "$ROS_SETUP && $*"
}

# Backgrounded (`docker exec -d`) launch of one component. $1 = its log path
# (display only), $2 = the inner command (already includes its own
# redirection to that log).
docker_exec_bg() {
  local inner="$2"
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY_RUN] docker exec -d -w /ws ${CONTAINER} bash -lc \"\$ROS_SETUP && ${inner}\""
    return 0
  fi
  sudo docker exec -d -w /ws "$CONTAINER" bash -lc "$ROS_SETUP && ${inner}"
}

# The recorder's python process only: anchored, so the `bash -lc` wrapper
# whose -c string also names the script is never signalled (the recorder must
# finish its own release(), not lose its parent mid-write). Matched from the
# host, where the container's processes are visible, as cleanup's pkill is.
REC_PROC_RE='^python3 /ws/scripts/[r]ecord_topic_video\.py'

# Asks the recorder to stop and waits, bounded, for it to exit. SIGTERM is
# its own stop request (record_topic_video.py main(): the loop ends and
# finish() writes the mp4 trailer, the same path its duration cap takes), as
# the S6 first-light driver's sidecar sent it (2026-10-08: "stop requested
# signal=15", then WROTE). Never fails the launch: a recorder that does not
# exit in time is left to cleanup's container restart, with a warning.
stop_recorder_cleanly() {
  local waited=0
  if ! sudo pkill -TERM -f "$REC_PROC_RE" 2>/dev/null; then
    log "recorder already exited; nothing to stop"
    return 0
  fi
  log "recorder stop requested (SIGTERM); waiting <= ${REC_STOP_WAIT_SEC}s for ${REC_OUT} to finalize"
  while sudo pgrep -f "$REC_PROC_RE" >/dev/null 2>&1; do
    if [ "$waited" -ge "$REC_STOP_WAIT_SEC" ]; then
      log "WARNING: recorder still running ${REC_STOP_WAIT_SEC}s after SIGTERM; cleanup's container restart will kill it and its open segment may be lost"
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  log "recorder exited ${waited}s after SIGTERM (mp4 finalized)"
}

parse_spawn_poses() {
  if [ "$DRY_RUN" = "1" ]; then
    printf '%s\n' "$SPAWN_PARSE_PY_SRC" | python3 - "$SCENARIO_YAML_HOST"
  else
    local b64
    b64=$(printf '%s' "$SPAWN_PARSE_PY_SRC" | base64 | tr -d '\n')
    docker_ros "echo ${b64} | base64 -d | python3 - '${SCENARIO_YAML_CONTAINER}'"
  fi
}

check_map_exists() {
  if ! docker_ros "test -f '${MAP}'"; then
    echo "ERROR: map not found inside container: ${MAP}" >&2
    exit 1
  fi
}

wait_topic() {
  local topic="$1" timeout="${2:-120}"
  log "waiting for publisher: ${topic}"
  docker_ros "timeout ${timeout}s bash -lc 'until ros2 topic list 2>/dev/null | grep -qx ${topic}; do sleep 1; done'"
}

wait_action() {
  local action="$1" timeout="${2:-150}"
  log "waiting for action server: ${action}"
  docker_ros "timeout ${timeout}s bash -lc 'until ros2 action list 2>/dev/null | grep -qx ${action}; do sleep 1; done'"
}

# Nav2 lifecycle gate. The action-list wait above passes once each stack's
# servers are registered, not once its lifecycle manager has activated them:
# with four stacks one bring-up in three failed behind it (intersection smoke
# 2026-09-29: robot_3 "Aborting bringup" with every goal rejected, IB2; robot_3
# active ~80 s and robot_4 >90 s after launch while M5 was already dispatching,
# IB7), and a two-robot stack once never went active at all (CE2, bshort
# gpt-4o batch). Wait until every robot's lifecycle_manager_navigation has
# logged "Managed nodes are active", so M5 only ever dispatches to active
# stacks and the robots depart together; an "Aborting bringup" in any stack,
# or the budget running out, aborts the launch with NAV2_BRINGUP_FAILED (the
# EXIT trap then restores the backend and restarts the container).
NAV2_ACTIVE_RE='lifecycle_manager_navigation\]: .*Managed nodes are active'
NAV2_ABORT_RE='Aborting bringup'
NAV2_ACTIVE_TIMEOUT_SEC="${NAV2_ACTIVE_TIMEOUT_SEC:-240}"
# Per-stack settle before every Nav2 launch after the first; 3 is the value
# the fixed two-robot stages always used (goldens pin `sleep 3`).
NAV2_LAUNCH_STAGGER_SEC="${NAV2_LAUNCH_STAGGER_SEC:-3}"
NAV2_BRINGUP_MODE="${NAV2_BRINGUP_MODE:-parallel}"
NAV2_STACK_ACTIVE_TIMEOUT_SEC="${NAV2_STACK_ACTIVE_TIMEOUT_SEC:-180}"
NAV2_HEALTH_GRACE_SEC="${NAV2_HEALTH_GRACE_SEC:-45}"
# One stack's lifecycle state from its own log: aborted (any "Aborting
# bringup"), active (last active line after the last bond-heartbeat CRITICAL
# FAILURE), down (went active, then lost a server and has not re-activated),
# pending (not active yet, or no log yet).
NAV2_STATE_AWK='/Aborting bringup/ {ab = 1}
/lifecycle_manager_navigation\]: .*Managed nodes are active/ {a = NR}
/CRITICAL FAILURE/ {c = NR}
END {
  if (ab) print "aborted"
  else if (a && a > c) print "active"
  else if (a) print "down"
  else print "pending"
}'

nav2_stack_state() {
  local state
  state="$(sudo docker exec "$CONTAINER" awk "$NAV2_STATE_AWK" "$1" 2>/dev/null || true)"
  printf '%s\n' "${state:-pending}"
}

# Sequential mode: blocks until one stack (robot $1, log $2) is active in its
# own log, failing the launch on an abort or after NAV2_STACK_ACTIVE_TIMEOUT_SEC.
wait_stack_active() {
  local robot="$1" log_path="$2" waited=0 state
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY_RUN] poll ${log_path} every 1s until ${robot} is active (<= ${NAV2_STACK_ACTIVE_TIMEOUT_SEC}s), abort on /${NAV2_ABORT_RE}/"
    return 0
  fi
  while :; do
    state="$(nav2_stack_state "$log_path")"
    case "$state" in
      active)
        log "Nav2 ${robot} active ${waited}s after its launch (sequential)"
        return 0 ;;
      aborted)
        log "NAV2_BRINGUP_FAILED: Aborting bringup in ${log_path} (sequential, ${robot}, ${waited}s after its launch)"
        exit 1 ;;
    esac
    if [ "$waited" -ge "$NAV2_STACK_ACTIVE_TIMEOUT_SEC" ]; then
      log "NAV2_BRINGUP_FAILED: ${robot} not active ${waited}s after its launch (sequential, state ${state})"
      exit 1
    fi
    sleep 1
    waited=$((waited + 1))
  done
}

# Every stack currently active (no un-recovered heartbeat loss), waiting up to
# NAV2_HEALTH_GRACE_SEC for a respawn re-activation. $1 labels the check.
wait_nav2_healthy() {
  local label="$1" waited=0 robot state bad crit
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY_RUN] ${label}: every stack's last active line after its last CRITICAL FAILURE (<= ${NAV2_HEALTH_GRACE_SEC}s)"
    return 0
  fi
  while :; do
    bad=""
    for robot in "${ROBOT_IDS[@]}"; do
      state="$(nav2_stack_state "$(nav2_log_of "$robot")")"
      [ "$state" = "active" ] || bad="${bad}${robot}=${state} "
    done
    if [ -z "$bad" ]; then
      crit="$(nav2_logs_matching 'CRITICAL FAILURE' | tr '\n' ' ')"
      log "${label}: all ${#ROBOT_IDS[@]} stacks active (heartbeat losses recovered in: ${crit:-none})"
      return 0
    fi
    case "$bad" in
      *aborted*)
        log "NAV2_BRINGUP_FAILED: ${label}: ${bad}"
        exit 1 ;;
    esac
    if [ "$waited" -ge "$NAV2_HEALTH_GRACE_SEC" ]; then
      log "NAV2_BRINGUP_FAILED: ${label}: not active after ${waited}s grace: ${bad}"
      exit 1
    fi
    sleep 1
    waited=$((waited + 1))
  done
}

# Prints the Nav2 logs (one per line) matching the extended regex $1.
nav2_logs_matching() {
  # shellcheck disable=SC2086 # NAV2_LOGS is a space-separated path list.
  sudo docker exec "$CONTAINER" grep -lE -e "$1" $NAV2_LOGS 2>/dev/null || true
}

wait_nav2_active() {
  local want="${#ROBOT_IDS[@]}" waited=0 active aborted
  log "waiting for Nav2 lifecycle: ${want} stack(s) active (<= ${NAV2_ACTIVE_TIMEOUT_SEC}s)"
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY_RUN] poll ${NAV2_LOGS} every 2s for /${NAV2_ACTIVE_RE}/ in all ${want}, abort on /${NAV2_ABORT_RE}/"
    return 0
  fi
  while :; do
    aborted="$(nav2_logs_matching "$NAV2_ABORT_RE" | tr '\n' ' ')"
    active="$(nav2_logs_matching "$NAV2_ACTIVE_RE" | grep -c . || true)"
    if [ -n "$aborted" ]; then
      log "NAV2_BRINGUP_FAILED: Aborting bringup in ${aborted}(active ${active}/${want} after ${waited}s)"
      exit 1
    fi
    if [ "$active" -ge "$want" ]; then
      log "Nav2 lifecycle active: ${active}/${want} stacks after ${waited}s"
      return 0
    fi
    if [ "$waited" -ge "$NAV2_ACTIVE_TIMEOUT_SEC" ]; then
      log "NAV2_BRINGUP_FAILED: only ${active}/${want} stacks active after ${waited}s"
      exit 1
    fi
    sleep 2
    waited=$((waited + 2))
  done
}

cleanup() {
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY_RUN] cleanup: restore reasoning_backend_id if changed, restart container, collect logs (skipped)"
    return
  fi
  set +e
  # First thing on an abort, so Isaac starts winding down (GT close, manifest,
  # close()) while the restore below runs. Never on a normal exit: a 4-robot
  # Isaac still running at the REC_SEC cap must finish its horizon.
  if [ "$TAIL_STAGE_DONE" != "1" ] && [ -n "$ISAAC_PID" ]; then
    touch "$ISAAC_STOP_FLAG" 2>/dev/null || sudo touch "$ISAAC_STOP_FLAG"
    ISAAC_STOP_REQUESTED=1
    log "abort before the M5 tail finished: touched Isaac stop flag ${ISAAC_STOP_FLAG} (Isaac PID ${ISAAC_PID})"
  fi
  if [ -n "${PREV_BACKEND_ID:-}" ] && [ "${PREV_BACKEND_ID}" != "${BACKEND_ID}" ]; then
    log "restoring reasoning_backend_id: ${BACKEND_ID} -> ${PREV_BACKEND_ID}"
    sed -i "s/^reasoning_backend_id: .*/reasoning_backend_id: ${PREV_BACKEND_ID}/" "$ORCH_CONFIG"
    # Rebuild so the INSTALLED copy (what orchestrator.launch.py actually
    # loads via get_package_share_directory) matches the restored source —
    # a source-only revert would silently leave the VM's installed package
    # pointed at this run's backend for the next launch.
    sudo docker exec -w /ws "$CONTAINER" bash -lc \
      "source /opt/ros/jazzy/setup.bash && cd ros2_ws && colcon build --merge-install --packages-select swarm_orchestrator" \
      >>"$BUILD_LOG" 2>&1
  fi

  log "cleanup: restarting container + killing Isaac"
  sudo docker restart "$CONTAINER" >/dev/null 2>&1 || true
  if [ "$ISAAC_STOP_REQUESTED" = "1" ]; then
    if isaac_wait_pid_exit "$ISAAC_PID" "$ISAAC_STOP_WAIT_SEC" 1; then
      log "Isaac honored the stop flag: PID ${ISAAC_PID} gone at $(date -u +%H:%M:%S) (waited ${ISAAC_WAIT_ELAPSED_SEC}s after the container restart)"
    else
      log "WARNING: Isaac PID ${ISAAC_PID} still running ${ISAAC_STOP_WAIT_SEC}s after the stop flag; pkill below cannot stop Kit (SIGTERM is swallowed) — keep the pgrep relaunch gate"
    fi
  fi
  # Bracketed so the pattern doesn't match pkill's own argv/invoking command
  # line (an unbracketed "isaac.scripts.run_simulation" would match itself).
  sudo pkill -f "[i]saac.scripts.run_simulation" 2>/dev/null || true
  sudo pkill -f "[r]ecord_topic_video.py" 2>/dev/null || true
  sudo docker exec -w /ws "$CONTAINER" bash -lc "
    for f in ${M1_LOG} ${M5_LOG} ${M4_LOG} ${REC_LOG} ${NAV2_LOGS}; do
      echo \"===\$f===\"; tail -n 60 \"\$f\" 2>/dev/null || true
    done" >"$TAIL_LOG" 2>/dev/null || true
  {
    echo "===${ISAAC_LOG}==="
    tail -n 80 "$ISAAC_LOG" 2>/dev/null || true
    # BUILD_LOG is written on the HOST (the colcon build redirect is outside
    # the docker-exec command string), unlike the logs above which are
    # written inside the container — collect it separately or it is silently
    # missing from TAIL_LOG.
    echo "===${BUILD_LOG}==="
    tail -n 60 "$BUILD_LOG" 2>/dev/null || true
  } >>"$TAIL_LOG" 2>/dev/null || true
  sudo chown -R ubuntu:ubuntu "$REC_DIR_HOST" 2>/dev/null || true
  log "logs saved to ${TAIL_LOG}; recordings (if RECORD=1) in ${REC_DIR_HOST}"
}
trap cleanup EXIT
# A bare `trap cleanup EXIT` alone would leave a Ctrl-C/dropped-SSH session
# waiting at the interrupted command instead of tearing down (INT/TERM/HUP
# resume execution unless the script itself exits) — on a long run that is
# the realistic way to abandon this script without the restore ever firing,
# so force an exit on those signals and let the EXIT trap fire once.
trap 'exit 130' INT TERM HUP

cd "$REPO"
log "restarting ROS container"
xrun sudo docker restart "$CONTAINER"
xrun_soft sudo pkill -f "[i]saac.scripts.run_simulation"
xrun_soft sudo pkill -f "[r]ecord_topic_video.py"
xrun sleep 2

xrun sudo mkdir -p data/logs/m5_decisions data/logs/m5_frames data/logs/m5_scene "$REC_DIR_HOST"
xrun sudo chmod 777 "$REC_DIR_HOST"
if [ "$RECORD" = "1" ]; then
  test -f "$REPO/scripts/record_topic_video.py" || { echo "recorder script missing on VM"; exit 1; }
fi

# ── 1. Point M5 at BACKEND_ID (restored on exit) ────────────────────────────
# BRINGUP_ONLY never starts M5, so it leaves orchestrator.yaml (a pinned
# config) untouched: no rewrite, no rebuild, nothing for cleanup to restore.
if [ "$BRINGUP_ONLY" = "1" ]; then
  log "BRINGUP_ONLY=1: skipping the backend rewrite + rebuild (M4/M5 never start)"
else
  # `|| true` is inside the substitution: under `pipefail`, a `grep` that
  # matches nothing makes the whole pipeline (and this assignment) exit
  # non-zero, which trips `set -e` before the explicit -z check below ever
  # runs — this keeps the failure reaching that check instead.
  PREV_BACKEND_ID=$(grep -m1 '^reasoning_backend_id:' "$ORCH_CONFIG" | awk '{print $2}' || true)
  if [ -z "$PREV_BACKEND_ID" ]; then
    echo "ERROR: could not read reasoning_backend_id from ${ORCH_CONFIG}" >&2
    exit 1
  fi
  log "reasoning_backend_id: ${PREV_BACKEND_ID} -> ${BACKEND_ID} (restored on exit)"
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY_RUN] sed -i s/^reasoning_backend_id: .*/reasoning_backend_id: ${BACKEND_ID}/ ${ORCH_CONFIG}"
  else
    sed -i "s/^reasoning_backend_id: .*/reasoning_backend_id: ${BACKEND_ID}/" "$ORCH_CONFIG"
  fi

  # orchestrator.launch.py loads the INSTALLED copy of orchestrator.yaml via
  # get_package_share_directory, so the source edit above is inert until this
  # package is rebuilt (plain `colcon build`, without --merge-install, errors
  # in this workspace layout).
  log "building swarm_orchestrator (merge-install) -> ${BUILD_LOG}"
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY_RUN] docker exec -w /ws ${CONTAINER} bash -lc \"colcon build --merge-install --packages-select swarm_orchestrator\" > ${BUILD_LOG}"
  else
    sudo docker exec -w /ws "$CONTAINER" bash -lc \
      "source /opt/ros/jazzy/setup.bash && cd ros2_ws && colcon build --merge-install --packages-select swarm_orchestrator" \
      >"$BUILD_LOG" 2>&1
  fi
fi

# ── 2. Validate SCENARIO before anything expensive: map exists inside the
#      container, and every robot's spawn pose parses. The container is
#      already reachable here (the colcon build above proves it), and a
#      missing/misnamed map or malformed scenario yaml is a realistic
#      mistake (scenario yaml edits are inert until the map/USD artifacts
#      are regenerated) — catching it here costs about a second instead of
#      the several minutes Isaac Sim + Nav2 bring-up would otherwise burn
#      before hitting the same failure in the old (stage-5) location. ────
check_map_exists
SPAWN_POSES="$(parse_spawn_poses)"
# Parallel indexed arrays, not an associative one: the script also runs
# under macOS's bash 3.2 (DRY_RUN checks and the golden test).
ROBOT_IDS=()
SPAWN_X=()
SPAWN_Y=()
SPAWN_YAW=()
POSES_TEXT=""
while read -r rid x y yaw; do
  # Only robot lines: a login shell inside the container may print other
  # text, which the old per-robot awk lookups skipped the same way.
  case "${rid}" in
    robot_[0-9]*) ;;
    *) continue ;;
  esac
  if [ -z "${x}" ] || [ -z "${y}" ] || [ -z "${yaw}" ]; then
    echo "ERROR: failed to parse spawn pose (${rid}) from ${SCENARIO_YAML_HOST}" >&2
    exit 1
  fi
  ROBOT_IDS+=("$rid")
  SPAWN_X+=("$x")
  SPAWN_Y+=("$y")
  SPAWN_YAW+=("$yaw")
  POSES_TEXT="${POSES_TEXT:+${POSES_TEXT}; }${rid} x=${x} y=${y} yaw=${yaw}"
  NAV2_LOGS="${NAV2_LOGS:+${NAV2_LOGS} }$(nav2_log_of "$rid")"
done <<<"$SPAWN_POSES"
if [ "${#ROBOT_IDS[@]}" -eq 0 ]; then
  echo "ERROR: no robots parsed from ${SCENARIO_YAML_HOST}" >&2
  exit 1
fi
log "scenario validated: map present, spawn poses parsed (${POSES_TEXT})"

# ── 3. Isaac Sim ─────────────────────────────────────────────────────────────
log "starting Isaac Sim ${SCENARIO} (headless, seed ${SEED}, ${SIM_SEC}s) -> ${ISAAC_LOG}"
# LD_LIBRARY_PATH is required: the isaacsim.ros2.core extension resolves its
# internal rclpy by itself, but the rmw/rcl C libraries must be on the path
# or the bridge fails with "ROS2 Bridge startup failed".
# sudo -H -u ubuntu: /home/ubuntu is mode 0750, so an SSH session under any
# other account fails with "python3: Permission denied" launching python.sh.
if [ "$DRY_RUN" = "1" ]; then
  log "[DRY_RUN] nohup sudo -H -u ubuntu env ... /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.run_simulation --scenario ${SCENARIO_YAML_HOST} --headless --seed ${SEED} --duration-sec ${SIM_SEC} --topic-timeout-sec 180 > ${ISAAC_LOG} 2>&1 &"
else
  rm -f "$ISAAC_STOP_FLAG" 2>/dev/null || sudo rm -f "$ISAAC_STOP_FLAG"
  nohup sudo -H -u ubuntu env \
    ROS_DISTRO=jazzy \
    RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
    LD_LIBRARY_PATH=/home/ubuntu/IsaacSim/exts/isaacsim.ros2.core/jazzy/lib \
    FASTRTPS_DEFAULT_PROFILES_FILE="$REPO/config/dds/fastdds.xml" \
    PYTHONPATH="$REPO" \
    VGU_ISAAC_STOP_FLAG="$ISAAC_STOP_FLAG" \
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.run_simulation \
      --scenario "$SCENARIO_YAML_HOST" \
      --headless --seed "$SEED" --duration-sec "$SIM_SEC" --topic-timeout-sec 180 \
    >"$ISAAC_LOG" 2>&1 &
  ISAAC_PID=$!
  log "Isaac PID ${ISAAC_PID}"
fi
log "Isaac stop flag: ${ISAAC_STOP_FLAG} (touched by cleanup on abort only)"

wait_topic /camera/image_raw 300
docker_ros "timeout 60s ros2 topic echo --qos-reliability best_effort --once /camera/image_raw >/dev/null"
for robot in "${ROBOT_IDS[@]}"; do
  wait_topic "/${robot}/odom" 120
  wait_topic "/${robot}/scan" 120
done
log "Isaac topics live"

# ── 4. M1 Perception (must start before Nav2: Nav2 uses camera localization) ─
log "starting M1 perception -> ${M1_LOG}"
docker_exec_bg "$M1_LOG" "ros2 launch swarm_perception perception.launch.py use_camera_node:=false >${M1_LOG} 2>&1"
wait_topic /perception/scene_state 90
wait_topic /perception/annotated_frame 90
log "M1 perception live"

# ── 5. Recorder (optional; fps stamped from a live measurement; see header
#      for the re-timing caveat) ─────────────────────────────────────────────
if [ "$RECORD" = "1" ]; then
  HZ=$(docker_ros "timeout 12s ros2 topic hz /perception/annotated_frame 2>/dev/null | grep -m1 'average rate' | awk '{print \$3}'" || true)
  FPS=${HZ:-9}
  log "annotated_frame measured rate ${HZ:-unknown} Hz -> stamping fps=${FPS}, recording ${REC_SEC}s -> ${REC_OUT}"
  docker_exec_bg "$REC_LOG" "python3 /ws/scripts/record_topic_video.py --topic /perception/annotated_frame --output ${REC_OUT} --duration-sec ${REC_SEC} --fps ${FPS} --qos best_effort --segment-frames 2000 >${REC_LOG} 2>&1"
  xrun sleep 3
else
  log "RECORD=0 — skipping recorder stage"
fi

# ── 6. Nav2 bringup (localization:=camera; spawn poses + map already
#      validated in stage 2, above) ──────────────────────────────────────────
# The first robot's stack starts the one shared map server; the rest reuse
# it (start_map_server:=false, nav2_robot.launch.py).
# Sequential mode (NAV2_BRINGUP_MODE, A23 infra wave) gates each launch on the
# previous stack's lifecycle instead of a fixed stagger sleep.
if [ "$NAV2_BRINGUP_MODE" = "sequential" ]; then
  log "Nav2 bring-up mode: sequential (stack k+1 launches once stack k is active)"
fi
NAV2_T0=$SECONDS
MAP_SERVER=true
for i in "${!ROBOT_IDS[@]}"; do
  robot="${ROBOT_IDS[$i]}"
  if [ "$MAP_SERVER" = "false" ] && [ "$NAV2_BRINGUP_MODE" = "parallel" ]; then
    xrun sleep "$NAV2_LAUNCH_STAGGER_SEC"
  fi
  nav2_log="$(nav2_log_of "$robot")"
  log "starting Nav2 ${robot} -> ${nav2_log}"
  docker_exec_bg "$nav2_log" "ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=${robot} x:=${SPAWN_X[$i]} y:=${SPAWN_Y[$i]} yaw:=${SPAWN_YAW[$i]} start_map_server:=${MAP_SERVER} localization:=camera map_yaml:=${MAP} >${nav2_log} 2>&1"
  MAP_SERVER=false
  if [ "$NAV2_BRINGUP_MODE" = "sequential" ]; then
    wait_stack_active "$robot" "$nav2_log"
  fi
done
for robot in "${ROBOT_IDS[@]}"; do
  wait_action "/${robot}/navigate_to_pose" 150
done
log "Nav2 action servers live"
wait_nav2_active
if [ "$NAV2_BRINGUP_MODE" = "sequential" ]; then
  wait_nav2_healthy "Nav2 health gate"
fi
log "Nav2 bring-up (${NAV2_BRINGUP_MODE}): first stack launch -> gate passed in $((SECONDS - NAV2_T0))s"

if [ "$BRINGUP_ONLY" = "1" ]; then
  if [ "$BRINGUP_HOLD_SEC" -gt 0 ]; then
    log "BRINGUP_ONLY: holding ${BRINGUP_HOLD_SEC}s past the gate before a post-hold health check"
    xrun sleep "$BRINGUP_HOLD_SEC"
  fi
  wait_nav2_healthy "BRINGUP_ONLY post-hold health check"
  SIM_CLOCK="$(docker_ros "timeout 10s ros2 topic echo --once /clock --field clock.sec 2>/dev/null | head -1" || true)"
  log "BRINGUP_ONLY PASS: ${#ROBOT_IDS[@]}/${#ROBOT_IDS[@]} stacks active, mode ${NAV2_BRINGUP_MODE}, sim clock at check ${SIM_CLOCK:-unknown} s"
  exit 0
fi

# ── 7. M4 Execution ──────────────────────────────────────────────────────────
log "starting M4 execution -> ${M4_LOG}"
docker_exec_bg "$M4_LOG" "ros2 launch swarm_execution execution.launch.py >${M4_LOG} 2>&1"
xrun sleep 4

# ── 8. M5 Orchestrator (backend from BACKEND_ID; VGU_MOCK_DECISION_FILE when
#      MOCK_DECISION_FILE is set) ────────────────────────────────────────────
# Source the key from /ws/.env inside the container rather than interpolating
# it into this command string — an inline API-key assignment lands in the
# docker-exec argv and is readable by every user on the host via `ps aux`
# for the whole life of the process.
M5_INNER="set -a && source /ws/.env && set +a && export VGU_RUN_ID=${STAMP}"
if [ -n "$MOCK_DECISION_FILE_CONTAINER" ]; then
  log "MOCK_DECISION_FILE set -> VGU_MOCK_DECISION_FILE=${MOCK_DECISION_FILE_CONTAINER}"
  M5_INNER="${M5_INNER} && export VGU_MOCK_DECISION_FILE=${MOCK_DECISION_FILE_CONTAINER}"
fi
if [ -n "$MOCK_RETREAT_CHOICE_FILE_CONTAINER" ]; then
  log "MOCK_RETREAT_CHOICE_FILE set -> VGU_MOCK_RETREAT_CHOICE_FILE=${MOCK_RETREAT_CHOICE_FILE_CONTAINER}"
  M5_INNER="${M5_INNER} && export VGU_MOCK_RETREAT_CHOICE_FILE=${MOCK_RETREAT_CHOICE_FILE_CONTAINER}"
fi
if [ -n "$MOCK_ECHO" ] && [ "$MOCK_ECHO" != "0" ]; then
  log "MOCK_ECHO set -> VGU_MOCK_ECHO=1 type=${MOCK_ECHO_TYPE:-deadlock} strategy=${MOCK_ECHO_STRATEGY:-yield} (apparatus only)"
  M5_INNER="${M5_INNER} && export VGU_MOCK_ECHO=1"
  if [ -n "$MOCK_ECHO_TYPE" ]; then
    M5_INNER="${M5_INNER} && export VGU_MOCK_ECHO_TYPE=${MOCK_ECHO_TYPE}"
  fi
  if [ -n "$MOCK_ECHO_STRATEGY" ]; then
    M5_INNER="${M5_INNER} && export VGU_MOCK_ECHO_STRATEGY=${MOCK_ECHO_STRATEGY}"
  fi
fi
M5_INNER="${M5_INNER} && ros2 launch swarm_orchestrator orchestrator.launch.py >${M5_LOG} 2>&1"
# Stage 9 tails this log 5 s after the backgrounded launch below. Under four
# Nav2 stacks M5's shell took longer than that to reach its redirect, GNU tail
# exited on the missing file and the launcher went straight to cleanup
# (intersection smoke IB1, 2026-09-29). Create it first; M5's `>` truncates
# the same file.
xrun sudo docker exec "$CONTAINER" touch "$M5_LOG"
log "starting M5 orchestrator (${BACKEND_ID} backend, CWD /ws) -> ${M5_LOG}"
docker_exec_bg "$M5_LOG" "$M5_INNER"
xrun sleep 5
log "all components started"

# ── 9. Monitor M5 decisions live until Isaac exits, capped at REC_SEC
#      (independent of RECORD) ─────────────────────────────────────────────
# Option B (2026-10-07 shutdown-timing ruling): once Isaac has exited, GT and
# the manifest are final and M5 has no camera input, so the rest of a fixed
# REC_SEC window only idles. The tail runs in the background and this shell
# polls Isaac's wrapper PID (a 2 s poll also lets an INT/TERM reach the
# cleanup trap promptly, where a foreground tail deferred it up to REC_SEC).
log "--- M5 decisions will appear in ${REPO}/data/logs/m5_decisions/ ---"
log "--- tailing M5 log for live feedback ---"
TAIL_CAP_SEC=$((REC_SEC - 10))
if [ "$DRY_RUN" = "1" ]; then
  log "[DRY_RUN] sudo timeout ${TAIL_CAP_SEC}s docker exec -w /ws ${CONTAINER} bash -lc \"tail -f ${M5_LOG}\""
  log "[DRY_RUN] poll Isaac PID every ${ISAAC_POLL_SEC}s: end the M5 tail ${ISAAC_EXIT_GRACE_SEC}s after Isaac exits, cap ${TAIL_CAP_SEC}s (sudo pkill -TERM -f [t]ail -f ${M5_LOG})"
else
  # `sudo timeout`, not `timeout sudo`: an unprivileged timeout cannot signal
  # the root-owned sudo child (EPERM), so the tail never dies and the script
  # hangs here forever — the recording is never finalized and cleanup never
  # runs. The timeout stays as the tail's own hard cap.
  sudo timeout ${TAIL_CAP_SEC}s \
    docker exec -w /ws "$CONTAINER" bash -lc "tail -f ${M5_LOG}" 2>/dev/null &
  TAIL_PID=$!
  TAIL_RC=0
  isaac_wait_exit_or_cap "$ISAAC_PID" "$TAIL_PID" "$TAIL_CAP_SEC" "$ISAAC_POLL_SEC" \
    "$ISAAC_EXIT_GRACE_SEC" || TAIL_RC=$?
  case "$TAIL_RC" in
    0) log "Isaac exited (PID ${ISAAC_PID} gone at ${ISAAC_EXITED_AT}); ending the M5 tail after ${ISAAC_EXIT_GRACE_SEC}s grace (${ISAAC_WAIT_ELAPSED_SEC}s into the tail)" ;;
    1) log "REC_SEC cap reached (${TAIL_CAP_SEC}s) with Isaac still running; ending the M5 tail, Isaac left to finish its horizon" ;;
    *) log "M5 tail ended by itself after ${ISAAC_WAIT_ELAPSED_SEC}s (its own ${TAIL_CAP_SEC}s timeout, or an error; Isaac running: $(isaac_pid_alive "$ISAAC_PID" && echo yes || echo no))" ;;
  esac
  # The in-container tail, not just the docker-exec client: killing the client
  # alone leaves `tail -f` running inside the container. Bracketed so the
  # pattern cannot match pkill's own command line.
  sudo pkill -TERM -f "[t]ail -f ${M5_LOG}" 2>/dev/null || true
  wait "$TAIL_PID" 2>/dev/null || true
fi
TAIL_STAGE_DONE=1

# ── 10. Recorder finalization (RECORD=1 only; recording is already on the
#      host bind mount, no docker cp needed) ─────────────────────────────────
if [ "$RECORD" = "1" ]; then
  log "recorder window elapsed — recording lives on the host bind mount"
  xrun sleep 10
  if [ "$DRY_RUN" = "1" ]; then
    log "[DRY_RUN] docker exec -w /ws ${CONTAINER} bash -lc \"cat ${REC_LOG}\""
  else
    # Option B ends stage 9 ISAAC_EXIT_GRACE_SEC after Isaac exits, long
    # before the recorder's REC_SEC window, and cleanup's `docker restart`
    # then SIGKILLs it before release(): at ~0.5 fps the 2000-frame segment
    # never rolls, so the whole video was lost (S6 first light, 2026-10-08).
    # Stop it cleanly first. On the REC_SEC-cap path the sleep above has
    # already let it reach its own duration, so this finds nothing to stop.
    stop_recorder_cleanly
    sudo docker exec -w /ws "$CONTAINER" bash -lc "cat ${REC_LOG} 2>/dev/null || true"
  fi
  xrun_soft sudo chown -R ubuntu:ubuntu "$REC_DIR_HOST"
  if [ "$DRY_RUN" != "1" ]; then
    ls -lh "$REC_DIR_HOST" || log "WARNING: recording directory not found at ${REC_DIR_HOST}"
  fi
fi

# ── 11. Print M5 decision summary ───────────────────────────────────────────
if [ "$DRY_RUN" = "1" ]; then
  log "[DRY_RUN] skipping M5 decision summary (reads real data/logs/m5_decisions/)"
else
  log "=== M5 decision summary ==="
  ls -lt "$REPO/data/logs/m5_decisions/" | head -10
  latest_dec=$(ls -t "$REPO/data/logs/m5_decisions/"*.json 2>/dev/null | head -3)
  for f in $latest_dec; do
    echo "--- $f ---"
    python3 -c "
import json, sys
d = json.load(open('$f'))
print('  terminal_stage:', d.get('terminal_stage'))
print('  grounded:', d.get('grounded_command_present'))
print('  strategy:', d.get('decision', {}).get('strategy') if d.get('decision') else 'none')
print('  failure:', d.get('failure_reason'))
" 2>/dev/null || cat "$f" | head -10
  done
fi

log "done: STAMP=${STAMP} SCENARIO=${SCENARIO} MAP=${MAP} M5_LOG=${M5_LOG} prompt_static_obstacles=${OBSTACLE_MODALITY}"
