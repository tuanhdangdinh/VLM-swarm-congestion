#import "../lib.typ": *

= Conclusion and Future Work <sec:concl>

== Conclusion <sec:concl-summary>

This report built and evaluated a two-layer coordinator for a small simulated warehouse fleet, in which a stall trigger calls a VLM on the annotated overhead view and a deterministic grounder turns its decision into commands. It runs end to end in Isaac Sim with ROS 2 and Nav2, can be switched off by one key on identical code, and also ran on physical TurtleBot3 robots as a demonstration #ev("1.07"). The live comparisons and the demonstration campaign were registered before their data, and post hoc analyses are labelled as such #ev("1.05") #ev("5.51").

The three research questions (@sec:intro-rq) are answered as follows; two further questions from the first registered design were not tested and are future work (@sec:intro-rq).

+ *RQ1, classification: answered in part.* In the registered pilot the coordination layer detected 9 of 11 GT conflicts, with no false positive in 26 positive analyses, type accuracy 0.778 and involved-set F1 0.915, on five seed pairs of one scene #ev("6.35") #ev("6.14"). Detection measures the stall trigger and the VLM together, not the VLM alone; type accuracy is scored against a single accepted label; the kind of blocker was not evaluated.
+ *RQ2, strategy competence: negative for the model.* The coordination layer cleared the four-robot intersection in 4 of 5 episodes against 0 of 5 with it off, but a scripted arm running the grounder's default plan with no VLM call did as well (4 of 4 valid, 5 of 5 after a post hoc re-run; live arm 5 of 5), and every live first dispatch re-grounds to that plan; both are exploratory five-episode pilots #ev("6.05") #ev("6.06"). The comparator the first design registered, a per-type policy table, never ran. Elsewhere nothing was cleared reliably: the registered five-robot pilot completed no episode (0 of 10) #ev("6.14"), the convoy stayed unresolved in five takes and resolved once only with the grounder's queued-robot hold, and the five-robot take stayed unresolved #ev("6.41") #ev("6.84") #ev("6.42").
+ *RQ3, yielder and order: negative at the decision level.* In the two-robot head-on scenes the feasibility gate, not the model, made the executed yielder correct (79 of 79, overturning 37 model picks) #ev("6.08"), and in the offline replays no tested model chose the yielder from the scene #ev("6.09"). The model's crossing order was never used in execution; its one executed contribution was a back-out order in one demonstration take, a near-tie (0.010 m against a 0.15 m tolerance) in a take selected for its label #ev("6.39").

Safety evidence is robot-pair distance only: one sustained robot-obstacle contact, from an unchecked escort path, is confirmed, October reverses pinned robots on boxes, and of the guards built since, the reverse guard and the stall abort were each validated live once in a scripted safety test #ev("6.42") #ev("6.13") #ev("6.18") #ev("6.86").

The answer to the problem of @sec:intro-problem is therefore narrow. The pipeline clears congestion that local control leaves in place in one staged scene, and the deterministic layer carries that result; the model supplied a valid strategy and robot set, which matched a scripted arm handed the same strategy in intersection run 2, and whether its choice helps where no scripted choice is known was not tested. These results come from simulation, small samples and one VLM in the live comparisons. The lasting contribution is a way to measure the model's share: plan-audit labels per dispatch, re-grounding without the plan, and a scripted default-plan arm on identical code.

== Future Work <sec:concl-future>

- *Test scene use:* complete the improved-annotation replay and randomise the listing order in every live study #ev("6.10") #ev("6.09").
- *Let verified plans act:* a plan grammar the model can meet, verified plans that set more than the back-out order, `reverse` and `reroute` grounded from the plan, and correct plan feedback in later prompts, each with a registered comparison against the default plan #ev("6.02") #ev("6.39") #ev("6.51") #ev("6.80").
- *Recover latched clusters, test the convoy yielder correction live, and report refusals to the model;* the per-cluster format has so far only run as a shadow #ev("6.40") #ev("6.85") #ev("6.15") #ev("6.47").
- *Check static obstacles on every straight manoeuvre,* including back-out, release, backup and pull-off legs, and decide the escort guard's margin rule #ev("6.13").
- *Validate the safeguards further:* repeat the scripted safety tests, test the escort guard live, and cover the stall cases not yet exercised (turns, escorts, latch-held robots) #ev("6.17") #ev("6.18") #ev("6.86").
- *Run a live comparison after the fixes* on the registered seed positions, with every mechanism keyed identically in all dispatching arms, as an exploratory run never pooled with the registered pilot; or run the remaining 15 registered seed pairs as the confirmatory test #ev("6.60") #ev("6.14").
- *Make the failure-cause rule decide more units* (12 of 18, 13 of 33 and 2 of 4 undetermined by stratum): record what the reproduce check lacks, add a clock anchor for the coordination-layer-off arm, and order codes within a class #ev("6.63").
- *Widen the comparison:* a classical coordinator, a second VLM live, and other layouts and robot counts.
- *Semantic advantage* (moved from the research questions, @sec:intro-rq): whether the VLM uses information no classical baseline has, such as what a blocker is, needs scenes whose correct strategy depends on the blocker's kind, the blocker kind scored against ground truth, and an arm that cannot see it; the improved-annotation replay is the nearest lead #ev("6.10").
- *Closed-loop adaptation* (moved likewise): whether feedback about a failed command changes the next decision needs forced-failure episodes comparing re-analysis with and without that feedback, once the feedback shown to the model is correct (@sec:disc-limits) #ev("6.80").

On the physical robots (@sec:impl-physical), the demonstration showed the chain running end to end, not an evaluation. Four steps would turn it into one:

- *Repeat the physical tests:* run each arrangement many times, varying starting distance and angle, lighting and network load, so that a success rate can be estimated with its uncertainty #ev("4.30").
- *Test mission resumption:* give every robot a destination before the conflict forms, and count a recovery as a success only when the robots disperse and continue to their goals; in the demonstration the robots had no goals #ev("4.29").
- *Try the other recovery strategies:* the hardware runs used only bounded `reverse` manoeuvres; yielding, phased junction clearing, priority-based coordination and re-routing remain untested on hardware #ev("4.38").
- *Strengthen localisation and communication:* fuse the overhead ArUco localisation with wheel odometry, and monitor network latency, packet loss, reconnection and state delay.
