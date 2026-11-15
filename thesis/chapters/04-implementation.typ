#import "../lib.typ": *

// The saved demo screenshots (1182 x 957 px) carry the rqt image-viewer toolbar in their top 86 px;
// clip it in layout rather than editing the source PNGs.
#let demo-frame(path) = layout(size => {
  let w = size.width
  box(width: w, height: w * 871 / 1182, clip: true, place(top + left, dy: -w * 86 / 1182, image(path, width: w)))
})

= Implementation <sec:impl>

This chapter describes how the design of Chapter 3 is built, for one pinned runtime. The registered five-robot pilot ran on a commit whose code is identical to the pin, and intersection run 1 on the pin itself #ev("4.01"). Where a shipped configuration value differs from the one an experiment used, both are given. Features added after the pin appear only in @sec:impl-later.

== Software Stack <sec:impl-stack>

Isaac Sim @isaacsimdocs runs on a cloud virtual machine with an NVIDIA L4 GPU and publishes sensors and the clock over ROS 2 @macenski2022robot; the project's nodes and one Nav2 stack per robot @macenski2020marathon run in a `ros:jazzy` container on the same machine; the VLM is reached over HTTP. The reasoning code is plain Python imported by the orchestrator, so it is unit-tested without ROS (@tab:impl-stack).

