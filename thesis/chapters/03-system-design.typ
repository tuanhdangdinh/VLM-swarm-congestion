#import "../lib.typ": *
#import "../figures/architecture.typ": architecture-figure
#import "../figures/pipeline.typ": pipeline-figure

= System Design <sec:design>

This chapter states the design of the coordinator and the reasons for it, for the runtime of the main live experiments: the pinned runtime of the third registered design (v3). Chapter 4 describes how it is built. Mechanisms added later are listed once, in @sec:impl-later, and are not part of the evaluated system.

== Requirements and Design Goals <sec:design-goals>

Local navigation stacks are myopic: two robots meeting head-on in a narrow aisle, or several converging on an intersection, can each wait for the other indefinitely, because no robot sees the whole situation. An observer above the scene can recognise such a jam and name a way out. A vision-language model (VLM) can read an image together with a textual state description and answer in a structured form, but it is slow, costly per call and fallible. The design therefore uses the VLM only where it may add information and keeps it out of everything that must be fast or safe:

+ *Local navigation by default.* Robots always navigate with their own planners; the coordination layer intervenes only when robots stop making progress, so normal traffic never waits for a model call.
+ *Semantic assessment.* When invoked, the coordination layer states from the overhead image and the tracked states whether congestion is present, its type, the robots involved and a resolution strategy.
+ *Executable commands only.* No model output reaches a robot as it is. A deterministic grounder checks each manoeuvre against the declared geometry and the robots' positions, repairs or replaces it, or refuses to move robots, and every command it emits is schema-validated; static obstacles enter only the yielder's retreat-room check (@sec:design-grounding).
+ *Safety independent of reasoning.* A separate monitor enforces distance and speed limits at control rate. A model failure leads to no action, but a valid decision can still produce motion that nothing checks against static obstacles.
+ *Model independence.* The VLM sits behind one backend interface.
+ *Traceability and ablation.* Every analysis is logged with its input, answer, grounded command and plan audit, and one key switches the coordination layer off, which gives a control with local navigation only on the same code.

The system uses one fixed overhead camera and estimates poses on the ground plane only. It does not replan the fleet globally, as a multi-agent path finding (MAPF) solver would @stern2019multi; it resolves one detected conflict at a time with a few local manoeuvres and then hands control back to the robots' planners.

== Two-Layer Architecture <sec:design-layers>

The architecture separates a fast, distributed layer from a slow, centralised one (@fig:architecture), with design targets of 20–50 Hz for local navigation (Layer 1) and 0.5–2 Hz for the coordination layer (Layer 2) #ev("3.01").

