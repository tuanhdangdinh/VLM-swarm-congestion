#import "../lib.typ": *

= Implementation <sec:impl>

This chapter describes how the architecture of Chapter 3 is realised in software. It describes one specific runtime: the pinned version of the code on which the live simulation experiments of this thesis were executed. The prereg-v3 tranche 1 pilot ran on a commit whose code is identical to this pin, and the intersection experiment (IB10) ran on the pin itself #ev("4.01"). Where a configuration value shipped in the repository differs from the value used in an experimental cell, both are given and the difference is stated. Features added after the pin are described only in @sec:impl-later; they are switched off by default and are not part of the evaluated system. Results are not reported here; they are held for Chapter 6.

== Software Stack <sec:impl-stack>

The system is split across three execution environments. Isaac Sim, the robotics simulator from NVIDIA @isaacsimdocs, runs on the host of a cloud virtual machine with an NVIDIA L4 GPU and publishes camera images, lidar scans, odometry, transforms and the simulation clock over ROS 2 @macenski2022robot. All ROS 2 nodes of the project (perception, orchestrator, execution) and one Nav2 navigation stack per robot @macenski2020marathon run inside a `ros:jazzy` container on the same machine. The VLM is reached over the network through the provider's HTTP API. The non-ROS reasoning code (prompt construction, backend adapters, output parsing and the grounding layer) is plain Python that the orchestrator imports, so it can be unit-tested without a ROS installation. @tab:impl-stack lists the components and the versions recorded for them.

