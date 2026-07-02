# M6→M1→M5→M2 Capstone Integration Test — GCP/Linux Execution Report

**Date:** 2026-06-18
**Branch:** main
**Guide under test:** `docs/guides/windows_host_integration_test.md`
**Executed on:** GCP VM (Ubuntu 22.04 / Jammy), Isaac Sim 6.0 **source build** at
`/home/ubuntu/IsaacSim`, accessed via SSH.
**Reasoning backend:** `openai` (real M2 decision pass).

> Status of this document: written **before** the final billed run completes, so
> the integration result is filled in at the end. The findings below (the guide
> does not work as written on a Linux single-VM box) are the primary deliverable
> and stand regardless of the final run outcome.

---

## Headline

The guide is written for **Windows 11 (native Isaac Sim) + WSL2 Ubuntu (ROS 2
Jazzy)** with two synchronized checkouts. The actual target was a **single Linux
GCP VM** running an Isaac Sim **source build** (Ubuntu 22.04, which cannot host a
system ROS 2 Jazzy — Jazzy requires 24.04/Noble). The integration *architecture*
(M6→M1→M5→M2) is sound, but the guide and several repo scripts assume a host
system ROS 2 Jazzy install that does not (and cannot) exist here. Reaching a
green pipeline required the adaptations and bug fixes recorded below.

### Adaptation used on this box

- **Isaac Sim (M6)** runs natively on the host, using its **bundled internal ROS 2
  Jazzy** bridge libraries (`exts/isaacsim.ros2.core/jazzy`). No system ROS 2 on
  the host.
- **ROS 2 nodes (M1, M5, CLI)** run inside a **`ros:jazzy` Docker container**
  started with `--network host --ipc=host` so Fast-DDS (`rmw_fastrtps_cpp`) shares
  transport with the host Isaac Sim process. Repo mounted at `/ws`.
- The private repo was transferred with **`rsync` over the SSH key** (no GitHub
  credentials on the box). The SSH private key was *not* left on the box, and the
  accidental `state/` copy (which contained the key) was removed.

---

## Repo bugs / guide defects found (actionable)

1. **Missing `ament_python` build-type export** in the three Python ROS 2
   packages (`swarm_perception`, `swarm_orchestrator`, `swarm_execution`).
   `package.xml` declared `<buildtool_depend>ament_python</buildtool_depend>` but
   had **no** `<export><build_type>ament_python</build_type></export>`. colcon then
   defaults to `ament_cmake`, looks for a `CMakeLists.txt`, and the build fails.
   **Fix (mirrored to local tree in this change):** add the export block to all
   three `package.xml` files. `swarm_simulation` and `swarm_interfaces` were
   unaffected (correct cmake/python config already).

2. **`scripts/build_ros2.sh` lacks `--merge-install`.** It runs plain
   `colcon build --symlink-install`. With isolated install dirs, the message/srv
   packages (`swarm_interfaces`) and `swarm_simulation` were not picked up on
   `AMENT_PREFIX_PATH` for the Python packages in a clean environment, so
   `swarm_interfaces/srv/TriggerCongestionAnalysis` failed to resolve at runtime.
   **Fix used:** `colcon build --symlink-install --merge-install` → all 5 packages
   register and the srv resolves. Recommend adding `--merge-install` to the script.

3. **TurtleBot3 URDF import folder collision.** The committed URDF already lives in
   `isaac/assets/robots/turtlebot3_burger/`. The Isaac URDF importer, finding that
   target folder occupied, writes the generated USD to
   `turtlebot3_burger_1/` instead. `paths.robot_asset_path()` expects
   `turtlebot3_burger/turtlebot3_burger.usda`, so `build_scenario` produced no USD.
   **Fix used:** merge `turtlebot3_burger_1/` contents into `turtlebot3_burger/`,
   remove the `_1` folder, then re-run `build_scenario` + `validate_simulation`
   ("PASS"). Importer should target a clean output dir or the path convention
   should tolerate the `_1` suffix.

