#import "../lib.typ": *

= Conclusion and Future Work <sec:concl>

== Conclusion <sec:concl-summary>

This report built and evaluated a two-layer coordinator for a small simulated warehouse fleet: local navigation on every robot, and a coordination layer in which a stall trigger calls a VLM on the annotated overhead view and a deterministic grounder turns its decision into commands. The pipeline runs end to end in Isaac Sim with ROS 2 and Nav2, can be switched off by one key on identical code, and also ran on physical TurtleBot3 robots as a demonstration #ev("1.07"). The grounder checks each decision against the scene, hands a yield to a robot with room or refuses, and labels every dispatch; an independent monitor holds robot pairs apart but does not check static obstacles #ev("1.04"). Live studies were registered before their data and post hoc analyses are labelled as such #ev("1.05") #ev("5.51").

At the four-robot intersection the coordination layer cleared a jam that local navigation never cleared (4 of 5 against 0 of 5), and a scripted arm running the grounder's default plan without a VLM call matched the live-VLM arm; both are exploratory pilots, five episodes per arm, never pooled #ev("6.05") #ev("6.06"). The model returned a valid decision in all 67 campaign analyses, but its plan was accepted unchanged in 6 of 65 as recorded (5 dispatched as written after offline correction) and changed execution once, by reordering two near-equivalent back-outs in a take selected for its label #ev("6.44") #ev("6.51") #ev("6.39"). In the head-on scenes the feasibility gate, not the model, made the yielder correct #ev("6.08"), and no tested model met the pre-registered scene-use rule #ev("6.09"). Beyond the intersection, the registered five-robot pilot completed no episode in either arm, and the convoy and five-robot demonstration takes stayed unresolved #ev("6.14") #ev("6.41") #ev("6.42"). Safety evidence is robot-pair distance only, and one sustained robot-obstacle contact, from an unchecked escort path, is confirmed #ev("6.42").

The answer to the problem of @sec:intro-problem is therefore narrow. The pipeline clears congestion that local control leaves in place in one staged scene, and the deterministic layer carries that result; the model supplied a valid strategy and robot set, whose value over a scripted choice was not tested. These results come from simulation, small samples and one VLM in the live comparisons. The lasting contribution is a way to measure the model's share: plan-audit labels per dispatch, re-grounding without the plan, and a scripted default-plan arm on identical code.

== Future Work <sec:concl-future>

- *Test scene use:* complete the improved-annotation replay and randomise the listing order in every live study #ev("6.10") #ev("6.09").
- *Let verified plans act:* a plan grammar the model can meet, verified plans that set more than the back-out order, `reverse` and `reroute` grounded from the plan, and correct plan feedback in later prompts, each with a registered comparison against the default plan #ev("6.02") #ev("6.39") #ev("6.51") #ev("6.80").
- *Recover latched clusters and report refusals to the model;* the per-cluster format has so far only run as a shadow #ev("6.40") #ev("6.15") #ev("6.47").
- *Check static obstacles on every straight manoeuvre,* including back-out, release, backup and pull-off legs, and decide the escort guard's margin rule #ev("6.13").
- *Validate the safeguards live* with a deterministic test (an authored box behind a robot told to back out), which also gives the contact logger its positive control #ev("6.17") #ev("6.18").
- *Run a live comparison after the fixes* on the registered seed positions, with every mechanism keyed identically in all dispatching arms, as an exploratory run never pooled with the registered pilot; or run the remaining 15 registered seed pairs as the confirmatory test #ev("6.60") #ev("6.14").
- *Make the failure-cause rule decide more units* (27 of 55 undetermined): record what the reproduce check lacks, add a clock anchor for the coordination-layer-off arm, and order codes within a class #ev("6.63").
- *Widen the comparison:* a classical coordinator, a second VLM live, and other layouts and robot counts; RQ4 and RQ5 need their own experiments.

On the physical robots (@sec:impl-physical), the demonstration showed the chain running end to end, not an evaluation. Four steps would turn it into one:

- *Repeat the physical tests:* run each arrangement many times, varying starting distance and angle, lighting and network load, so that a success rate can be estimated with its uncertainty #ev("4.30").
- *Test mission resumption:* give every robot a destination before the conflict forms, and count a recovery as a success only when the robots disperse and continue to their goals; in the demonstration the robots had no goals #ev("4.29").
- *Try the other recovery strategies:* the hardware runs used only bounded `reverse` manoeuvres; yielding, phased junction clearing, priority-based coordination and re-routing remain untested on hardware #ev("4.38").
- *Strengthen localisation and communication:* fuse the overhead ArUco localisation with wheel odometry, and monitor network latency, packet loss, reconnection and state delay.
