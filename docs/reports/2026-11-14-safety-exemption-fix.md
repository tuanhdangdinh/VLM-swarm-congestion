# Safety Exemption Scope: Fix and Replay Regression

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: the `scoped_clearing_exemption` fix (P1-P3 plus the owner-approved A19 input change), its unit tests, and the replay regression over 68 recorded bundles (59 earlier plus 9 new IB10 live).

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
| P4 mutual waivers | unchanged | unchanged |
| P5 own-command scope | unchanged | unchanged |

**A19 with the key on.** Say a clearing robot starts its command already
latched with an unhonoured partner or a rejected-leg robot.

- The clearing robot is released (one-sided waiver). The other robot stays held.
- If the rejection status arrives after the waiver capture, it is applied to
  the latches that stood at command start.
- A latch that forms during the window still holds both robots, exactly as A19
  already does.

**What A19 does not require.** A waiver has no direction check. A released
reverser that drives toward the held robot instead of away stays released
until the pair separates. The only backstop is `hard_contact_floor_m`, which
is 0.20 m in the experiment kits and 0.0 in the base `safety.yaml`. Pinned by
the tests `test_waived_reverser_closing_*`.

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
  - Two log lines that are emitted only when the key is on.
- **`config/safety/scoped_clearing_exemption.fragment.yaml`** is an overlay
  fragment. The pinned safety files are not edited.
- **Kit rule.** Merge the fragment into the safety file the kit installs. In
  every episode, assert `scoped_clearing_exemption=True` from the monitor's
  startup line, not from the yaml. The loader falls back to key off on any
  read error.

---

## Tests

- `tests/unit/test_safety_exemption_scope.py` has 50 tests. They cover:
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
GT positions standing in for M1, three times:

- key off;
- key on;
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

| Set | Bundles | Needed exemptions lost | New holds vs key off | Releases vs 11-13 key-on |
|---|---|---|---|---|
| tranche 1 | 10 | 0 | 0 | 0 |
| Stage 1 | 7 | 0 | 0 | 0 |
| IB10 closure | 5 | 0 | 0 | 0 |
| IB10 live (e01-e10) | 11 | 1 (e09) | 1 | 1 |
| convoy/B3 + S6 | 8 | 0 | 0 | 0 |
| older (verbatim, Oct smokes, remedy, step7b, step0) | 27 | 5 | 41 | 3 |

**Released pairs** (key on releases a robot that the 2026-11-13 key-on held)
and their minimum recorded distance while waived:

- vp10 `1296b5b8`, from sim 68.2: robot_1 released against robot_3
  (0.354 m) and robot_2 against robot_3 (0.244 m). robot_3, the `continue`
  robot, is held.
- vp10 `6fdbc5c7`, from sim 180.4: robot_1 released against robot_4 (0.385 m).
- IB10 live e09 `a73d6e03` junction recede, from sim 111.1: robot_4 released
  against robot_1 (0.373 m). robot_1 is a plan `continue` partner, a live P1
  instance, and is held for 1.6 s.

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
- A19's missing direction check (above) is unchanged and out of scope.
- The S6 four-robot reverse reached GT contact (0.149 m) under P5 own-command
  scope with the floor off. This is P5 and out of scope here.