4. **`scripts/run_simulation.sh` hard-gates on host `/opt/ros/jazzy`.** It
   `exit 1`s if `/opt/ros/jazzy/setup.bash` is absent and also requires
   `ISAAC_SIM_ROOT/python.sh`. On a source-build / no-system-ROS host this gate is
   impossible to satisfy.
   **Adaptation:** bypass the wrapper and invoke the runner directly:
   `"$ISAAC_SIM_ROOT/python.sh" -m isaac.scripts.run_simulation --scenario ...`.
   The runner enables `isaacsim.ros2.bridge` *before* it `import rclpy`
   (`runner.py:53` then `:174`), so the bundled Jazzy `rclpy` is injected at
   runtime inside Kit — no host ROS 2 needed.

5. **`--duration-sec` is a silent no-op in `isaac/scripts/run_simulation.py`.**
   The flag is parsed and validated (`> 0`) but **never assigned** into
   `ResolvedRunConfig` / the scenario, so run duration always comes from the
   scenario YAML's `duration_sec` (45s for `head_on_deadlock`) regardless of the
   CLI value. To extend the run for this test the scenario YAML had to be edited
   directly. `--topic-timeout-sec` *does* exist (default 15.0), contrary to an
   earlier note — the guide's `run_simulation.ps1` example is otherwise fine on
   that flag. The Windows/WSL2 two-checkout framing still diverges from a Linux
   single-VM; a Linux variant of the guide is warranted.

6. **`run_perception.sh` / `run_orchestrator.sh` assume host system ROS 2 + CWD.**
   Both `source /opt/ros/jazzy/setup.bash` and `source ros2_ws/install/setup.bash`
   (relative path → must run from repo root) under `set -euo pipefail`. They work
   *inside the container* (where `/opt/ros/jazzy` exists and repo is `/ws`), but
   not on this host. `set -u` can also trip ROS `setup.bash`
   (`AMENT_TRACE_SETUP_FILES: unbound variable`) in some shells.

---

## Environment facts (for the record)

- Host OS: Ubuntu 22.04 (Jammy). Cannot install system ROS 2 Jazzy (needs Noble).
- Isaac Sim: 6.0 source build, `ISAAC_SIM_ROOT=/home/ubuntu/IsaacSim`, bundles both
  `humble` and `jazzy` internal ROS 2 libs under `exts/isaacsim.ros2.core/`.
- ROS 2 nodes: `ros:jazzy` container, `--network host --ipc=host`,
  `ROS_DOMAIN_ID=0`, `rmw_fastrtps_cpp`. Workspace built with `--merge-install`.
  Runtime deps installed: `pydantic>=2`, `jsonschema`, `requests`, `pyyaml`
  (`numpy` left as the Debian-managed package to avoid an uninstall error).
- Assets generated + validated on host: warehouse, turtlebot3_burger USD,
  `isaac/scenarios/head_on_deadlock.usd` (validate_simulation → PASS).

---

## Integration run result

**BLOCKED — the M6 simulation publishes no ROS 2 topics on `main`.**

After clearing every environment/setup blocker above, the headless sim boots
cleanly, the internal **Jazzy** ROS 2 bridge loads
("Attempting to load internal rclpy for ROS Distro: jazzy → rclpy loaded"), the
stage validates, physics starts, and the timeline plays. The runner then times
out:

```
[Error] [isaac.vgu_sim.runner] ROS topics not ready within 90.0s.
        Missing: {'/clock', '/robot_1/odom', '/robot_2/odom'}
```

(`/camera/image_raw` is *not* listed as missing only because M1, running in the
container on the same domain, **subscribes** to it — a false positive. Nothing
actually publishes it.)

### Root cause (blocking architectural gap, not an environment issue)

The runtime ROS 2 OmniGraph publishers are **never wired up**. `isaac/vgu_sim/
ros_graphs.py` implements `create_global_ros_graphs()` (ROS2PublishClock,
ROS2CameraHelper → `/camera/image_raw`, ROS2CameraInfoHelper → `/camera/camera_info`)
and `create_robot_ros_graph()` (twist sub, differential + articulation control,
IsaacComputeOdometry → ROS2PublishOdometry `/robot_*/odom`, TF, lidar). These
require a live OmniGraph runtime (`og.Controller.edit`, `omni.replicator.core`).

