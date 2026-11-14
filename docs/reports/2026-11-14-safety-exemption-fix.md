# Safety Exemption Scope: Fix and Replay Regression

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: the `scoped_clearing_exemption` fix (P1-P3 plus the owner-approved A19 input change), its unit tests, and the replay regression over 68 recorded bundles (59 earlier plus 9 new IB10 live).
- Rev 2: direction check on third-robot waivers (owner ruling 2026-11-14), replay re-run, lost-exemption itemisation, wording of "loses nothing" corrected.

---

## Scope

- **Companion to** `docs/reports/2026-11-13-safety-exemption-trace.md` on
  `feat/v4-per-cluster-parity`. That report holds the code trace of paths
  P1-P5. It lives in a read-only worktree, so it was not edited here.
- **Branch:** `fix/safety-exemption-scope`, based on 68e67b5 (the runtime
  deployed for tranche 1). The change is M4 only; M5 is untouched.
- **Owner rulings:**
  - 2026-11-13: fix P1-P3 behind one config key; P4 and P5 out of scope.
  - 2026-11-14: approved changing the A19 waiver inputs under the same key.
  - 2026-11-14 (later): a third-robot release must require the released
    robot to be moving away.
- **Evidence grade:**
  - Unit tests.
  - Offline replay of recorded command and status streams.
  - A what-if on recorded trajectories.
  - No live run.

---

## Behaviour

The new key is `safety.scoped_clearing_exemption`. It is on only for a literal
YAML `true`. When it is absent or false, the monitor behaves exactly as at
68e67b5 and the startup log line is identical.

| Path | Key off (68e67b5) | Key on |
|---|---|---|
| P1 `plan_continue_partners` | exempt against named `continue` robots, including other clusters | not honoured |
| P2 partner list frozen at publish | survives a new plan or the partner's own command | moot, because no partner is honoured |
| P3 rejected leg (FAILED before any ACTIVE) | still a member, still exempt | not a partner |
| A19 inputs | unhonoured partner counts as "own", so it is never waived | unhonoured partner and rejected leg count as third robots |
| Third-robot waiver lifetime | n/a | ends permanently once the gap is shrinking (below) |
| P4 mutual waivers | unchanged | unchanged |
| P5 own-command scope | unchanged | unchanged |

**A19 with the key on.** Say a clearing robot starts its command already
latched with an unhonoured partner or a rejected-leg robot.

- The clearing robot is released (one-sided waiver). The other robot stays held.
- If the rejection status arrives after the waiver capture, it is applied to
  the latches that stood at command start.
- A latch that forms during the window still holds both robots, exactly as A19
  already does.

**Direction check (third-robot waivers only).**

- **Measure.** Range from fresh M1 centre positions, evaluated on every
  scene. Commanded velocity is not used: the monitor does not see the
  raw-cmd_vel primitives' commands, and range is what the latch acts on.
- **Rule.** The reference is the widest fresh distance seen since the waiver
  was captured. The waiver ends once the current distance is more than
  `waiver_closing_tolerance_m` below that reference on
  `waiver_closing_readings` consecutive fresh readings.
- **Defaults** (in `SafetyLimits`, the loader and the fragment):
  - `waiver_closing_tolerance_m` = 0.05 m. Stationary M1 pair-distance noise
    in the recorded IB10 live and S1b scenes is at most 0.0045 m
    peak-to-peak; a reverse travels 0.7-1.3 m.
  - `waiver_closing_readings` = 3.
- **Hysteresis.** The reference only ratchets up, so a one-reading spike
  cannot revoke. Ending is permanent for the command window, so the pair
  cannot flap. After revocation it is an ordinary pair: both robots are held
  while it is inside 0.45 m.
- **Stationary pair.** It stays within tolerance, so a robot that has not
  started moving can start.
- **Rotate in place.** The centre moves only by the marker's offset from the
  rotation axis, which stays inside the tolerance (unit-tested with a 0.02 m
  circle). No recorded rotate-in-place frames were available to measure
  this, so the claim is inferred.
- **STALE.** A reading with either robot STALE carries no distance: the check
  is frozen, and A19's own STALE handling is unchanged.
- **Scope.** Only the 2026-11-14 third-robot path (unhonoured plan partners
  and rejected legs). Waivers on the original prereg-v3 A19 path (a bystander
  latched at command start) are not checked; pinned by
  `test_legacy_a19_waiver_has_no_direction_check`.
- **Proposal, not implemented:** apply the same check to every A19 waiver.
  That changes A19 for every scenario, including the S1b yields A19 was made
  for, so it needs its own replay and ruling.
- **Backstop.** The hard-contact floor still latches a waived pair at once
  (0.20 m in the kits, 0.0 in the base `safety.yaml`).

