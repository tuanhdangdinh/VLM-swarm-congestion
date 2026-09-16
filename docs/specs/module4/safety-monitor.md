# Module 4 — Safety Monitor

**Prepared:** 2026-06-25

**Revision history:**

- Initial draft: safety invariants, the resolved hard-stop decision, and the
  emergency-stop override path. Written alongside the Phase 3 closed-loop
  implementation.
- Rev 2 (2026-07-03): added §4 `/safety/holds` — the safety-hold signal that
  stops `coordination_client`'s retry loop from fighting the monitor's goal
  cancel.
- Rev 3 (2026-07-03): raised `min_distance_m` from 0.3 to 0.45 in
  `config/safety.yaml` — see §1 for rationale.
- Rev 4 (2026-07-03): §4 `/safety/holds` refresh made an unconditional 1 s
  heartbeat (empty set included) so a client holding robots from before a
  monitor restart recovers.
- Rev 5 (2026-09-16): added §7 — the STALE fail-safe. Run D showed a STALE
  robot was treated as absent rather than unsafe, which blinded the monitor;
  resolves the §5.2 under-detection note for the proximity invariant.

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
  min_distance_m: 0.45
  max_linear_velocity_mps: 0.2
  command_timeout_sec: 20.0
```

`min_distance_m` was raised from 0.3 to 0.45 (2026-07-03): 0.3 m center-to-center
leaves ~0.14 m shell gap and ~0.5 s reaction at the 0.28 m/s worst-case closing
speed against an M1→safety pipeline latency of 0.2–0.4 s — too tight a margin.
0.45 m restores ~1 s of margin and still fits the 0.55 m aisle standoff
geometry (robots stop before entering marker-overlap range).

---

## 2. Inputs & Outputs

| Interface | Type | Direction |
|---|---|---|
| `/perception/scene_state` | `std_msgs/String` (JSON `SceneState`) | M1 → monitor |
| `/<robot_id>/cmd_vel` | `geometry_msgs/Twist` | monitor → Isaac drive |
| `/safety/holds` | `std_msgs/String` (JSON `{"held": [...]}`) | monitor → coordination_client |

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

## 4. Safety holds — coordinating with `coordination_client`

Cancelling a latched robot's Nav2 goal (§3 predecessor) is not enough on its
own: `coordination_client`'s base-mission driver treats a cancelled goal as
unaccepted and re-issues it on its 2 s retry tick, the monitor cancels it
again on the next scene update, and the two nodes fight indefinitely (16,861
stop events observed in one run before this fix).

**`/safety/holds`** (`std_msgs/String`, JSON `{"held": ["robot_1", ...]}`)
closes that loop:

- **Publish trigger:** whenever the latched-robot set (`_latched_stops`)
  *changes* — a robot added or removed — the monitor publishes the full
  current set immediately, so consumers do not wait out the heartbeat
  interval on a change.
- **Periodic refresh:** a 1 s timer (separate from the 40 Hz
  `HOLD_PERIOD_SEC` hold-republish timer) republishes the current set
  **unconditionally**, empty set included. Besides late-joiner tolerance for
  a `coordination_client` that starts or reconnects after a change-triggered
  publish landed, the unconditional heartbeat covers monitor restarts: a
  fresh monitor starts with an empty latch set and publishes no change until
  the next violation, so a client still holding robots latched before the
  restart would otherwise be stranded forever. The empty-set heartbeat
  releases them within one tick.
- **Consumer behavior:** `coordination_client` forwards the parsed `held` set
  to `BaseMissionDriver.on_holds`. The driver skips held robots in its
  initial registry issuance, its `retry()` re-issuance, and status-driven
  resume — it does not re-send a `navigate_to_pose` goal for a robot the
  monitor just cancelled. There is no special resume path for a robot
  released from hold: it is simply no longer excluded, so the normal 2 s
  retry tick picks it up like any other unaccepted goal.

---

## 5. Known integration risks (UNVERIFIED — host-gated)

These are consequences of the override decision and the Phase 3 clearing
maneuver. They cannot be settled offline; they are flagged for the host run.

1. **Override vs. backup contention.** At a head-on standoff the Phase 3 grounder
   commands the yielding robot to **reverse** (BackUp) on `/<robot_id>/cmd_vel`,
   while a `min_distance_m` breach has this monitor hold **zero** on the *same*
   topic for the *same* robot. With the rate-dominant hold (§3) the monitor now
   *wins* that race — which is correct safety semantics, but it means: if the
   robots are still within 0.45 m when the backup is commanded, the hold will
   stall the very backup meant to clear the deadlock. The demo therefore depends
   on Nav2's `collision_monitor` + costmap inflation keeping the robots > 0.45 m
   apart so the breach clears (latch empties) before/while the backup runs. If
   the host run shows a stall, the fix is to exempt a robot under an active
   backup recovery from the latch, or add hysteresis below `min_distance_m`.
   Decide after observing the host run.

2. **Speed-limit source.** `linear_velocity` is M1's estimate, not a Nav2/Isaac
   command echo; under-detection (STALE markers) reads near-zero and would not
   trip the speed invariant. Acceptable for the PoC guard; note for real-robot.

---

## 6. Status

- **Offline complete:** pure logic + node callback unit-tested
  (`tests/unit/test_safety_monitor.py`), wired into `execution.launch.py`.
  `/safety/holds` publish-on-change/refresh logic and `BaseMissionDriver`
  hold-skipping are unit-tested in `tests/unit/test_safety_monitor.py` and
  `tests/unit/test_base_mission.py`.
- **Host demo pending:** the override path and the risks in §5 are verified only
  on the GCP `vgu_ros` + Isaac host run, not from the offline suite.

---

## 7. STALE fail-safe — an unknown pose is unsafe, not absent (2026-09-16)

**Observed (run D, 2026-09-16).** The two robots drove into each other until
their ArUco quads overlapped. Overlapping markers are undetectable, so M1
declared **both** robots `STALE` after `stale_after_sec` (3 s) and kept
publishing their last known poses with that status. The monitor then stopped
protecting them: with no fresh non-STALE pair it neither latched nor *kept* a
latch (the scene callback recomputes `_latched_stops` wholesale from each
snapshot), the coordination layer kept issuing motion, and the robots were
pushed around interpenetrating for ~400 s at 0.078 m centre distance. Physics
did not stop them either. This is §5.2's under-detection note biting the
*proximity* invariant, not just the speed one.

**Rule (on by default).** A robot M1 reports as `STALE`:

1. **keeps whatever latch it had** — a STALE snapshot never clears a latch; and
2. **is latched afresh** (stop + Nav2 goal cancel, both pair members) if the
   last reading in which it and another robot were *both* non-STALE put the
   pair within `stale_unsafe_distance_m`.

The latch lifts only when a **fresh non-STALE** reading shows the pair at or
beyond `min_distance_m`. The wider band gates unknown poses only: a fresh pair
at 0.50 m (≥ 0.45 m, < 0.60 m) is not latched.

**Why the remembered distance and not the carried pose.** M1 freezes and
republishes a STALE robot's last pose, and that carried pose is exactly the
datum that goes wrong while the robot keeps moving — in run D it was the
pre-contact pose while the robots were interpenetrating. The rule therefore
keys off a pairwise-distance memory refreshed **only from both-fresh pairs**; a
distance measured against a carried pose would launder the stale datum into the
memory the fail-safe trusts. A pair never observed fresh together has no memory
entry and is not latched by distance — only a pre-existing latch carries it.

**Parameters** (`config/safety.yaml`):

```yaml
  stale_pose_is_unsafe: true
  stale_unsafe_distance_m: 0.6   # min_distance_m + 0.15
