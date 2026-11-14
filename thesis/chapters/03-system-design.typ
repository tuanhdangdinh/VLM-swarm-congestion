#import "../lib.typ": *
#import "../figures/architecture.typ": architecture-figure
#import "../figures/pipeline.typ": pipeline-figure

= System Design <sec:design>

This chapter describes the design of the coordinator as it ran in the main live experiments of this thesis, the prereg-v3 pilot on the five-robot scene and the IB10 intersection comparison: the pinned runtime of the third preregistration (prereg-v3), which is the code base at one fixed commit. Where the source tree contains later additions, they are named only in passing, marked as extensions that are switched off by default, and never treated as part of the evaluated system. Implementation choices (software stack, engineering lessons, physical deployment) follow in Chapter 4, and the experimental configuration in Chapter 5. This chapter makes no claim about outcomes; results are reported in Chapter 6.

The chapter first states the requirements the design answers (@sec:design-goals). It then presents the two-layer architecture (@sec:design-layers), the six modules and their contracts (@sec:design-modules), and the decision pipeline that links them (@sec:design-pipeline). The last three sections cover the strategy vocabulary (@sec:design-strategies), the deterministic grounding layer M3 (@sec:design-grounding), and the safety invariants that the monitor enforces independently of the reasoning layer (@sec:design-safety).

== Requirements and Design Goals <sec:design-goals>

The project starts from an observation about warehouse fleets: local navigation stacks handle most traffic well, but they are myopic. Two robots meeting head-on in a narrow aisle, or several robots converging on an intersection, can each wait for the other indefinitely, because no single robot sees the whole situation. A central observer that sees the scene from above can recognise such a jam and name a way out. A vision-language model (VLM) is a candidate for that observer, since it can read an image together with a textual state description and answer in a structured form. It is also slow, costly per call and fallible. The design therefore uses the VLM where it adds information and keeps it away from everything that must be fast or safe.

Six requirements follow from this position.

+ *Layer 1 by default.* Robots navigate with their own planners at all times. The reasoning layer intervenes only when local control has demonstrably failed, that is, when robots stop making progress towards their goals. Normal traffic never waits for a model call.
+ *Semantic assessment.* When it is invoked, the reasoning layer states whether congestion is present, what kind it is, which robots are involved, and which resolution strategy applies, from the overhead image and the tracked robot states.
+ *Executable commands only.* A model output is never sent to a robot as it is. A deterministic layer checks every proposed manoeuvre against the declared scene geometry and the robots' positions, repairs or replaces it where it is infeasible, and refuses to move robots when no safe manoeuvre exists. Every command that leaves this layer is validated against a fixed schema.
+ *Safety independent of reasoning.* Distance and speed limits are enforced by a separate monitor that runs at control rate and does not trust the reasoning layer. A failure of the model (timeout, refusal, malformed output) leads to no action, never to an unchecked motion.
+ *Model independence.* The VLM sits behind one backend interface, so that hosted and local models can be exchanged by configuration.
+ *Traceability and ablation.* Every analysis is logged with its input, the model's answer, the grounded command and the provenance of that command. The whole reasoning layer can be switched off by one configuration key, which gives the experiments a Layer-1-only baseline on the same code.

Two scope limits apply throughout. The system uses a single fixed overhead camera and estimates poses on the ground plane only; multi-camera fusion and full 6-DOF pose estimation are out of scope. The coordinator also does not replan the fleet globally, as a multi-agent path finding (MAPF) solver would @stern2019multi: it resolves one detected conflict at a time with a small set of local manoeuvres, and then hands control back to the robots' own planners.

== Two-Layer Architecture <sec:design-layers>

The architecture separates a fast, distributed layer from a slow, centralised one (@fig:architecture). The design targets, stated in the project's module decomposition, are 20–50 Hz for Layer 1 and 0.5–2 Hz for Layer 2 #ev("3.01").

