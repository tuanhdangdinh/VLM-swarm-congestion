# Module 4 — Phase 3 — Closed Loop

**Prepared:** 2026-06-19

**Revision history:**

- Initial draft: Phase 3 of the M4 Nav2 rollout — an M2 congestion decision
  re-commands the robots through M3 → M4 → Nav2. Split out of
  `module4_navigation.md`.

---

## 1. Goal

Close the Layer-2 → Layer-1 loop: an M2 congestion decision actually re-commands
the robots so the standoff clears. Requires Phase 2
([phase2-nav2-stack.md](phase2-nav2-stack.md)) and a working M3 grounding stage.

See [README.md](README.md) for the module overview and target architecture.

---

## 2. Prerequisites

- **M3 grounding** must be implemented. It is currently
  `NotImplementedError` (the capstone artifact shows
  `terminal_stage: grounding`). Phase 3 cannot start until M3 turns a decision
  (e.g. `reroute`, `yield`) into a concrete goal or waypoint list.
- The scene must be **dynamic** (Phase 1 drive chain active), so the deadlock
  emerges over time rather than at spawn.

---

## 3. Wiring

```text
M2 decision -> M3 grounding -> M5 fan-out -> /coordination/commands (N per-robot)
            -> M4 command bus -> M4 safety monitor -> Nav2Adapter
            -> /<robot_id>/navigate_to_pose
            ... M4 -> /coordination/status -> M5 CommandTracker
```

- M5 (not M4) fans the grounded command out into **N** per-robot
  `CoordinationCommand` messages on `/coordination/commands` (M5 spec §9.2 / M5.4).
  M4's command bus subscribes to that topic; it never sees the raw M3 blob.
- The safety monitor validates against `safety.yaml`
  (`min_distance_m`, `max_linear_velocity_mps`, `command_timeout_sec`) and may
  veto or cancel (see the safety hard-stop open question in
  [README.md](README.md) §7).
- `Nav2Adapter` issues / pre-empts the per-robot Nav2 goal.
- M4 reports per-robot execution on `/coordination/status`
  (`CoordinationStatus`); M5's `CommandTracker` consumes it to resolve the
  command and clear the registry override.

---

## 4. Acceptance Demo

Script an approach; assert the full loop fires:

1. Two robots approach head-on (Phase 1 drive).
2. M1 → M5 → M2 detects the standoff.
3. M3 grounds a command (e.g. `yield` → reverse / `reroute` → alternate goal).
4. M4 pre-empts or updates the affected robot's Nav2 goal.
5. The deadlock clears; both robots reach their goals.

Verify with the `data/logs/m5_decisions/<id>.json` artifact plus odometry: confirm
the robot's motion after the trigger matches the grounded decision (e.g. the
robot told to yield actually reversed).

---

## 5. Open Question — two-loop contention

Define precisely when M4 may pre-empt an active Nav2 goal versus let it finish, so
Layer-2 decisions (0.5–2 Hz) do not thrash Layer-1 (10–30 Hz). A debounce or
minimum-goal-duration policy likely belongs in the command bus or safety monitor,
not in `Nav2Adapter`.

---

## 6. Implementation status (2026-06-25)

**Offline complete; acceptance demo PENDING host.** The mechanism is built and
unit-tested; the §4 acceptance property ("deadlock clears; both robots reach
goals") is an integration claim the offline suite structurally cannot establish.

| Piece | State | Tests |
|---|---|---|
| Base-mission driver (`coordination_client_node` + `BaseMissionDriver`) | Done | `test_base_mission.py` |
| Grounder emits clearing maneuver (`yield`/`reverse` → backup distance) | Done | `test_command_grounder.py` |
| `Nav2Adapter.backup()` (Nav2 `BackUp` action, verified Jazzy fields) | Done | `test_nav2_adapter.py` |
| Command bus routes `yield`/`reverse` → `backup` (was `cancel`) | Done | `test_command_bus_node.py` |
| Real completion feedback (status on action result, not on dispatch) | Done | `test_command_bus_node.py` |
| Safety monitor (min-distance + speed, direct `cmd_vel` override) | Done | `test_safety_monitor.py` |

**Loop closure.** The driver realizes the M5-spec rule "M5 does not issue initial
goals; Layer 1 runs continuously; commands modulate it, they do not replace it":

1. **Initiation.** `coordination_client_node` subscribes to `/coordination/tasks`
   (TRANSIENT_LOCAL, matching M5) and issues `navigate_to_pose` to each robot's
   effective goal at startup → robots approach → the standoff forms. A 2 s retry
   timer re-issues any goal Nav2 has not yet accepted, so a registry that arrives
   before the Nav2 action servers are lifecycle-ACTIVE still recovers (the
   registry is otherwise static after startup).
2. **Override.** M2 `yield` → M3 grounds `yield` for `involved_robots[0]` with
   `backup_distance_m` → M5 fan-out → command bus → `Nav2Adapter.backup` →
   `/<id>/backup`. On seeing the command, the driver cancels its own navigate for
   that robot (separate `Nav2Adapter` instances) and suppresses re-issue, so the
   two do not fight. The non-yielding robot keeps navigating.
3. **Resumption.** When the bus publishes the terminal `CoordinationStatus`, the
   driver un-suppresses and re-issues the base goal — required because the yield
   override goal equals the base goal, so resumption cannot rely on a goal change.
   Both robots then reach their goals.

Ownership boundary: the command bus owns a robot from command dispatch until the
command's terminal status; the coordination client owns it otherwise.

### 6.1 Known integration risks (UNVERIFIED — host-gated)

1. **Safety override vs. backup contention** on `/<robot_id>/cmd_vel` — see
   [safety-monitor.md](safety-monitor.md) §4.1. The zero-`Twist` safety stop and
   the reverse BackUp target the same topic for the same robot; whether they
   collide depends on whether the robots breach `min_distance_m`, which only the
   host run reveals.
2. **Aisle geometry vs. clearing.** Per the M4 Phase 2 notes, the 1.2 m aisle is
   too wide for a genuine deadlock, while a too-narrow straight aisle makes
   backup useless (robot_1 retreats, robot_2 follows, they never pass). Whether
   the chosen geometry actually produces "clears" is the acceptance criterion and
   is unverified offline.

### 6.2 Host run path

The closed loop spans the Isaac host (Isaac Sim embedded Python) and the
`vgu_ros` container (ROS2 Jazzy + Nav2). On the host:

1. Isaac Sim runs the dynamic scenario with the Phase 1 drive chain + Phase 2
   RTX lidar (`isaac/scripts/run_simulation.py`).
2. Per-robot Nav2 bringup (`nav2_robot.launch.py` per robot).
3. M4 nodes: `ros2 launch swarm_execution execution.launch.py` (command bus +
   coordination client + safety monitor).
4. M1 perception, M5 orchestrator (owns the registry + trigger policy), M2/M3
   reasoning. The coordination client — not M5 — issues the navigate goals from
   the registry's effective goals.
5. The coordination client drives robots toward goals across each other; confirm
   the standoff forms, M2 classifies it, the yielding robot reverses, the driver
   resumes its goal on the bus's COMPLETED status, and both reach their goals.
   Verify via `data/logs/m5_decisions/<id>.json` + odometry.
