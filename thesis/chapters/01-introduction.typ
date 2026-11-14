#import "../lib.typ": *

= Introduction <sec:intro>

== Motivation <sec:intro-motivation>

*Warehouse fleets jam.* Automated warehouses move goods with fleets of mobile robots that share narrow aisles, intersections and pick stations. Such fleets trace back to the Kiva system #todo[cite: Wurman 2008 Kiva warehouse coordination]. The planning literature treats the warehouse as a stream of path finding problems, in which robots receive new goals as soon as they finish old ones, and even there congestion is a first-order concern: planners that route each robot along its free-flow shortest path create congestion themselves @chen2023traffic, and a solver that plans over a bounded horizon can leave two agents in a corridor waiting for each other @li2020lifelong. When robots meet head-on in an aisle, or several arrive at a junction together, the fleet can stop moving altogether. A deadlock of this kind does not dissolve on its own: each robot holds the floor it stands on while it waits for floor held by another, which is the structure of the classical "deadly embrace" @coffman1971system.

*Local reactive control cannot break the symmetry.* In practice, many robots navigate with a local stack such as Nav2 @macenski2020marathon, which plans for one robot at a time and treats other robots as obstacles. Reactive methods of this kind keep each robot safe, but they decide how to avoid a collision, not who should give way. A planner can conclude that every path forward is unsafe and stop, although a feasible path exists @trautman2010unfreezing. For controllers built on control barrier functions, deadlock has been characterised as an equilibrium of the closed-loop dynamics on the boundary of the safe set @grover2019deadlock: the robots stop precisely because continuing would violate safety. Two robots that face each other and run the same recovery policy can recreate the stall they are trying to escape (@sec:bg-reactive).

*A slow semantic layer could supply what is missing.* The remedies proposed for reactive deadlock share one structure. A slower decision layer sets an order or a timing, and a faster layer keeps the motion safe (@sec:bg-reactive). What such a layer needs is a view of the whole situation: where the robots stand, which of them blocks which, and what else occupies the aisle. A fixed overhead camera sees exactly that. Vision-language models (VLMs), which read an image together with a text description and answer in a structured form, are candidates for turning that view into a decision. They can name the kind of jam and choose a way out from a closed vocabulary of strategies, such as letting one robot yield or clearing a junction in phases. A closely related line of work already calls a VLM on a stall, shows it a top-view image, and uses it as a high-level planner above a safe low-level controller @garg2024foundation @garg2026online.

*A model's plan cannot be trusted as it stands.* Language models do not plan reliably on their own @valmeekam2023planning. The position that has emerged is to treat their output as a candidate that external, model-based checks must verify @kambhampati2024llms. A VLM is also slow, costly per call and fallible: it may time out, refuse, return malformed output, or pick a robot to yield that has no room to back up. The design question is therefore not only whether a VLM can recognise a jam, but how its decision can be turned into commands that are safe to execute, and how much of the executed plan can still be credited to the model. These two questions run through the whole thesis.

== Problem Statement <sec:intro-problem>

This thesis studies a hybrid, two-layer coordinator for a warehouse robot fleet. Layer 1 is fast and local: each robot navigates with its own Nav2 stack, with a design target of 20–50 Hz #ev("1.01"). Layer 2 is slow and central, with a design target of 0.5–2 Hz #ev("1.01"). When a stall detector reports that robots have stopped making progress, an orchestrator sends the annotated overhead frame and the tracked robot states to a VLM. The VLM classifies the congestion and chooses a strategy from a closed set of eight #ev("1.02"). A deterministic grounding layer turns that decision into robot commands, and an independent safety monitor enforces distance and speed limits whatever the reasoning layer decides (@sec:design).

The project proposal named the grounding layer "RAG action grounding" and planned to retrieve action templates from a knowledge base. In the evaluated system the layer does no retrieval. It is a deterministic, geometry-driven grounder that checks the model's decision against the scene, repairs or replaces an infeasible plan, and refuses to move robots when no safe manoeuvre exists (@sec:design-grounding). The historical name is kept for continuity. One property of this design shapes every claim in the thesis: the command the robots execute is always the grounder's output. The grounder also audits any scene-wide plan the model proposes and labels it as matched verbatim, repaired, or replaced by the grounder's own default plan (its provenance label). These labels record how far the executed command agrees with the model's proposal. They do not mean that the model's plan was dispatched in place of the grounder's.

