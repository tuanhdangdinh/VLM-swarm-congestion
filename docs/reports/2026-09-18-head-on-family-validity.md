# Head-On Asymmetric Family - Validity Evidence

**Prepared:** 2026-09-18

**Revision history:**

- Initial draft: T1 control run (`head_on_asymmetric_wopen_eopen_o0`, mock backend) on the GPU VM, plus the VM sync and artifact-build verification that preceded it.
- Rev 2 (2026-09-19): corrected the T1 root-cause conclusion. The original "Root cause" section named an M4 defect as the cause of `robot_1`'s failure to arrive; that conclusion is wrong. The actual cause is `build_backend`'s mock branch (`reasoning/vlm/backend_factory.py`) collapsing `VGU_MOCK_DECISION_FILE` to a single repeated decision, so M2 replayed "deadlock / yield" on all 16 analyses instead of reporting `congestion_detected=false` once the scene cleared. The resume/cancel forensics in the original section are accurate and preserved — they are the *mechanism* by which the repeated commands stopped `robot_1`, not evidence of an independent M4 bug. The original text is marked superseded rather than removed; see "Root cause (revised)" below and the corrected Entry Criteria bullet. Fixed in the same commit by giving `VGU_MOCK_DECISION_FILE` an optional scripted-sequence form (`config/mock_decisions/head_on_yield_once.json`, `head_on_yield_robot_2_once.json`).
- Rev 3 (2026-09-19): added "Validity Pairs (T2a)" — the four forced-yielder runs (Task 8) that test each T2a variant's frozen `oracle:` block against both yielder orders, with the run_id rows added to the mapping table below. Both variants pass: the oracle-infeasible yielder's maneuver ends `FAILED` in each, with the yielding robot stalled against its blocker's near face, and the oracle-feasible yielder's maneuver completes with both robots reaching their goals. The Rev 2 verification gate on the M4 resume race is met (130.17 s and 131.23 s uninterrupted navigation windows against a 17 s requirement), so that race remains latent and does not block Task 9.
- Rev 4 (2026-09-19): added "RQ5 recovery runs (gpt-4o), modality A/B" — two recorded live-model runs (Task 9) on the blocked variant `head_on_asymmetric_w0p2_eopen_o0`, paired on the static-obstacle prompt modality (Run A `20260919_042935` OFF, Run B `20260919_044729` ON). Both runs opened with `yield` naming `robot_1`, the robot the parked box makes it impossible for, and both first maneuvers ended `FAILED` with the chassis 0.093–0.094 m from the blocker's near face — indistinguishable outcomes, so supplying the obstacle's geometry produced no measurable change in the decision under test. The failure-context block reached the next prompt in both runs and both second decisions were `reverse`, which M4 dispatches symmetrically and which therefore cannot resolve a two-robot head-on; neither run produced an arrival. The section records why first-answer yielder identity is not evidence of spatial reasoning (it is confounded with `involved_robots` order, and under Run A the blocker is not perceivable at all), and verifies the modality end-to-end from the rendered prompt stored in each decision artifact rather than from build output.
- Rev 5 (2026-09-19): one factual refinement to the Rev 2 correction, using Task 8's own evidence. Rev 2 called the M4 resume race "real but **latent**, needing a pathological repeat-command stream." Task 8's forced-yielder runs show it reproducing on a **single** dispatched command (7–8 cancels over 14–15 s in Runs 2 and 4) but **self-limiting** — the churn stops on its own and the resuming robot still gets its full window (130.17 s / 131.23 s against the 17 s gate). Rev 2's causal story for T1 still holds: the frozen mock's ~38 s re-triggers kept re-issuing commands before the churn could settle, which is why `robot_1` never progressed in that run — but "latent, needs a pathological stream" is too strong and is reworded to "reproduces on a single command, is self-limiting, and did not prevent arrival here, but still needs its own investigation." The three passages carrying the stale wording ("Root cause (revised)" → "What remains open", the T2a navigation-window-gate conclusion, and the Entry Criteria bullet) are corrected in place with the original text kept and marked superseded, not deleted.
- Rev 6 (2026-09-19): two related corrections from the final whole-branch review (Finding 1), retro-applying the same reasoning the "First-answer yielder identity is not evidence of spatial reasoning" section (below) already applies to Runs A/B, to the pre-existing 524-artifact census and comparability claims. (a) The "Run A ... comparable with every decision artifact collected to date" line and the "Run A's comparability with the pre-feature artifacts is backed by the pinned prompt-hash guard" line (both below) overstate what `test_build_prompt_payload_off_prompt_is_byte_identical_to_pre_feature_prompt` proves. Rendering the shared `_request()` fixture at branch base `e21326f` (3171 chars, sha `5a57c937…`) versus HEAD with the obstacle modality off (3338 chars, sha `3b77d224…`) gives a 167-char delta: Task 11's three `yield_robot` prompt edits (FR2.1.9), which have no OFF condition and landed in the same window as the obstacle modality. The pinned guard (provenance commit `056fa22`) is against the tree *after* those edits, so it isolates the obstacle modality correctly but does not establish that Run A's OFF prompt matches the pre-2026-09-19 stimulus. Both passages are marked superseded in place below, not deleted. (b) The 44/44 `robot_1`-first census (design review Finding 2, cited via module-2 FR2.1.9) was collected under a prompt that *instructed* "first listed robot backs up" — the same clause Task 11 removed — so it is substantially evidence of compliance with an explicit instruction, not only evidence that an unused channel went unused. Full reasoning: `docs/specs/module2_vlm_reasoning.md` FR2.1.8/FR2.1.9.

---

## Scope

This report collects the hardware evidence for the `head_on_asymmetric` scenario
family. It records, per run, the `run_id` mapping, the M2/M3/M4 pipeline counts,
and the arrival outcome. Tasks 8 and 9 append their own sections.

`VGU_RUN_ID` is the launch timestamp only; it does not encode the backend or the
mock decision file. The mapping table below is the sole record of that
association.

---

## Run ID Mapping

| run_id | Scenario | Backend | Mock decision file | Start (UTC) | End (UTC) | Outcome |
|---|---|---|---|---|---|---|
| `20260918_183831` | `head_on_asymmetric_wopen_eopen_o0` | mock | `/ws/config/mock_decisions/head_on_yield.json` | 2026-09-18T18:38:31Z | 2026-09-18T18:41:52Z | Aborted - M5 `ImportError` at startup (stale install tree) |
| `20260918_184400` | `head_on_asymmetric_wopen_eopen_o0` | mock | `/ws/config/mock_decisions/head_on_yield.json` | 2026-09-18T18:44:00Z | 2026-09-18T19:00:20Z | Partial - `robot_2` reached goal, `robot_1` did not (frozen mock replayed the yield decision; see "Root cause (revised)") |
| `20260919_033142` | `head_on_asymmetric_w0p2_eopen_o0` | mock | `/ws/config/mock_decisions/head_on_yield_once.json` | 2026-09-19T03:31:42Z | 2026-09-19T03:41:19Z | Forced `robot_1` (blocked) - yield `FAILED` as the oracle predicts |
| `20260919_034224` | `head_on_asymmetric_w0p2_eopen_o0` | mock | `/ws/config/mock_decisions/head_on_yield_robot_2_once.json` | 2026-09-19T03:42:24Z | 2026-09-19T03:53:41Z | Forced `robot_2` (open) - yield `COMPLETED`, both robots reached their goals |
| `20260919_035429` | `head_on_asymmetric_wopen_e0p2_o0` | mock | `/ws/config/mock_decisions/head_on_yield_robot_2_once.json` | 2026-09-19T03:54:29Z | 2026-09-19T04:03:42Z | Forced `robot_2` (blocked) - yield `FAILED` as the oracle predicts |
| `20260919_040414` | `head_on_asymmetric_wopen_e0p2_o0` | mock | `/ws/config/mock_decisions/head_on_yield_once.json` | 2026-09-19T04:04:14Z | 2026-09-19T04:14:25Z | Forced `robot_1` (open) - yield `COMPLETED`, both robots reached their goals |
| `20260919_042935` | `head_on_asymmetric_w0p2_eopen_o0` | `openai` (gpt-4o), live | none - obstacle modality **OFF** (`prompt_static_obstacles: false`) | 2026-09-19T04:29:35Z | 2026-09-19T04:44:12Z | Run A - model chose `yield` / `yield_robot=robot_1` (infeasible); `FAILED` after 254.7 s, then `reverse` also `FAILED`; no arrivals |
| `20260919_044729` | `head_on_asymmetric_w0p2_eopen_o0` | `openai` (gpt-4o), live | none - obstacle modality **ON** (`prompt_static_obstacles: true` + `static_obstacles`) | 2026-09-19T04:47:29Z | 2026-09-19T05:02:08Z | Run B - same first answer `yield` / `yield_robot=robot_1`; `FAILED` after 254.0 s, then `reverse` also `FAILED`; no arrivals |

