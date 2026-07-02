# Module 4 — Safety Monitor

**Prepared:** 2026-06-25

**Revision history:**

- Initial draft: safety invariants, the resolved hard-stop decision, and the
  emergency-stop override path. Written alongside the Phase 3 closed-loop
  implementation.

---

## 1. Goal

An independent, fast guard that enforces M4's safety invariants on top of the
reasoning loop (M1 → M5 → M2 → M3 → M4, 0.5–2 Hz) and Nav2's own per-robot local
avoidance. The monitor watches M1's *global* overhead scene state — which sees
inter-robot geometry the per-robot lidar planners cannot — and stops robots that
breach an invariant.

Invariants come from `config/safety.yaml`:

```yaml
safety:
  min_distance_m: 0.3
  max_linear_velocity_mps: 0.2
  command_timeout_sec: 20.0
```

---

## 2. Inputs & Outputs

| Interface | Type | Direction |
|---|---|---|
| `/perception/scene_state` | `std_msgs/String` (JSON `SceneState`) | M1 → monitor |
| `/<robot_id>/cmd_vel` | `geometry_msgs/Twist` | monitor → Isaac drive |

The monitor parses the same flat `robots[]` shape M5's `parse_scene_snapshot`
consumes (`robot_id`, `x`, `y`, `linear_velocity`). Pure invariant logic lives in
`swarm_execution/safety.py` (`detect_proximity_violations`, `exceeds_speed_limit`)
so it is unit-testable without ROS2; `safety_monitor_node.py` is a thin wrapper.

---

## 3. Resolved — safety hard-stop path

README §7 left this open: cancelling a Nav2 goal only decelerates via the
controller, and the FR6.4.8 watchdog (~0.5 s) is far too slow for a safety stop.

**Decision (2026-06-25): direct zero-`Twist` override on `/<robot_id>/cmd_vel`.**
On any invariant breach the monitor publishes a zero `Twist` directly to the
robot's `/cmd_vel`, a deliberate exception to M4's no-direct-`cmd_vel` rule. This
is the only path that yields a near-immediate stop.

This is a **PoC-grade** override, not a hardware e-stop:

- It competes **last-writer-wins** with Nav2's controller output on the same
  `/<robot_id>/cmd_vel` topic (the cmd_vel watchdog relays the last value to
  `/cmd_vel_safe`). To win that race reliably, a breach is **latched** and a
  `HOLD_PERIOD_SEC` (50 ms) timer re-publishes zeros for every latched robot —
  faster than Nav2's controller frequency and M1's scene rate — instead of
  relying on a single per-scene publish landing last. The scene callback updates
  the latch set; when the breach clears the set empties and the hold stops.
- It does not pre-empt (cancel) the Nav2 goal; once the breach clears, Nav2's
  next `cmd_vel` resumes motion. This is deliberate — the override *is* the stop,
  and not cancelling lets motion resume automatically without re-issuing a goal.

---

## 4. Known integration risks (UNVERIFIED — host-gated)

These are consequences of the override decision and the Phase 3 clearing
maneuver. They cannot be settled offline; they are flagged for the host run.

1. **Override vs. backup contention.** At a head-on standoff the Phase 3 grounder
   commands the yielding robot to **reverse** (BackUp) on `/<robot_id>/cmd_vel`,
   while a `min_distance_m` breach has this monitor hold **zero** on the *same*
   topic for the *same* robot. With the rate-dominant hold (§3) the monitor now
   *wins* that race — which is correct safety semantics, but it means: if the
   robots are still within 0.3 m when the backup is commanded, the hold will
   stall the very backup meant to clear the deadlock. The demo therefore depends
   on Nav2's `collision_monitor` + costmap inflation keeping the robots > 0.3 m
   apart so the breach clears (latch empties) before/while the backup runs. If
   the host run shows a stall, the fix is to exempt a robot under an active
   backup recovery from the latch, or add hysteresis below `min_distance_m`.
   Decide after observing the host run.

2. **Speed-limit source.** `linear_velocity` is M1's estimate, not a Nav2/Isaac
   command echo; under-detection (STALE markers) reads near-zero and would not
   trip the speed invariant. Acceptable for the PoC guard; note for real-robot.

---

## 5. Status

- **Offline complete:** pure logic + node callback unit-tested
  (`tests/unit/test_safety_monitor.py`), wired into `execution.launch.py`.
- **Host demo pending:** the override path and the risks in §4 are verified only
  on the GCP `vgu_ros` + Isaac host run, not from the offline suite.
