# Deadlock Collision & Resolution Fixes

**Date:** 2026-07-02
**Branch:** `fix/deadlock-collision-resolution`
**Source investigation:** autonomous phase-3 demo run `20260702T144939Z` (video + logs).

## Problem Statement

The fully autonomous head-on-deadlock run exposed two failures:

1. **Robots collide and interpenetrate.** The RTX lidar misses *moving* bodies
   (MotionBVH disabled), so Nav2 costmaps and collision_monitor are blind
   during approach; the M1-based safety monitor fires (16,861 stops in one
   run) but its Nav2-goal cancels are immediately undone by
   coordination_client's 2 s goal-retry loop, letting robots crawl into each
   other; Isaac applies no robot-robot contact, so they merge.
2. **Resolution never completes.** All coordination timing is wall-clock but
   the sim runs at ~0.4× real time. M5 expired each yield command at
   `expected_resolution_time_sec` (~37 s) while robot_1's backup was still
   executing, re-analyzed, and dispatched a new yield that silently
   cancel-restarted the backup. Three yields went ACTIVE; none ever reached a
   terminal status. robot_2's fixed 25 s `temporary_wait` expired mid-yield
   and it drove back into the aisle.

## Global Constraints

- Follow CLAUDE.md development standards: full type hints (`X | Y`, built-in
  generics), Google-style docstrings on public functions, Pydantic v2 frozen
  models for cross-module contracts, comments only for non-obvious
  constraints.
- TDD: write the failing test first, then the implementation. Tests are named
  `test_<behavior>_<condition>` and live in `tests/unit/`.
- Pure logic stays out of node classes so it is testable without rclpy
  (pattern: `command_lifecycle.py`, `base_mission.py`, `safety.py`).
- Do not change ROS2 topic names except where a task explicitly adds a new
  topic; new topics must be added to the relevant spec doc in the same task.
- Commit style: Conventional Commits, subject < 72 chars, **no body, no
  Co-Authored-By trailer** (project rule overrides tool defaults).
- Stage ONLY files your task touches (`git add <paths>`); never `git add -A`.
- Run the covering test file(s) for your change and report results. The full
  unit suite has 6 pre-existing failures unrelated to this work (pxr markers,
  OPENAI_API_KEY, modified M5 test) — do not chase them.
- Offline only: no task in this plan touches the GCP VM or Isaac Sim. Host
  verification is a separate controller-run phase.

## Offline Tasks (subagent-executable)

### Task 1 — M5: do not expire commands that are still ACTIVE

**Files:** `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py`,
`tests/unit/test_command_lifecycle.py` (extend existing file if present, else create).

`CommandTracker.check_timeouts(now)` currently marks any unresolved command
TIMED_OUT once `now - dispatched_at >= timeout_sec`, even when robot states
are ACTIVE (M4 mid-execution). This frees the robots for re-analysis and M5
dispatches a duplicate command that restarts the maneuver.

Change `check_timeouts` semantics:

- A command with **any robot in `CommandState.ACTIVE`** is never timed out.
  Rationale: M4 guarantees every ACTIVE command terminates on its own
  (backup has an odometry-progress safety deadline that publishes FAILED;
  wait/hold use bounded timers) — liveness is delegated to M4.
- A command whose non-terminal robots are all still `PENDING` past the
  deadline times out as before (covers a lost dispatch: M4 never received
  it, no status will ever come).
- Mixed case (some PENDING, some ACTIVE): treat as ACTIVE — do not expire.

Tests (minimum):
- `test_check_timeouts_expires_pending_command_past_deadline`
- `test_check_timeouts_keeps_active_command_past_deadline`
- `test_check_timeouts_mixed_pending_and_active_not_expired`
- `test_check_timeouts_resolved_command_not_reported` (existing behavior kept)

### Task 2 — M4 command bus: reject commands for a busy robot

**Files:** `ros2_ws/src/swarm_execution/swarm_execution/command_bus_node.py`,
`tests/unit/test_command_bus_node.py`.

`_on_command` currently dispatches unconditionally; a second yield for the
same robot silently cancels and restarts the in-flight backup with no
terminal status for either command.

Add an in-flight registry to `CommandBusNode`:

- `self._in_flight: dict[str, str]` mapping `robot_id -> command_id`.
- A command enters the registry when its first `ACTIVE` status is published
  and leaves it when a terminal status (`COMPLETED`/`FAILED`) is published
  for that `(command_id, robot_id)`.
- In `_on_command`, if the robot is in `_in_flight` under a **different**
  command_id, publish `FAILED` for the incoming command with detail
  `f"robot busy: {active_command_id}"` and do not dispatch. Duplicate
  delivery of the *same* command_id (DDS redelivery, republish) is ignored
  silently (no dispatch, no status).
- Integrate via `_publish_status` so registry bookkeeping cannot drift from
  what is actually published.

Tests (minimum):
- `test_second_command_while_busy_rejected_with_failed_status`
- `test_same_command_id_redelivery_ignored`
- `test_robot_freed_after_terminal_status_allows_new_command`
- Existing tests must still pass (yield/reverse/wait dispatch paths).

### Task 3 — M4 command bus: event-gated release of linked waits

**Files:** `ros2_ws/src/swarm_execution/swarm_execution/command_bus_node.py`,
`tests/unit/test_command_bus_node.py`. Depends on Task 2's registry.

M5 dispatches robot_1's `yield` and robot_2's `temporary_wait` under the
**same `command_id`**. Today robot_2's wait expires on a fixed wall-clock
duration and it re-enters the aisle while robot_1 is still yielding.

Change: track active wait timers per `(command_id, robot_id)`. When the
command bus publishes a **terminal** status for a `yield`/`reverse` action
under command_id C, immediately complete every still-active wait under the
same C for other robots:

- On yield `COMPLETED`: cancel the wait timer, publish `COMPLETED` with
  detail `"released: yield complete"`.
- On yield `FAILED`: same release, detail `"released: yield failed"` (M5
  will see both terminal states and can re-analyze with both robots free).
- A wait whose own timer expires first behaves exactly as today
  (`"wait complete"`), and its registry entry is cleared.

Tests (minimum):
- `test_linked_wait_released_when_yield_completes`
- `test_linked_wait_released_when_yield_fails`
- `test_unlinked_wait_unaffected_by_other_commands_terminal`
- `test_wait_natural_expiry_still_publishes_completed`

### Task 4 — M3 grounder: passing wait becomes an upper bound

**Files:** `reasoning/rag/command_grounder.py`,
`tests/unit/test_command_grounder.py`.

With Task 3 the passing robot is released by the yield's terminal status, so
`passing_wait_sec` no longer needs to predict motion duration (it was 25 s
wall, wrong at any RTF ≠ 1). Make it a generous safety upper bound:

- `passing_wait_sec = 120.0` (constant; released early by the linked yield
  in the normal path — only reached if the yield's terminal status is lost).
- `yield_total_sec` (used as `expected_resolution_time_sec`) = `150.0`
  (constant upper bound; with Task 1, M5 no longer expires ACTIVE commands,
  so this only bounds the PENDING/lost-dispatch case).
- Update the comments to state the new semantics (upper bounds + event
  release, not motion estimates). Update existing assertions in
  `test_command_grounder.py` that pin the old computed values.

Tests: adjust existing value assertions; add
`test_passing_wait_is_upper_bound_constant`.

### Task 5 — Safety holds: stop the safety/retry fight

**Files:** `ros2_ws/src/swarm_execution/swarm_execution/safety_monitor_node.py`,
`ros2_ws/src/swarm_execution/swarm_execution/base_mission.py`,
`ros2_ws/src/swarm_execution/swarm_execution/coordination_client_node.py`,
`tests/unit/test_safety_monitor.py`, `tests/unit/test_base_mission.py`,
`docs/specs/module4/safety-monitor.md` (document the new topic).

Today safety_monitor cancels a latched robot's Nav2 goal, coordination_client
sees the rejection and re-issues it 2 s later, forever (16,861 stop events in
one run).

- safety_monitor publishes `/safety/holds` (`std_msgs/String`, JSON
  `{"held": ["robot_1", ...]}`) whenever the latched set **changes**, plus a
  1 s periodic refresh while any robot is held (late-joiner tolerance;
  publish empty list once when the set empties).
- `BaseMissionDriver` gains held-robot awareness: `on_holds(held: set[str])`
  stores the set; `retry()` and the initial `on_registry` issuance skip held
  robots; a robot released from hold is picked up by the normal 2 s retry
  tick (no special resume path).
- coordination_client subscribes to `/safety/holds` and forwards to the
  driver. Safety-exempt robots (ACTIVE coordination command) are already
  excluded from latching by safety_monitor — unchanged.

Tests (minimum):
- `test_retry_skips_held_robot`
- `test_initial_issue_skips_held_robot`
- `test_release_from_hold_reissues_on_next_retry`
- `test_holds_published_on_latch_change` (safety monitor: pure-logic part)

### Task 6 — Safety margin + config

**Files:** `ros2_ws/src/swarm_execution/config/safety.yaml`,
`tests/unit/test_safety_monitor.py` (only if it pins the old value),
`docs/specs/module4/safety-monitor.md`.

- `min_distance_m: 0.3` → `0.45`. Rationale: 0.3 m center-to-center leaves
  ~0.14 m shell gap and ~0.5 s reaction at the 0.28 m/s worst-case closing
  speed against an M1→safety pipeline latency of 0.2–0.4 s. 0.45 m restores
  ~1 s of margin and still fits the 0.55 m aisle standoff geometry (robots
  stop before entering marker-overlap range).
- Document the new value and rationale in the safety-monitor spec.

### Task 7 — M4 execution nodes on sim time

**Files:** `ros2_ws/src/swarm_execution/launch/execution.launch.py`,
`tests/unit/test_execution_launch.py` (create; follow the pattern of
`tests/unit/test_nav2_navigation_launch.py` if it exists).

`command_bus_node`'s hold/wait timers must tick in **sim time** so grounded
durations stay motion-consistent at any RTF: add
`parameters=[{"use_sim_time": True}]` to `command_bus_node` and
`coordination_client_node` in the launch file. Leave `safety_monitor_node`
on wall time (its latching reacts to M1 messages, not durations).
`Nav2Adapter.backup()`'s wall-clock safety deadline is intentionally
unaffected (it guards against a hung sim, which sim time cannot do).

Test: launch-description introspection asserting the parameter is set for
exactly those two nodes.

## Host Phases (controller-run, after offline tasks)

- **H1 (lidar visibility):** verify exact Isaac Sim setting names against
  current docs, then enable MotionBVH for the RTX lidar (or switch to a
  PhysX lidar if RTX cannot see moving meshes on this install). Probe: with
  robot_2 driving, `/robot_1/scan` must contain returns at robot_2's
  bearing.
- **H2 (physics contact):** probe robot-robot collision by driving one robot
  into the other with raw cmd_vel; inspect imported USD colliders and
  collision filtering; fix so bodies contact instead of interpenetrating.
- **H3 (end-to-end re-verify):** rerun the autonomous demo. Success criteria:
  no marker overlap at any frame; exactly one yield cycle that reaches
  COMPLETED; robot_2 resumes only after the release event; both robots reach
  goals; video recorded and delivered.