---

## Environment and Artifact Build

All three family scenarios were synced to the VM and built before the control
run. Every artifact was verified by content, not by existence.

### Map installation

`colcon build --merge-install --packages-select swarm_simulation` installed all
six `warehouse_map_head_on_asymmetric_*` files. The control map matches the
worktree source byte for byte:

```text
96113d926af758682de3dd96c995e67e  (worktree) ros2_ws/src/.../warehouse_map_head_on_asymmetric_wopen_eopen_o0.pgm
96113d926af758682de3dd96c995e67e  (container) /ws/ros2_ws/install/share/swarm_simulation/maps/warehouse_map_head_on_asymmetric_wopen_eopen_o0.pgm
```

### Scenario USDs

All three stages built with exit code 0 and fresh mtimes (`18:36` on
2026-09-18), ruling out the known stale-USD failure mode:

```text
########## BUILD head_on_asymmetric_w0p2_eopen_o0 exit=0 18:36:05 ##########
########## BUILD head_on_asymmetric_wopen_e0p2_o0 exit=0 18:36:30 ##########
########## BUILD head_on_asymmetric_wopen_eopen_o0 exit=0 18:36:55 ##########
```

The stages are USD crate (binary), so the blocker prims were verified with a
`pxr` traversal inside Isaac's Python rather than a text search:

```text
=== head_on_asymmetric_w0p2_eopen_o0.usd ===
  /World/Scenario/StaticObstacles | Xform
  /World/Scenario/StaticObstacles/blocker_west | Cube | CollisionAPI | {'xformOp:translate': Gf.Vec3d(-1.85, 0.0, 0.25), 'xformOp:scale': Gf.Vec3f(0.15, 0.15, 0.25)} | size=2.0
=== head_on_asymmetric_wopen_e0p2_o0.usd ===
  /World/Scenario/StaticObstacles | Xform
  /World/Scenario/StaticObstacles/blocker_east | Cube | CollisionAPI | {'xformOp:translate': Gf.Vec3d(1.85, 0.0, 0.25), 'xformOp:scale': Gf.Vec3f(0.15, 0.15, 0.25)} | size=2.0
=== head_on_asymmetric_wopen_eopen_o0.usd ===
  /World/Scenario/StaticObstacles | Xform
```

`size=2.0` with `scale=(0.15, 0.15, 0.25)` gives a 0.3 x 0.3 x 0.5 m box
resting on the floor (`translate.z = 0.25`), matching the family design. The
`wopen_eopen` control carries an empty `StaticObstacles` scope and no blocker,
as intended.

---

## T1 Control

### Configuration

| Key | Value |
|---|---|
| run_id | `20260918_184400` |
| Scenario | `head_on_asymmetric_wopen_eopen_o0` (T1 control, no blocker) |
| Backend | `mock` (forced by `MOCK_DECISION_FILE`) |
| Mock decision | `/ws/config/mock_decisions/head_on_yield.json` (`strategy: yield`) |
| Map | `warehouse_map_head_on_asymmetric_wopen_eopen_o0.yaml` |
| Spawns | `robot_1` (-1.5, 0.0, yaw 0.0); `robot_2` (1.5, 0.0, yaw pi) |
| Goals | `robot_1` (2.5, 0.0); `robot_2` (-2.5, 0.0) |
| Start / End (UTC) | 2026-09-18T18:44:00Z / 2026-09-18T19:00:20Z |
| Session | `session_id=5eebc2b27b624f8288a7d4765958914b` |

### Pipeline counts

| Metric | Count |
|---|---|
| M2 analyses started | 16 |
| M2 decision artifacts written | 16 |
| M3/M4 dispatches | 32 (2 per decision, one per robot) |
| `robot_1` base-goal arrivals | 0 |
| `robot_2` base-goal arrivals | 16 (re-logged once per cycle) |
| M5 tracebacks / import errors | 0 |
| M4 safety stops (`min_distance_violation`) | 1372 |

### Timeline

The congestion formed and the pipeline fired on its first cycle:

```text
[1789757116.086966222] [orchestrator_node]: session_id=5eebc2b27b624f8288a7d4765958914b run_id=20260918_184400
[1789757154.764957120] [orchestrator_node]: starting analysis request=4ee9afb83a834877a0218bdc7ec2a16d robots=['robot_2'] reason=1 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_2': 2.58}
[1789757155.189685529] [orchestrator_node]: decision artifact written: data/logs/m5_decisions/4ee9afb83a834877a0218bdc7ec2a16d.json
[1789757155.192704527] [orchestrator_node]: dispatch request=4ee9afb83a834877a0218bdc7ec2a16d command=4ee9afb83a834877a0218bdc7ec2a16d-yield robot=robot_1
[1789757155.194751145] [orchestrator_node]: dispatch request=4ee9afb83a834877a0218bdc7ec2a16d command=4ee9afb83a834877a0218bdc7ec2a16d-yield robot=robot_2
```

| Event | Epoch | UTC | Offset from M5 start |
|---|---|---|---|
| M5 session start | 1789757116.087 | 18:45:16.086 | 0 s |
| First M2 analysis | 1789757154.765 | 18:45:54.764 | +38.7 s |
| First M3/M4 dispatch | 1789757155.192 | 18:45:55.192 | +39.1 s |
| `robot_2` arrival | 1789757324.587 | 18:48:44.587 | +208.5 s |
| `robot_1` arrival | - | never | - |
| Last M2 analysis | 1789757871.605 | 18:57:51.604 | +755.5 s |

The first analysis at +38.7 s falls inside the scenario's declared
`onset_window_sec: [8.0, 40.0]`.

`robot_2` reached its goal:

```text
[1789757324.587262782] [orchestrator_node]: robot robot_2 arrived at base goal (-2.5, 0.0)
```

### Outcome: success criterion not met

`robot_1` never reached `(2.5, 0.0)`. It stalled at a fixed distance and stayed
there for the remaining nine minutes, re-triggering an identical analysis every
~38 s:

```text
[1789757331.447286292] [orchestrator_node]: starting analysis request=d5334cc8e1c1496e8e8414cbd58aebbd robots=['robot_1'] reason=1 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_1': 3.78}
[1789757408.088446098] [orchestrator_node]: starting analysis request=247ad7ffaa8d4b85b703d803fa83b817 robots=['robot_1'] reason=1 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_1': 3.73}
[1789757871.604911587] [orchestrator_node]: starting analysis request=bdf2d052c39b445fbdbed18296024e74 robots=['robot_1'] reason=1 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_1': 3.73}
```

`distance_to_goal_m` for `robot_1` is pinned at `3.73` from 18:50:08 onward. A
live probe of `/perception/scene_state` at 18:55:20 confirms both robots
stationary and both still holding the yield command's wait task:

```text
stamp 1789757720.8408062
robot_2  x= -2.462 y= -0.003 theta= -0.12 v= 0.000 status=STOPPED  task=temporary_wait goal=None
robot_1  x= -1.226 y=  0.149 theta= -0.68 v= 0.000 status=STOPPED  task=temporary_wait goal=None
```

### Root cause (superseded): M4 cancels every base-mission resume it issues

> **Superseded by Rev 2 (2026-09-19).** This section's conclusion — that an
> M4 defect in `coordination_client_node`'s resume path caused `robot_1`'s
> failure to arrive — is wrong. The forensic counts below (resume/cancel
> tallies, timings, the safety-monitor ruling-out) are accurate and are kept
> as originally recorded. They describe the *mechanism* by which `robot_1`
> was repeatedly stopped, not the *cause*. See "Root cause (revised)"
> immediately below for the corrected analysis.

`robot_1`'s failure was traced to the M4 command layer, not to the scenario
geometry, the map, or the mock backend's frozen decision.

