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