The problem addressed is therefore the following. _Can a pipeline in which a VLM detects and classifies congestion from an overhead view, and a deterministic layer grounds its decision into safe commands, clear congestion that local reactive control leaves in place, and what does each part of the pipeline contribute?_ The question is posed for a small simulated warehouse fleet and answered with preregistered experiments. Any success is credited to the pipeline (VLM and grounding together), not to the model alone.

The project proposal framed a broader comparison against classical geometric coordinators. The study narrowed as the work progressed: the final experiments compare the pipeline with Layer 2 switched off on the same code, and with the grounder alone. @sec:intro-scope and Chapter 5 give the reasons.

== Research Questions <sec:intro-rq>

The research design frozen with the first preregistration states five research questions #ev("1.03"). They are defined in @sec:ch5-rq and repeated here in short form.

- *RQ1, perception and classification.* Does the VLM classify the congestion type and the kind of blocker correctly from the annotated scene, and does it tell congestion apart from normal flow? Because the VLM is called only after the stall trigger fires, RQ1 concerns post-trigger classification and false positives, not open-world detection.
- *RQ2, strategy competence.* Do the strategies the VLM chooses clear congestion?
- *RQ3, social reasoning.* Are the robot the VLM names to yield, and the crossing order it proposes, effective?
- *RQ4, semantic advantage.* Does the VLM use information that no classical baseline has, such as what a blocker is?
- *RQ5, closed-loop adaptation.* Does feedback about a failed command change the VLM's next decision? (Here "closed loop" means re-analysis that receives feedback about the failed command, not the pipeline cycle defined in @sec:intro-contributions.)

These questions frame the thesis. The experiments that were finally run answer narrower questions, which Chapter 5 states with each experiment (@sec:ch5-arms). The three live comparisons and the offline bench are kept strictly apart and never pooled.

- *prereg-v3, tranche 1 (pilot).* In a five-robot task-stream scene #ev("1.14"), how large is the effect of switching Layer 2 on, against switching it off, on task completion, throughput, delay and per-conflict decision quality, and how uncertain is that estimate? No directional hypothesis was registered. Tranche 1 ran 5 seeds per arm, 10 episodes in all, against a registered 20 per arm #ev("1.08"); because tranche 2 was not run, it is reported as a *pilot*.
- *IB10, Layer 2 on against off (exploratory).* In a four-robot intersection, does the full Layer 2 pipeline physically clear a jam that stays frozen when Layer 2 is off? It ran 5 episodes per arm #ev("1.09").
- *IB10, grounder default (exploratory).* In a second, separate run on the same intersection, does the jam clear in the same way when no VLM is called and the plan is the grounder's default? That arm had 5 slots #ev("1.10").
- *Offline bench and live shadow (exploratory).* How do prompt and input variants for the VLM rank on recorded scenes, judged by what the real grounder would do with their answers? A later per-cluster variant also ran as a decision-only live shadow in 7 episodes #ev("1.11").

@tab:intro-rq-map maps each of these to the registered questions it informs.

#figure(
  table(
    columns: (1fr, 0.9fr, 1.5fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Experiment*], [*Informs*], [*Comparator actually used*]),
    [prereg-v3 tranche 1 (pilot)], [RQ2; RQ1 in part], [Layer 2 off. Decision measures (detection, type label, involved-robot F1) exist only for Arm A, which calls the model.],
    [IB10, Layer 2 on against off], [RQ2], [Layer 2 off; the jam is expected to stay frozen. Not a per-type policy table.],
    [IB10, grounder default], [Share of RQ2 credited to the grounder], [The same pipeline with no VLM call, handed the strategy and robot set.],
    [Offline bench], [RQ1 and RQ3, decision level only], [A default-ordered first-option chooser and the classical chooser; text only, nothing is executed.],
  ),
  caption: [Which registered research questions each experiment informs, and against what.],
) <tab:intro-rq-map>

The experiments therefore do not test every registered question. RQ4 and RQ5 are not tested by any experiment reported here. RQ2 and RQ3 are not tested against the comparators registered for them at prereg-v1 (a per-type policy table, and a first-come-first-served rule with a commitment tiebreak), because from prereg-v3 the control is Layer 2 switched off. RQ3 is informed only at the decision level, by the bench and by the presentation-order finding from the pilots (@sec:intro-contributions). Because the grounder may repair or replace the model's plan, every live outcome is reported together with the plan-provenance label of its dispatches, so that the model's share in each executed plan is visible.