**The safety monitor is ruled out.** `safety stop robot=robot_1` fires 686 times
*before* `robot_2` arrives and **0 times after** — once the aisle cleared,
nothing was holding `robot_1` on safety grounds.

**`robot_1` was repeatedly commanded to move, and never got to finish.** M4
issued `resume base mission robot=robot_1 goal=(2.5, 0.0)` 30 times, and Nav2
accepted 85 `Begin navigating` goals — with **zero** successes:

| `robot_1` Nav2 (`/robot_1/navigate_to_pose`) | Count |
|---|---|
| `Begin navigating` | 85 |
| `Goal canceled` | 84 |
| Goals succeeded | 0 |
| `resume base mission` (M4) | 30 |
| `cancel-all robot=robot_1` (M4) | 260 |

Every navigation window was cut short — median **0.70 s**, max **18.21 s**, none
over 30 s. Covering the remaining 3.73 m needs an uninterrupted window far
longer than any it received.

**The cancel comes from M4 itself, immediately after its own resume.** Each
`resume base mission` is followed by a `cancel-all` a median of **0.11 s** later
(min 0.05 s, max 0.32 s). A window around one resume shows
`coordination_client_node` emitting the resume twice and then cancelling the
goal it had just placed (`goals_canceling=1`):

```text
[1789757352.347419904] [coordination_client_node]: resume base mission robot=robot_1 goal=(2.5, 0.0)
[1789757352.360392073] [command_bus_node]: status published command=d5334cc8e1c1496e8e8414cbd58aebbd-yield robot=robot_1 status=COMPLETED
[1789757352.467610355] [coordination_client_node]: resume base mission robot=robot_1 goal=(2.5, 0.0)
[1789757352.554849075] [coordination_client_node]: cancel-all robot=robot_1 action=navigate_to_pose return_code=0 goals_canceling=0
[1789757352.579605450] [coordination_client_node]: cancel-all robot=robot_1 action=navigate_to_pose return_code=0 goals_canceling=1
[1789757352.598851613] [coordination_client_node]: cancel-all robot=robot_1 action=navigate_to_pose return_code=0 goals_canceling=1
```

So `coordination_client_node` emits duplicate base-mission resumes, and each
fresh resume's cancel-all step wipes the in-flight Nav2 goal the previous resume
had just started. `robot_1` is therefore commanded to its goal, cancelled within
a fraction of a second, and re-commanded — 30 times — never travelling far
enough to escape the stall detector, which re-triggers M2 every ~38 s and keeps
the cycle alive.

`robot_2` was unaffected because it reached its goal during the very first
yield, before the resume path was ever exercised for it.

This is an M4 defect in `coordination_client_node`'s resume path, and it is
**not** specific to the mock backend: any backend that resolves a yield and
resumes the base mission would hit the same race. It should be fixed before the
T2a comparisons are read as evidence about scenario asymmetry.

For completeness, the `failure_context` the loop fed back to M2 was
`executed=temporary_wait` 14 times and `executed=yield` once:

```text
[1789757446.188319212] [orchestrator_node]: request=40032f55952144279266496fa6886a92 failure_context attached command=247ad7ffaa8d4b85b703d803fa83b817-yield strategy=yield executed=temporary_wait outcome=completed
```

### Root cause (revised)

**Cause: the mock backend's decision file was a single frozen decision, not
a scene that changes.** T1's `VGU_MOCK_DECISION_FILE` pointed at
`head_on_yield.json`, one JSON object. Before this report's Rev 2,
`build_backend`'s mock branch (`reasoning/vlm/backend_factory.py:73-81`)
always wrapped that file's text in `MockBackend(response_text=...)`, which
returns the identical text on every call. M5 re-analyses whenever a robot
stalls, so all 16 of T1's M2 analyses — including the 15 that ran after
`robot_2` had already reached its goal and the aisle was empty — replayed
the same `congestion_detected=true / deadlock / yield [robot_1, robot_2]`
decision. A live backend does not do this: run 5 (2026-09-17, gpt-4o)
resolved in a single dispatch followed by 31 `none` answers, because the
failure-context loop reports `congestion_detected=false` once the scene
clears. A frozen mock structurally cannot report that, regardless of what M4
does with the commands it is given.

**Mechanism: the M4 resume/cancel behavior described above is real, and is
how the frozen decision turned into a stopped robot.** Every one of the
repeated "yield" decisions M3/M4 grounded and dispatched a fresh command to
`robot_1`; M4's documented ownership handoff cancels a robot's in-flight
Nav2 goal when a new command targets it. Sixteen repeated dispatches
therefore produced the exact resume/cancel forensics recorded above and
preserved unchanged: 30 `resume base mission` calls, 85 `Begin navigating`
goals, 84 cancels, 0 successes, a median 0.11 s from resume to cancel, and
the safety monitor ruled out (686 stops before `robot_2` arrived, 0 after).
Those counts are not evidence of an M4 bug firing under ordinary operation —
they are evidence of what 16 back-to-back identical commands to the same
robot do to any resume path that cancels on re-command. `robot_2` was
unaffected only because it happened to reach its goal during the very first
yield, before it was ever re-commanded.

**What remains open (superseded by Rev 5, 2026-09-19 — see below).** A resume
that gets cancelled a median of 0.11 s after it starts is unusual on its own
terms, independent of what caused the repeat-command stream. That is
recorded here as a real but **latent** M4 issue: it takes a pathological
repeat-command stream to manifest — which is exactly what the frozen mock
produced and what a live backend would not produce — so it did not block
this task, but it needs its own investigation before the codebase can assume
rapid successive commands to one robot are safe. It should not be read as
ruled out by this correction.