#figure(
  architecture-figure(),
  caption: flex-caption([Two-layer architecture.], [Two-layer architecture. The coordination layer (orange) observes the scene through perception (M1) and decides through the orchestrator (M5), VLM reasoning (M2) and the grounder (M3). Local navigation (grey) executes through the execution and safety monitor (M4) and the per-robot Nav2 stacks. Simulation (M6) provides the robots and the camera. Arrow labels are ROS 2 topic names. #fig-source("3.02")]),
) <fig:architecture>

*Local navigation.* Each robot runs its own Nav2 stack @macenski2020marathon @nav2docs; in the evaluated configuration the controller runs at 20 Hz and forward speed is capped at 0.18 m/s, below the monitor's speed limit #ev("3.03"). M4 belongs to this layer: it turns coordination commands into Nav2 goals or short velocity-level manoeuvres, and its monitor republishes stop commands for held robots at 40 Hz #ev("3.04"). Nothing here waits on a model call.

*Coordination layer.* The orchestrator runs the congestion detector on every scene update. Only when it reports a stall does it request a VLM decision, have it grounded and publish the command. M2 and M3 run inside the M5 process on one worker thread, polled by a 0.5 s timer #ev("3.05"), so a slow call never blocks the callbacks that keep the scene current. All modules but the model, which is reached over HTTP, use ROS 2 topics @macenski2022robot.

*Effective decision rate.* The 0.5–2 Hz figure is a target #ev("3.01"). Robots are analysed only after 12 s without progress and then wait out a 15 s cool-down #ev("3.12")\; one first-stage call to Gemini Robotics-ER 2 (ER-2) took about 3.2–3.8 s, and a request may use two attempts of up to 120 s #ev("3.30") #ev("3.10"). The same robots are therefore re-analysed below about 0.07 Hz #ev("3.30"), and with one analysis in flight, latency bounds the fleet's rate too; with the longer prompts of the demonstration campaign, calls took 6.7–11.5 s in the first three convoy takes and 7.0–13.0 s in the five-robot take #ev("6.01"). Both thresholds run on the wall clock (@sec:impl-lessons).

*Intervention principle.* The layers meet only at the congestion event. The coordination layer issues a bounded command (a yield, a reverse, a wait, a reroute or a phased junction clearance) and each robot resumes its own mission when it ends. A wrong or late decision can cost time, but every motion stays under the monitor, within the clearing exemption of @sec:design-safety; the monitor checks robot pairs, not clearance to static obstacles.

== Modules M1–M6 and Their Contracts <sec:design-modules>

Six modules with separate owners make up the system. Data crossing a module boundary is an immutable, validated model, or a ROS 2 message carrying one as JSON; raw provider responses and ROS 2 message objects never cross a reasoning boundary. @tab:module-io in Chapter 4 lists the contracts.

*Perception (M1)* turns overhead frames into world-frame robot states from one ArUco marker per robot @garridojurado2014automatic @opencv2026aruco, with a status `MOVING`, `SLOW`, `STOPPED` or `STALE` (marker not seen recently), and draws a Set-of-Mark annotation @yang2023mark on the frame M2 receives. It reads goals from the task registry but never writes it.

*The orchestrator (M5)* alone decides _when_ the coordination layer acts. It owns the task registry, the congestion detector, the command lifecycle and the plan tracker, allows one analysis in flight, suppresses an event while any of its robots is cooling down or executing, and folds a lone stalled robot queued behind a running multi-robot manoeuvre into that episode #ev("3.08"). The key `reasoning_enabled: false` switches the coordination layer off: detection, M2, M3 and dispatch never run, while logging, the registry and the task stream continue #ev("3.09").

*VLM reasoning (M2)* renders a prompt from the annotated frame and a state list, calls the backend and parses a `CongestionDecision` (@sec:design-strategies); prompt building, retries and parsing are backend-agnostic. A request has at most two attempts of 120 s each in the shipped model configuration (the code default of 30 s applies only when nothing sets one); if all fail, nothing is dispatched #ev("3.10"). Robots can be listed in ascending or descending identifier order or in a random permutation per episode #ev("3.10"), a control against a positional preference of the model.

*The grounder (M3)* is deterministic: it derives roles, distances and order from snapshot positions and declared geometry and audits the model's plan with the same checks (@sec:design-grounding). *The execution and safety monitor (M4)* runs each leg as a Nav2 goal or a clearing primitive, resumes base missions, rejects commands for busy robots, and bounds every Nav2 leg with a watchdog (@sec:design-safety). *Simulation (M6)* provides Isaac Sim @isaacsimdocs with TurtleBot3 Burger robots @robotis2026turtlebot3 and records ground-truth poses for validation only; its contact lists were hard-coded empty in the evaluated runtime, so ground truth supplies poses and pair distances, not contacts #ev("6.20").

== Decision Pipeline: Detect, Decide, Ground, Act, Resolve <sec:design-pipeline>

@fig:pipeline shows the path from a stall to its resolution; each step has one owner and a defined exit on failure.

#figure(
  pipeline-figure(),
  caption: flex-caption([Decision pipeline.], [Decision pipeline. The main path runs left to right; orange elements are the deterministic checks that can change or stop a decision before or during execution. A refusal dispatches nothing and returns control to monitoring. #fig-source("3.11")]),
) <fig:pipeline>

*1. Detect.* A robot with a goal is stalled when its best distance to the goal has not improved by more than 0.10 m for 12 s of wall-clock time; `STALE` robots and robots at their goal are excluded #ev("3.12"). A second rule catches slow robots close together, including `STALE` ones, because a hidden marker does not end a standoff. All robots stalled in one tick form one event; conflict clusters are not separated, which matters for the exemption scope (@sec:design-safety).

*2. Decide.* M5 builds a request from the snapshot and its annotated frame. A decision without congestion ends the cycle. For a yield, an optional second-stage question asks the model to pick one of the retreat candidates M3 has lettered on the image; an answer that names no validated candidate falls back to the top-ranked one #ev("3.13").

*3. Ground.* M3 produces a schema-valid command or a recorded grounding failure.

*4. Act.* M5 publishes one `CoordinationCommand` per robot, and the phases of a `junction_clear` one after another.

*5. Resolve.* Robots of a resolved command, or of an analysis without dispatch, cool down for 15 s; a command whose robots are all still pending after 20 s is expired #ev("3.12"). If the jam persists, the detector fires again, and the new request can summarise the failed attempt. The model is never re-asked inside a phased `junction_clear`.

== Strategy Vocabulary <sec:design-strategies>

A `CongestionDecision` holds `congestion_detected`, `type` (`none`, `deadlock`, `bottleneck`, `crowding` or `anomaly`), `involved_robots`, `root_cause`, `strategy` and `justification`, and optionally a yielder, a crossing order, a blocker kind and a scene-wide `proposed_plan`. The strategy is one of eight values, enforced at every prompt version, and the parser checks consistency: a yielder must be involved, a crossing order must permute the involved robots, and a plan names each robot at most once #ev("3.14"). A strategy is a label, not an action; the grounder emits only `yield`, `reverse`, `reroute` and `temporary_wait` #ev("3.14") (@tab:strategies).

#figure(
  placement: auto,
  table(
    columns: (auto, 1.25fr, 1fr),
    align: (left, left, left),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Strategy (M2)*], [*Grounding (M3)*], [*Execution (M4)*]),
    [`none`], [No command; the cycle ends.], [—],
    [`yield`], [One yielder backs up to a park point, optionally steps aside, and holds while the passers cross in order. An infeasible yielder is swapped or the yield refused.], [Clearing primitive: backup, sidestep, odometry-gated hold, optional escort, ordered release.],
    [`reverse`], [Backward clearing leg without a hold; refused when both robots sit beyond the corridor on the same side.], [Clearing primitive: backup.],
    [`junction_clear`], [Phased plan from one snapshot: one `reverse` per back-out candidate in cost order, a `yield` for the crossing axis, a staggered release; a plain yield if a phase fails.], [The primitives above, phase by phase.],
    [`reroute`], [Waypoints of a declared detour, else the robot's own goal re-sent.], [Nav2 waypoints or goal.],
    [`temporary_wait`], [Bounded wait for the involved robots.], [Goal cancelled, timer, resume.],
    [`convoy`], [Ordered yield when exactly one involved robot moves against all others; else a bounded wait tagged unsupported.], [As `yield` or `temporary_wait`.],
    [`priority_override`], [Ordered yield when exactly two robots are involved and one has the unique highest priority; else a bounded wait tagged unsupported.], [As `yield` or `temporary_wait`.],
  ),
  caption: flex-caption([Strategy vocabulary of the evaluated runtime.], [Strategy vocabulary of the evaluated runtime and how each strategy reaches the robots. A "bounded wait" is a `temporary_wait` of fixed length for every involved robot. #fig-source("3.15")]),
) <tab:strategies>

The vocabulary is closed, so the model cannot invent a manoeuvre; every executable strategy ends in primitives that M4 implements and the monitor understands; and a strategy without a grounded meaning degrades to waiting, not to invented motion: `convoy` needs a robot whose goal bearing differs by more than 90° from every other involved robot's, `priority_override` is limited to two robots because one yield cannot make several robots give way, and the bounded wait lasts 8 s #ev("3.16"). `junction_clear`, the only composite, exists because no single yield opens a multi-robot junction jam; only prompt version 3 offers it.

== Grounding: Feasibility, Repair, Refusal and the Default Plan <sec:design-grounding>

The grounder makes the system's main safety-relevant judgement deterministic. It takes the decision, its snapshot, the declared geometry (corridor, junction arms and boxes, static obstacles, robot footprint) and a parameter set (@tab:grounding-config); Chapter 5 gives each experiment's configuration.

#[
#show raw: set text(size: 8pt)
#figure(
  placement: auto,
  table(
    columns: (2.3fr, 1fr, 1.1fr, 2.6fr),
    align: (left, left, left, left),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    inset: 5pt,
    table.header([*Setting*], [*Shipped default*], [*Five-robot overlay*], [*Effect*]),
    [`grounding_yield_feasibility`], [`off`], [`swap`], [Checks the named yielder's retreat room; swaps or refuses.],
    [`plan_channel_enabled`], [false], [true], [Prompt version 3, plan audit, plan tracking, `junction_clear` phases.],
    [`refusal_no_action`], [off], [on], [A refused yield dispatches nothing (requires the task stream).],
    [Grounding mode], [derived], [derived], [Feasibility bands and swept-path checks instead of fixed distances.],
    [`max_repair_edits`], [4], [4], [Largest repair accepted before the default plan is used.],
    [`plan_dispatch_order_source`], [`chi`], [`chi`], [The grounder's default (cost) order sets the `junction_clear` back-out order.],
  ),
  caption: flex-caption([Grounding settings, shipped and in the five-robot scene overlay.], [Grounding settings in the shipped configuration and in the orchestrator overlay of the five-robot pickup-and-delivery scene. The registered five-robot pilot ran with the plan channel and refusal-as-no-action on and a variant of the derived-mode grounding file; the intersection runs enable the plan channel with the shipped, derived-mode grounding file (Chapter 5). #fig-source("3.17")]),
) <tab:grounding-config>
]

*Feasibility checks.* A yielder must have enough free room behind it, along its corridor side or junction arm up to the nearest static obstacle, to reach a park point from which the passer can get by. A reverse is refused when both robots already sit beyond the corridor on the same side, since it would traverse the corridor instead of opening it. In derived mode, backup and escort distances must fall in configured bands, and each retreat candidate is swept against obstacles and robots. For `junction_clear`, back-out candidates are ranked by a cost function, the grounder's default order (`chi` in the logs); when none survives, a plain yield is grounded #ev("3.18"). *Legacy mode*, used by the convoy scene, clamps distances (from the declared geometry when supplied) and has no bands, ranked candidates or degradation list #ev("3.18")\; the queued-robot hold works only in it #ev("6.19"), and as the convoy scene declares no static obstacles, the gate would change none of its 49 recorded first-trigger yields #ev("6.85").

In the evaluated runtime, static obstacles enter only the yielder's retreat-room check: escort segments are checked against the parked yielder only, and `reverse` legs are not swept against declared boxes. One escort drove into a rack island for this reason (Chapter 6) #ev("6.01"), and in a later validation take a reverse passed 5.5 mm from a declared box #ev("6.17").

*Yield feasibility gate.* When the named yielder cannot reach a park point, the gate in `swap` mode hands the yield to another involved robot that can, ties broken by the decision's robot order; when none can, or in `refuse` mode, the yield is refused, and a swap is recorded with its shortfall #ev("3.18"). The model is trusted to recognise a deadlock and choose yielding, not to judge from an image which robot has room to retreat; geometry decides that.

*Refusal and no action.* Under `refusal_no_action`, which the task-stream scene sets, M5 withholds the bounded wait of a refused yield, and of a yield that degrades to a reroute with no declared detour, and dispatches nothing #ev("3.19"): where other robots keep moving, a wait that cancels Nav2 goals disturbs traffic without resolving anything. The withheld decision is logged with its reason, and the detector can fire again.

*Plan audit.* With the plan channel on, the model may return a `proposed_plan`, an ordered list of legs pairing a robot with `yield`, `reverse`, `cross`, `wait`, `reroute` or `continue`. The plan verifier audits it with the grounder's own checks #ev("3.20"): an omitted robot is completed with `continue`; a plan that names an unknown robot, does not fit the strategy or contradicts the decision's yielder or crossing order is rejected; a consistent feasible plan is accepted unchanged; a consistent plan with infeasible legs is repaired by a breadth-first search for the fewest edits (swap two roles, reorder two legs, or substitute one action with the grounder's own), bounded at four edits. Each plan gets one plan-audit label (provenance in the logs): *accepted unchanged* (`vlm_verbatim`), *repaired* (`repaired`, each edit logged) or *grounder default* (`m3_default`: absent, discarded by the parser, rejected or not repairable) #ev("3.20") #ev("6.02"). The default plan is built from the same functions that construct commands, so for a decision without a plan it is exactly what is dispatched.

*Audit, not dispatch.* The command that reaches M4 is always the grounder's, built after the feasibility gate from the decision's strategy, involved robots, yielder, crossing order and second-stage choice. The audit runs afterwards: it labels the plan, records edits and a `dispatch_matches_plan` flag, sets the legs the plan tracker follows and seeds the `junction_clear` phase queue, but the phases are grounded from the decision fields, not the plan #ev("3.20") #ev("6.02"). The flag is not a strict match: under the order tolerance, a plan whose back-out order differed from the executed one was recorded as matching #ev("6.02"). "Accepted unchanged" therefore means the plan passed the audit, not that it was executed in place of the grounder's. The one exception, a switch that lets a verified plan set the back-out order, is off in the evaluated configuration (@sec:impl-later).

*Degradation tags* on every command name what the grounder changed or refused and why, so each command's history is readable from its decision record.

== Safety Invariants <sec:design-safety>

The safety monitor in M4 is the last line of defence and deliberately the simplest component in the motion path. It reads M1's scene state and the command and status topics, never M2 or M3. When a rule fires it publishes zero velocity at 40 Hz and cancels the robot's Nav2 goal, so the planner cannot drive against the stop #ev("3.04"), and it publishes the held set so that their goals are not re-issued (@tab:safety).

#figure(
  placement: auto,
  table(
    columns: (auto, auto, 1fr),
    align: (left, left, left),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Invariant*], [*Value*], [*Rule*]),
    [Proximity latch], [0.45 m], [A pair closer than this, centre to centre, is held (both robots) until a fresh reading shows it at or beyond the limit.],
    [Speed limit], [0.2 m/s], [A faster robot is held; robots in a clearing primitive are exempt.],
    [STALE fail-safe], [0.6 m], [A robot whose marker is lost keeps any hold, and is held if its last fresh distance to another robot was below this band.],
    [Hard-contact floor], [0.20 m (armed per run; 0, off, in the shipped file)], [Holds a pair below this centre distance (M1 poses), even under a clearing exemption.],
  ),
  caption: flex-caption([Safety invariants enforced by the M4 safety monitor.], [Safety invariants enforced by the M4 safety monitor. The floor is off in the shipped safety file and armed by a per-run configuration swap in the live experiments (Chapter 5). #fig-source("3.22")]),
) <tab:safety>

*Proximity latch.* The proposal's 0.3 m left about 0.5 s of reaction at the worst-case closing speed against a perception-to-monitor latency of 0.2–0.4 s; 0.45 m restores about one second and still fits the narrow-aisle geometry #ev("3.23"). The grounder sizes escort and pass legs with the same radius, so a grounded manoeuvre does not trip the latch.

*STALE fail-safe.* An undetected marker means an unknown pose, which the design treats as unsafe. The robot keeps any hold and is held when its last distance measured while both robots were tracked lies within 0.6 m, the latch plus 0.15 m #ev("3.22"). The remembered distance is used, not the frozen pose M1 republishes, because that pose is what goes wrong while the robot moves; and overlapping markers are undetectable, so without this rule two robots in contact would both turn `STALE` and vanish from the monitor.

*Clearing exemption.* A robot backing out of a nose-to-nose standoff starts inside 0.45 m of its partner, so clearing primitives must work inside the latch distance. The exemption is scoped as follows #ev("3.24"):

- A robot in a clearing primitive is exempt from the latch and STALE pair rules against the partners named in its own command, and from the speed rule.
- During a yield's backup and sidestep, every robot of the command is a partner; from the hold on, only the passers admitted so far.
- Bystanders keep full protection; Nav2 legs and waits exempt nothing; robots held only as a shield from a retreat are not partners.
- A clearing robot already held with a third robot is released one-sidedly: it may leave, the other stays held until the pair separates.

*Hard-contact floor.* Inside one command, nothing in the latch rule stops a clearing robot from pushing its partner. The floor holds any pair below 0.20 m centre distance, exempt or not #ev("3.22"), so it limits damage at or near contact rather than preventing the approach. The value is the 0.18 m footprint contact separation plus about twice M1's median static position error of 0.011 m #ev("3.25"). Centre distance is only a proxy: the distance at which two chassis touch depends on their headings, and nose to nose it is about 0.076 m #ev("6.01").

*Exemption scope, reviewed after the experiments.* A static code review found five paths by which the exemption reaches further than intended or as designed #ev("3.27"): partner lists that cross conflict clusters, because one tick forms one event; partner lists that go stale after publication; a robot whose leg was rejected still counting as a partner; two clearing robots releasing each other one-sidedly; and the intended own-command scope. It attributed no recorded incident to them and noted that the floor was armed in recent live cells #ev("3.27"). The first three were fixed later behind the key `scoped_clearing_exemption`, which changes behaviour only when true #ev("3.28"). The evaluated runtime lacks the fix, so the registered five-robot pilot and intersection run 1 ran with the wider scope; intersection run 2 had the key on, but it never fired, so that run is no live validation #ev("6.06").

*Summary.* The grounder, the monitor and the floor keep safety independent of the model, but all three concern robot pairs or the yielder's retreat room: a grounded motion can still meet a static obstacle, as one escort in the demonstration campaign did #ev("6.01"). Later obstacle guards are listed in @sec:impl-later.
