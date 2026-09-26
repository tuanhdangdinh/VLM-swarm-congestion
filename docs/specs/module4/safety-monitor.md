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
- Rev 6 (2026-09-16): added §8 — the authoritative hold at the M6 cmd_vel
  relay. Runs D/E/G showed robots creeping into contact while latched, because
  the §3 override is only last-writer-wins on a four-publisher topic.
- Rev 7 (2026-09-17): added §9 — the Nav2 cancel-all was a silent no-op
  (`ActionClient.cancel_goals_async` does not exist). Fixed in `Nav2Adapter`;
  records that `safety_monitor_node._cancel_nav2_goal` still carries the same
  bug, which is why the §3/§7 latch does not stop Nav2.
- Rev 8 (2026-09-26): added §10 — the coordination exemption now covers only
  the clearing maneuvers `yield` and `reverse`; Nav2-goal legs and waits keep
  both latch rules armed (runs G4/K1). Corrected §7's exemption bound from
  20 s to the 120 s wall-monotonic Nav2-leg watchdog. Updated §2, §5.1, §7
  and §8 to match.

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
| `/coordination/commands` | `swarm_interfaces/CoordinationCommand` | M5 → monitor (per-robot `action`, §10) |
| `/coordination/status` | `swarm_interfaces/CoordinationStatus` | command bus → monitor (`ACTIVE`/terminal, §10) |

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

   **Resolved by the coordination exemption, narrowed in §10 (2026-09-26).**
   A pair is exempt while one of its robots runs an ACTIVE `yield` or
   `reverse`, which lifts the hold for the backup. Other ACTIVE commands no
   longer lift anything.

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
the coordination lift: the distance rule skips any pair with an exempt member
(as `detect_proximity_violations` does), and the keep rule skips an exempt
robot. Since Rev 8 the exempt robots are only those running an ACTIVE `yield`
or `reverse` (§10). A STALE robot that is not running one of those is still
held. A robot with an unknown pose being driven past a blind partner is
precisely the run-D failure, and a Nav2 leg doing it is the G4/K1 failure.

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
  blind in exactly the run-D way.

  **Correction (Rev 8, 2026-09-26).** This bullet originally said the blind
  window was bounded by the Nav2-leg watchdog at `command_timeout_sec: 20.0`.
  That was wrong. The watchdog deadline is
  `max(3 × command.timeout_sec, 120 s)` on `time.monotonic()`
  (`command_bus_node.py`, `NAV_WATCHDOG_*`), and M5 sends
  `timeout_sec = 20.0`, so the bound in force is **120 s wall**. That is
  about 46 sim-s at RTF 0.38. The `command_timeout_sec` key in `safety.yaml`
  is loaded by no node. In runs G4 and K1, a `reroute` leg and its partner's
  `temporary_wait` held the exemption for the full 121–122 s wall while one
  robot pushed the other.

  Since §10, a Nav2 leg or wait no longer disarms anything, so that watchdog
  does not bound the exemption at all. The exemption now lasts only as long
  as a `yield` or `reverse`. Those run raw-`cmd_vel` primitives, and each
  primitive carries its own monotonic safety deadline, `max(15 × nominal, 30 s)`
  in `Nav2Adapter`. The yield's hold phase is bounded by its `hold_sec` timer.

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

---

## 8. Authoritative hold at the cmd_vel relay (2026-09-16)

**What.** The M6 cmd_vel watchdog — `isaac/vgu_sim/cmd_vel_watchdog.py` and its
relay node `cmd_vel_watchdog_node.py`, which is the only producer of
`/<robot_id>/cmd_vel_safe` and therefore the single point every velocity passes
through on its way to the wheels — now subscribes `/safety/holds` and forwards a
zero `Twist` for any robot in `held`, checked **before** the FR6.4.8
stale-command rule. `enforce_safety_holds` (default `true`) is the kill-switch
that restores plain stale-command relaying.