> **Refinement (Rev 5, 2026-09-19).** Task 8's four forced-yielder runs (see
> "Navigation-window gate (Runs 2 and 4)" below) show the resume/cancel churn
> reproducing on a **single** dispatched command — 7 cancels in 14.05 s
> (Run 2) and 8 in 15.48 s (Run 4) — not only under T1's repeated-decision
> stream. So "it takes a pathological repeat-command stream to manifest" is
> too strong: the race is reachable from one ordinary resume. What the two
> runs also show is that the churn is **self-limiting** — it stops on its own
> within roughly 15 s and the robot then gets a full, uninterrupted window
> (130.17 s and 131.23 s against Rev 2's 17 s gate) — so Rev 2's causal story
> for T1 still holds: the frozen mock's ~38 s re-triggers kept re-issuing
> commands before the churn could settle, which is why `robot_1` never
> progressed in that run. "Latent, needs a pathological stream" is reworded
> to: **the race reproduces on a single command and is self-limiting; it does
> not, by itself, prevent arrival, but it remains real and still needs its
> own investigation** — this paragraph's original wording is kept above,
> marked superseded rather than deleted, per this document's own convention.

**Fix landed in the same commit as this revision.** `build_backend`'s mock
branch now accepts either a single decision object (unchanged behaviour) or
a JSON array, which becomes a `MockBackend` scripted `response_sequence`
that holds its last entry once exhausted.
`config/mock_decisions/head_on_yield_once.json` and
`config/mock_decisions/head_on_yield_robot_2_once.json` are two-entry
sequences: the existing yield decision, then a `congestion_detected: false`
decision matching `MockBackend`'s default no-congestion response.
`head_on_yield.json` and `head_on_yield_robot_2.json` are left unchanged — a
later task still needs the frozen single-decision form for an arm where the
forced maneuver is expected to fail and therefore never produces a
resolution.

> **Update (Rev 3, 2026-09-19).** Task 8's four runs used the `*_once.json`
> sequences throughout and the frozen single-decision form was not needed
> even for the two arms whose forced maneuver fails: M4 terminates those
> maneuvers itself with `status=FAILED`, so the sequence advances normally.
> See "Validity Pairs (T2a)" below.

**Verification gate for Task 8.** When Task 8 next runs a one-shot arm
(mock decision file switched to the `*_once.json` sequence), `robot_1`
should receive an uninterrupted navigation window longer than 17 s after the
last command resolves. If it does not, the M4 resume race is not latent
after all, and Tasks 8/9 stop until it has its own fix — report rather than
tune.

### Other anomalies

- **Success-criterion token does not exist.** The planned criterion was a
  `base_mission ... COMPLETED` line for each robot. `base_mission` appears zero
  times in either the M5 or M4 log. The equivalent M5 signal is
  `robot <id> arrived at base goal (x, y)`, used above.

- **`robot_2` arrival is re-logged every cycle** (16 occurrences of one arrival).
  Arrival count is therefore not a usable metric; first-occurrence timestamp is.

- **1372 M4 safety stops** (`reason=min_distance_violation`) while the two robots
  were nose to nose, all of them before `robot_2` cleared the aisle. Expected for
  a head-on deadlock, noted for baseline.

---

## Validity Pairs (T2a)

Each T2a variant parks a 0.3 x 0.3 x 0.5 m collision box 0.2 m behind one
robot's spawn point and carries a frozen `oracle:` block naming the robot that
*can* feasibly yield. This section tests that claim directly: each variant was
run twice, forcing each robot in turn to be the yielder, and the maneuver's
terminal M4 status was read against the oracle. Four runs, no tuning of the
scenario, geometry, or thresholds.

### Configuration common to all four runs

| Key | Value |
|---|---|
| Launcher | `scripts/vm/fc_launch.sh` (`REC_SEC` 500/600, `SIM_SEC` 1200, `RECORD=0`) |
| Backend | `mock` (forced by `MOCK_DECISION_FILE`) |
| Mock decisions | the two-entry `*_once.json` sequences from `056fa22` |
| Map | `warehouse_map_<variant>.yaml` |
| Spawns | `robot_1` (-1.5, 0.0, yaw 0.0); `robot_2` (1.5, 0.0, yaw pi) |
| Goals | `robot_1` (2.5, 0.0); `robot_2` (-2.5, 0.0) |

The `*_once.json` files carry **no `yield_robot` field**, so
`resolve_robot_order` returns `involved_robots` unchanged and the first robot
listed becomes the yielder. This is deliberate: it selects the yielder purely
by list order and so also exercises the backward-compatible path that predates
`c4072d0`.

Using the scripted sequences instead of the frozen single-decision files had
the intended effect. Where T1 replayed the same yield decision across 16
analyses, these runs produced **3, 4, 3 and 3** analyses and **one** dispatched
congestion decision each; every later analysis returned the sequence's second
entry (`congestion_detected: false`) and dispatched nothing.

### Outcome

Full `run_id` -> (scenario, backend, mock file, start/end UTC, outcome) rows for
these four runs are in the Run ID Mapping table above, which this document
keeps as the sole record of that association.

| run_id | Variant | Blocker | Forced yielder | Oracle `feasible_yielders` | Expected | Observed |
|---|---|---|---|---|---|---|
| `20260919_033142` | `head_on_asymmetric_w0p2_eopen_o0` | west | `robot_1` (blocked) | `[robot_2]` | `FAILED`/`TIMED_OUT` | **`FAILED`** after 253.3 s |
| `20260919_034224` | `head_on_asymmetric_w0p2_eopen_o0` | west | `robot_2` (open) | `[robot_2]` | completes, both arrive | **`COMPLETED`**, both arrived |
| `20260919_035429` | `head_on_asymmetric_wopen_e0p2_o0` | east | `robot_2` (blocked) | `[robot_1]` | `FAILED`/`TIMED_OUT` | **`FAILED`** after 252.7 s |
| `20260919_040414` | `head_on_asymmetric_wopen_e0p2_o0` | east | `robot_1` (open) | `[robot_1]` | completes, both arrive | **`COMPLETED`**, both arrived |

All four cells match the frozen oracle. **Both T2a variants pass their
authoring-time validity check.**

### Run 1 - `w0p2_eopen`, `robot_1` forced (blocked)

The pipeline fired once and dispatched the yield to `robot_1`:

```text
[1789788817.767471684] [orchestrator_node]: starting analysis request=0edabe11d5024e7db2c108a82e391d0f robots=['robot_1'] reason=1 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_1': 2.6}
[1789788817.994172639] [orchestrator_node]: dispatch request=0edabe11d5024e7db2c108a82e391d0f command=0edabe11d5024e7db2c108a82e391d0f-yield robot=robot_1
[1789788818.063830035] [command_bus_node]: status published command=0edabe11d5024e7db2c108a82e391d0f-yield robot=robot_1 status=ACTIVE
```

The maneuver ran 253.3 s and ended in the expected terminal status:

```text
[1789789071.398963888] [command_bus_node]: status published command=0edabe11d5024e7db2c108a82e391d0f-yield robot=robot_1 status=FAILED
```

`robot_2`, the waiter, completed its `temporary_wait` in the same instant
(`... robot=robot_2 status=COMPLETED`). Neither robot reached its goal.

**The failure is the blocker, not a reporting artifact.** `robot_1`'s
trajectory over the 238 scene samples inside the maneuver window shows it
reversing out of the aisle and then stopping dead against the box:

```text
first  t=1789788818.4  robot_1 x=-0.101   robot_2 x=+0.092
min                    robot_1 x=-1.607 at t=1789788872.6
last   t=1789789071.4  robot_1 x=-1.606   robot_2 x=+0.090
```

The variant's generated header fixes the west blocker's near face at
`x = -1.700`. `robot_1` reached `x = -1.607` 54.6 s into the maneuver — its
rear against the box, roughly one rear-overhang (~0.09 m) short of the face —
and stayed within 1 mm of that spot for the remaining 198.8 s until the command
failed. It needed to clear `x = -2.079` (the corridor mouth at -1.0 plus the
oracle's `required_room_m = 1.079`) to park; the box stops it 0.472 m short.
`robot_2` never moved, so the aisle never opened.

The safety monitor is ruled out as the cause: it fired 7 times for `robot_1`
in the maneuver window, all inside the first 0.13 s, and never again.

### Run 2 - `w0p2_eopen`, `robot_2` forced (open)

```text
[1789789458.017818622] [orchestrator_node]: starting analysis request=8b7c66380b5c4d328a8ed345849329c7 robots=['robot_2'] reason=1 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_2': 2.61}
[1789789458.489324495] [orchestrator_node]: dispatch request=8b7c66380b5c4d328a8ed345849329c7 command=8b7c66380b5c4d328a8ed345849329c7-yield robot=robot_2
[1789789620.667555645] [command_bus_node]: status published command=8b7c66380b5c4d328a8ed345849329c7-yield robot=robot_2 status=COMPLETED
[1789789620.669820295] [command_bus_node]: status published command=8b7c66380b5c4d328a8ed345849329c7-yield robot=robot_1 status=COMPLETED
```

Both robots reached their goals:

```text
[1789789620.861936412] [orchestrator_node]: robot robot_1 arrived at base goal (2.5, 0.0)
[1789789764.946377949] [orchestrator_node]: robot robot_2 arrived at base goal (-2.5, 0.0)
```

`robot_1` arrives 0.19 s after the command resolves because M4 escorts the
passer through the aisle inside the yield maneuver itself; Nav2 only handles
its last 0.06 m. `robot_2` is therefore the robot that resumes and has real
distance left to cover, and its window is measured below.

### Run 3 - `wopen_e0p2`, `robot_2` forced (blocked)

The mirror of Run 1, on the mirrored variant:

```text
[1789790185.775119335] [orchestrator_node]: starting analysis request=9df43174930f48d78f83d7bbd4e9c9af robots=['robot_2'] reason=1 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_2': 2.6}
[1789790186.273593583] [orchestrator_node]: dispatch request=9df43174930f48d78f83d7bbd4e9c9af command=9df43174930f48d78f83d7bbd4e9c9af-yield robot=robot_2
[1789790439.023566190] [command_bus_node]: status published command=9df43174930f48d78f83d7bbd4e9c9af-yield robot=robot_2 status=FAILED
```

`robot_2`'s trajectory across the 236 samples in the maneuver window:

```text
first  t=1789790186.6  robot_1 x=-0.113   robot_2 x=+0.105
max                    robot_2 x=+1.602 at t=1789790229.9
last   t=1789790438.2  robot_1 x=-0.113   robot_2 x=+1.602
```

The east blocker's near face is at `x = +1.700`. `robot_2` reached `x = +1.602`
43.6 s in and held it for the remaining 209.1 s — the same 0.098 m standoff,
the same stall, the same terminal status as Run 1's west arm. `robot_1` did not
move at all (`x = -0.113` throughout). Neither robot reached its goal.

### Run 4 - `wopen_e0p2`, `robot_1` forced (open)

```text
[1789790769.043133265] [orchestrator_node]: starting analysis request=75c3424155b246aa8a71b41153b25294 robots=['robot_1'] reason=1 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_1': 2.59}
[1789790769.398558500] [orchestrator_node]: dispatch request=75c3424155b246aa8a71b41153b25294 command=75c3424155b246aa8a71b41153b25294-yield robot=robot_1
[1789790928.810015783] [command_bus_node]: status published command=75c3424155b246aa8a71b41153b25294-yield robot=robot_1 status=COMPLETED
```

Both robots reached their goals:

```text
[1789790939.526735134] [orchestrator_node]: robot robot_2 arrived at base goal (-2.5, 0.0)
[1789791075.557042902] [orchestrator_node]: robot robot_1 arrived at base goal (2.5, 0.0)
```

As in Run 2 with the roles swapped, the passer (`robot_2`) is escorted clear
and finishes 10.7 s after the command resolves, leaving `robot_1` as the robot
that resumes with distance to cover.

### Navigation-window gate (Runs 2 and 4)

Rev 2 set a verification gate for this task: if the resuming robot cannot get
an **uninterrupted navigation window longer than 17 s** — the time it needs to
cover its remaining distance at 0.22 m/s — then the M4 resume race
(`coordination_client_node` cancelling a base-mission resume it just issued) is
not latent and Tasks 8/9 must stop.

Windows were measured from the per-robot Nav2 log (`fc_<run_id>_nav2_r{1,2}.log`)
as the interval between the **last** `Begin navigating` line after the
coordination command's terminal `status published ... COMPLETED` and the
`Goal succeeded` line that ends it, with no intervening `Goal canceled`. The
terminating event is a success, not a cancel, so counting only cancels would
have measured no window at all.

| run_id | Resuming robot | Window start (`Begin navigating`) | Window end (`Goal succeeded`) | Uninterrupted window | Gate (> 17 s) |
|---|---|---|---|---|---|
| `20260919_034224` | `robot_2` | `1789789634.766154644` from (1.22, -0.20) | `1789789764.936797498` | **130.17 s** | pass |
| `20260919_040414` | `robot_1` | `1789790944.316104865` from (-1.35, 0.19) | `1789791075.546648100` | **131.23 s** | pass |

Run 2:

```text
[1789789634.766154644] [robot_2.bt_navigator]: Begin navigating from current location (1.22, -0.20) to (-2.50, 0.00)
[1789789764.936797498] [robot_2.bt_navigator]: Goal succeeded
```

Run 4:

```text
[1789790944.316104865] [robot_1.bt_navigator]: Begin navigating from current location (-1.35, 0.19) to (2.50, 0.00)
[1789791075.546648100] [robot_1.bt_navigator]: Goal succeeded
```

Both clear the 17 s bar by a factor of about 7.7. **The gate is met: neither
run's resuming robot was starved of the window it needed, so the race did not
block arrival here.** (Superseded by Rev 5, 2026-09-19: the original wording
here — "the M4 resume race stays classified as latent" — overstated the
paragraph immediately below, which already shows the race reproducing on a
single dispatched command, not only under a pathological repeat-command
stream; see the "Refinement (Rev 5, 2026-09-19)" note in "Root cause
(revised)" above for the corrected classification.)

The race is nonetheless visible in both runs and is worth recording precisely,
because Rev 2 left it open. Immediately after the command resolves there is a
short burst of resume/cancel churn before navigation settles: Run 2 cancels 7
goals in the 14.05 s between `1789789620.72` and `1789789634.77` (longest slice
5.6 s), and Run 4 cancels 8 in the 15.48 s between `1789790928.84` and
`1789790944.32`. In both cases the churn then stops on its own and the robot
gets its full window. So the behaviour reproduces with a *single* dispatched
command — it is not purely an artifact of T1's repeat-command stream — but it
is self-limiting and does not prevent arrival. It still deserves its own
investigation; it does not block Task 9.

### Evidence

Per-run M1/M4/M5/Nav2/Isaac logs, the launcher log, the M5 scene JSONL, and the
run's decision artifacts are on the VM (git-ignored) under
`/home/ubuntu/vgu-vlm-swarm/data/logs/family_check_20260918/<variant>/<forced_yielder>/`:

```text
head_on_asymmetric_w0p2_eopen_o0/robot_1    9 files   4.0M   (run 20260919_033142)
head_on_asymmetric_w0p2_eopen_o0/robot_2   12 files   1.3M   (run 20260919_034224)
head_on_asymmetric_wopen_e0p2_o0/robot_2   19 files   3.8M   (run 20260919_035429)
head_on_asymmetric_wopen_e0p2_o0/robot_1   11 files   1.2M   (run 20260919_040414)
```

### VM state after the four runs

```text
--- stray procs (expect none) ---
(end)
--- gpu ---
136 MiB, 0 %
--- container ---
vgu_ros Up 12 seconds
--- ros2 nodes in container ---
(none)
--- backend_id source+install ---
reasoning_backend_id: openai
reasoning_backend_id: openai
```

Isaac Sim stopped after every run (its process outlives the launcher's EXIT
trap and was killed by hand each time, as Task 7 recorded), GPU back to its
136 MiB baseline, container restarted clean, and `reasoning_backend_id`
restored to `openai` in both the source and installed configuration after each
of the four runs.

---

## Harness Findings

Three defects were found and fixed on the way to the run. All three would have
recurred for Tasks 8 and 9.

### Sync: `--delete` destroys VM-only artifacts

The planned rsync had no exclude for `.env`, `ros2_ws/build|install|log`, or the
generated Isaac assets. A `--dry-run` listed these for deletion:

```text
deleting isaac/assets/warehouse/warehouse_base.usd
deleting isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.usda
deleting isaac/assets/robots/turtlebot3_burger/payloads/...
```

`.env` (the API key Tasks 8-9 need) and the warehouse/robot USD assets exist
only on the VM — they are build outputs, not repository content. The sync was
run with added `--exclude` rules for `.env`, `ros2_ws/build/`,
`ros2_ws/install/`, `ros2_ws/log/`, and the generated asset paths, reducing the
deletion list to zero. **Any future sync must carry these excludes.**

**Rev 3 (2026-09-19) addendum.** Task 8 re-ran the same `--dry-run --delete`
check before its runs. With every exclude above in place the deletion list was
still *not* empty — three VM-only files remained:

```text
deleting tmp_parse_scene.py
deleting data/rA_pstatus_copy.log
deleting scripts/probe_gemini_er2.py
```

None is a build output or a secret, but the result shows an exclude list
curated against one run's findings does not stay complete. Task 8 therefore
dropped `--delete` altogether and synced an explicit six-file list
(`reasoning/vlm/{backend_factory,models,prompt_builder}.py`,
`reasoning/rag/command_grounder.py`, and the two `*_once.json` decisions),
which makes deletion structurally impossible rather than merely excluded. The
stronger standing rule: **prefer an explicit file list with no `--delete`**;
reserve the full-tree form for when the VM genuinely needs pruning, and only
behind a dry-run whose deletion list you have read line by line.

That sync also showed why a presence check is not a content check. Before it,
`grep -c yield_robot` on the VM's `command_grounder.py` and `models.py`
returned non-zero, which looks like `c4072d0`/`0efd01e` had already landed —
but `md5sum` against the worktree disagreed on both files plus
`prompt_builder.py`. The non-zero counts came from a different branch's
implementation of the same field. Only the checksums were conclusive, and they
matched exactly after the sync. No `colcon` rebuild was needed for these runs:
`git show --stat` confirms none of the three commits touches `ros2_ws/src/`,
and everything they do touch is either imported via `PYTHONPATH=/ws` or read
from disk at runtime — so the Rev 2 mtime trap did not apply.

### Build: `rsync -a` mtimes silently defeat `colcon`

The first run died at M5 startup:

```text
[orchestrator_node-1] ImportError: cannot import name 'GeminiBackendConfig' from 'reasoning.vlm.models' (/ws/reasoning/vlm/models.py). Did you mean: 'OpenAIBackendConfig'?
```

The VM *source* was correct (this branch, no Gemini); the *installed* copy was
still a different branch's file. `colcon build` reported success in 1.47 s
without refreshing it, because `rsync -a` preserves source mtimes and this
branch's sources are older than the VM's previous build output:

```text
2026-09-17 16:33:58  SRC      ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py
2026-09-18 08:41:43  BUILD    ros2_ws/build/.../swarm_orchestrator/orchestrator_node.py
2026-09-18 08:41:43  INSTALL  ros2_ws/install/lib/python3.12/site-packages/swarm_orchestrator/orchestrator_node.py
```

setuptools `build_py` copies only when the source is newer, so the stale module
survived. `/ws/reasoning/` is not a ROS package — it is imported via
`PYTHONPATH=/ws` — so it *was* current, which is exactly why the two halves
disagreed.

The fix was to touch every source and wipe the build tree:

```bash
sudo find ros2_ws/src -type f \( -name '*.py' -o -name '*.yaml' -o -name '*.msg' -o -name '*.xml' \) -exec touch {} +
sudo docker exec vgu_ros bash -lc "rm -rf /ws/ros2_ws/{build,install,log} \
  && source /opt/ros/jazzy/setup.bash && cd /ws/ros2_ws && colcon build --merge-install"
```

All 5 packages rebuilt in 13.2 s; afterwards `grep -rl Gemini /ws/ros2_ws/install/`
returns nothing. **Tasks 8 and 9 inherit this freshly rebuilt workspace.** The
standing rule: *after any `rsync -a` to the VM, a plain `colcon build` is not
sufficient* — touch the sources and wipe `build/ install/ log/`, or the run
silently executes another branch's code while reporting a successful build.

One piece of foreign-branch code remains on the VM by deliberate choice:
`reasoning/vlm/gemini_backend.py` (excluded from the sync so as not to delete
another branch's work). It is not a ROS package and is not rebuilt; it is inert
unless `reasoning_backend_id` is set to `gemini`, so it does not affect the
`openai` or `mock` runs.

### `scripts/vm/fc_launch.sh` live paths

This was the script's first execution against a real container. Its live paths
worked: scenario resolution from `isaac/config/scenarios/family/`, in-container
map check, spawn-pose parsing from the scenario yaml
(`robot_1 x=-1.5 y=0.0 yaw=0.0; robot_2 x=1.5 y=0.0 yaw=3.14159...`), staged
bring-up, `VGU_MOCK_DECISION_FILE` export, per-run log paths, and the
`reasoning_backend_id` rewrite-and-restore (verified restored to `openai` in
both the source and installed `orchestrator.yaml` after the run). No fault was
found in the script itself; the ImportError above was an environment fault that
the script correctly surfaced.

Two operational notes:

- The EXIT trap does **not** kill Isaac Sim. After cleanup ran, the
  `isaac.scripts.run_simulation` process was still alive and had to be killed by
  hand. The script's `pkill` fires, but the Isaac process outlives it.
- The script blocks in `tail -f` for `REC_SEC - 10` seconds. Killing that tail
  (`pkill -TERM -f "[t]imeout <N>s"`) is the clean way to end a run early: the
  script then falls through to its summary and EXIT trap, so the backend-id
  restore still fires. A `kill -9` on the script would skip the restore and
  leave the VM pinned to the run's backend.

---

## Final VM State

```text
--- stray procs (expect none) ---
(end)
--- gpu ---
136 MiB, 0 %
--- container ---
vgu_ros Up About a minute
--- backend_id source+install ---
23:reasoning_backend_id: openai
23:reasoning_backend_id: openai
```

Isaac Sim stopped, GPU idle at its 136 MiB baseline, container restarted clean
with no ROS 2 nodes running, and `reasoning_backend_id` restored to `openai` in
both the source and installed configuration.

Evidence for this run is on the VM (git-ignored) at
`/home/ubuntu/vgu-vlm-swarm/data/logs/family_check_20260918/control_wopen_eopen/`:
the M1/M4/M5/Nav2/Isaac logs, the launcher log, and the 16 decision artifacts
carrying `run_id=20260918_184400`.

---

## Entry Criteria for Tasks 8 and 9

- [x] Three family scenario USDs built and blocker prims verified as collision bodies.
- [x] Six family Nav2 maps installed into the `swarm_simulation` share directory.
- [x] `scripts/vm/fc_launch.sh` exercised live; no fault found in the script.
- [x] VM install tree rebuilt clean; no foreign-branch code remains.
- [ ] T1 control reaches both goals. **Not met** - `robot_1` did not arrive.
      **Superseded by Rev 2 (2026-09-19):** the line originally here attributed
      this to an M4 defect (`coordination_client_node` cancelling the Nav2
      goal its own base-mission resume just issued, median 0.11 s later, 30
      resumes, 0 successful navigations). Those counts are correct but the
      cause was the mock backend replaying the same "yield" decision on all
      16 analyses (`reasoning/vlm/backend_factory.py`'s mock branch collapsed
      `VGU_MOCK_DECISION_FILE` to one repeated response); see "Root cause
      (revised)" above. The resume/cancel behavior is a real but latent M4
      issue, not a confirmed defect blocking T2a. With the scripted-sequence
      fix in place, re-run T1 with `head_on_yield_once.json`; if `robot_1`
      still fails to arrive, the M4 resume race is not latent and Tasks 8/9
      stop until it has its own fix.
      **Resolved by Rev 3 (2026-09-19):** T1 itself was not re-run, but the
      condition this criterion exists to test was met on both T2a variants.
      In runs `20260919_034224` and `20260919_040414` the resuming robot got
      130.17 s and 131.23 s of uninterrupted navigation against a 17 s
      requirement and reached its goal, and both robots arrived in each run.
      The gate is met and Tasks 8/9 proceed; see "Navigation-window gate
      (Runs 2 and 4)" above, which also records the short resume/cancel burst
      — reproducing on a single dispatched command, self-limiting, and not
      preventing arrival — that remains open for its own investigation.
      **Refined by Rev 5 (2026-09-19):** "stays classified as latent" is
      corrected in "Root cause (revised)" above — the race is not confined to
      a pathological repeat-command stream, only self-limiting when it
      occurs.
- [x] Both T2a variants pass their authoring-time validity check (Task 8).

---

## RQ5 recovery runs (gpt-4o), modality A/B

Two live-model runs on `head_on_asymmetric_w0p2_eopen_o0`, the variant whose
parked box makes a yield by `robot_1` physically impossible. Task 8 established
that fact by forcing each yielder in turn; here the model decides for itself,
under two conditions that differ only in whether the prompt carries the box's
geometry.

- **Run A — obstacle channel OFF** (`prompt_static_obstacles: false`, the
  shipped default). The model cannot perceive the blocker through any channel.
  This is the information-bound condition and is comparable with every decision
  artifact collected to date. **Superseded by Rev 6**: comparable to every
  artifact collected *since* the `yield_robot` field landed (2026-09-19
  onward) — not to the pre-2026-09-19 corpus, since that field permanently
  changed the prompt in the same window with no OFF condition of its own.
- **Run B — obstacle channel ON** (`prompt_static_obstacles: true` with the
  `static_obstacles` list supplied). The model is told the box's id, centre and
  extent, and nothing about what they imply.

**The A/B contrast is the result.** Neither run's first answer means anything on
its own.

### Configuration

| Key | Run A | Run B |
|---|---|---|
| run_id | `20260919_042935` | `20260919_044729` |
| `prompt_static_obstacles` | `false` | `true` |
| `static_obstacles` | absent | `[{obstacle_id: obstacle_1, x: -1.85, y: 0.0, size_x_m: 0.3, size_y_m: 0.3}]` |
| Backend | `openai` (gpt-4o), live key sourced inside the container | same |
| Launcher | `scripts/vm/fc_launch.sh` (`RECORD=1`, `REC_SEC=780`, `SIM_SEC` default 1200) | same |
| M5 session | `c78150f576ee4c65b703359481845464` | `7009d9ab2cb7495e93eba4d92a1a8fbe` |
| Start / End (UTC) | 04:29:35Z / 04:44:12Z | 04:47:29Z / 05:02:08Z |

Both runs' `run_id` rows are in the Run ID Mapping table above, which this
document keeps as the sole record of that association.

### The modality was verified from the rendered prompt, not from build output

`bf2d89d` and `501bb49` modify `ros2_ws/src/swarm_orchestrator/`, which is
colcon-built rather than mounted live, so a skipped rebuild would have produced
an OFF run mislabelled as ON. Before Run A the VM's installed
`swarm_orchestrator/models.py` contained **zero** occurrences of
`prompt_static_obstacles`; after touching the sources, wiping
`ros2_ws/{build,install,log}` and rebuilding all five packages it contained two,
and all three installed orchestrator modules matched their sources by md5.

The decisive check is downstream of every build path: `write_decision_artifact`
persists the rendered prompt in each decision artifact. Across the two runs:

| | Run A | Run B |
|---|---|---|
| Prompts containing `obstacle_1` | **0 of 16** | **10 of 10** |
| First-decision prompt length | 3405 chars | 3641 chars |

The two first-decision prompts were diffed directly rather than inferred from
the length delta. **The only structural difference is the obstacle block plus
its one-sentence completeness clause**; everything else that differs is
sub-centimetre pose noise between two separate physical episodes
(`robot_1 x=-0.09` vs `-0.10`, pairwise distance 0.18 m vs 0.19 m). No section
is present in one prompt and absent from the other. The full diff:

```diff
-- robot_id=robot_1, x=-0.09, y=-0.02, theta=-0.20, status=STOPPED, linear_velocity=0.01
-- robot_id=robot_2, x=0.09, y=0.00, theta=-3.07, status=STOPPED, linear_velocity=0.00
+- robot_id=robot_1, x=-0.10, y=0.00, theta=0.05, status=STOPPED, linear_velocity=0.00
+- robot_id=robot_2, x=0.10, y=0.00, theta=-3.09, status=STOPPED, linear_velocity=0.00
-- robot_1 <-> robot_2: distance 0.18 m; ...
+- robot_1 <-> robot_2: distance 0.19 m; ...
+Static obstacles (world-frame axis-aligned boxes):
+- obstacle_1: centre (-1.85, 0.00) m, extent 0.30 x 0.30 m
+
 - Robots are roughly 0.3 m wide; ... do not re-derive distances or facing from the coordinates.
+   Fixed obstacles in the scene are listed above and are the only ones present; a robot can neither occupy nor drive through one.
```

Run B's prompt carries exactly the intended block and nothing more:

```text
Static obstacles (world-frame axis-aligned boxes):
- obstacle_1: centre (-1.85, 0.00) m, extent 0.30 x 0.30 m
```

The id is the deliberately neutral `obstacle_1`; it names neither the object's
role nor its side. The accompanying completeness clause was also rendered:
`Fixed obstacles in the scene are listed above and are the only ones present; a
robot can neither occupy nor drive through one.`

Run A's comparability with the pre-feature artifacts is backed by the pinned
prompt-hash guard: `tests/unit/test_prompt_builder.py` passes 37/37 on the
synced code, including
`test_build_prompt_payload_off_prompt_is_byte_identical_to_pre_feature_prompt`
and `test_shipped_orchestrator_yaml_obstacle_ids_do_not_leak_into_the_prompt`.
**Superseded by Rev 6**: that guard pins Run A's OFF prompt against the tree
after the `yield_robot` field (FR2.1.9) landed, not against the pre-2026-09-19
tree — it backs comparability among artifacts collected under this feature's
OFF default, not comparability with the pre-feature corpus.

### Run A — modality OFF

**First strategy: `yield`, targeting `robot_1`** — the robot with no retreat
space.

```text
[1789792297.489545030] [orchestrator_node]: starting analysis request=d33b77a6979d47bd8ab41c718266218f robots=['robot_2'] reason=1 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_2': 2.59}
[1789792302.794017507] [orchestrator_node]: dispatch request=d33b77a6979d47bd8ab41c718266218f command=d33b77a6979d47bd8ab41c718266218f-yield robot=robot_1
```

The artifact records `strategy=yield`, `involved_robots=['robot_1','robot_2']`,
`yield_robot=robot_1`.

**The maneuver failed:**

```text
[1789792557.539289431] [command_bus_node]: status published command=d33b77a6979d47bd8ab41c718266218f-yield robot=robot_1 status=FAILED
```

254.7 s after dispatch. `robot_2`'s `temporary_wait` completed in the same
instant.

**The previous-attempt block did reach the next prompt.** M5 logged it:

```text
[1789792588.871010555] [orchestrator_node]: request=800087d0128941cfad269618aeb28109 failure_context attached command=d33b77a6979d47bd8ab41c718266218f-yield strategy=yield executed=yield outcome=failed
```

and the stored prompt for that request contains it verbatim:

```text
Previous attempt in this episode:
- strategy=yield, yield_robot=robot_1, outcome=failed
- detail: yield failed after 255 s; congestion re-detected for the same robots
If the congestion is no longer present, report congestion_detected=false. If it persists and the previous strategy did not clear it, prefer a different strategy unless the scene has changed.
```

**Second decision: `reverse`**, dispatched to both robots:

```text
[1789792592.794368242] [orchestrator_node]: dispatch request=800087d0128941cfad269618aeb28109 command=800087d0128941cfad269618aeb28109-reverse robot=robot_1
[1789792592.796081018] [orchestrator_node]: dispatch request=800087d0128941cfad269618aeb28109 command=800087d0128941cfad269618aeb28109-reverse robot=robot_2
[1789792787.829972669] [command_bus_node]: status published command=800087d0128941cfad269618aeb28109-reverse robot=robot_1 status=FAILED
```

**Arrivals: none.** `arrived at base goal` appears zero times in the M5 log. The
remaining 13 analyses all returned `congestion_detected=false` and dispatched
nothing. Final scene: `robot_1 x=-1.606 STOPPED`, `robot_2 x=-1.777 STOPPED`,
against goals `(2.5, 0.0)` and `(-2.5, 0.0)`.

### Run B — modality ON

**First strategy: `yield`, targeting `robot_1`** — the same blocked robot,
with the box's geometry in the prompt.

```text
[1789793374.023551663] [orchestrator_node]: starting analysis request=05a0f4f516264e0b9351fea7ea575334 robots=['robot_1', 'robot_2'] reason=2 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_1': 2.6, 'robot_2': 2.6}
[1789793377.487267119] [orchestrator_node]: dispatch request=05a0f4f516264e0b9351fea7ea575334 command=05a0f4f516264e0b9351fea7ea575334-yield robot=robot_1
```

Artifact: `strategy=yield`, `involved_robots=['robot_1','robot_2']`,
`yield_robot=robot_1`.

**The maneuver failed:**

```text
[1789793631.499922846] [command_bus_node]: status published command=05a0f4f516264e0b9351fea7ea575334-yield robot=robot_1 status=FAILED
```

254.0 s after dispatch.

**The previous-attempt block reached the next prompt**, as in Run A:

```text
[1789793648.771319884] [orchestrator_node]: request=4c10dfe471a9426fa0b459f7f7d073d2 failure_context attached command=05a0f4f516264e0b9351fea7ea575334-yield strategy=yield executed=yield outcome=failed
```

**Second decision: `reverse`** (`bbc60e7e`), again dispatched to both robots
and again ending `FAILED` for `robot_1`:

```text
[1789793866.106914375] [command_bus_node]: status published command=bbc60e7ec5104931a20d64d6c02eacbd-reverse robot=robot_1 status=FAILED
```

The loop then kept cycling for the rest of the recording — `yield`
(`yield_robot=robot_2`), `reverse`, `yield` (`robot_2`), `reverse`, `yield`
(`robot_1`) — each completing in about 20 s, followed by two analyses returning
`decision=None`. Those two are **backend-stage failures, not no-congestion
answers** — both artifacts carry `terminal_stage=vlm`,
`failure_reason=decision=None`, i.e. M2 returned `ReasonerResult(decision=None)`
after its bounded retries. They coincide with both robots going `STALE` (their
markers overlapping) and with M5 reporting an empty `distance_to_goal_m={}`, so
the scene handed to M2 was already degenerate. **Arrivals: none.** Final scene: `robot_1 x=-1.608 STALE`,
`robot_2 x=-1.500 STALE`.

The two `yield_robot=robot_2` answers at +514 s and +597 s are **not** clean
evidence that the obstacle channel eventually worked: by then `robot_2` had been
driven west by the symmetric `reverse` and the analysis reported
`distance_to_goal_m={'robot_2': 1.0}`, so the scene the model was shown had
materially changed, and the preceding prompts also carried a previous-attempt
block. Modality, failure context and scene state are confounded at that point.

### Separating the two failure modes

The brief's one analysis trap is conflating "failed because the strategy cannot
work" with "failed because the chosen side has no retreat space". The trajectory
data separates them cleanly.

**First maneuver (`yield`) — no retreat space on the chosen side.** Positions in
the maneuver window, from the M5 scene JSONL:

| | Run A | Run B |
|---|---|---|
| Samples in window | 238 | 237 |
| Maneuver duration | 254.7 s | 254.0 s |
| `robot_1` start x | -0.092 | -0.107 |
| `robot_1` stall x | **-1.606** | **-1.607** |
| Reached stall at | +45.2 s | +45.5 s |
| Held there for | ~209 s | ~208 s |
| Standoff from the -1.700 near face | 0.094 m | 0.093 m |
| `robot_2` motion | +0.089 -> +0.088 (none) | +0.098 -> +0.097 (none) |

The standoff equals the robot's half-width (`robot.half_width_m: 0.09`), i.e.
the chassis is against the box. Both figures reproduce Task 8's forced-`robot_1`
run (-1.607, 0.093 m, 253.3 s) to within a millimetre and a second. The yield
strategy is sound here — it succeeds in Task 8 run 2 when aimed at `robot_2` —
so this failure is the chosen side, not the strategy.

**Second maneuver (`reverse`) — the strategy cannot work.** `reverse` is
dispatched symmetrically to both robots, so it cannot resolve a two-robot
head-on regardless of geometry. Both runs show both robots reversing together:

| | Run A | Run B |
|---|---|---|
| Window | 195.0 s | 195.1 s |
| `robot_1` | -0.544 -> -1.606 (against the box) | -0.483 -> -1.608 (against the box) |
| `robot_2` | +1.150 -> -1.732 | +1.261 -> -1.504 |

`robot_2` is driven from the open east side past `robot_1` and into the same
blocked west region, leaving both robots stranded at the wrong end. This is a
distinct failure from the first: even an unblocked scene would not be resolved
by it.

### The A/B comparison

| | Run A (OFF) | Run B (ON) |
|---|---|---|
| Obstacle geometry in prompt | no | yes |
| First strategy | `yield` | `yield` |
| First `yield_robot` | `robot_1` (infeasible) | `robot_1` (infeasible) |
| First maneuver outcome | `FAILED` after 254.7 s | `FAILED` after 254.0 s |
| `robot_1` standoff from the box | 0.094 m | 0.093 m |
| Previous-attempt block in next prompt | yes | yes |
| Second strategy | `reverse` (symmetric, `FAILED`) | `reverse` (symmetric, `FAILED`) |
| Arrivals | 0 | 0 |

**Supplying the obstacle's id, centre and extent did not change the model's
first decision.** Under both conditions gpt-4o chose `yield` and named
`robot_1` — the robot the box makes it impossible for — and the resulting
failures are indistinguishable in duration, stall position and standoff. On this
single paired run the obstacle channel produced no measurable change in the
decision under test.

This is one pair, not a distribution. It bounds nothing about the modality's
effect in general; it records that the effect was not visible here.

### First-answer yielder identity is not evidence of spatial reasoning

Under Run A the model chose `robot_1`, which is also the **first robot the
prompt presents it with**. This is a property of the input, not merely of the
model's own output ordering: the prompt renders `Robot states (sorted by ID)`
and `Known robot IDs: ["robot_1", "robot_2"]`, so `robot_1` is listed first in
**both** runs, deterministically, by ID sort. The choice and the presentation
order are therefore perfectly confounded here, and the answer is equally
consistent with:

1. a positional default (pick the first listed robot), and
2. a spatial judgement that happened to land on `robot_1`.

Nothing in Run A can distinguish them, because under modality OFF the model has
no channel through which the box is perceivable at all — not the state vector,
and not the overhead image, in which a 0.3 x 0.3 x 0.5 m box behind a robot is
not identifiable as an obstruction with a known extent. A model that cannot
perceive the blocker cannot be reasoning about retreat space, so Run A's answer
must not be reported as evidence either for or against that ability. It is an
information-bound answer, and that is all it is.

Run B removes the perception objection but not the confound: the model was told
the box's geometry and still named the first-presented robot. That is consistent
with a positional default surviving the added information, but a single run
cannot separate "ignored the obstacle block" from "read it and judged
differently". Breaking the confound needs the presentation order varied
independently of the geometry — a counterbalanced order condition, which neither
run here provides. Note this is a property of the prompt builder's ID sort, so
it applies to every artifact collected to date, not just these two runs.

### Evidence

Per-run M1/M4/M5/Nav2 logs, the launcher log, the recorder log, the M5 scene
JSONL and the run's decision artifacts are on the VM (git-ignored) under
`/home/ubuntu/vgu-vlm-swarm/data/logs/task9_20260919/`:

```text
runA_modality_off   9 files + 16 decision artifacts   6.5M   (run 20260919_042935)
runB_modality_on    9 files + 10 decision artifacts   5.2M   (run 20260919_044729)
```

The two re-timed recordings are in the worktree at
`data/logs/recordings/2026-09-19/` (git-ignored) with a `README.md` carrying
both timelines:

| File | Bytes | Duration | Frames |
|---|---|---|---|
| `run_a_modality_off_w0p2_eopen.mp4` | 11,028,283 | 780.00 s | 2454 |
| `run_b_modality_on_w0p2_eopen.mp4` | 11,424,450 | 780.00 s | 2613 |

Both were concatenated losslessly from their two recorder segments and re-timed
from the stamped fps to the achieved fps taken from each recorder's `WROTE`
line (Run A 7.870 -> 3.14615, ratio 2.50147; Run B 7.734 -> 3.35000, ratio
2.30866), so playback duration equals the recorder's 780 s wall clock.

Because `-r <achieved_fps>` forces that duration arithmetically, the re-timing
was also checked **independently** against the frame timestamps burnt into the
annotated video. Sampling each file at playback t=60 s and t=770 s (710 s apart):

| | Frame at t=60 s | Frame at t=770 s | Scene time elapsed | vs 710 s playback |
|---|---|---|---|---|
| Run A | `t=1789792302.20` | `t=1789793000.69` | 698.49 s | 98.4 % |
| Run B | `t=1789793375.81` | `t=1789794073.78` | 697.97 s | 98.3 % |

Both play back within ~1.7 % of real time; the small deficit is the recorder's
non-uniform capture rate under load, not a re-timing error.

### Modality restored

`prompt_static_obstacles` was set back to `false` and the `static_obstacles`
block re-commented immediately after Run B, then `swarm_orchestrator` was
rebuilt. The launcher restores `reasoning_backend_id` but knows nothing about
this flag, and with `openai -> openai` its restore branch does not fire at all,
so the restoration was done and checked by hand. Source and installed
`orchestrator.yaml` both hash to the shipped value:

```text
b7918706b14bf90b45ac93dd3a2ce253  ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml
b7918706b14bf90b45ac93dd3a2ce253  /ws/ros2_ws/install/share/swarm_orchestrator/config/orchestrator.yaml
INSTALLED prompt_static_obstacles = False
INSTALLED static_obstacles key present = False
INSTALLED reasoning_backend_id = openai
```

### VM state after both runs

```text
--- stray procs (expect none) ---
(end)
--- gpu ---
136 MiB, 0 %
--- container ---
vgu_ros Up 12 seconds
--- ros2 nodes in container ---
(none)
--- backend_id + flag source+install ---
prompt_static_obstacles: false
reasoning_backend_id: openai
prompt_static_obstacles: false
reasoning_backend_id: openai
```

### Open items

- **`reverse` is dispatched symmetrically** and therefore cannot resolve a
  two-robot head-on; in both runs it actively worsened the scene by driving the
  unblocked robot into the blocked end. The failure-context prompt's standing
  instruction to "prefer a different strategy" steers the model toward it after
  a failed yield, so this is reachable in ordinary operation, not a corner case.
- **`status=FAILED` still carries no reason string** (carried over from Task 8),
  so "blocked by the box" had to be established from the trajectory each time.
- **The order/geometry confound** described above is not resolvable from these
  two runs and needs a counterbalanced `involved_robots` order condition.