**Equivalence to "the decision's own robots".** Every reverse grounding path
makes each robot in `involved_robots` a member of its command, so "command
members" is the same set as "decision robots". Verified on data: 0 of 15
recorded reverse legs with partners name a partner that is in the decision but
not in the command.

---

## Code and Config

- **`ros2_ws/src/swarm_execution/swarm_execution/safety.py`**
  - `SafetyLimits.scoped_clearing_exemption`.
  - `CoordinationTracker(scoped_exemption=...)`.
  - Acceptance and rejection tracking, plus `rejected_members`.
  - The `exemption()` filter.
  - The `capture_latch_partners` inputs.
- **`ros2_ws/src/swarm_execution/swarm_execution/safety_monitor_node.py`**
  - New `limits_from_config` and `startup_log_line`.
  - Three log lines that are emitted only when the key is on, including
    `latch waiver revoked ... reason=closing`.
  - With the key on, the startup line also prints both direction thresholds.
- **`config/safety/scoped_clearing_exemption.fragment.yaml`** is an overlay
  fragment. The pinned safety files are not edited.
- **Kit rule.** Merge the fragment into the safety file the kit installs. In
  every episode, assert `scoped_clearing_exemption=True` from the monitor's
  startup line, not from the yaml. The loader falls back to key off on any
  read error.

---

## Tests

- `tests/unit/test_safety_exemption_scope.py` has 64 tests. The direction
  tests cover: a closing reverser re-held after 3 readings; revocation stays
  permanent; an opening reverser stays released; a stationary pair is
  releasable; jitter does not flap; rotate in place; STALE freezes the check;
  legacy A19 is unchecked; the floor; key off is a no-op; a rejected-leg
  closing case; config and validation; the node's scene path. The tests for
  this step were written before the code but not run red first. The earlier
  tests cover:
  - key on and off for P1, P2 and P3;
  - the vp10 geometry: reversers released, continuing robot held;
  - rejected legs, including a rejection that arrives after capture and one
    with no latch at command start;
  - a reverser closing on a waived robot;
  - the convoy, junction-crossing and S6 sequences;
  - the loader, the startup line and the fragment;
  - the node's log lines.
- The full `tests/unit` failing-id set is identical to the base's: 57 failed
  and 3 errors, all from aruco/pxr environment issues.

---

## Replay Regression

**Method.** `data/logs/vm_runs/safety_exemption_analysis/regression_2026_11_14.py`
(gitignored) re-drives the tracker from reconstructed streams. Commands and
statuses come from the bus log lines. Parameters come from the decision
artifacts. `plan_continue_partners` are recomputed as M5 at 68e67b5 computes
them. Yield phases are inferred from the bus ACTIVE publishes and
`gate_admit` lines.

At every ground-truth row (5 Hz) the script runs the monitor's sequence with
GT positions standing in for M1, four times:

- key off;
- key on (current code, with the direction check);
- key on without the direction check;
- key on with the 2026-11-13 A19 inputs.

**Validation.** The key-off exemption timelines match the logged
`exempt pairs changed` lines 100% in tranche 1, Stage 1, IB10 closure and all
11 IB10 live bundles. They are also identical to the 68e67b5 tracker's over 59
bundles (`base_identity.txt`).

**Limits.** This is a what-if on recorded trajectories.

- The trajectories were produced under key-off behaviour. A robot that would be
  held or released differently would have moved differently afterwards, so
  every hold or release after the first divergence is indicative only.
- GT positions replace M1. STALE status and M1 error are not modelled.
- Older bundles (pre-10-03) ran different code, and some have few clock
  anchors.

"Exemptions lost" counts pairs that are exempt with the key off, not exempt
with the key on, and inside 0.45 m. It says nothing about whether the
manoeuvre needed the pair (see the itemisation below).

| Set | Bundles | Exemptions lost (<0.45 m) | New holds vs key off | Releases vs 11-13 key-on | Direction revocations |
|---|---|---|---|---|---|
| tranche 1 | 10 | 0 | 0 | 0 | 0 |
| Stage 1 | 7 | 0 | 0 | 0 | 0 |
| IB10 closure | 5 | 0 | 0 | 0 | 0 |
| IB10 live (e01-e10) | 11 | 1 (e09) | 1 | 1 | 0 |
| convoy/B3 + S6 | 8 | 0 | 0 | 0 | 0 |
| older (verbatim, Oct smokes, remedy, step7b, step0) | 27 | 5 | 41 | 3 | 0 |

**Wording correction.** Rev 1 said "every other set loses nothing". That
holds only for tranche 1, Stage 1, IB10 closure and convoy/B3 + S6. With the
key on, 6 exemptions are lost: 1 in IB10 live e09 and 5 in the older set.

**Direction check on the recordings.** It revokes none of the 4 releases, so
no completed manoeuvre would stall because of it. Gap profiles are in
`release_gap_profiles.txt`.