```

`stale_unsafe_distance_m` defaults to `min_distance_m + STALE_UNSAFE_MARGIN_M`
(0.15 m) when the key is absent, so the band tracks `min_distance_m` if that is
retuned again. The margin covers the closing a robot can still do between its
marker disappearing and M1 declaring STALE 3 s later. Setting
`stale_pose_is_unsafe: false` disables **both** halves of the rule and restores
pre-Rev-5 behaviour.

**Interaction with §5.1 (backup contention).** The fail-safe must not fight the
commanded backup that is the designed way out of a close standoff, so it reuses
the existing coordination lift unchanged: the distance rule skips any pair with
an `ACTIVE`-coordinating member (as `detect_proximity_violations` already does),
and the keep rule skips a coordinating robot. A STALE robot that is *not* under
a command is still held — a robot with an unknown pose being driven past a blind
partner is precisely the run-D failure.

Two consequences of reusing that lift, both for the host run:

- **New post-pass stall mode (UNVERIFIED).** `reasoning/rag/scene_geometry.py`
  sizes escort/pass legs to clear `min_distance_m` (0.45 m) *exactly*, which is
  inside the 0.60 m STALE band. While the command is in flight the lift covers
  the pair, but once it reports `COMPLETED` the lift drops: a pair left at
  ~0.50 m that then loses a marker is now latched where before Rev 5 it was
  not. If the host run shows a post-pass stall, widen the escort clearance to
  `stale_unsafe_distance_m` rather than shrinking the band.
- **A wedged `ACTIVE` status disarms the fail-safe.** The lift is keyed on
  `/coordination/status`, so a status stuck at `ACTIVE` leaves the monitor
  blind in exactly the run-D way. Bounded in practice by `command_bus_node`'s
  nav2-leg watchdog, which publishes `FAILED` on timeout
  (`command_timeout_sec: 20.0`) and clears the exemption. This is the one
  remaining instance of the bug class §7 closes.

**Implementation.** `evaluate_latches` in `swarm_execution/safety.py` is the
pure, ROS2-free rule: it takes the snapshot, the limits, the previous latched
set and the distance memory, and returns the new latched set, a per-robot reason
(`REASON_MIN_DISTANCE` / `REASON_SPEED_LIMIT` / `REASON_STALE_POSE`) and the
updated memory. It **unions** onto the existing proximity result rather than
replacing it, so the change can only add latches. `safety_monitor_node.py` stays
thin: it carries `status` through into the snapshot dicts, holds the memory
between messages, and logs the reason once per latch in the newly-flagged loop
(`safety stop robot=… reason=stale_pose_unsafe`) rather than at the 40 Hz hold
rate. `/safety/holds` keeps its `{"held": [...]}` shape — it carries no reason
field and `coordination_client` parses `held`. Tests:
`tests/unit/test_safety_monitor.py`.

**Residual gap (not addressed here).** M1 suppresses late frames by publishing
an empty `robots[]` with `dropped_frame=True`. An empty snapshot contains no
STALE entry, so the keep rule does not see those robots and the latch set
empties for that message. The bound is narrow: the distance memory survives an
empty snapshot untouched, so the next good frame re-latches the pair through the
distance rule and re-fires the Nav2 cancel. What is genuinely not covered is a
robot that disappears from `robots[]` entirely rather than going STALE — still
treated as absent. Fixing that needs a presence memory with its own timeout,
deliberately out of scope here.