**Why.** §3's override is only *last-writer-wins* on `/<robot_id>/cmd_vel`, a
topic with four publishers (this monitor, Nav2's controller, Nav2's
`collision_monitor`, the docking server). Runs D, E and the recorded run G show
what that loses: the latch fires at a clean `min_distance_m` separation, the
monitor cancels the goals and republishes zeros at 40 Hz, and the robots
nevertheless creep toward each other at ≤ 0.06 m/s and reach contact — 0.45 m
down to 0.08 m in ~40 s on run G's annotated video, with full marker overlap 47 s
after the latch. Out-publishing the competition is not a stop; gating the one
relay is. This does not replace §3 (the zero-`Twist` override still decelerates
Nav2's own controller loop); it makes the stop hold.

**Invariant.** *A held robot's wheels receive zero irrespective of `cmd_vel`
publishers; coordination lift is expressed by removal from `held`.* The monitor
drops a robot from `held` while a clearing maneuver (`yield` or `reverse`) is
in flight for it or its pair partner (§5.1, §7's reuse of the same lift,
narrowed in §10). Gating on `held` membership therefore cannot stall the
yield's commanded backup, because the hold is lifted at its source, not
negotiated at the relay. Conversely, a latched robot on a Nav2 leg or a
wait stays in `held`, so this relay keeps its wheels at zero even while DWB
drives the leg. Two corollaries:

- **`held` is the whole contract.** The relay reads nothing else: no reason
  field, no distance, no status. `/safety/holds` keeps its `{"held": [...]}`
  shape.
- **A malformed `/safety/holds` payload keeps the previous hold set.** Parsing
  fails closed (`parse_holds` returns `ok=False` and the callback warns without
  touching the hold state) because applying an empty set on a corrupt message
  would release the stop. §4's unconditional 1 s heartbeat re-delivers a genuine
  release within a tick, so failing closed costs nothing.

**Implementation.** `watchdog_velocity(elapsed_sec, commanded, timeout_sec,
held)`, `parse_holds(payload) -> (ids, ok)` and the shared `SafetyHoldState`
(`set_held` returns `(engaged, released)`) are rclpy-free and unit-tested in
`tests/unit/test_cmd_vel_watchdog.py`. The node side is one `/safety/holds`
subscription for all robots (`SafetyHoldListener`, depth 10, default RELIABLE),
logging `cmd_vel relay hold engaged|released robot=…` once per transition rather
than per message. Commands are still recorded while held so a release resumes on
the publisher's live command instead of waiting out a freshly-expired timeout.

**Host verification (pending).** Latch the pair and confirm the ground-truth
`min_pairwise_distance_m` stays ≥ 0.4 m for 3 minutes. The relay runs inside the
Isaac process with Isaac's bundled rclpy, so it cannot be exercised offline.

---

## 9. Nav2 cancel-all was a silent no-op (2026-09-17)

**Defect.** `Nav2Adapter.cancel` called
`ActionClient.cancel_goals_async(goals_to_cancel=None)`. That method does not
exist. The Jazzy `ActionClient`
([rclpy/action/client.py](https://github.com/ros2/rclpy/blob/jazzy/rclpy/rclpy/action/client.py))
exposes `send_goal`/`send_goal_async`, `wait_for_server`, `server_is_ready` and
`destroy`, but no public cancel entry point: cancellation lives on
`ClientGoalHandle.cancel_goal`/`cancel_goal_async` or the private
`ActionClient._cancel_goal_async(goal_handle)`, both of which need a handle the
cancelling node does not own. The `AttributeError` was swallowed by a bare
`except: pass`, so every cancel-all did nothing while the caller logged success.
This is why the handle-less cancel path never stopped a goal issued by another
node — `command_bus_node` and `coordination_client_node` hold separate
`Nav2Adapter` instances, and `controller_server` kept looping `Failed to make
progress` / `Aborting handle` / `Received a goal, begin computing control
effort` for minutes after a latch while DWB nudged the pair together.

**Fix.** Cancel through the action's own cancel service,
`/{robot_id}/{action}/_action/cancel_goal` (`action_msgs/srv/CancelGoal`), for
both `navigate_to_pose` and `follow_waypoints`. Per that service's documented
policy, a request whose `goal_info.goal_id.uuid` is all zeros **and** whose
`goal_info.stamp` is zero cancels every goal on the server
([CancelGoal.srv](https://github.com/ros2/rcl_interfaces/blob/rolling/action_msgs/srv/CancelGoal.srv));
a zero id with a *non-zero* stamp would only cancel goals accepted at or before
that stamp, so both fields are zeroed explicitly. `build_cancel_all_request` is
a pure helper; clients are cached per `(robot_id, action_name)`. Readiness is
checked with `service_is_ready()` and never waited on, because `cancel()` runs
inside safety and coordination callbacks — a skip logs
`cancel-all skipped: service not ready robot=… action=…` at WARNING, and the
response logs `return_code`/`goals_canceling` at INFO. Nothing is swallowed.
Consequence of staying non-blocking: a client created on the first `cancel()`
is not ready until discovery completes, so that first cancel can legitimately
skip. Tests: `tests/unit/test_nav2_adapter.py` (35).

**Not fixed here — the latch path still has this bug.** `safety_monitor_node`
does **not** use `Nav2Adapter`; `_cancel_nav2_goal`
(`swarm_execution/safety_monitor_node.py:204-221`) keeps its own `_nav_clients`
and its own identical `cancel_goals_async(goals_to_cancel=None)` call behind a
bare `except: pass`, then logs `nav2 goal cancelled robot=…` regardless. The
§3/§7 latch therefore still fails to stop Nav2 until that copy gets the same
treatment. Fixing it was out of scope for this change; it is the blocking
follow-up for §8's host verification, since a latch that cannot stop
`controller_server` leaves the relay hold as the only thing holding the pair
apart.

**Host verification (pending).** After the node-side copy is fixed, latch a pair
and confirm `controller_server` logs no further `Received a goal, begin
computing control effort` once the latch fires.

**2026-09-17 — node-side copy fixed.** `_cancel_nav2_goal` no longer keeps its
own `_nav_clients`/`cancel_goals_async` path; `SafetyMonitorNode.__init__` now
constructs `self._adapter = Nav2Adapter(self)` (same pattern as
`command_bus_node` and `coordination_client_node`) and `_cancel_nav2_goal`
delegates to `self._adapter.cancel(robot_id)`, so the latch path gets the real
cancel-all fix described above instead of the dead handle-less call. The
`nav2 goal cancelled robot=…` log line — which asserted a result the node
never observed — is now `nav2 cancel-all requested robot=…`; the adapter logs
the server's actual `return_code`/`goals_canceling` response separately, as it
already does for `command_bus_node` and `coordination_client_node`. Tests:
`tests/unit/test_safety_monitor.py::test_latch_requests_cancel_all_through_adapter`
and `::test_cancel_log_no_longer_claims_result` (37 total in that file). The
host verification above is still pending — this only lands the code-side fix.

---

## 10. Exemption restricted to clearing maneuvers (2026-09-26)

**Observed (runs G4 and K1).** Before this change, any robot with an `ACTIVE`
`/coordination/status` exempted every pair it belonged to from the §1 distance
rule and from both halves of the §7 STALE fail-safe. In both runs, ER-2's
`reroute` was grounded as a Nav2 leg for robot_1 and a 15 s `temporary_wait`
for robot_2, and both commands went `ACTIVE` during the re-approach that
followed a `reverse`. The monitor was disarmed for the leg's full
120 s-wall watchdog. In K1 it also lifted a latch that had fired 0.8 s
earlier. robot_1 drove into its parked partner and held nose-to-nose contact
at 0.076 m for about 51 sim-s. Root cause and evidence:
`docs/reports/2026-09-26-close-approach-analysis.md` (Q2, mitigation 1 of Q5).

**Rule.** A robot is *exempt* while its current `ACTIVE` command's per-robot
action is in `CLEARING_ACTIONS = {"yield", "reverse"}`. These are the
raw-`cmd_vel` clearing primitives: backup, sidestep, hold and escort. A pair is
exempt while at least one member is exempt. The exempt set feeds every rule:

- the §1 distance rule skips an exempt pair;
- the §7 STALE rule does not latch an exempt pair afresh, and an exempt STALE
  robot does not keep its latch;
- exempt robots are removed from the final latched set, which covers the speed
  rule too.

These actions do **not** exempt: `navigate`, `goal`, `priority_override`,
`reroute` and `convoy` (Nav2 legs), `wait`, `temporary_wait` and `stop`, plus
any action the monitor has not seen. Pairs where one robot runs a clearing
maneuver and the other runs something else are exempt through the clearing
robot. That is what keeps the yield flow working: the passer's linked
`temporary_wait` is not exempt, but the pair stays exempt through the yielder's
own `ACTIVE` `yield` for the whole backup, pull-off, hold and escort. At yield
`COMPLETED` the archived pairs were already 0.73–0.76 m apart.

**Where the action comes from.** `CoordinationStatus` carries no action. The
command id cannot stand in for one: M3 builds it as
`<request_id>-<strategy>` (`reasoning/rag/command_grounder.py`), so every
robot in a decision shares the suffix. The passer's wait inside a yield is
`…-yield`, and a refused `reverse` is grounded as two `temporary_wait`s under a
`…-reverse` id. The monitor therefore also subscribes
`/coordination/commands`, which carries each robot's `action` keyed by
`(command_id, robot_id)`. `coordination_client` already subscribes that topic,
so no message changes.

`CoordinationTracker` (`swarm_execution/safety.py`) keeps both maps and joins
them only when a scene is evaluated (`clearing_exempt_robots`). A status that
arrives before its command therefore resolves once the command lands. Three
other cases:

- **Command never seen.** The robot is not exempt (fail closed). A monitor
  restarted mid-yield cannot see the earlier command on the volatile topic, so
  it would latch that yield's pair. That is the safe direction.
- **Terminal status for a different command.** A robot is cleared only by a
  terminal status for the command it is `ACTIVE` on, mirroring the command
  bus's in-flight registry. A busy-rejected command's `FAILED`, or a
  `base_mission` status from `coordination_client`, no longer ends a live
  maneuver's exemption. Before this change, either one did.
- **Command with no terminal status.** Its action entry is dropped on the
  terminal status. The map is also capped at 256 entries.

**Consequences.**

- **K1 latch continuity.** A latch that fired before a non-clearing command
  went `ACTIVE` persists. It is released only by a fresh reading at or beyond
  `min_distance_m`, or by a clearing maneuver.
- **Nav2 legs and the latch.** The monitor cancels Nav2 goals only on the
  newly-latched edge.
  - A leg that is already `ACTIVE` when the latch fires is cancelled by that
    cancel-all. The command bus then reports the leg `FAILED`, and M5
    re-analyses. The host run below showed this.
  - A leg that goes `ACTIVE` after the latch (the K1 order) keeps its goal.
    The §8 relay keeps its wheels at zero while DWB tries, until the command
    bus's 120 s-wall watchdog fails the leg (about 46 sim-s at RTF 0.38).
    Failing such a leg sooner (the report's mitigation 2) is not
    implemented.
- **A STALE passer keeps its latch.** If a passer is STALE and still latched
  when its partner's yield starts, the passer's own `temporary_wait` no longer
  releases it. At the 0.21–0.32 m yield standoffs both markers are detected,
  so this has not been observed.

**Diagnostics.** The startup line now ends
`exempt_actions=reverse,yield`. Each change of a robot's `ACTIVE` command
logs once, not on every 0.25/0.75 s republish:
`coordination status robot=… command=… status=… action=… exempt=True|False`.

**Implementation.** `CLEARING_ACTIONS`, `is_clearing_action`,
`clearing_exempt_robots` and `CoordinationTracker` are in
`swarm_execution/safety.py`. `detect_proximity_violations` and
`evaluate_latches` take the result as `exempt` (renamed from `coordinating`).
`safety_monitor_node.py` records commands and statuses into the tracker and
passes `exempt_robots()` to `evaluate_latches` and to the final subtraction.
Tests are in `tests/unit/test_safety_monitor.py`, 65 in total. They cover
yield, reverse, reroute, temporary_wait and the other non-clearing actions, a
refused reverse, mixed pairs, status-before-command, latch continuity (K1),
the latch firing during a reroute (G4), and the STALE fail-safe while
non-clearing commands are `ACTIVE`.

**Host verification (2026-09-26, both passed).** Both runs used
`head_on_asymmetric_w0p2_eopen_bshort_o0` on tree `cf4899f` with this change
installed (md5-verified). Artifacts are in `data/logs/vm_runs/m4fix/`.

- **Exposure regression, M1 (`20260926_101653`).** The mock backend was
  scripted with `config/mock_decisions/head_on_reverse_then_reroute.json`.
  1. The `reverse` lifted the approach-1 latch as before.
  2. The `reroute` and `temporary_wait` went `ACTIVE` with `exempt=False`.
     robot_2 was parked by the wait while robot_1 drove at it at 0.15 m/s.
  3. The monitor latched both robots 8.7 s wall later, and the relay hold
     engaged. The latch's cancel-all ended the leg, which went `FAILED`
     0.03 s later.
  4. The pair rested at a ground-truth 0.381 m and was held for 49.2 s wall,
     until the scripted `yield` went `ACTIVE`.
  5. The yield completed, and both robots arrived `within_tolerance`.

  This reproduced the G4 order, where the leg is `ACTIVE` before the
  crossing. The K1 order is covered by
  `test_latch_persists_when_reroute_goes_active_after_latch`.
- **Yield non-regression, M2 (`20260926_103507`).** ER-2 ran with gate
  `swap`, order `random` and obstacles on.
  - The run opened with `reverse`. The approach-2 latch was lifted by the
    yield going `ACTIVE`.
  - The yield completed in 152.8 s wall, and both robots arrived
    `within_tolerance`.
  - Minimum pairwise distance was 0.276 m.
  - There was no latch during the backup, pull-off or escort. The escort
    passed the parked yielder at 0.392 m, unlatched.