#figure(
  architecture-figure(),
  caption: flex-caption([Two-layer architecture.], [Two-layer architecture. Layer 2 (orange) observes the scene through M1 and decides through M5, M2 and M3; Layer 1 (grey) executes through M4 and the per-robot Nav2 stacks; M6 provides the simulated robots and camera. Arrow labels are ROS 2 topic names. #fig-source("3.02")]),
) <fig:architecture>

*Layer 1: local reactive control.* Each robot runs its own Nav2 navigation stack @macenski2020marathon @nav2docs with a DWB local planner. In the evaluated configuration the controller runs at 20 Hz, and the planner's forward speed is capped at 0.18 m/s, below the speed limit of the safety monitor #ev("3.03"). The M4 execution layer belongs to Layer 1 as well. It turns coordination commands into Nav2 goals or into short velocity-level manoeuvres, and its safety monitor republishes stop commands for held robots at 40 Hz #ev("3.04"). None of this depends on a model call.

*Layer 2: centralised semantic reasoning.* The orchestrator M5 receives every scene update from perception and runs the congestion detector on it. Only when the detector reports a stall does M5 build a request for the VLM (M2), pass the validated decision to the grounder (M3), and publish the resulting command to M4. The effective rate of Layer 2 is therefore not a fixed loop frequency: it is limited by the detector's stall threshold and by model latency. M5’s housekeeping timer runs every 0.5 s, and M2 and M3 run inside the M5 process on a single worker thread #ev("3.05"), so a slow model call never blocks the ROS 2 callbacks that keep the scene and status picture current.

*Effective decision rate.* The 0.5–2 Hz figure is a design target #ev("3.01"); how often Layer 2 actually acts is set by the detector and the cool-down. In the shipped configuration a set of robots is analysed only after they have made no progress for 12 s, and after an analysis or a resolved command the same robots wait out a 15 s cool-down before they can trigger again #ev("3.12"). One stage-1 call to ER-2 took about 3.2–3.8 s in the measurements recorded in the configuration code, and a request may use two attempts of up to 120 s each #ev("3.30") #ev("3.10"). The same robots can therefore be re-analysed at most once per 15 s plus model latency, which is below about 0.07 Hz, an order of magnitude under the lower design target #ev("3.30"). Because only one analysis is in flight at a time, model latency also bounds the rate for the fleet as a whole. Both thresholds run on the wall clock, while the robots move in simulated time (@sec:impl-lessons), so the same configuration behaves differently on machines with different real-time factors: at a factor of about 0.38 the 12 s stall threshold corresponds to about 4.6 simulated seconds #ev("4.18"), and at the factor of about 0.18 recorded for the tranche-1 run to about 2.2 #ev("3.31").

*Intervention principle.* The two layers meet at one point, the congestion event. Layer 2 does not steer robots continuously. It issues a bounded command (a yield, a reverse, a wait, a reroute or a phased junction clearance), and each robot returns to its own base mission when that command ends. This keeps the slow layer out of the control loop. A wrong or late decision can cost time, and every motion it causes remains subject to the Layer 1 safety monitor, within the limits of the clearing exemption described in @sec:design-safety.

*Process and network boundaries.* All modules except the model communicate over ROS 2 topics @macenski2022robot. The model is reached over HTTP: hosted models through their providers' APIs, local models through an OpenAI-compatible server. Keeping the model outside the ROS 2 graph means that its machine needs no DDS configuration, and that a model can be exchanged without touching the robot side.

== Modules M1–M6 and Their Contracts <sec:design-modules>

The system is decomposed into six modules with separate owners in the source tree. Data crossing a module boundary is an immutable, validated model (Pydantic v2 in Python) or a ROS 2 message whose payload is such a model serialised as JSON. Raw provider responses and ROS 2 message objects never cross a reasoning boundary. @tab:module-io lists each module's inputs and outputs with the names used in the code.

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
    [*M3* Grounding],
    [`ReasonerResult`; `SnapshotFrame`; declared `SceneGeometry` and static obstacles; `GroundingParams`; optional stage-2 retreat choice],
    [Schema-valid coordination command (actions, expected resolution time, fallback, degradation tags); `VerifiedPlan` with provenance; `JunctionClearPhasePlan`],
    [*M4* Execution and safety],
    [`/coordination/commands`; `/perception/scene_state` (safety monitor); `/<robot>/odom`; `/safety/holds`],
    [`/coordination/status`; Nav2 `NavigateToPose` and `FollowWaypoints` goals; `/<robot>/cmd_vel`; `/safety/holds`],
    [*M6* Simulation],
    [`/<robot>/cmd_vel`],
    [`/camera/image_raw`; `/<robot>/odom`; `/<robot>/scan`; `/clock`; validation-only ground-truth poses],
  ),
  caption: flex-caption([Module inputs and outputs in the evaluated runtime.], [Module inputs and outputs in the evaluated runtime. Names in monospace are ROS 2 topics, services or data contracts as they appear in the code; `<robot>` stands for a robot namespace such as `robot_1`. #fig-source("3.06")]),
) <tab:module-io>

*M1, perception and robot tracking.* M1 turns overhead camera frames into world-frame robot states. Each robot carries an ArUco marker @garridojurado2014automatic @opencv2026aruco from the `DICT_4X4_50` dictionary #ev("3.07"). M1 detects the markers, maps their corners from pixel to world coordinates through a ground-plane homography, derives each robot's position and heading, and estimates velocity by filtered finite differences. From speed and marker age it assigns each robot a status: `MOVING`, `SLOW`, `STOPPED` or `STALE`, the last meaning that the marker has not been seen recently. Task and goal information comes from M5’s registry, which M1 reads but never writes. M1 also draws a Set-of-Mark annotation @yang2023mark (status-coloured boxes, identifiers, velocity arrows) on the frame that M2 later receives. In the simulated setup the camera delivers 1280 × 960 pixels at 30 frames per second #ev("3.07"). Late frames are dropped rather than reordered, so every consumer tolerates an occasional missing scene.

*M5, orchestrator.* M5 is the central state machine and the only module that decides _when_ Layer 2 acts. It owns the task registry (each robot's base mission and goal), the congestion detector, the command lifecycle and, when the plan channel is enabled, the plan tracker. Its state machine has three states (monitoring, analysing, dispatching) and allows one analysis in flight at a time. An event is suppressed while any of its robots is in cool-down or still executing an earlier command. A single stalled robot queued behind a manoeuvre that already moves two or more other robots is folded into that episode rather than analysed on its own #ev("3.08"). One configuration key, `reasoning_enabled`, turns Layer 2 off as a whole. With it set to false, detection, M2, M3 and dispatch never run, while scene logging, the task registry and the task stream continue unchanged #ev("3.09"). This switch defines the Layer-1-only arm of the experiments.

*M2, VLM reasoning.* M2 renders a prompt from the annotated frame and a textual state list, sends it to the configured backend, and parses the answer into a `CongestionDecision` (@sec:design-strategies). Backends for a scripted mock, a local `llama-server`, OpenAI, Anthropic and Gemini sit behind one interface. Prompt building, retries and output parsing are shared and backend-agnostic, while each backend owns its HTTP payload, authentication and image encoding. A request is attempted at most twice. The shipped model configuration sets a timeout of 120 s per call, and this is the value the live experiments ran with; the code default of 30 s applies only when no configuration sets one #ev("3.10"). If every attempt fails, M2 returns a result without a decision, and M5 records the failure and dispatches nothing. Robots can be listed in the prompt in ascending identifier order (the default), in descending order, or, in scenes with three or more robots, in a random permutation drawn per episode #ev("3.10"). This is a deliberate control against a possible positional preference of the model for whichever robot is listed first. When the plan channel is enabled, M2 also receives the status of the plan currently executing and may return a scene-wide `proposed_plan`.

*M3, grounding.* M3 translates a validated decision into a command that M4 can execute. M3 is a deterministic, geometry-driven grounder: it derives roles, distances and order from the snapshot positions and the declared scene geometry, and it audits the model's own proposed plan against the same checks. @sec:design-grounding describes M3 in detail.

*M4, execution and safety.* M4 has three parts. The command bus executes each robot's leg of a command, either as a Nav2 goal (navigation, reroute) or as a velocity-level clearing primitive (backup, sidestep, hold, escort), and reports `ACTIVE`, `COMPLETED` or `FAILED` status. A coordination client per robot resumes the robot's base mission once its command ends. The safety monitor enforces the invariants of @sec:design-safety on every scene update. The command bus rejects a command for a robot that is already busy, and a watchdog bounds every Nav2 leg, so that a hung goal cannot lock a robot out of later analyses.

*M6, simulation.* M6 provides the warehouse world in Isaac Sim @isaacsimdocs: TurtleBot3 Burger robots @robotis2026turtlebot3 with simulated lidar and odometry, the fixed overhead RGB camera, static obstacles, and the scenario files from which scenes are generated. It publishes the simulation clock and records ground-truth poses for validation only; ground truth never feeds the decision pipeline. A velocity relay in front of each robot zeroes the drive command when no command has arrived recently, so a crashed publisher cannot leave a robot moving.

== Decision Pipeline: Detect, Decide, Ground, Act, Resolve <sec:design-pipeline>

@fig:pipeline shows the path from a stall to its resolution. Each step has a single owner and a defined exit on failure.

#figure(
  pipeline-figure(),
  caption: flex-caption([Decision pipeline.], [Decision pipeline. The main path runs left to right; orange elements are the deterministic checks that can change or stop a decision before or during execution. A refusal dispatches nothing and returns control to monitoring. #fig-source("3.11")]),
) <fig:pipeline>

*1. Detect.* M5 tracks, for every robot with a goal, the smallest distance to that goal seen so far. A robot is stalled when this distance has not improved by more than a progress margin for the length of the stall threshold. Robots that are `STALE` or already at their goal are excluded from this test. A second rule covers robots that are close together and slow, and it includes `STALE` robots, because two robots jammed next to each other are a real standoff even when one marker is hidden. In the shipped configuration the stall threshold is 12 s (wall clock) and the progress margin 0.10 m #ev("3.12"). The detector reports all robots stalled in the same tick as one event. It does not group them into separate clusters, which matters for the safety discussion in @sec:design-safety.

*2. Decide.* For an admitted event, M5 saves the current annotated frame, builds a `ReasonerRequest` from the same scene snapshot, and submits it to the worker thread. M2 returns a validated decision or none. A decision with `congestion_detected` false ends the cycle without action. When the decision is a yield, an optional second VLM call (stage 2) asks the model to pick one of several retreat candidates that M3 has generated and labelled with letters on the image. Its answer is used only if it names a candidate that M3 has already validated; otherwise the top-ranked candidate is used #ev("3.13").

*3. Ground.* M3 converts the decision into a command, applies its feasibility checks and, with the plan channel enabled, audits the model's proposed plan (@sec:design-grounding). Grounding either produces a schema-valid command or raises an error that M5 records as a grounding failure. A refused yield becomes a bounded wait, which M5 can withhold altogether.

*4. Act.* M5 fans the command out as one `CoordinationCommand` per robot on `/coordination/commands`, with the action and its parameters encoded as JSON. For a `junction_clear` decision, M5 seeds a phase queue and dispatches the phases one after another, each only after the previous one has ended. M4 executes each leg while the safety monitor watches every pair of robots.

*5. Resolve.* M4’s status messages update M5’s command lifecycle. When a command is resolved, or when an analysis ends without a dispatch, the robots concerned enter a cool-down, 15 s (wall clock) in the shipped configuration #ev("3.12"), before they can trigger a new analysis. A command whose robots are all still pending after the command timeout, 20 s (wall clock) by default #ev("3.12"), is expired as a lost dispatch; active legs are bounded by M4 itself. Robots return to their base missions through the coordination client. If the jam persists, the detector fires again and a new cycle starts. The new request can carry a short summary of the previous attempt and its outcome, so the model can see that a strategy already failed. M5 never re-invokes the model in the middle of a phased `junction_clear`: later phases come from the plan M3 computed up front.

== Strategy Vocabulary <sec:design-strategies>

M2’s answer is a `CongestionDecision` with the fields `congestion_detected`, `type`, `involved_robots`, `root_cause`, `strategy` and `justification`. Optional fields carry the model's chosen yielder (`yield_robot`), a crossing order for three or more robots, a blocker kind and the scene-wide `proposed_plan`. The type is one of `none`, `deadlock`, `bottleneck`, `crowding` and `anomaly`. The strategy is one of a closed set of eight values, which the parser enforces at every prompt version #ev("3.14"). The parser also enforces consistency: a stated yielder must be among the involved robots, a crossing order must be a permutation of them, and a proposed plan may name each robot at most once.

A strategy is a semantic label, not an executable action. @tab:strategies shows, for each strategy, what M3 grounds it to and which M4 primitive finally moves the robots. The grounder emits only four per-robot actions: `yield`, `reverse`, `reroute` and `temporary_wait` #ev("3.14"). The other strategies are expressed through these four or fall back to a wait.

#figure(
  placement: auto,
  table(
    columns: (auto, 1.25fr, 1fr),
    align: (left, left, left),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Strategy (M2)*], [*Grounding (M3)*], [*Execution (M4)*]),
    [`none`], [No command; the cycle ends.], [—],
    [`yield`], [One yielder backs up to a park point, optionally steps aside, and holds while the passers cross in order. Distances come from positions and declared geometry. An infeasible yielder is swapped or the yield is refused (@sec:design-grounding).], [Clearing primitive: backup, sidestep, odometry-gated hold, optional escort of the passer, ordered release.],
    [`reverse`], [Backward clearing leg for the robots concerned, without a hold. Refused when both robots sit beyond the corridor on the same side.], [Clearing primitive: backup.],
    [`junction_clear`], [Phased plan: one `reverse` per recede candidate in cost order, then a `yield` for the robots on the crossing axis, then a staggered release. Precomputed from one snapshot; a plain yield is the fallback if a phase fails.], [Sequence of the primitives above, dispatched phase by phase by M5.],
    [`reroute`], [Waypoints of a detour the scene declares; otherwise the robot's own goal is re-sent.], [Nav2 waypoint following or goal.],
    [`temporary_wait`], [Bounded wait for the involved robots.], [Nav2 goal cancelled, timer, then resume.],
    [`convoy`], [No template of its own. Mapped to an ordered yield when exactly one involved robot moves against all the others; otherwise a bounded wait tagged as unsupported.], [As `yield`, or as `temporary_wait`.],
    [`priority_override`], [No template of its own. Mapped to an ordered yield when exactly two robots are involved and one has the unique highest registry priority; otherwise a bounded wait tagged as unsupported.], [As `yield`, or as `temporary_wait`.],
  ),
  caption: flex-caption([Strategy vocabulary of the evaluated runtime.], [Strategy vocabulary of the evaluated runtime and how each strategy reaches the robots. A "bounded wait" is a `temporary_wait` of fixed length for every involved robot. #fig-source("3.15")]),
) <tab:strategies>

Three design decisions are visible in the table. First, the vocabulary is closed. The model cannot invent a manoeuvre, and a token outside the set fails validation instead of being interpreted. Second, every executable strategy ends in a small set of primitives that M4 already implements and the safety monitor understands: two clearing primitives (`yield` and `reverse`), Nav2 legs and waits. Third, a strategy without a grounded meaning degrades to waiting, not to invented motion. `convoy` and `priority_override` are executed only as the ordered yield they reduce to. For `convoy`, the robot moving against the platoon is the unique robot whose goal bearing differs by more than 90° from every other involved robot's #ev("3.16"). For `priority_override`, the mapping is limited to two robots, because one yield cannot make several lower-priority robots give way at once #ev("3.16"). The bounded wait lasts 8 s #ev("3.16"). `junction_clear` is the only composite strategy. It was added for multi-robot junction jams, in which no single yield opens a path, and only the third prompt version offers it to the model.

== Grounding: Feasibility, Repair, Refusal and the Default Plan <sec:design-grounding>

M3 is where the system's main safety-relevant judgement is made deterministic. Its inputs are the decision, the scene snapshot the decision was made on, the declared scene geometry (corridor, junction arms and boxes, static obstacles, robot footprint, and the camera height used to keep markers visible) and a parameter set. @tab:grounding-config lists the settings that switch M3’s mechanisms on. Several of them are off in the shipped configuration and switched on by the experiment overlays; Chapter 5 records the configuration of each experiment.

#figure(
  placement: auto,
  table(
    columns: (auto, auto, auto, 1fr),
    align: (left, left, left, left),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Setting*], [*Shipped default*], [*S1b scene overlay*], [*Effect*]),
    [`grounding_yield_feasibility`], [`off`], [`swap`], [Checks the named yielder's retreat room; swaps or refuses.],
    [`plan_channel_enabled`], [false], [true], [Prompt version 3, `proposed_plan` audit, plan tracking, `junction_clear` phases.],
    [`refusal_no_action`], [off], [on], [A refused yield dispatches nothing (requires the task stream).],
    [Grounding mode], [derived], [derived], [Feasibility bands and swept-path checks instead of fixed distances.],
    [`max_repair_edits`], [4], [4], [Largest repair accepted before the default plan is used.],
    [`plan_dispatch_order_source`], [`chi`], [`chi`], [The recede order of `junction_clear` is M3’s cost order.],
  ),
  caption: flex-caption([Grounding settings, shipped and in the S1b scene overlay.], [Grounding settings in the shipped configuration and in the M5 overlay that the five-robot S1b scene file declares. The prereg-v3 pilot ran with the plan channel and refusal-as-no-action on, with a variant of the derived-mode grounding file; the IB10 registration enables the plan channel and names the shipped grounding file, which sets derived mode (Chapter 5). #fig-source("3.17")]),
) <tab:grounding-config>

*Feasibility checks.* Every spatial strategy is checked against the scene before anything is commanded. A yielder must have enough free room behind it, measured along its own corridor side or junction arm up to the nearest static obstacle, to back up to a park point from which the passer can get by. A reverse is refused when both robots already sit beyond the corridor on the same side, because the backup would then traverse the corridor instead of opening it. In derived mode, backup and escort distances must fall inside configured bands, and each retreat candidate is swept along its path against obstacles and other robots before it can be used. For `junction_clear`, recede candidates are ranked by a cost function (the "chi" order). The release phase lets the lowest-cost candidate leave first and the yielder re-enter last. When no recede candidate survives, M3 grounds a plain yield instead, and tags the command if the scene lacks the junction geometry the composite needs #ev("3.18").

*Yield feasibility gate: swap or refuse.* When the yielder named by the model cannot reach a park point, the gate in `swap` mode hands the yield to another involved robot that can, with ties broken by the decision's own robot order. When no involved robot is feasible, or in `refuse` mode, the yield is refused #ev("3.18"). The swap is recorded on the command as a re-grounding, together with the shortfall that caused it. This gate encodes a design decision: the model is trusted to recognise a deadlock and to choose yielding as the way out, but not to judge from an image which robot has room to retreat. The system checks that from geometry.

*Refusal and no action.* A refused yield is grounded as a bounded wait for the involved robots. Under `refusal_no_action`, which the task-stream scene sets, M5 withholds that wait and dispatches nothing at all. A yield that degrades to a reroute with no declared detour is withheld in the same way #ev("3.19"). The reason is that, in a scene where other robots keep moving, a wait that cancels Nav2 goals would itself disturb traffic without resolving anything. The withheld decision is still logged with its refusal reason, and the detector can fire again later.

*The proposed plan and its audit.* With the plan channel on, the model may return a scene-wide `proposed_plan`: an ordered list of legs, each pairing a robot with one of `yield`, `reverse`, `cross`, `wait`, `reroute` or `continue`. M3’s verify-and-repair engine audits this plan leg by leg against the same feasibility checks the grounder uses #ev("3.20"):

- a robot the plan omits is completed with a `continue` leg, which does not count as a repair;
- a plan that names an unknown robot, does not fit the decided strategy (for example a `yield` decision without exactly one `yield` leg), or contradicts the decision's own yielder or crossing order, is rejected;
- a consistent plan whose legs are all feasible is accepted unchanged;
- a consistent plan with infeasible legs is repaired by a breadth-first search for the fewest edits. An edit swaps the roles of two robots, reorders two legs, or substitutes one robot's action with M3’s own. The search is bounded at four edits #ev("3.20"). Among repairs of equal depth, the one that keeps M3’s preferred yielder wins.

Each audited plan receives one of three provenance labels: `vlm_verbatim` (accepted unchanged), `repaired` (accepted after edits, each logged with its reason) or `m3_default` (absent, rejected, or not repairable within the bound) #ev("3.20").

*The default plan.* `m3_default` names M3’s own scene-wide plan for the decision. It is built from the same functions the grounder uses to construct commands, never from a second implementation. For a decision without a plan it is therefore exactly what the grounder dispatches, and it is the target towards which repairs move.

*Audit, not dispatch.* One property of the evaluated runtime matters for interpreting the results. The command that reaches M4 is always produced by the deterministic grounder from the decision's strategy and role fields (strategy, involved robots, yielder, crossing order and stage-2 choice), after the feasibility gate. The plan audit labels the model's proposed plan, records whether the dispatched command matches it, and seeds the `junction_clear` phase queue; it does not replace the grounder's output #ev("3.20"). A `vlm_verbatim` label thus says that the model's plan passed the audit unchanged, not that the model's plan was executed in place of M3’s. The one exception (plan channel only) is an opt-in mode in which a verified model plan sets the recede order of `junction_clear`; it is off in the evaluated configuration (@tab:grounding-config).

*Degradation tags.* Every command carries a list of tags that name what M3 changed or refused and why: for example a yield made infeasible by geometry, a reverse shortened to stay inside the tracked area, a strategy mapped onto a yield, a retreat chosen by default because the stage-2 answer was invalid, or a junction plan replaced by its fallback. The tags make each command's history readable from its decision record alone. The provenance labels reported in Chapter 6 come from the plan audit above, and the tags complement them with the reason for each change.

*Later extensions (not evaluated).* After the experiments, further variants were built on later branches: a grounding-first prompt that offers the model only options M3 can execute, which exists as an offline benchmark variant; a per-cluster mode that grounds each conflict group separately and ran in the live loop only as a decision-only shadow; and a feedback channel that tells the model which of its decisions were withheld. The runtime switches for the shadow and the feedback channel are off by default #ev("3.21"). None of these variants dispatched a command in the experiments evaluated here, and they appear in this thesis only as exploratory work.

== Safety Invariants <sec:design-safety>

The safety monitor in M4 is the last line of defence and deliberately the simplest component in the motion path. It subscribes to M1’s scene state and to the coordination command and status topics, and it does not consult M2 or M3. When a rule fires, it publishes zero velocity to the robot at 40 Hz and cancels the robot's Nav2 goal, so the local planner cannot keep driving against the stop #ev("3.04"). It also publishes the set of held robots, which stops the coordination client from re-issuing their goals. @tab:safety lists the invariants.

#figure(
  placement: auto,
  table(
    columns: (auto, auto, 1fr),
    align: (left, left, left),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Invariant*], [*Value*], [*Rule*]),
    [Minimum distance], [0.45 m], [Any pair of robots closer than this, centre to centre, is held (both robots) until a fresh reading shows the pair at or beyond the limit.],
    [Speed limit], [0.2 m/s], [A robot reported faster than this is held. Robots executing a clearing primitive are exempt.],
    [STALE fail-safe], [0.6 m], [A robot whose marker is lost keeps any hold it had, and is held if its last fresh distance to another robot was below this band.],
    [Hard-contact floor], [0.20 m (armed per run; 0, i.e. off, in the shipped file)], [Holds a pair below this distance even while a clearing exemption covers it.],
  ),
  caption: flex-caption([Safety invariants enforced by the M4 safety monitor.], [Safety invariants enforced by the M4 safety monitor. The floor is off in the shipped safety file and enabled by a per-run configuration swap in the live experiments. #fig-source("3.22")]),
) <tab:safety>

*Minimum distance, 0.45 m.* The proposal set the minimum distance at 0.3 m #ev("3.23"). It was raised to 0.45 m because 0.3 m centre to centre left about 0.5 s of reaction time at the worst-case closing speed, against a perception-to-monitor latency of 0.2–0.4 s; the larger value restores about one second of margin and still fits the narrow-aisle standoff geometry #ev("3.23"). M3 uses the same radius when it sizes escort and pass legs, so that a grounded manoeuvre does not itself trip the latch.

*STALE fail-safe.* A robot whose marker M1 can no longer detect has an unknown pose. The design treats that pose as unsafe, not as absent. The robot keeps an existing hold, and it is held when its last distance measured while both robots were tracked lies within 0.6 m, the minimum distance plus a 0.15 m margin #ev("3.22"). The rule uses this remembered distance, not the frozen pose that M1 republishes, because the frozen pose is exactly the datum that becomes wrong while the robot keeps moving. Overlapping markers cannot be detected, so without this rule two robots in contact would both become `STALE` and the monitor would see nothing.

*Clearing exemption.* The two clearing primitives, `yield` and `reverse`, must work inside the minimum distance: a robot backing out of a nose-to-nose standoff starts closer than 0.45 m to its partner. The exemption is scoped as follows #ev("3.24"):

- While a robot's active command is a clearing primitive, its pairs with the partners named in the same command are exempt from the minimum-distance and STALE pair rules, and the robot itself is exempt from the speed rule.
- During a yield's backup and sidestep, every robot of the command is a partner; from the hold onwards, only the passers admitted so far are.
- Robots outside the command (bystanders) keep full protection against the clearing robot. Nav2 legs and waits never exempt anything, and robots that M3 holds only to shield them from a retreat are not partners.
- A clearing robot already held together with a third robot when its command starts is released one-sidedly: it may leave, while the other robot stays held until the pair separates.

*Hard-contact floor, 0.20 m.* The exemption leaves a gap: within one command, nothing in the distance rule stops a clearing robot from pushing its own partner. The floor is a backstop for that gap. Any pair below 0.20 m is held, exempt or not #ev("3.22"); since it acts at or near contact, it limits the damage rather than preventing the approach. The value is the footprint contact separation of 0.18 m plus about twice M1’s median static position error of 0.011 m #ev("3.25"), so it lies far below the 0.45 m limit and leaves room for clearing manoeuvres. The shipped safety file keeps the floor at 0, which disables it; the live experiments install a variant of the file that differs only in that line #ev("3.22").

*Arming the floor.* Because the floor is armed by a per-run file swap rather than by the code default, the experiment procedure checks it around every run. Before launch, the floor variant is installed in place of the shipped safety file, and the deploy check confirms that the installed file is the floor variant. An episode is accepted only if M4’s startup log line reports `hard_contact_floor_m=0.2`; a missing line stops the run chain. After the run, the shipped file is restored and verified by checksum #ev("3.26"). Every floor stop is counted as a safety finding of its episode. The preregistration addenda additionally require "pre- and post-arm gates" in every live cell of the five-robot scene, but the sources read for this chapter do not define what each of these gates checks. They are therefore not described further here. All of these checks belong to the experimental procedure, not to the runtime code, and Chapter 5 reports their use per experiment. #todo[[VERIFY] owner to define what the pre-arm and post-arm gates check]

*Exemption scope: a gap found after the experiments.* A code review made after the experiments traced how far the clearing exemption and the one-sided releases reach #ev("3.27"). It identified five paths:

+ partner lists that cross conflict clusters, because the detector reports all robots stalled in one tick as one event (a bug);
+ partner lists that are fixed when a command is published and can go stale (a bug and a residual risk);
+ a robot whose leg the command bus rejected as busy still counting as a partner (a bug);
+ two clearing robots releasing each other one-sidedly (a bug, left for a separate decision);
+ the intended own-command scope (by design).

The trace is a static reading of the code made after the experiments, not an analysis of live outcomes. It attributed no recorded incident to these paths and noted that in recent live cells the 0.20 m floor was armed as a backstop for every exempt pair #ev("3.27"). The first three paths were fixed afterwards on a separate branch, behind a new safety key, `scoped_clearing_exemption`. The key takes effect only when it is set to true; when it is absent or false, the monitor behaves exactly as in the evaluated runtime #ev("3.28"). The evaluated runtime does not contain the fix. In the prereg-v3 pilot and the main IB10 comparison the exemption therefore had the wider scope described above, and this is stated as a limitation wherever a result depends on it. A later exploratory IB10 run enabled the key on top of the same runtime #ev("3.28"); it is reported separately and is not part of the evaluated system described here.

*Summary of the safety design.* Safety rests on three mechanisms that do not depend on the model. M3 refuses or reshapes manoeuvres that the geometry does not allow. M4’s monitor holds any robot that breaks the distance, speed or STALE rules, with an exception for clearing primitives whose scope proved wider than intended (above); inside that exception only the 0.20 m floor applies. The model cannot select a motion that escapes the floor.