**Nothing calls them.** A repo-wide search finds references to `ros_graphs` only
in `docs/` (the spec and the Phase-2 plan). `runner.py:run_repetition` does
`_open_stage → _enable_extensions → _validate_stage → _init_physics →
timeline.play → _wait_for_ros_topics`, with **no** graph-wiring step.
`scenario_builder.py` only defines the empty container prims
(`/World/ROSGraphs`, `/World/ROSGraphs/Global`, `/World/ROSGraphs/<robot_id>`);
inspecting the built `head_on_deadlock.usd` confirms `/World/ROSGraphs` is an
empty `Xform` with no `OmniGraph`/Node children. The Phase-2 plan
(`docs/superpowers/plans/2026-06-10-m6-phase2-isaac-sim.md:983-987`) shows the
intended call site:

```python
from isaac.vgu_sim.ros_graphs import create_global_ros_graphs, create_robot_ros_graph
create_global_ros_graphs(stage, "/World/Sensors/OverheadCamera", CameraConfig())
```

…but that wiring was never connected into the runner (or the build step). So
`ros_graphs.py` is effectively dead code on `main`, and the M6 → ROS 2 hand-off
does not exist at runtime.

### Consequence

The M6→M1→M5→M2 capstone **cannot pass end-to-end with the code as it stands in
this working tree** — the failure is in the simulation's topic publishing,
upstream of M1/M5/M2. Note `isaac/vgu_sim/runner.py` is in the **uncommitted
modified set** here (`git status` shows `M isaac/vgu_sim/runner.py`), i.e. it is
likely active WIP; the runtime graph-wiring is plausibly known-incomplete. I did
not verify the state of any other checkout (e.g. the Windows host), so I make no
claim about it — only about the tree exercised on this VM. Everything downstream was
verified ready: M1 perception node starts and subscribes; M5/M2 (openai) config is
correct; all 5 ROS 2 packages build and the `TriggerCongestionAnalysis` srv
resolves; the bridge transport (internal Jazzy ↔ container Jazzy, Fast-DDS over
`--network host --ipc=host`) is in place.

### To unblock (recommended fix, not yet applied)

Add a runtime graph-wiring step in `runner.py` that calls
`create_global_ros_graphs(stage, camera_prim_path, camera_cfg)` and, per robot,
`create_robot_ros_graph(stage, robot, robot_prim_path, robot_asset_cfg)`. Two
details that a one-line "just call them" would get wrong:

1. **Order: wire the graphs *before* `timeline.play()`, after `_init_physics()`.**
   `ros_graphs.py` builds `OnPhysicsStep`-triggered graphs; those triggers latch at
   play time, so the nodes must exist before the timeline starts. (The current
   sequence is `_init_physics → timeline.play → _wait_for_ros_topics`; insert the
   wiring between `_init_physics` and `timeline.play`.)

2. **Extensions: the current `_enable_extensions()` is insufficient for the graph
   node types.** It enables `isaacsim.ros2.bridge`, `isaacsim.ros2.nodes`,
   `isaacsim.robot.wheeled_robots`, `isaacsim.sensors.rtx`. But `ros_graphs.py` also
   uses node types from **`isaacsim.core.nodes`** (`OnPhysicsStep`,
   `IsaacComputeOdometry`, `IsaacArticulationController`) and the OmniGraph /
   replicator runtime (**`omni.graph.core`**, **`omni.replicator.core`** for the
   camera render product). Those must be enabled too, or `og.Controller.edit` fails
   on unknown node types even once the call site is added.

With both in place, the existing topic-wait + M1/M5/M2 path should run unmodified.
(No OpenAI credits were spent: the sim never published, so M5 was never triggered.)

### Field-by-field artifact (per guide)

Not produced — blocked upstream as above:

- `terminal_stage`: N/A (no trigger)
- `decision.congestion_detected` / `type` / `involved_robots`: N/A
- `diagnostics.backend_id`: N/A

## Honest framing

A green pipeline here proves the **integration** (M6→M1→M5→M2) works on Linux with
the container/bridge adaptation. It does **not** prove the **guide passes as
written** — the guide failed as written on this box and required the fixes above.
Run was **headless** (no GPU display reachable over SSH), so GUI visual
confirmation of the head-on approach was not performed; both-robot presence is
confirmed via `/perception/scene_state` instead.

---

## Update 2026-06-19 — graph wiring implemented, blocked at Isaac timeline driving