== Contributions <sec:intro-contributions>

The contributions are of two kinds. The system and method contributions are artefacts that exist and have been run, and they are stated plainly. The empirical findings come from pilots and offline analysis, and each is stated with the kind of evidence behind it. Outcomes of the main experiments are reported in Chapter 6.

*System and method contributions.*

+ *A working closed loop in simulation.* Here and below, "closed loop" means the full cycle of detect, decide, ground, act and resolve, run in simulation. The coordinator runs end to end in Isaac Sim with ROS 2, Nav2 and a hosted VLM. An overhead camera with ArUco tracking produces robot states, a stall detector decides when to ask, the VLM decides, the grounder produces commands, and an execution layer carries them out and reports back (Chapters 3 and 4). Layer 2 can be switched off by one configuration key, which gives every experiment a Layer-1-only control on identical code (@sec:design-modules).
+ *A deterministic grounding layer with plan provenance.* The grounder checks each decision against the scene geometry and the robot positions. It hands a yield to another robot when the named yielder has no room to back up, refuses when no robot has, and audits the model's proposed plan with a bounded repair search. Every dispatch carries a provenance label and degradation tags, so the division of credit between model and grounder can be read from the record of each decision (@sec:design-grounding). As far as we found, none of the closest published systems reports this division (@sec:bg-comparison).
+ *A safety layer that does not depend on the model.* In the evaluated system, the model's choice passes through the same safety checks as any other command, except for the clearing-manoeuvre exemption, whose scope proved wider than intended (@sec:design-safety). An independent monitor holds any pair of robots closer than 0.45 m and any robot faster than its speed limit, and treats a robot whose marker is lost as unsafe. In the live experiments it adds a hard-contact floor at 0.20 m that applies even inside the exemption that clearing manoeuvres need #ev("1.04"). The floor is armed per run and checked by the run procedure around every run (@sec:design-safety). That wider scope was found by a review after the experiments, and the evaluated runtime does not contain the fix.
+ *Preregistration discipline.* The experimental design was registered in three versions, the first frozen with a repository tag on 2026-09-30 and the third dated 2026-10-06 #ev("1.05"). Later changes were made as numbered, append-only addenda. Every scored criterion was fixed before the data it scores were collected, and pilot episodes were excluded from confirmatory counts (@sec:ch5-prereg).
+ *An offline replay bench.* The bench replays 187 recorded analyses from 31 live episodes #ev("1.06"), re-grounds each answer with the production grounder, and scores it against ground-truth conflict definitions. It ranks prompt and input variants for the VLM by what would happen downstream, without simulating any episode (@sec:ch5-bench).
+ *A physical demonstration.* The detect-to-dispatch chain also runs on real robots. On 12 November 2026, the perception, reasoning, grounding and dispatch chain ran on physical TurtleBot3 robots under an overhead camera, in four staged arrangements of up to four robots #ev("1.07"). The demonstration used a different reasoning model from the simulation experiments, the robots had no navigation goals, one run per arrangement was recorded, and its code is not part of this repository's history (@sec:impl-physical). It shows that the chain runs on real hardware; it is not an evaluation.

*Evaluations performed.* The thesis carries out the three live comparisons and the offline bench listed in @sec:intro-rq, each with its registered measures, safety gates and plan-provenance labels. Their outcomes are reported in Chapter 6. \
#todo[Held: one sentence per evaluation once released: tranche-1 pilot outcome (worded as a pilot); IB10 Arm A vs Arm B outcome with plan-provenance labels (claim "the pipeline (VLM + grounding) clears the jam" only if Chapter 6 supports it); grounder-default arm outcome and what it implies for the VLM's share; bench and Stage 1 shadow findings.]

*Empirical findings from pilots and offline analysis.*

- *Presentation order.* In pilot probes, the robot that one model named to yield followed the robot listed first in the prompt rather than the geometry of the scene. The finding changed the registered design: from the first preregistration on, the order in which robots are listed is drawn at random, seeded and recorded, and analyses condition on it #ev("1.12").
- *The grounder carries the plan.* In the earlier live pilot on the intersection scene, every plan the model proposed was repaired or replaced by the grounder #ev("1.13"). This observation is why the claims of this thesis are worded about the pipeline, and why every outcome is reported with its plan-provenance label.
- *Grounding as the limiting stage.* The thesis examines whether grounding, rather than detection, limits the pipeline, using decision-only re-grounding of recorded live analyses and the offline bench. \
  #todo[Held: grounding-versus-detection finding, stated with its evidence type (decision-only re-grounding; offline bench) once Chapters 6 and 7 are released.]

