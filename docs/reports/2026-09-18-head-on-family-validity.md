# Head-On Asymmetric Family - Validity Evidence

**Prepared:** 2026-09-18

**Revision history:**

- Initial draft: T1 control run (`head_on_asymmetric_wopen_eopen_o0`, mock backend) on the GPU VM, plus the VM sync and artifact-build verification that preceded it.
- Rev 2 (2026-09-19): corrected the T1 root-cause conclusion. The original "Root cause" section named an M4 defect as the cause of `robot_1`'s failure to arrive; that conclusion is wrong. The actual cause is `build_backend`'s mock branch (`reasoning/vlm/backend_factory.py`) collapsing `VGU_MOCK_DECISION_FILE` to a single repeated decision, so M2 replayed "deadlock / yield" on all 16 analyses instead of reporting `congestion_detected=false` once the scene cleared. The resume/cancel forensics in the original section are accurate and preserved — they are the *mechanism* by which the repeated commands stopped `robot_1`, not evidence of an independent M4 bug. The original text is marked superseded rather than removed; see "Root cause (revised)" below and the corrected Entry Criteria bullet. Fixed in the same commit by giving `VGU_MOCK_DECISION_FILE` an optional scripted-sequence form (`config/mock_decisions/head_on_yield_once.json`, `head_on_yield_robot_2_once.json`).

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

**What remains open.** A resume that gets cancelled a median of 0.11 s after
it starts is unusual on its own terms, independent of what caused the
repeat-command stream. That is recorded here as a real but **latent** M4
issue: it takes a pathological repeat-command stream to manifest — which is
exactly what the frozen mock produced and what a live backend would not
produce — so it did not block this task, but it needs its own investigation
before the codebase can assume rapid successive commands to one robot are
safe. It should not be read as ruled out by this correction.

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