The "to unblock" work above was carried out: `runner.py` now wires the ROS 2
OmniGraphs at runtime and the publishers are correct. The capstone is **still
BLOCKED**, but the blocker has moved one layer deeper — from "no wiring" to
"Isaac headless standalone timeline does not advance the publish clock." This is
an Isaac Sim infrastructure gap, not a wiring or M1/M5/M2 defect.

### What was implemented and proven correct

`isaac/vgu_sim/ros_graphs.py` and `runner.py` were rewritten and the following
five concrete bugs were found and fixed (each verified against the live sim and,
where relevant, the Isaac MCP API index):

1. **Articulation discovery** — `ArticulationRootAPI` is applied deep inside the
   referenced robot asset (`…/Geometry/base_footprint/base_link`), not on the
   robot prim; discovered via recursive `Usd.PrimRange`.
2. **Trigger node** — `OnPhysicsStep` silently never fires in an `execution`
   graph ("Physics OnSimulationStep node detected in a non on-demand Graph");
   replaced with `omni.graph.action.OnPlaybackTick` (pin `outputs:tick`).
3. **Odometry pins** — `ROS2PublishOdometry` uses `odomFrameId`/`chassisFrameId`,
   not `frameId`/`childFrameId`.
4. **qosProfile** — the Isaac ROS2 nodes parse `qosProfile` as a JSON document;
   the literal `"default"` is invalid JSON and floods the log with parse errors.
   Left at the node default (`""`).
5. **Camera timestamping** — set `useSystemTime=True` on the camera RGB /
   camera-info helpers (sim time is unreliable here; see blocker below).

**Result: all expected topics advertise** from the container (`ros2 topic list`
over the host-network Fast-DDS bridge): `/camera/image_raw`,
`/camera/camera_info`, `/clock`, `/robot_1/odom`, `/robot_2/odom`, alongside
M1/M5's `/perception/*` and `/coordination/tasks`. The kit child renders on the
GPU (`nvidia-smi`: NVIDIA L4, ~39% util, ~2 GB VRAM held by the kit PID), so the
render product is GPU-bound and the `deviceIds not found …/HydraTextures`
warning is benign.

### The blocker: timeline clock pinned at 0 under standalone `step()`

No topic ever delivers a **message** (every `ros2 topic hz` / `echo` is empty),
even though topics advertise and the sim renders. Instrumenting the step loop
(`omni.timeline.get_timeline_interface()` + `SimulationContext.current_time`)
isolated the exact cause:

```
TL is_playing=True  timeline_t=0.0000  sim_t=0.0667
```

The timeline reports **playing**, and physics simulation time (`sim_ctx.current_time`)
advances — but `timeline.get_current_time()` stays **pinned at 0**. The Isaac
ROS2 publish path keys on the timeline/`IsaacReadSimulationTime` clock, so with
that clock frozen at 0 the publishers never emit a valid-stamped message and the
camera's `IsaacSimulationGate` drops every frame. Two driver variants were tried,
both blocked for this same root reason:

- **A. `initialize_physics()` + `play()`** — `OnPlaybackTick` fires (odom emits),
  but `IsaacReadSimulationTime` returns 0, so every message carries stamp 0 and
  the bridge drops it (246× `Timestamp 0 will be neglected`); camera gate drops
  all frames.
- **B. `reset()` + `play()`** — physics `current_time` advances, but `reset()`
  reloads the stage to its initial USD state and detaches the post-open graph
  wiring / render-product writer, so the graphs stop ticking entirely (zero
  publishes, zero warnings).

### To unblock (next session, not yet applied — do NOT blind-retry)

The fix is in the Isaac driving sequence, and the next attempt must be
**instrumented** (keep the `TL is_playing/timeline_t/sim_t` print), not blind.
Candidate directions, in order of likelihood:

1. **Wire the ROS graphs *after* `reset()`** (reset wipes post-open wiring) and
   keep `play()`, so variant B keeps its advancing clock without losing the
   graphs. Re-confirm `timeline_t` advances after wiring.
2. If `timeline_t` still stays 0 with the timeline "playing", the publish clock
   is genuinely not driven by standalone `step()`. Either drive the sim via the
   timeline (`timeline.play()` + `app.update()` per the NVIDIA standalone ROS2
   camera examples) instead of `SimulationContext.step()`, or set the camera/odom
   helpers' time source to the advancing physics clock.