== Scope and Non-Goals <sec:intro-scope>

The thesis is bounded in the following ways.

- *One overhead camera, planar poses.* The system uses a single fixed overhead camera and estimates positions and headings on the ground plane only. Multi-camera fusion and full six-degree-of-freedom pose estimation are out of scope.
- *Conflict clearing, not global planning.* The coordinator does not replan the fleet as a multi-agent path finding solver would @stern2019multi. It handles one detected conflict at a time with a small set of bounded manoeuvres and then hands control back to the robots' own planners. Layer 2 is not in the fast (20–50 Hz) control loop #ev("1.01"); it acts only on detected stalls.
- *No retrieval.* Despite the module's historical name, the evaluated grounder does no retrieval and calls no second model; the retrieval modules in the source tree are unimplemented stubs (@sec:design-modules).
- *No classical coordinator as control.* The proposal planned comparisons with potential fields, reciprocal collision avoidance and conflict-based search. The final experiments do not include them. Their control is Layer 2 switched off on the same code, so they measure pipeline on against pipeline off, not a VLM against a classical coordinator (@sec:ch5-threats). The measures registered for the final design (@sec:ch5-measures) do not include energy use, which the proposal had listed.
- *Simulation for every scored episode.* All scored episodes ran in Isaac Sim, each experiment in one scene, with one model in the live comparisons and one pinned runtime. The physical demonstration is not part of the experiments.
- *Small samples and exploratory status.* The live comparisons have five episodes or seed pairs per arm #ev("1.08") #ev("1.09"). Only prereg-v3 was registered as confirmatory, and its single tranche is reported as a pilot. The IB10 runs, the bench and the shadow run are exploratory. No result is generalised beyond its scene, model and runtime.
- *Later extensions are not evaluated.* Variants built after the pinned runtime (grounding-first prompts, per-cluster choice, refusal feedback and the fix to the safety exemption) are switched off by default and appear only as exploratory work (@sec:impl-later).
- *Safety is bounded.* The safety gates bound contact in the episodes reported, and no more. The 0.20 m floor limits a push at or near contact rather than preventing the approach #ev("1.04"), and passing the gates is not a general safety claim.

== Thesis Outline <sec:intro-outline>

*Chapter 2* reviews multi-agent path finding and congestion-aware planning, reactive collision avoidance and Nav2, taxonomies and resolution strategies for deadlock, language and vision-language models as robot planners, and the methods that ground or check their plans. Each section ends with the gap it leaves. A comparison table then sets the closest systems against this thesis along five axes (@sec:bg-comparison), and the chapter closes with the combined research gap (@sec:bg-gap).

*Chapter 3* presents the system design: the two-layer architecture, the six modules and their contracts, the detect–decide–ground–act–resolve pipeline, the strategy vocabulary, the deterministic grounding layer and the safety invariants (@sec:design).

*Chapter 4* describes the implementation on the pinned runtime: the software stack, each module as built, the VLM backends and the prompt, the engineering lessons that shaped the simulation platform, testing and reproducibility, the physical TurtleBot3 demonstration, and the later extensions that are not evaluated (@sec:impl).

*Chapter 5* sets out the experimental methodology: the research questions, the history of the preregistration from v1 to v3, the two simulated scenes, the arms, the registered measures, the run procedure and safety gates, the analysis plan, the offline bench, and the threats to validity known in advance (@sec:ch5-rq).

*Chapter 6* is planned to report the results: the IB10 comparisons, the prereg-v3 tranche-1 pilot, the exploratory findings (presentation order, model refusals, the offline bench) and the physical demonstration. \
  #todo[Held: Chapter 6 stays a skeleton until the owner releases the results.]

*Chapter 7* is planned to discuss what the evidence supports, whether grounding rather than detection is the bottleneck, the limitations and the threats to validity. \
  #todo[Held.]

*Chapter 8* is planned to conclude the thesis and outline future work. \
  #todo[Held.]

An appendix, the Evidence Index, maps every number in the text to the file or commit that supports it.
