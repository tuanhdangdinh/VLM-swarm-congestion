#import "../lib.typ": *
#import "../figures/architecture.typ": architecture-figure
#import "../figures/pipeline.typ": pipeline-figure

= System Design <sec:s-design>

== Two Layers and Six Modules <sec:s-design-layers>

The architecture separates a fast, distributed layer from a slow, centralised one (@fig:s-architecture), with design targets of 20–50 Hz for local navigation and 0.5–2 Hz for the coordination layer #ev("3.01"). Six modules with separate owners make up the system: perception (M1) turns overhead ArUco detections into robot states and an annotated frame; VLM reasoning (M2) builds the prompt, calls the model and validates its answer; the grounder (M3) turns the decision into commands; execution and safety (M4) dispatches primitives and enforces the safety rules; the orchestrator (M5) owns the task registry and the decision pipeline; simulation (M6) provides the robots and the camera.

#figure(
  architecture-figure(),
  caption: flex-caption([Two-layer architecture.], [Two-layer architecture. The coordination layer (orange) observes the scene through perception (M1) and decides through the orchestrator (M5), VLM reasoning (M2) and the grounder (M3). Local navigation (grey) executes through the execution and safety monitor (M4) and the per-robot Nav2 stacks. Simulation (M6) provides the robots and the camera. Arrow labels are ROS 2 topic names. #fig-source("3.02")]),
) <fig:s-architecture>

== Decision Pipeline <sec:s-design-pipeline>

@fig:s-pipeline shows the path from a stall to its resolution. *Detect:* a robot with a goal is stalled when its best distance to the goal has not improved by more than 0.10 m for 12 s of wall-clock time #ev("3.12"). *Decide:* M2 sends the annotated frame and the robot states to the VLM and validates its `CongestionDecision`: a congestion type, the involved robots, one of eight strategies (for example `yield`, `reverse`, `reroute` or `junction_clear`), optionally a yielder, a crossing order and a scene-wide `proposed_plan`. @tab:s-strategies lists how each strategy reaches the robots. *Ground*, *act* and *resolve* follow below; a refusal dispatches nothing and returns control to monitoring.

#figure(
  pipeline-figure(),
  caption: flex-caption([Decision pipeline.], [Decision pipeline. The main path runs left to right; orange elements are the deterministic checks that can change or stop a decision before or during execution. A refusal dispatches nothing and returns control to monitoring. #fig-source("3.11")]),
) <fig:s-pipeline>

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
) <tab:s-strategies>

== Grounding <sec:s-design-grounding>

The grounder trusts the model to recognise a jam and choose a strategy, not to judge from an image which robot has room to move; geometry decides that. A yielder must have enough free room behind it to reach a park point from which the passer can get by. When it has none, the *yield feasibility gate* in `swap` mode hands the yield to another involved robot that can, and refuses when none can #ev("3.18"). For `junction_clear`, back-out candidates are ranked by a cost function, the grounder's default order. In the evaluated runtime, static obstacles enter only the yielder's retreat-room check: escort segments are checked against the parked yielder only, and `reverse` legs are not swept against declared boxes #ev("6.01") #ev("6.17").

*Plan audit, not dispatch.* With the plan channel on, the model may return a `proposed_plan`. The verifier audits it with the grounder's own checks and labels it *accepted unchanged*, *repaired* (a bounded search of at most four edits) or replaced by the *grounder default* #ev("3.20"). The command that reaches M4 is always the grounder's, built from the decision's strategy, involved robots, yielder and crossing order; the audit runs afterwards, and the `junction_clear` phases are grounded from the decision fields, not from the plan #ev("3.20") #ev("6.02"). "Accepted unchanged" therefore means the plan passed the audit, not that it was executed; for `reverse` and `reroute` the grounder never reads the plan at all (@sec:s-res-plan).

== Safety <sec:s-design-safety>

The safety monitor in M4 reads only perception and the command topics, never the model. It holds any robot pair closer than 0.45 m centre to centre, any robot above 0.2 m/s outside a clearing primitive, and any robot whose lost marker leaves it within 0.6 m of another; clearing primitives are exempt from the pair rules against their own command partners, because a robot backing out of a standoff starts inside the latch distance. The live experiments arm a hard-contact floor that holds any pair below 0.20 m centre distance even under the exemption #ev("3.22") #ev("1.04"). Centre distance is a proxy for contact; nose to nose two chassis touch at about 0.076 m #ev("3.25"). @tab:s-safety lists the invariants. The monitor has no obstacle check. A review after the experiments found the exemption reaching further than intended; a fix exists behind a key that the evaluated runtime lacks #ev("6.07"). Obstacle guards and a stall abort were built later and are off by default (@sec:s-impl).

#figure(
  placement: auto,
  table(
    columns: (auto, 1fr, 2fr),
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
) <tab:s-safety>