#figure(
  table(
    columns: (auto, 1fr, auto),
    align: (left, left, left),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Component*], [*Version or setting*], [*Evidence*]),
    [Simulator], [Isaac Sim 6.0.1, source build; the run manifest records major version 6.0 and ROS distribution Jazzy], [#ev("4.02"), #ev("4.03")],
    [Simulation rates], [physics 60 Hz, rendering 30 Hz (fixed by the scenario schema)], [#ev("4.03")],
    [Middleware], [ROS 2 Jazzy; Fast DDS 2.14.6, forced onto UDP transport by a shared profile], [#ev("4.02")],
    [Navigation], [Nav2 1.3.13; NavFn global planner, DWB local controller, collision monitor; one namespaced stack per robot], [#ev("4.02"), #ev("4.04")],
    [Robot model], [TurtleBot3 Burger: wheel radius 0.033 m, wheel separation 0.160 m, mechanical speed limit 0.22 m/s], [#ev("4.05")],
    [Container Python], [Python 3.12.3; pydantic v2; OpenCV 4.6.0 from the distribution packages], [#ev("4.02")],
    [Project requirement], [Python 3.10 or newer; pydantic 2.7 or newer], [#ev("4.06")],
    [VLM, evaluated runs], [`gemini-robotics-er-2-preview` (Gemini Robotics-ER 2, "ER-2") @google2026geminier], [#ev("4.07"), #ev("4.01")],
    [VLM, shipped default], [`gpt-4o-2024-08-06`, a dated snapshot @openai2024system], [#ev("4.07")],
    [VLM, further pinned model], [`claude-sonnet-5-5`], [#ev("4.07")],
    [Grounder (M3)], [deterministic, geometry-derived grounding (`derived` mode)], [#ev("4.08")],
  ),
  placement: auto,
  caption: flex-caption([Software stack of the pinned runtime.], [Software stack of the pinned runtime. Simulator, middleware and container package versions are those inventoried on an experiment machine on 9 October 2026 #ev("4.02").]),
) <tab:impl-stack>

The registered pilot's machine, a snapshot clone of an earlier disk, was not re-inventoried #ev("4.01") #ev("4.03"). The robots are articulated by Isaac Sim's Newton backend #ev("4.33"), not the PhysX that the simulation specification required #ev("4.34"). Of eleven pinned backend sections #ev("4.07"), each evaluated run's launch configuration selects ER-2 #ev("4.01")\; `gpt-4o-2024-08-06` served the earlier pilots and `claude-sonnet-5-5` the offline work. @tab:module-io lists the module contracts.

#figure(
  placement: auto,
  table(
    columns: (auto, 1fr, 1fr),
    align: (left, left, left),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Module*], [*Inputs*], [*Outputs*]),
    [*M1* Perception and robot tracking],
    [`/camera/image_raw` (RGB image); `/coordination/tasks` (task registry from M5)],
    [`/perception/scene_state` (`SceneState` with one `RobotState` per robot); `/perception/annotated_frame`; `/perception/status`],
    [*M5* Orchestrator],
    [`/perception/scene_state`; `/perception/annotated_frame`; `/coordination/status` (`CoordinationStatus`); service `/orchestrator/trigger_analysis`],
    [`ReasonerRequest` to M2; `/coordination/commands` (`CoordinationCommand`, one per robot); `/coordination/tasks`; decision artifacts],
    [*M2* VLM reasoning],
    [`ReasonerRequest`: frame image, `RobotStateInput` list, optional failure and plan-state context, presentation order],
    [`ReasonerResult` holding a `CongestionDecision`, or no decision after bounded retries; per-attempt diagnostics],
    [*M3* Grounder],
    [`ReasonerResult`; `SnapshotFrame`; declared `SceneGeometry` and static obstacles; `GroundingParams`; optional second-stage retreat choice],
    [Schema-valid coordination command (actions, expected resolution time, fallback, degradation tags); `VerifiedPlan` with its plan-audit label; `JunctionClearPhasePlan`],
    [*M4* Execution and safety monitor],
    [`/coordination/commands`; `/perception/scene_state` (safety monitor); `/<robot>/odom`; `/safety/holds`],
    [`/coordination/status`; Nav2 `NavigateToPose` and `FollowWaypoints` goals; `/<robot>/cmd_vel`; `/safety/holds`],
    [*M6* Simulation],
    [`/<robot>/cmd_vel`],
    [`/camera/image_raw`; `/<robot>/odom`; `/<robot>/scan`; `/clock`; validation-only ground-truth poses],
  ),
  caption: flex-caption([Module inputs and outputs in the evaluated runtime.], [Module inputs and outputs in the evaluated runtime. Names in monospace are ROS 2 topics, services or data contracts as they appear in the code; `<robot>` stands for a robot namespace such as `robot_1`. #fig-source("3.06")]),
) <tab:module-io>

== Perception (M1) <sec:impl-perception>

An Isaac Sim render product publishes a 1280 #sym.times 960 RGB image at a nominal 30 frames per second from a camera 3.0 m above the floor, looking straight down. Each robot carries one `DICT_4X4_50` ArUco marker @garridojurado2014automatic, 0.12 m wide, at a height of 0.21 m #ev("4.09"). The container's OpenCV 4.6.0 predates `ArucoDetector`, so the legacy detection call is used, never mixed with the newer API, which crashes that version #ev("4.02") @opencv2026aruco.

The calibration is analytic: intrinsics and a pixel-to-world homography are derived from the simulated camera's configuration for the plane at marker height, which removes the parallax of the marker height #ev("4.09")\; heading follows from the order of the projected corners. The state estimator differentiates successive poses, smooths velocity with a first-order low-pass filter and classifies each robot, with a stopped threshold of 0.01 m/s, a slow threshold of 0.05 m/s, a smoothing factor of 0.15 and a stale timeout of 1.15 s #ev("4.10"). A frame older than the newest processed one is dropped and flagged; a backward jump of more than 1.0 s is treated as a simulator clock reset and clears all tracks #ev("4.10").

== Orchestrator (M5): State Machine and Task Registry <sec:impl-orchestrator>

M5 is one ROS 2 node whose logic (state machine, detector, registry, command lifecycle, phase queue) sits in ROS-free modules behind thin callbacks. Only the `MONITORING` state of its three (`MONITORING`, `ANALYZING`, `DISPATCHING`) can start a cycle, after the gates of Chapter 3 and a check for a fresh matching camera frame. A grounded command becomes a dispatch; any other outcome increments a per-robot failure counter and starts a cool-down.

The registry holds each robot's base assignment and any active override. Arrival needs both a navigation success _and_ a perception estimate within the arrival tolerance, because one earlier run recorded a navigation success for a robot that perception placed 0.59 m from its goal #ev("4.11"). For the five-robot scene, an optional task stream, off in the shipped configuration, replaces static goals with a seeded queue of tasks per robot. @tab:impl-m5 lists the parameters.

#figure(
  table(
    columns: (1fr, auto, auto),
    align: (left, right, left),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Parameter*], [*Value*], [*Evidence*]),
    [Stall threshold (wall clock)], [12.0 s], [#ev("4.11")],
    [Progress tolerance], [0.10 m], [#ev("4.11")],
    [Goal-reached tolerance], [0.15 m], [#ev("4.11")],
    [Arrival position check tolerance], [0.35 m], [#ev("4.11")],
    [Proximity rule: distance, speed], [0.50 m, 0.05 m/s], [#ev("4.11")],
    [Cool-down after an analysis], [15.0 s], [#ev("4.11")],
    [Command timeout], [20.0 s], [#ev("4.11")],
    [Failure-context window], [60.0 s], [#ev("4.11")],
    [Second-stage retreat call: attempts #sym.times timeout], [2 #sym.times 8.0 s], [#ev("4.11")],
  ),
  caption: [Orchestrator (M5) parameters as shipped at the pinned runtime.],
) <tab:impl-m5>

Every analysis writes one JSON decision artifact with the scene, the exact prompts and their SHA-256 digests, the raw model text, the parsed decision, the grounded command or the reason none was dispatched, the plan-audit label and backend diagnostics; these artifacts feed the offline analyses of Chapter 6.

== Execution (M4) <sec:impl-execution>

M4 has a command bus, a per-robot coordination client that drives base missions through Nav2, and the safety monitor. Navigation legs become Nav2 goals; clearing manoeuvres bypass Nav2.

*Backup.* A `yield` or `reverse` leg starts with a backup that publishes reverse velocity at 0.1 m/s directly to the robot and stops on odometry once the grounded distance is travelled #ev("4.12"). Nav2's own back-up passes through the collision monitor, whose forward stop zone always contains the other robot in a head-on standoff, and a timer of distance over speed ends too early when the simulator runs below real time. A wall-clock deadline of fifteen times the nominal duration, with a 30 s floor, guards only against a physically blocked robot #ev("4.12").

*Yield.* A `yield` runs the backup, a pull-off sidestep off the aisle centre line (turn, drive, turn; fallback offset 0.35 m) #ev("4.13"), and a hold that ends as soon as the passer has covered its grounded clearance by its own odometry; the grounded hold time is only an upper bound, because fixed holds expired mid-traverse at low real-time factors. With an escort distance, the passer is driven through the gap by a raw heading-and-distance primitive, because the DWB controller crept through at about 0.01 m/s #ev("4.14")\; this straight segment does not check static obstacles. Several passers are admitted one at a time in the grounded order.

A `reverse` is a backup without pull-off or hold; a wait cancels the goal and holds for the grounded duration in simulation time.

*`junction_clear` phase queue.* M3 precomputes all phases once (@tab:strategies). Every phase addresses every involved robot, the inactive ones with `temporary_wait`, because the exemption applies only within one command; M5 dispatches the next phase, or the fallback, without calling the VLM or the grounder again. The furthest phase reached (back-out, cross, release, resolved or fallback) is recorded as an ordinal outcome #ev("4.15").

*Safety monitor.* The shipped values are a 0.45 m proximity latch, a 0.2 m/s speed limit and a 0.6 m STALE band; the floor is 0.0 (off) in the shipped safety file and 0.20 m in the file installed for the registered pilot and the intersection runs #ev("4.16"). Navigation legs are also bounded by a watchdog of three times the command timeout, with a 120 s floor #ev("4.12").

== VLM Backends, Prompt and Grounding Interface (M2, M3) <sec:impl-vlm>

*Backends.* Each provider is an adapter that owns the HTTP payload, authentication, image encoding and response parsing; adapters exist for OpenAI-compatible endpoints, the Gemini Interactions API, Anthropic, `llama-server` and two mocks (scripted and echo). The three relevant pins differ in decoding control #ev("4.07"). `gpt-4o-2024-08-06` decodes at temperature 0.0 with up to four attempts, and after two refusals re-sends the text with a neutral grey image, because an earlier offline replay found its refusals triggered by the camera image rather than the text, and not by the annotation overlay #ev("4.37"). `claude-sonnet-5-5` uses the same settings but receives no sampling parameters, which it rejects. ER-2 runs with `thinking_level: low`; its API has no temperature, top-p or top-k fields, so none is sent, and it uses two attempts of 120 s without the grey fallback #ev("4.07"). The shared temperature of 0.6 is recorded in each artifact, with no evidence that the provider applies it #ev("4.35").

*Prompt.* With the plan channel on, the prompt is version 3.4, as in the registered pilot #ev("4.17"). The system prompt is one assistant line; the user prompt holds, in order, the robot states (identifier, pose, speed, status, task and goal), pairwise distance and whether each robot faces the other within 60 degrees #ev("4.17"), the known identifiers, an optional summary of the previous attempt, guidance glossing each type and strategy, the plan grammar, the output schema with a bounded `reasoning` field before the classification fields, and a closing instruction to write only JSON. @fig:impl-prompt-excerpt shows an abridged recorded prompt.

#figure(
  kind: raw,
  supplement: [Listing],
  block(width: 100%)[
    #show raw: set text(size: 7.5pt)
    ```text
You are a warehouse swarm robotics traffic controller. Analyze the overhead camera view […]

Robot states:
- robot_id=robot_1, x=-0.36, y=0.00, theta=0.00, status=STOPPED, goal_x=1.75, goal_y=0.00, […]
- robot_id=robot_2, x=0.22, y=0.00, theta=3.14, status=STOPPED, goal_x=-1.75, goal_y=0.00, […]
- robot_id=robot_3, x=0.02, y=-0.38, theta=1.50, status=STOPPED, goal_x=0.00, goal_y=1.75, […]
- robot_id=robot_4, x=0.01, y=0.23, theta=-1.42, status=SLOW, goal_x=0.00, goal_y=-1.75, […]

Pairwise geometry (faces = heading within 60° of the direction to the other robot):
- robot_1 <-> robot_2: distance 0.58 m; robot_1 faces robot_2: yes; robot_2 faces robot_1: yes
[… four more pairs …]
- robot_3 <-> robot_4: distance 0.60 m; robot_3 faces robot_4: yes; robot_4 faces robot_3: yes

Known robot IDs: ["robot_1", "robot_2", "robot_3", "robot_4"]

Guidance:
- Robots are roughly 0.3 m wide; treat any two robots within ~0.5 m of each other […]
[… five more guidance lines, the plan invitation and the plan grammar …]
Produce a JSON object with exactly these fields:
- "reasoning": one to three sentences of your analysis, written before you commit […]
- "congestion_detected": true or false
- "type": "none" | "deadlock" | "bottleneck" | "crowding" | "anomaly"
[…]
- "strategy": one of
  - "none": no congestion to resolve
  - "yield": one robot (yield_robot) backs up and steps aside while the others pass
  [… five more strategy glosses …]
  - "junction_clear": multi-robot junction recovery: some robots first back out, […]
[… justification, yield_robot, blocker_kind, crossing_order, proposed_plan, rules …]

Write ONLY the final JSON object, with no surrounding text or markdown.
    ```
  ],
  caption: flex-caption([Abridged excerpt of a recorded v3.4 user prompt.], [Abridged excerpt of a recorded user prompt, prompt version 3.4, from an analysis in episode 3 of intersection run 1 (coordination layer on, four robots jammed in the junction, three `STOPPED` and one `SLOW`, robots listed in ascending identifier order). Cuts are marked "[…]"; every kept line, or the kept start of a line, is verbatim. The annotated overhead image is sent after the text. The full prompt, the system prompt and the model's answer are given in @sec:app-prompts.#fig-source("4.39")]),
) <fig:impl-prompt-excerpt>

The baseline user prompt is 5,804 characters long and its SHA-256 digest is pinned by a test, so any edit appears as a new prompt version #ev("4.17"). The robot listing order, the pairwise geometry block, static-obstacle text and annotation overlays are experimental switches recorded in every artifact #ev("4.11"). A reply that fails parsing or schema validation (@sec:design-strategies) spends an attempt; when all fail, M5 records the failing stage and dispatches nothing.

*Grounding interface.* In `derived` mode M3 sweeps candidate retreat points along the robot's lane and keeps those whose backup, sweep and escort fit fixed bands, checking escorts against the parked yielder only #ev("4.13"). The plan channel is off in the shipped configuration, where M5 renders prompt version 2, and on in the registered pilot and the intersection overlay #ev("4.32")\; the dispatched command is always the grounder's, whatever the plan-audit label #ev("4.15"). The second-stage question draws the validated retreat candidates as letters on the frame, as in Set-of-Mark prompting @yang2023mark. The report's claims therefore concern the _pipeline_, never the model's plan alone.

== Engineering Lessons <sec:impl-lessons>

Five implementation decisions shaped the platform.

*Which clock each component runs on.* The simulator ran far below real time: about 0.38 on one earlier machine #ev("4.18"), 0.396 against 0.397 in a side-by-side check of two machines, 0.179 in one five-robot episode #ev("4.36"), and about 0.18 in the registered pilot #ev("3.31"). Frames stamped with wall time made M1's speeds read about 0.38 of their true value; since 27 September 2026 they carry simulation time, with the stale timeout retuned from 3.0 s to 1.15 s #ev("4.19"). The stall and cool-down timers, the watchdog and the backup deadlines stay on the monotonic wall clock, because a node clock that follows the simulator freezes exactly when the simulator hangs; backup distances are closed-loop on odometry. The 12 s stall threshold therefore corresponded to about 4.6 simulated seconds at a factor of 0.38 #ev("4.18") and about 2.2 in the registered pilot #ev("3.31"), and every threshold in this report is stated with its clock.

*Fabric and USD synchronisation.* Under Newton, Isaac Sim 6.0 keeps two scene stores, the USD stage and Fabric, which the renderer reads. In an early run the robots moved about 0.56 m by odometry while the camera showed a frozen scene, because the markers hung under a static prim #ev("4.20"). The marker is therefore authored under a physics child of the chassis link, and the ground-truth logger reads the chassis link's world transform, not the root prim, which keeps its spawn pose. Ground truth thus serves as the metric source for positions and pair distances #ev("4.20"), but not for contacts, whose lists were hard-coded empty #ev("6.20").

*DDS transport profile.* With the simulator on the host and ROS 2 in a container, the default shared-memory transport silently dropped all data to the container, which looked like a hang. A Fast DDS profile that forces UDP is set on both sides for every launch, and its presence was verified live on the experiment machine #ev("4.21").

*Motion-aware ray tracing for lidar.* Without motion support in the RTX ray tracer, lidars saw only static geometry, so costmaps and the collision monitor were blind to approaching robots, and robots interpenetrated head-on. The fix needs three renderer settings passed together at start; enabling only one breaks renderer creation and silences every sensor #ev("4.22"). They are fixed in the runner code.

*Scenario rebuild.* The simulator loads a generated USD stage, so scenario edits do nothing until the stage is rebuilt; a stale stage cost about ten debugging runs in July 2026 #ev("4.23"). In the registered pilot's run kit the build step checks that every stage is newer than its scenario file and that its spawn poses equal the seeded draw, and records each stage's MD5 checksum #ev("4.23").

== Testing and Reproducibility <sec:impl-testing>

At the pinned runtime the repository holds 4,633 test functions in 199 files: 4,616 offline unit tests in 191 files, with ROS 2, the simulator and the model APIs mocked; 5 integration tests in 4 files; and 12 simulation tests in 4 files #ev("4.24"). The suite is not fully green: for the registered pilot's runtime it recorded 57 failed, 6,903 passed, 151 skipped and 3 errors, accepted as a zero delta against a reference list of failing identifiers #ev("4.25").

Live runs are executed from a prepared run kit. Before each episode a pin gate compares the MD5 checksum of every runtime file the run depends on with its registered value, in the source tree and in the installed path, because a colcon build can succeed and still leave a stale file installed. After each episode a condition gate checks the recorded condition and expected log lines, for example the 0.20 m floor on the monitor's start-up line, or no decision artifact in a coordination-layer-off episode. The scorer and its frozen free-flow reference are fixed by commit and checksum before collection #ev("4.26"). Model identifiers are dated snapshots where the provider offers one, and the prompt digest is pinned by a test #ev("4.17").

== Physical TurtleBot3 Demonstration <sec:impl-physical>

The pipeline was also run on physical TurtleBot3 robots @robotis2026turtlebot3 on 12 November 2026, with an overhead RealSense camera, ArUco localisation, `gemini-3.1-flash-lite` as the model, deterministic grounding, Zenoh transport @eclipse2026zenoh, stamped velocity commands, live execution and the safety monitor #ev("4.28")\; the saved artifacts confirm the model #ev("4.29"). Its safety boundary was 0.50 m, wider than the 0.45 m of simulation #ev("4.30") #ev("4.16").

Four arrangements were staged: two parallel head-on pairs (scenario A, @fig:impl-physical), a three-robot triangle with a fourth robot outside it (C), four robots facing a shared centre (D), and a tighter dual-lane variant of A (E) #ev("4.30"). Unparsable replies and earlier wait-only or timed-out attempts are excluded #ev("4.31"). The model chose `reverse` every time. In A it named all four robots as deadlocked and all four recorded `COMPLETED` (pair distances about 0.575 m and 0.614 m) #ev("4.30")\; in C only the three triangle robots, all `COMPLETED`; in D, labelled crowding, all four `COMPLETED`; in E four robots, of which three `COMPLETED` and one `FAILED` #ev("4.38").

#figure(
  grid(
    columns: (1fr, 1fr),
    column-gutter: 8pt,
    demo-frame("../assets/images/scenario_a_two_parallel_deadlocks.png"),
    demo-frame("../assets/images/scenario_c_three_robot_triangle.png"),
  ),
  caption: flex-caption([Annotated perception frames from the physical demonstration.], [Annotated perception frames saved by the demonstration run on 12 November 2026. Left: scenario A, two simultaneous head-on pairs. Right: scenario C, a three-robot triangle with a fourth robot outside the cluster.#fig-source("4.30")]),
) <fig:impl-physical>

The robots had no navigation goals: the saved robot states hold only identifier, pose, speed, status and stamp, and every distance-to-goal map is empty #ev("4.29"). `COMPLETED` means the reverse finished, not that a conflict was resolved in the sense of the simulation experiments. One run per scenario is recorded and the code that ran is not in the repository's history. The demonstration is illustrative: it shows the chain running end to end on hardware, not an evaluation.

== Later Extensions (Not Evaluated) <sec:impl-later>

These were written after the pin and are off unless enabled, except the contact logging, which has no switch. None ran in the registered pilot or intersection run 1; later live use is stated per item. Chapter 6 applies the obstacle guards and the stall abort offline to recorded five-robot episodes (@sec:res-failure-causes).

- *Per-group decision variants and live shadow.* An offline decision benchmark, grounding-first and per-group decision variants, and a live shadow that asks a second, per-group question after each analysis and never dispatches it (`per_cluster_shadow: enabled: false` by default) #ev("4.27") #ev("3.21").
- *Refusal feedback.* Tells the model which decisions the grounder withheld, and can restrict the offered strategies to groundable ones; both switches default to off #ev("4.27") #ev("3.21").
- *Safety-exemption scope fix* (`scoped_clearing_exemption`). Stops honouring plan-`continue` partners, drops robots whose leg was rejected, and ends a one-sided release once the gap starts to close; absent, hence off, in the pinned safety files #ev("4.27"). Tested with 64 unit tests and a replay of 68 recorded bundles; on in intersection run 2, where it never fired, and in the demonstration takes, where its firings were not counted; neither is a live validation #ev("6.07") #ev("6.06") #ev("5.51").
- *Plan-order prompt condition and switch.* A prompt that lists the plan actions the verifier accepts, with `plan_dispatch_order_source: model_when_verified`, which lets a verified plan set the `junction_clear` back-out order; both ran only in the demonstration campaign #ev("6.03").
- *Held-robot prompt condition.* Marks queued robots as not yet started; tested offline on the convoy scene and found no-go #ev("6.04").
- *Escort obstacle guard.* The grounder refuses an escort whose straight segment crosses a declared obstacle. Unit tests and offline replay only #ev("6.13")\; armed in one live validation take, where no escort was grounded and it never fired #ev("6.17").
- *Reverse obstacle guard.* The same check for `reverse` legs in derived grounding, refusing the whole reverse; unit tests and an offline replay of 17 recorded reverse commands, not run live #ev("6.13").
- *Geometric contact logging.* Ground truth records footprint gaps to boxes and robots on every row. In the validation take the fields were present on every row and reproduced exactly offline, but the lists stayed empty, so entries appearing at a real contact were not shown live: partially validated #ev("6.12") #ev("6.17").
- *Stall abort* (M4). Cancels a primitive whose commanded motion produces no measured movement and stops the robot; unit and node tests and an offline replay of 221 recorded primitives, not run live #ev("6.18").
- *Queued-robot hold* (convoy). The grounder holds unnamed robots outside the corridor whose goals lie past its far end; used in two demonstration convoy takes, both unresolved #ev("6.19") #ev("6.01").