3. Cross-check against an official NVIDIA `standalone_examples/api/
   isaacsim.ros2.bridge/*camera*` script for the exact play/step idiom that makes
   `/clock` tick on this 6.0 build.

**No OpenAI credits were spent** in any run this session — the sim never
published a frame, so M1 never produced a populated `/perception/scene_state` and
M5 was never triggered.

### Update 2026-06-19 (later) — root narrowed to two divergent clocks

Two further fixes were applied and the blocker narrowed substantially:

- **Wire ROS graphs *after* `reset()`** (runner.py) — confirmed correct: the
  graphs now survive `reset()` and tick (odom warnings return, i.e. OnPlaybackTick
  fires in the step loop).
- **Author a timeline window** (`_set_timeline_window`: `SetStartTimeCode(0)`,
  `SetEndTimeCode(10_000_000)`) — the scenario builder set `timeCodesPerSecond`
  but never start/end codes, so the stage had a **zero-length timeline**. After
  this fix the **playback cursor advances**: instrumentation shows
  `timeline_t=0.1000` (was `0.0000`).

**Transport is proven good.** From the container, `ros2 topic info
/camera/image_raw -v` shows `Publisher count: 1` (the host Isaac bridge) and
`Subscription count: 1` (M1's `/perception_node`), both RELIABLE — the
`--network host --ipc=host` Fast-DDS bridge discovers and connects host↔container.

**Remaining blocker — `IsaacReadSimulationTime` frozen at 0.** There are two
clocks and they diverge:

- `timeline.get_current_time()` (playback cursor) — now advances (0.1).
- `SimulationContext.current_time` (physics step counter) — advances (0.0667).
- `IsaacReadSimulationTime` (Isaac sim clock the OG nodes read) — **still 0**.

Because the OG publish path reads the third clock: odom messages carry stamp 0
(dropped), and the camera's `IsaacSimulationGate` — keyed on sim time, *not* on
the wall-clock `useSystemTime` stamp — drops every frame. So the camera topic is
advertised and connected but emits **zero** messages, while odom emits with
invalid stamps. `useSystemTime=True` fixes only the camera *stamp*, never the
*gate*.

**Next lever (direction #2, now the prime suspect):** `SimulationContext.step()`
advances the step counter and renders but does not advance the Isaac simulation
clock that the OG nodes read. Drive the sim the NVIDIA standalone way —
`timeline.play()` + `omni.kit.app.get_app().update()` per
`standalone_examples/api/isaacsim.ros2.bridge/*camera*` — so a real
simulation-time tick reaches `IsaacReadSimulationTime`. Verify with the same `TL`
instrument that `IsaacReadSimulationTime`/`/clock` becomes non-zero, then
`ros2 topic hz /camera/image_raw` should show ~30 Hz.

**Also note for the full run:** the container currently runs only
`/perception_node` (M1) — **M5 orchestrator is not running**, so even once frames
flow, M5 must be started (with `OPENAI_API_KEY` via `docker exec -e`) before the
manual `/orchestrator/trigger_analysis`. Still no OpenAI credits spent.

### Update 2026-06-19 (THE ROOT CAUSE) — Fast-DDS shared-memory fails host↔container

The real blocker was **never** the sim publishing — it was the **ROS 2 transport**.
With the default Fast-DDS config, host↔container **discovery works** (the
container sees the topic list and `Publisher count: 1`) but **data delivery over
shared memory silently fails**, so every `ros2 topic hz`/`echo` from the container
returned empty no matter what the sim did. Forcing UDP on the *subscriber* side
proved it instantly, against the unchanged running sim:

```
docker exec ... -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4 ... ros2 topic hz /clock
  → average rate: 23.2 Hz
docker exec ... -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4 ... ros2 topic hz /camera/image_raw
  → average rate: 13.5 Hz
```

So `/clock` and the camera **were publishing all along**, and the camera flowing
at ~13.5 Hz also confirms simulation time advances (the `IsaacSimulationGate`
passes) — i.e. the timeline-window + `app.update()` driver fixes did work; SHM
delivery merely hid the result. **Fix: every ROS 2 participant that talks
host↔container (Isaac sim, M1, M5, and any `ros2` CLI check) must set
`FASTDDS_BUILTIN_TRANSPORTS=UDPv4`** under `--network host --ipc=host`. (The
`--ipc=host` SHM sharing is the thing that misbehaves; UDP over the shared host
network namespace is reliable.)

The earlier `M6 → ROS 2` wiring/driver work was still necessary and correct
(graphs must tick; odom needs a non-zero timeline; the camera gate needs
advancing sim time). The five OmniGraph fixes + reset-ordering + timeline window +
`app.update()` driver are all real and load-bearing. But the symptom that made
every run look dead — "topics advertise, zero messages" — was this SHM transport
gap sitting on top of them.

### Update 2026-06-19 (UNBLOCKED) — full pipeline validated end-to-end (mock backend)

With transport fixed, three more defects surfaced and were fixed, after which the
**entire M6→M1→M5→M2 pipeline ran green** (mock backend, no credits):

1. **M1 SIGSEGV in `cv2.aruco.detectMarkers` (`swarm_perception/detection.py`).**
   OpenCV 4.6.0 (container) exposes **both** `DetectorParameters()` and
   `DetectorParameters_create()`. The old guard keyed the params factory on
   `hasattr(cv2.aruco, "DetectorParameters")` → chose the 4.7-style
   `DetectorParameters()` object, which **segfaults** when passed into the legacy
   `cv2.aruco.detectMarkers` (taken because `ArucoDetector` is absent in 4.6.0).
   **Fix:** key `_make_detector_params` on the **same** discriminator as the
   detection path — `hasattr(cv2.aruco, "ArucoDetector")` — so the params object
   always matches the detector API. M1 no longer crashes.

2. **Black render → no lighting.** The warehouse asset authors **no lights** (only
   the ArUco markers are emissive). An unlit RTX scene tonemaps to a fully-black
   frame (max 0), so M1 saw nothing. **Fix:** `runner._add_scene_lighting()` adds a
   `UsdLux.DomeLight` after `reset()`. An initial dome(1000)+distant(2000) over-
   exposed the scene (mean ~196, blown-out central hotspot that washed out the
   marker black/white contrast); dialed to a **single dome @ 500** (distant
   dropped) → mean ~81, markers read cleanly.

3. **Markers clipped at FOV edges / no deadlock geometry (scenario design).**
   `head_on_deadlock.yaml` spawned the robots at the goal lines (`x=±3`), which on
   this overhead camera (≈6 m footprint) sit **exactly on the frame boundary** —
   each marker straddles the edge and is undetectable — and 6 m apart is not a
   deadlock. Because the integration run is a **static** scene (`ros_graphs.py`
   omits the `/cmd_vel` driver), robots never leave spawn, so the spawn must itself
   be the deadlock snapshot. **Fix:** spawn nose-to-nose near aisle centre
   (`x=±0.6`, headings opposed); goals stay `±3` to match the orchestrator
   `initial_tasks`. Rebuilt the scenario USD (`build_scenario`). Also bumped
   `duration_sec` 45→300 so the run stays up long enough for the M5 trigger +
   collect (recall `--duration-sec` is a no-op, bug #5 above).

**Result — verified against the live sim:**
- `/camera/image_raw` flows ~11 Hz; a pulled frame detects `DICT_4X4_50 ids [2, 1]`.
- M1 `/perception/scene_state` carries **both** `robot_1` and `robot_2` at
  `x≈±0.64` (matching spawn ±0.6). *(Note: a stale `robot_6` phantom track
  lingered from the earlier ±3 run because `perception_node` persisted across
  sims; cleared by restarting M1.)*
- M5 (`orchestrator_node`) ingests the scene (`frame_ready=True`,
  `robots=['robot_1','robot_2']`) and accepts the manual
  `/orchestrator/trigger_analysis` (`accepted=True`, `analysis_id=…`).
- Decision artifact written to `data/logs/m5_decisions/<id>.json`, matching the
  guide's expected **mock** shape exactly: `terminal_stage=vlm`,
  `congestion_detected=false`, `type=none`, `diagnostics.backend_id=mock`,
  `parse_status=valid`.

This proves the **complete transport + integration path** M6→M1→M5→M2→artifact
for the first time. Build/runtime notes discovered en route: `swarm_orchestrator`
was **not previously built** in this workspace (only M1 was) — built with
`colcon build --merge-install --packages-select swarm_orchestrator`; its console
script installs to `install/bin/orchestrator_node` (not `install/lib/<pkg>/`), so
`ros2 run`/`ros2 launch` can't find it — invoke the binary directly. M5 also needs
the repo root on `PYTHONPATH` (`PYTHONPATH=/ws`) to import the non-ROS `reasoning`
(M2) package. The `OpenAIBackend` uses `requests` (no `openai` SDK needed) and
reads `OPENAI_API_KEY`; model `gpt-4o` via `api.openai.com/v1`.

### Remaining for full acceptance — openai backend swap (needs API key)

Everything is staged. The only outstanding step is the **real M2 decision**: run
M5 against the committed `openai` config with `OPENAI_API_KEY` in the container
env, re-trigger, and collect the artifact (expected `type=deadlock`,
`involved_robots=[robot_1,robot_2]`, `backend_id=openai`). The key was **not**
present anywhere on the box and must be supplied securely (never written to a
committed file, never echoed in a command); the previously-used key should be
**rotated** since it appeared in an earlier chat transcript. No OpenAI credits
have been spent in any run to date.

### Open issue (non-blocking) — M1 heading 90° offset

Detected headings show a consistent ~90° offset (robot_1 θ≈+π/2, robot_2 θ≈−π/2)
vs the authored yaws (0 / π) — a marker-frame / corner-ordering convention issue
in M1's `estimate_marker_heading` (or the marker texture's on-quad rotation). It
does **not** block detection and is unlikely to block M2's deadlock read (which
leans on positions + goals + the annotated image), but it should be reconciled
before any heading-sensitive downstream logic relies on it.

> **Correction (2026-06-19), see next section:** the "unlikely to block" claim
> above is **revised upward**. Goals do **not** reach M2 (neither as text nor as
> a drawn goal marker), and the annotated frame is M2's primary visual input — so
> the 90° offset corrupts the one directional signal M2 has. It is now the
> **leading** risk to a `deadlock` (vs `none`/`bottleneck`) label, not a footnote.

---

## Update 2026-06-19 — Pre-spend image audit (before any billed run)

Before spending OpenAI credits I audited the **exact image and payload** the
`openai` call would send, because the mock backend ignores the prompt entirely
and therefore proves transport/wiring only — never the scene→prompt→decision path
that actually decides the deadlock outcome. Findings:

1. **Phantom STALE tracks.** The M1 node had run ~13 h across sessions and
   accumulated stale tracks (`robot_6`, `robot_21`) stacked on top of robot_2, so
   `scene_state` carried **4** robots, 3 at ≈(0.64, 0). Any decision off that
   payload is invalid. **Fixed** by restarting `perception_node`; `scene_state`
   now carries exactly `robot_1` + `robot_2`, `markers_detected: 2`.

2. **Goals never reach M2 — by design.** `RobotStateInput` (reasoning/vlm/models.py)
   has no `goal` field; `build_reasoner_request` (reasoning_pipeline.py) omits even
   `task`; the prompt (prompt_builder.py) says *"Decide from the robot coordinates
   and the image, not from assumptions about intent."* And M5 is not feeding
   `/coordination/tasks` to M1 (`task: null`, `goal: null` in scene_state), so the
   annotated frame draws **no goal markers** either. The crossing intent
   (robot_1→+x, robot_2→−x) is therefore absent from both the text and the image.

3. **The annotated frame** (the image M2 receives — orchestrator_node.py subscribes
   to `/perception/annotated_frame`, not the raw camera) **does** show two clearly
   labelled red robot boxes — so an earlier "no robot body / M2 sees flat tags"
   worry (drawn from the raw frame) is **moot**. But the robots are ~1.2 m apart
   (the prompt's own heuristic flags conflict only within ~0.5 m) at a 4-way
   intersection with visible escape routes, and the heading arrows point **±y**
   (the 90° offset) — i.e. M2 sees two stopped robots facing *sideways*, not
   head-on. Saved evidence: `state/frames/annotated_full.png`,
   `state/frames/annotated_center.png` (raw-frame comparison in `frame_full.png`,
   `center_zoom.png`).

**Net:** the pipeline is healthy and the scene is now clean, but an honest
`openai` run on the current geometry would plausibly return `none`/`bottleneck`
rather than `deadlock` — not because anything is broken, but because the 90°
heading offset misrepresents the head-on geometry and the snapshot is
geometrically borderline. The legitimate (non-gaming) lever is **fixing the 90°
marker-mount offset** so M2 sees the robots' true opposed headings; tightening the
spawn gap below ~0.7 m would also clear the prompt's 0.5 m heuristic. Decision on
how far to take scene fidelity vs. running as-is and reporting the honest result
is deferred to the user (who must also supply the key).

### Fix applied 2026-06-19 — marker-mount 90° offset corrected (verified)

Root cause confirmed to be the **asset**, not M1: `estimate_marker_heading` is
correct and unit-tested (test_perception.py top-edge cases), so M1 was left
untouched. The marker quad in `isaac/vgu_sim/marker_asset.py` had its ArUco
printed-top (M1's robot-forward edge) mounted +90° from the robot prim's +x. Fix:
add `AddRotateZOp().Set(-90.0)` to the marker prim (detected θ = yaw + 90° → yaw).
Redeployed the one file, regenerated `isaac/scenarios/head_on_deadlock.usd` on the
host (`python.sh -m isaac.scripts.build_scenario`), relaunched the sim, restarted
M1. **Verified** in `scene_state`: `robot_1 θ=0.0` (faces +x → toward robot_2),
`robot_2 θ=π` (faces −x → toward robot_1) — a true head-on, both STOPPED,
`markers_detected: 2`, no phantom tracks. Evidence: `state/frames/annotated_*2.png`.

The scene now honestly depicts the head-on standoff. **Staged and ready for the
single billed `openai` run** (sim + M1 up, clean payload); the only remaining
dependency is the OpenAI API key, supplied securely at runtime.

### Valid billed run — 2026-06-19 (capstone result)

The end-to-end pipeline ran with the **live gpt-4o backend** against a clean
2-robot scene. Run-1 (`36dc93f…`) was discarded as invalid: a recurring phantom
STALE track (`robot_40`, stacked on robot_2 at 0.00 m) drove a false anomaly. The
phantom was a *retained stale track* from a transient ArUco misread — `scene_state`
always reported `markers_detected: 2`. Eliminated by restarting M1 and triggering
inside the ~200 s phantom-accrual window (the durable fix is to drop STALE / unknown
tracks in `build_reasoner_request`).

**Run-2 (`261751a1e5734f109362fb23245a880b`) is the valid result.** Clean payload:
`robot_1` (STOPPED, x=−0.65, θ=0.0), `robot_2` (STOPPED, x=0.64, θ=π), no phantom.
gpt-4o returned (`parse_status: valid`, `latency 4414 ms`, 1588 tokens):

- `congestion_detected: true`, `involved_robots: [robot_1, robot_2]`
- `type: anomaly`, `strategy: reverse`
- root cause: "Both robots are stopped and facing each other, indicating a
  potential conflict."

gpt-4o's chain of thought computed `robot_1↔robot_2 = 1.29 m`, judged it
`> 0.5 m → no physical conflict` per the prompt's own heuristic, yet still flagged
the head-on standoff as an **anomaly** and recommended `reverse`. It did **not**
emit the literal word "deadlock" — and this is the honest finding, not a failure:
the scenario's "deadlock" semantics hinge on the robots' **opposing goals**, which
**never reach M2 by design** (`RobotStateInput` carries no goal/intent field). With
only coordinates + image, gpt-4o correctly read two stopped robots facing each
other at 1.2 m as an anomaly to be cleared by reversing — a faithful reading of its
actual inputs.

**Capstone proven:** Isaac Sim M6 → ROS 2 → M1 perception → M5 trigger → M2 live
VLM decision, artifact at `data/logs/m5_decisions/261751a1….json`
(`backend_id: gpt-4o`). `terminal_stage: grounding` because M3 grounding is not yet
implemented (expected). The robots were **not** moved closer to manufacture a
"deadlock" label: gpt-4o correctly judged 1.29 m as non-conflicting, so shrinking
the gap would be tuning ground truth to trip the proxy, not correcting a
misperception (contrast the legitimate heading fix). The principled lever for a
true deadlock signal is feeding **goals** to M2 — a contract change, future work.
Artifact saved at `state/decisions/261751a1e5734f109362fb23245a880b.json`.