| Release | Gap start → end | Largest shrink below widest | Margin to 0.05 m |
|---|---|---|---|
| vp10 `1296b5b8` robot_1 vs robot_3 | 0.354 → 0.454 | 0.000 | 0.050 |
| vp10 `1296b5b8` robot_2 vs robot_3 | 0.244 → 0.453 | 0.005 | 0.045 |
| vp10 `6fdbc5c7` robot_1 vs robot_4 | 0.424 → 0.450 | 0.039 (arcing backup closes first) | 0.011 |
| e09 `a73d6e03` robot_4 vs robot_1 | 0.402 → 0.457 | 0.046 recorded; 0.000 with robot_1 frozen | 0.004 / 0.050 |

- **e09.** The recorded shrink comes from robot_1 moving, and robot_1 is the
  robot the key-on monitor holds. With robot_1 frozen at its start, the gap
  only opens.
- **vp10 `6fdbc5c7`.** The 0.039 m close-then-open is robot_1's own arcing
  backup against a stationary robot_4. A tolerance at or below about 0.035 m
  would re-hold this recorded, completed reverse. 0.05 m is the smallest round
  value with a margin over it.

**Exemptions lost with the key on, itemised:**

| # | Bundle | Command | Pair | Window (sim) | Min distance | Needed to complete? |
|---|---|---|---|---|---|---|
| 1 | vp10 | `1296b5b8` reverse | robot_1+robot_3 | 68.2-69.5 | 0.354 m | Replaced by a third-robot waiver: robot_1 is released and opens the gap. Not lost in effect (inferred). |
| 2 | vp10 | `1296b5b8` reverse | robot_2+robot_3 | 68.2-72.1 | 0.244 m | Same as #1 for robot_2 (inferred). |
| 3 | vp10 | `1296b5b8` reverse | robot_3+robot_4 | 72.8-82.1 | 0.210 m | Cannot tell. The latch forms during the window as robot_3 chases robot_4, so key on would hold robot_4 to its recorded end at 82.1. Under key on, robot_3 is held from 68.2 to 72.1, so the chase may not happen. |
| 4 | vp10 | `6fdbc5c7` reverse | robot_1+robot_4 | 180.4-185.1 | 0.385 m | Replaced by a third-robot waiver; passes the direction check with a 0.011 m margin (inferred). |
| 5 | Oct-2 IB10 `live` smoke | `4362ae38` reverse | robot_1+robot_4 | 99.3-300 | 0.295 m | Verified that the recorded run had no such exemption: it latched robot_1/robot_4 9 s into the reverse, and the reverse never went terminal (step-7a finding 3). Key on reproduces that stall. Only 2 clock anchors. |
| 6 | IB10 live e09 | `a73d6e03` junction recede | robot_1+robot_4 | 111.1-114.1 | 0.373 m | Replaced by a third-robot waiver: robot_4 released, robot_1 held 1.6 s; the gap only opens with robot_1 frozen (inferred). |

**vp10 acceptance.** The start-time latch no longer holds the reversers, so
vp10 now passes the approved criterion. A later finding remains:

- From sim 72.8 to 82.1 of the recorded trajectory, robot_3 drives after the
  reversing robot_4 and closes from 0.449 m to 0.210 m.
- With the key on, that latch forms during the window, so it holds both robots,
  robot_4 included.
- Under key on, robot_3 would have been held from sim 68.2 to 72.1, so the
  recorded chase may not have happened. Replay cannot tell.

**Oct-2 IB10 live smoke.** The 38 new holds of robot_1 rest on 2 clock anchors.
They reproduce the recorded step-7a finding 3: robot_1 drove into the
reversing robot_4 during the window, which A19 does not waive by design.

**IB10 e09, robot_1 + robot_2 at 0.263 m (sim 295.5).** This pair is exempt
through the junction-crossing yield's own-command scope (P5): robot_2 is
`crossing_order[0]` of robot_1's yield. It stays exempt from sim 260.1 to the
end of GT at sim 300.0. The key changes nothing here: the replay with the key
on is identical. The floor (0.20 m) was not reached.

**Convoy and intersection.**

- The convoy passers stay exempt against the yielder as they are admitted.
- Every junction recede, cross and release phase keeps its pairs.
- Neither loses any exemption with the key on.

---

## Open Items

- Live validation: the key-on startup line on the VM, one IB10 plain-reverse
  episode and one convoy episode.
- P3 has no recorded instance: 0 legs were rejected across all bundles.
- The direction check covers the third-robot path only; extending it to every
  A19 waiver is a proposal (above).
- Item #3 (vp10, robot_3 chasing reversing robot_4) and item #5 (finding 3)
  are latches formed during the window; neither key setting waives them.
- The S6 four-robot reverse reached GT contact (0.149 m) under P5 own-command
  scope with the floor off. This is P5 and out of scope here.
