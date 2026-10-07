# Isaac process-lifecycle helpers, sourced by scripts/vm/fc_launch.sh.
#
# Kept apart from fc_launch.sh so tests/unit/test_isaac_lifecycle_sh.py can
# exercise them offline with stand-in processes (fc_launch.sh itself runs
# top-level code and cannot be sourced). bash 3.2 compatible (macOS tests).
#
# Liveness is read with `ps`, never `kill -0`: the tracked PIDs are
# root-owned `sudo` wrappers, and `kill -0` from an unprivileged fc_launch
# fails with EPERM, which would read as "exited" and end a live episode's
# tail at once. A zombie (exited, not yet reaped by bash) counts as exited.

# isaac_pid_alive PID -> 0 while PID is running, 1 once gone, a zombie, or empty.
isaac_pid_alive() {
  local stat
  [ -n "${1:-}" ] || return 1
  stat="$(ps -o stat= -p "$1" 2>/dev/null)" || return 1
  stat="${stat//[[:space:]]/}"
  case "$stat" in
    "" | Z*) return 1 ;;
  esac
  return 0
}

# isaac_wait_exit_or_cap ISAAC_PID TAIL_PID CAP_SEC POLL_SEC GRACE_SEC
#
# Blocks while the M5 tail (TAIL_PID) runs, polling every POLL_SEC, until
# one of:
#   0  Isaac (ISAAC_PID) exited; returns GRACE_SEC later so M5 writes in
#      flight at Isaac's exit can land (the tail may end during the grace);
#   1  CAP_SEC elapsed with Isaac still running (the REC_SEC cap);
#   2  the tail ended by itself before either (its own timeout or an error).
# An empty ISAAC_PID never counts as exited, so the stage falls back to the
# fixed cap. Sets ISAAC_EXITED_AT (UTC HH:MM:SS, empty unless 0) and
# ISAAC_WAIT_ELAPSED_SEC.
isaac_wait_exit_or_cap() {
  local isaac_pid="$1" tail_pid="$2" cap_sec="$3" poll_sec="$4" grace_sec="$5"
  local start="$SECONDS"
  ISAAC_EXITED_AT=""
  ISAAC_WAIT_ELAPSED_SEC=0
  while :; do
    ISAAC_WAIT_ELAPSED_SEC=$((SECONDS - start))
    if [ -n "$isaac_pid" ] && ! isaac_pid_alive "$isaac_pid"; then
      ISAAC_EXITED_AT="$(date -u +%H:%M:%S)"
      sleep "$grace_sec"
      ISAAC_WAIT_ELAPSED_SEC=$((SECONDS - start))
      return 0
    fi
    if [ "$ISAAC_WAIT_ELAPSED_SEC" -ge "$cap_sec" ]; then
      return 1
    fi
    if ! isaac_pid_alive "$tail_pid"; then
      return 2
    fi
    sleep "$poll_sec"
  done
}

# isaac_wait_pid_exit PID WAIT_SEC POLL_SEC -> 0 once PID is gone (or was
# never set), 1 if it is still running after WAIT_SEC. Sets
# ISAAC_WAIT_ELAPSED_SEC.
isaac_wait_pid_exit() {
  local pid="$1" wait_sec="$2" poll_sec="$3"
  local start="$SECONDS"
  while isaac_pid_alive "$pid"; do
    ISAAC_WAIT_ELAPSED_SEC=$((SECONDS - start))
    if [ "$ISAAC_WAIT_ELAPSED_SEC" -ge "$wait_sec" ]; then
      return 1
    fi
    sleep "$poll_sec"
  done
  ISAAC_WAIT_ELAPSED_SEC=$((SECONDS - start))
  return 0
}