#figure(
  table(
    columns: (auto, 1fr, auto),
    align: (left, left, left),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Component*], [*Version or setting*], [*Evidence*]),
    [Simulator], [Isaac Sim 6.0.1, source build; the run manifest records major version 6.0 and ROS distribution Jazzy], [#ev("4.02"), #ev("4.03")],
    [Simulation rates], [physics 60 Hz, rendering 30 Hz (fixed by the scenario schema)], [#ev("4.03")],
    [Middleware], [ROS 2 Jazzy; Fast DDS 2.14.6, forced onto UDP transport by a shared profile], [#ev("4.02")],
    [Navigation], [Nav2 1.3.13; NavFn global planner, DWB local controller, collision monitor; one namespaced stack per robot], [#ev("4.02"), #ev("4.04")],
    [Robot model], [TurtleBot3 Burger: wheel radius 0.033 m, wheel separation 0.160 m, mechanical speed limit 0.22 m/s], [#ev("4.05")],
    [Container Python], [Python 3.12.3; pydantic v2; OpenCV 4.6.0 from the distribution packages], [#ev("4.02")],
    [Project requirement], [Python 3.10 or newer; pydantic 2.7 or newer], [#ev("4.06")],
    [VLM, evaluated cells], [`gemini-robotics-er-2-preview` (Gemini Robotics-ER 2, "ER-2") @google2026geminier], [#ev("4.07"), #ev("4.01")],
    [VLM, shipped default], [`gpt-4o-2024-08-06`, a dated snapshot @openai2024system], [#ev("4.07")],
    [VLM, further pinned arm], [`claude-sonnet-5-5`], [#ev("4.07")],
    [Grounding (M3)], [deterministic, geometry-derived grounding (`derived` mode); no retrieval on the runtime path], [#ev("4.08")],
  ),
  placement: auto,
  caption: [Software stack of the pinned runtime. Simulator, middleware and container package versions are those inventoried on an experiment machine on 9 October 2026.],
) <tab:impl-stack>

Three remarks qualify the table. First, the version numbers for Isaac Sim, Nav2 and the container packages come from a version inventory taken on one experiment machine on 9 October 2026 #ev("4.02"). The later tranche 1 run used a different virtual machine, a snapshot clone of an earlier experiment disk #ev("4.01"); its package versions were not re-inventoried, and the runner itself records only the major simulator version #ev("4.03"). Second, code comments and the simulation module specification disagree about which physics backend articulates the robots (PhysX or Newton). The thesis does not depend on that choice, and the point is left open here [VERIFY]. Third, the stack contains no vector store or embedding model on the runtime path, although the original module plan named M3 "RAG". The grounding layer imports no retriever, and every command it emits is computed from the scene geometry and a fixed rule set #ev("4.08"). "RAG" survives only as the historical module label.

The configuration of the VLM layer pins eleven backend sections, from a local Cosmos Reason 2 model served by `llama-server` to several hosted models #ev("4.07"). Three of them matter for this thesis: ER-2, which ran the evaluated live cells; `gpt-4o-2024-08-06`, the shipped default and the model of the earlier pilots; and `claude-sonnet-5-5`, which appears in the offline bench. The remaining sections served pilot or capability-probe work and are not described further. The shipped default backend is therefore not the one that ran the evaluated cells: the experiment overlays select ER-2 per cell #ev("4.01").

== Perception (M1) <sec:impl-perception>

M1 turns overhead camera frames into a list of robot states. In simulation, an Isaac Sim render product publishes a 1280 #sym.times 960 RGB image at a nominal 30 frames per second from a camera mounted 3.0 m above the floor and looking straight down #ev("4.09"). Each robot carries one ArUco fiducial marker @garridojurado2014automatic from the `DICT_4X4_50` dictionary, 0.12 m wide, at a height of 0.21 m #ev("4.09").

*Detection.* Markers are detected with the OpenCV ArUco module @opencv2026aruco. The OpenCV build in the container (version 4.6.0) predates the newer `ArucoDetector` class, so the detector checks for that class at run time and otherwise uses the legacy detection call with legacy parameters #ev("4.02"). The two APIs cannot be mixed on that version: passing the newer parameter object to the legacy call crashes the process. Detected corners are normalised to a 4 #sym.times 2 array before they enter the shared data contract.

*Homography.* The calibration is analytic rather than measured. A script derives the pinhole intrinsics and a pixel-to-world homography from the simulated camera's configuration, for the horizontal plane at the marker height, and writes them to the calibration file that M1 loads at start-up #ev("4.09"). Projecting onto the marker plane rather than the floor removes the parallax that the marker height would otherwise introduce towards the image edges. Only planar pose is estimated: position is the projected marker centre, heading follows from the ordering of the projected marker corners, and no six-degree-of-freedom pose is computed.

*State estimation.* A state estimator associates detections with robot identifiers, differentiates successive poses for linear and angular velocity, and smooths velocity with a first-order low-pass filter. It classifies each robot as `MOVING`, `SLOW`, `STOPPED` or `STALE`. The launch values are a stopped threshold of 0.01 m/s, a slow threshold of 0.05 m/s, a smoothing factor of 0.15 and a stale timeout of 1.15 s without a detection #ev("4.10"). A frame whose stamp is older than the newest processed frame is dropped and flagged in the diagnostics; a backward jump larger than 1.0 s is instead treated as a clock reset (the simulator's timeline restarting) and clears all tracks #ev("4.10"). The output is a `SceneState` message, serialised as JSON on a ROS topic, together with an annotated copy of the frame on which each robot's box is coloured by status. The annotated frame is the image the VLM receives.

== Orchestrator (M5): State Machine and Task Registry <sec:impl-orchestrator>

M5 is a single ROS 2 node that owns the task registry and the slow reasoning loop. Its logic is split into small modules without ROS dependencies (state machine, congestion detector, task registry, command lifecycle, phase queue), which the node calls from thin callbacks. Its parameters are listed in @tab:impl-m5.

*State machine.* The machine has three states: `MONITORING`, `ANALYZING` and `DISPATCHING`. Only `MONITORING` can start a reasoning cycle, so at most one VLM request is in flight at any time. A congestion event is turned into a directive by a fixed sequence of gates. The event is suppressed if no fresh camera frame matches the scene, or if any involved robot is in cool-down or still executing a dispatched command. A single stalled robot outside a busy multi-robot command is folded into that command's episode instead of opening a new one. Only an event that passes every gate starts an analysis. The analysis itself (M2 and M3) runs on a worker thread whose result the node polls on a timer, so no ROS callback blocks on the network. A successful outcome with a grounded command becomes a dispatch; any other outcome increments a per-robot failure counter and starts a cool-down.

*Congestion trigger.* The trigger is deliberately simple and classical. A robot counts as stalled when its distance to its goal has not improved by more than the progress tolerance for the stall threshold, while it has a goal, is not `STALE` and is not already at its goal. A second rule catches pairs of slow robots closer than the proximity threshold. The trigger only decides _when_ to ask; whether the scene is congested, and what to do about it, is decided by the VLM.

*Task registry.* The registry holds, for each robot, a base assignment (task label and goal) and, while a coordination command is active, an override. It publishes the effective assignment as JSON on the coordination task topic. M1 reads it to annotate goals, and the execution layer reads it to drive the base missions. Robot motion status is never taken from the registry; it is always derived by M1. Arrival is accepted only when the navigation stack reports success _and_ the latest perception estimate places the robot within the arrival tolerance of its goal, because one earlier run recorded a navigation success for a robot that perception placed 0.59 m from its goal #ev("4.11"). For the multi-task scenes of the prereg-v3 cells, an optional task stream replaces the static goals with a seeded queue of tasks per robot; it is off in the shipped configuration and enabled by the experiment overlays.

#figure(
  table(
    columns: (1fr, auto, auto),
    align: (left, right, left),
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
    [Stage-2 retreat call: attempts #sym.times timeout], [2 #sym.times 8.0 s], [#ev("4.11")],
  ),
  caption: [Orchestrator (M5) parameters as shipped at the pinned runtime.],
) <tab:impl-m5>

*Decision artifacts.* Every analysis writes one JSON decision artifact. It holds the scene, the exact system and user prompts with their SHA-256 digests, the raw model text, the parsed decision, the grounded command or the reason none was dispatched, the grounding provenance, and backend diagnostics such as latency, token usage and refusals. A once-per-second scene log and the annotated frames can be kept as well. These artifacts are the raw material of the offline analyses reported in Chapter 6.

== Execution (M4) <sec:impl-execution>

M4 consists of a command bus, a per-robot coordination client and a safety monitor. The coordination client drives each robot's base mission through Nav2 according to the registry. The command bus receives grounded coordination commands, executes one leg per robot, and reports `ACTIVE`, `COMPLETED` or `FAILED` on a status topic. Navigation legs (navigate, reroute, convoy, priority override) become Nav2 navigate-to-pose or waypoint-following goals. The clearing maneuvers do not go through Nav2.

*Backup.* A `yield` or `reverse` leg begins with a backup that publishes reverse velocity commands directly to the robot's velocity topic at 0.1 m/s and stops on odometry, once the robot has actually travelled the grounded distance #ev("4.12"). Two observations led to this design. Nav2's own back-up behaviour passes through the collision monitor, whose forward stop zone always contains the other robot in a head-on standoff, so it cancels the maneuver before a gap opens. And a timer of distance over speed ends too early, because the simulator runs well below real time. A wall-clock deadline of fifteen times the nominal duration, with a 30 s floor, only guards against a robot that is physically blocked #ev("4.12").

*Yield as pull-off and escort.* A `yield` is a sequence of phases on the yielding robot: the backup; a pull-off sidestep off the aisle centre line, executed as turn, drive and turn (the grounding file's fallback offset is 0.35 m) #ev("4.13"); and a hold while the other robots pass. The current phase is published in the status detail, so the safety monitor can tell a backing yielder from a holding one. The hold ends as soon as the passer has moved its grounded clearance distance, measured from its own odometry. The grounded hold time is only an upper bound, because fixed holds expired mid-traverse at low real-time factors. When the grounded command carries an escort distance, the passer is not handed back to Nav2 during the hold. It is driven through the gap by a raw heading-and-distance primitive instead, since the DWB controller crept through the narrow gap at about 0.01 m/s in earlier runs #ev("4.14"). With two or more passers, they are admitted one at a time in the grounded crossing order, and the hold ends after the last one has cleared. A yield is therefore not "stop and wait": it physically opens the aisle and escorts the other robot through it.

*Reverse and wait.* A `reverse` is a backup without pull-off or hold. A `wait`, `temporary_wait` or `stop` leg cancels the robot's navigation goal and holds it for the grounded duration on the node clock, which follows simulation time. A wait that is linked to a yield is released early when that yield ends.

*`junction_clear` phase queue.* The intersection strategy is the only multi-phase command, and its execution is split between M3 and M5. M3 precomputes the whole phase sequence once, from the single scene snapshot on which the decision was made. The sequence is one `reverse` per recede candidate in a deterministic ranking order, one ordinary `yield` for the robots on the crossing axis, an optional staggered release phase, and a plain `yield` fallback. Every phase addresses every involved robot, the inactive ones with `temporary_wait`, because the safety exemption described below applies only between members of the same command. M5 keeps a small phase queue per decision. It dispatches the next precomputed phase when the previous one resolves, or the fallback when one fails. The queue never calls the VLM or the grounder again, so advancing a phase does not count as a new plan. The furthest phase reached (recede, cross, release, resolved or fallback) is recorded as an ordinal outcome #ev("4.15").

*Safety monitor.* The safety monitor reads the M1 scene state and enforces the invariants of Chapter 3. Its shipped values are a minimum centre distance of 0.45 m, a speed limit of 0.2 m/s, and a fail-safe that treats a robot whose marker has gone `STALE` as unsafe when the last fresh pair distance was below 0.6 m #ev("4.16"). A violating pair is latched and stopped. Robots executing a clearing maneuver (`yield` or `reverse`) are exempt from the latch, but only against the partners in their own command, because clearing maneuvers legitimately work inside 0.45 m. A hard-contact floor overrides even that exemption below a set centre distance. The floor is 0.0 (off) in the shipped safety file and 0.20 m in the safety file installed for the prereg-v3 and IB10 cells #ev("4.16"). Navigation legs are additionally bounded by a command-bus watchdog of three times the command timeout, with a 120 s floor #ev("4.12").

== VLM Backends, Prompt and Grounding Interface (M2, M3) <sec:impl-vlm>

*Backend interface.* Each provider is an adapter behind a single backend protocol. The adapter owns the HTTP payload, authentication, image encoding and the parsing of the provider's response into a backend-neutral response object; retry policy, output parsing and decision validation are shared. A configuration section names a backend identifier and can select its transport with an `adapter` key, so one adapter can serve several pinned models. There are adapters for OpenAI-compatible endpoints, the Gemini Interactions API, Anthropic, `llama-server`, and two mocks (scripted and echo). API keys are read only from environment variables.

The three relevant pins differ in decoding control #ev("4.07"). `gpt-4o-2024-08-06` decodes at temperature 0.0 with up to four attempts; after two refused attempts, the next attempt re-sends the same text with a neutral grey image, because refusals were found to be triggered by the annotated frame rather than by the text (Chapter 6). `claude-sonnet-5-5` uses the same attempt and fallback settings but receives no sampling parameters, since the model rejects non-default values; the configured values are recorded per call as unsupported. ER-2 runs with `thinking_level: low`. Its API exposes no temperature, top-p or top-k fields at all, so none is sent, and it inherits the shared settings of two attempts and a 120 s timeout, without the grey-image fallback #ev("4.07").

*Prompt.* The prompt is version 3 in its fourth in-place revision (v3.4), the version used by the prereg-v3 cells #ev("4.17"). The system prompt is a minimal assistant line, and the task framing is in the user prompt, which contains, in order:
- the robot state block (identifier, position, heading, speed, status and, when the registry supplies them, task and goal);
- derived pairwise geometry: the distance, and whether each robot faces the other within 60 degrees;
- the list of known robot identifiers;
- an optional block describing the previous attempt and its outcome;
- classification guidance, with a one-line gloss for each congestion type and each strategy token;
- the plan grammar and an invitation to return an ordered `proposed_plan`;
- the output schema, with a bounded free-text `reasoning` field placed before every classification field;
- a closing instruction to write only the JSON object.

The rendered baseline user prompt is 5,804 characters long, and its SHA-256 digest is pinned by a test, so any edit shows up as a new prompt version #ev("4.17"). Several prompt channels are experimental switches that are recorded in every artifact. Examples are the order in which robots are listed (ascending identifier, descending identifier, or a random draw per episode), the pairwise geometry block, static obstacles and annotation overlays #ev("4.11").

*Output validation.* The reply is parsed into a JSON object and validated against the decision schema. The schema requires a congestion flag; a type from `none`, `deadlock`, `bottleneck`, `crowding` and `anomaly`; the involved robots; and a strategy from `none`, `yield`, `reroute`, `convoy`, `priority_override`, `temporary_wait`, `reverse` and `junction_clear`. A yielder, a blocker kind, a crossing order and a proposed plan are optional. A reply that fails parsing or validation spends an attempt. When all attempts fail, the result carries no decision, M5 records the stage at which it failed, and nothing is dispatched.

*Grounding interface.* M3 receives the validated decision together with the same scene snapshot. In `derived` mode it sweeps candidate retreat points along the robot's lane, keeps those whose backup, sweep and escort are feasible within fixed distance bands, and checks every escort leg against the parked yielder #ev("4.13"). The plan in the decision is then verified and, where needed, minimally repaired. Each grounded command is labelled with its provenance: `vlm_verbatim` if the model's plan was executable as given, `repaired` if M3 substituted or reordered legs within a bounded number of edits, and `m3_default` if M3 discarded the plan and used its own default plan for the chosen strategy #ev("4.15"). For a yield, an optional second VLM call ("stage 2") shows the frame with the validated retreat candidates drawn as letters, in the manner of set-of-mark prompting @yang2023mark, and asks the model to pick one; any failure of that call falls back to the geometrically best candidate. M3 can also refuse: a decision without an executable grounding is withheld, and the artifact records why. For these reasons the thesis states its claims about the _pipeline_ (VLM plus grounding), never about the model's plan alone.

== Engineering Lessons <sec:impl-lessons>

Five implementation decisions shaped the simulation platform. Each is stated as the decision taken and its consequence for the experiments.

*Which clock each component runs on.* The simulator ran at a real-time factor of about 0.38 on the experiment machine #ev("4.18"), so wall time and simulation time diverge by a factor of almost three, and the clock of every timed quantity had to be chosen explicitly. Camera frames were first stamped with wall time, which made M1's speeds read at about 0.38 times their true value. Since 27 September 2026 the frames are stamped with simulation time, and M1's stale timeout was retuned from 3.0 s to 1.15 s so that the same physical window applies #ev("4.19"). M5's stall and cool-down timers, the command-bus watchdog and the backup deadlines deliberately stay on the operating system's monotonic clock, because a node clock that follows the simulator freezes exactly when the simulator hangs. Backup distances are closed-loop on odometry and so independent of either clock. As a consequence, the 12 s stall threshold corresponds to about 4.6 simulated seconds at that factor #ev("4.18"), and every threshold in this thesis is stated together with its clock.

*Fabric and USD synchronisation.* Isaac Sim 6.0 keeps two scene stores: the USD stage, and Fabric, which the RTX renderer reads #ev("4.20"). In an early run the robots moved under physics, about 0.56 m by odometry, while the overhead camera showed a frozen scene: the markers were attached to a static parent prim, and the renderer's store was not receiving the articulated poses #ev("4.20"). The decision was to treat the articulated chassis link as the single source of truth for pose. The ArUco marker is authored under a link that is a physics child of the chassis, and the ground-truth logger reads the chassis link's world transform instead of the robot's root prim, which keeps its spawn pose for the whole run. As a result, the camera, M1 and the ground-truth log observe the same moving body, and the ground-truth log could serve as the metric source for distances and contacts #ev("4.20").

*DDS transport profile.* With the simulator on the host and ROS 2 in a container, the default shared-memory transport silently dropped all data to the container, which looked like a hung system #ev("4.21"). The decision was a Fast DDS profile that disables the built-in transports and forces UDP, set on both sides for every launch. Its presence on the simulator process and on the container nodes was verified live during the environment audit of the experiment machine #ev("4.21").

*Motion-aware ray tracing for lidar.* Without motion support in the RTX ray tracer, the simulated lidars saw only static geometry. Moving robots were missing from each other's scans, so the Nav2 costmaps and the collision monitor were blind to an approaching robot, and robots interpenetrated head-on. The fix needs three renderer settings passed together at application start; enabling only one of them breaks renderer creation and silences every camera and lidar #ev("4.22"). The simulator's start-up arguments are therefore part of the runtime and are fixed in the runner code rather than left to the operator.

*Scenario rebuild.* Scenario files describe the world, but the simulator loads a generated USD stage. Edits to a scenario file have no effect until the scene builder regenerates the stage, and a stale stage cost about ten debugging runs in July 2026 #ev("4.23"). The decision was to make the rebuild a gated step. In the tranche 1 kit, the build step checks that every stage is newer than its scenario file and that the spawn poses in the stage equal the seeded draw, and the MD5 checksum of each episode's stage is recorded #ev("4.23").

== Testing and Reproducibility <sec:impl-testing>

*Test suite.* At the pinned runtime the repository contains 4,633 test functions in 199 files #ev("4.24"). Almost all are offline unit tests that replace ROS 2, the simulator and the model APIs with mocks; a few integration and simulation tests need a sourced ROS 2 environment or the simulator and are marked as such. This is a count of test functions, not of passing test cases: parametrised tests expand when they are collected, and the suite is not fully green. For the tranche 1 runtime the recorded unit-suite result was 57 failed, 6,903 passed, 151 skipped and 3 errors #ev("4.25"). The acceptance criterion was a zero delta: the failing and erroring test identifiers were identical to a reference list recorded before the change, so the change added no failure #ev("4.25"). The same zero-delta comparison is reported for runtime changes throughout the implementation log.

*Pins and checksums.* Experimental cells are run from a prepared kit rather than from an interactive session. Before each episode, a pin gate compares the MD5 checksum of every runtime file the cell depends on (grounding code, orchestrator modules, configuration files, safety file and launcher) with its registered value, for the source tree and for the installed path. Installed paths are checked because a colcon build can report success and still leave a stale file installed #ev("4.26"). After each episode, a condition gate checks the episode's recorded condition and the expected log lines: for example, that the safety monitor started with the 0.20 m floor, and that a Layer-2-off episode wrote no decision artifact #ev("4.26"). The scorer and its frozen free-flow reference table are fixed by commit and checksum before any data are collected #ev("4.26"). Model identifiers are dated snapshots where the provider offers one, and the prompt digest is pinned by a test #ev("4.17").

== Later Extensions (Not Evaluated) <sec:impl-later>

Three groups of changes were written after the pin. None of them ran in the prereg-v3 tranche 1 pilot or in the IB10 experiment, and each is off unless explicitly enabled.

- *v4 per-cluster choice and live shadow.* The code baseline adds an offline VLM bench, grounding-first and per-cluster decision variants, and a live "shadow" that asks the model a second, per-cluster question after each analysis but never dispatches its answer. The shadow is disabled by default (`per_cluster_shadow: enabled: false`) #ev("4.27").
- *Safety-exemption scope fix.* A later fix narrows the clearing exemption to partners that accepted their leg. It is a separate overlay key, absent and therefore off in the pinned safety files #ev("4.27").
- *Refusal feedback.* A later branch tells the model about decisions that the grounder withheld, and can restrict the offered strategies to those the grounder can execute. Both switches default to off #ev("4.27").

These extensions are exploratory. Where Chapter 6 reports on them, they are kept separate from the prereg-v3 data and never pooled with it.

== Physical TurtleBot3 Demonstration <sec:impl-physical>

Beyond simulation, the pipeline was demonstrated on physical TurtleBot3 robots #todo[cite: TurtleBot3 platform documentation (ROBOTIS e-Manual)] on 12 November 2026. The account below uses only the demonstration record and its saved decision artifacts #ev("4.28").

*Setup.* The test stack used an overhead RealSense camera, ArUco-based localisation, `gemini-3.1-flash-lite` as the reasoning model, deterministic command grounding, Zenoh as the transport #todo[cite: Zenoh protocol documentation], stamped velocity commands, live execution with dry-run disabled, and the safety monitor #ev("4.28"). The saved decision artifacts confirm the model identifier in their backend diagnostics #ev("4.29"). The safety boundary of this deployment was 0.50 m, wider than the 0.45 m used in simulation #ev("4.30").

*Scenarios.* Four arrangements of up to four robots were set up by hand: two simultaneous, parallel head-on pairs (scenario A, @fig:impl-physical); a three-robot triangle with a fourth robot outside the cluster (scenario C); four robots facing a shared central region (scenario D); and a tighter dual-lane variant of A (scenario E) #ev("4.30"). Two further attempts whose model reply could not be parsed into a decision are excluded, as are earlier attempts that produced only waiting or timed-out backup commands #ev("4.31"). In scenario A, the model classified the scene as a deadlock involving all four robots and chose `reverse`. The orchestrator dispatched `reverse` to the four robots, and the command bus recorded `COMPLETED` for each of them; the two pair distances in the decision scene were about 0.575 m and 0.614 m #ev("4.30"). The outcomes of the other scenarios are reported in Chapter 6.

#figure(
  grid(
    columns: (1fr, 1fr),
    column-gutter: 8pt,
    image("../assets/images/scenario_a_two_parallel_deadlocks.png", width: 100%),
    image("../assets/images/scenario_c_three_robot_triangle.png", width: 100%),
  ),
  caption: [Annotated overhead perception frames from the physical demonstration on 12 November 2026. Left: scenario A, two simultaneous head-on pairs. Right: scenario C, a three-robot triangle with a fourth robot outside the cluster.#fig-source("4.30")],
) <fig:impl-physical>

*What the demonstration does not show.* The robots had no navigation goals. The robot states in the saved decision artifacts contain only identifier, position, heading, speed, status and stamp, and each artifact's per-robot distance-to-goal map is empty #ev("4.29"). `COMPLETED` therefore means that the reverse command finished executing on the robot. It does not mean that a conflict was resolved in the sense used for the simulation experiments, where robots must go on to reach their goals. Each scenario was run once. Finally, the code that ran on the physical robots, including the Zenoh transport and the camera integration, is not part of this repository's history, so the deployment cannot be reproduced from the pinned runtime described in this chapter. The demonstration is reported as evidence that the perception, reasoning, grounding and dispatch chain runs end to end on real hardware, not as an evaluation.
