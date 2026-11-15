#import "../lib.typ": *

= Conclusion and Future Work <sec:concl>

== Conclusion <sec:concl-summary>

This report built a two-layer coordinator in which a stall trigger calls a VLM on the annotated overhead view and a deterministic grounder turns its decision into commands; it runs end to end in Isaac Sim and ran on physical TurtleBot3 robots as a demonstration #ev("1.07"). The live comparisons and the demonstration campaign were registered before their data #ev("1.05") #ev("5.51"). The research questions (@sec:intro-rq) are answered as follows; two further questions from the first registered design were not tested and are future work.

+ *RQ1, classification: answered in part.* In the registered pilot the coordination layer detected 9 of 11 GT conflicts, with no false positive in 26 positive analyses, type accuracy 0.778 and involved-set F1 0.915, on five seed pairs of one scene #ev("6.35") #ev("6.14"). Detection measures the stall trigger and the VLM together; type accuracy is scored against a single accepted label; blocker kind was not evaluated.
+ *RQ2, strategy competence: negative for the model.* The coordination layer cleared the four-robot intersection in 4 of 5 episodes against 0 of 5 with it off, but a scripted default-plan arm with no VLM call did as well (4 of 4 valid, 5 of 5 after a post hoc re-run; live arm 5 of 5), and every live first dispatch re-grounds to that plan; both are exploratory five-episode pilots #ev("6.05") #ev("6.06"). The registered comparator, a per-type policy table, never ran. Elsewhere nothing cleared reliably: the registered five-robot pilot completed no episode (0 of 10) #ev("6.14"); the convoy stayed unresolved in five takes and resolved once only with the grounder's queued-robot hold; the five-robot take did not resolve #ev("6.40") #ev("6.41") #ev("6.84") #ev("6.42").
+ *RQ3, yielder and order: negative at the decision level.* In the two-robot head-on scenes the feasibility gate, not the model, made the executed yielder correct (79 of 79, overturning 37 model picks) #ev("6.08"), and in the offline replays no tested model chose the yielder from the scene #ev("6.09"). The model's crossing order was never executed; its one executed contribution was a back-out order in one demonstration take selected for its label, a near-tie (0.010 m against a 0.15 m tolerance) #ev("6.39").

Safety evidence is robot-pair distance only: one sustained robot-obstacle contact, from an unchecked escort path, is confirmed, October reverses pinned robots on boxes, and of the guards built since, the reverse guard and the stall abort were each validated live once in a scripted safety test, the escort guard offline only #ev("6.42") #ev("6.13") #ev("6.18") #ev("6.86").

The answer to @sec:intro-problem is narrow: the pipeline clears congestion that local control leaves in place in one staged scene, carried by the deterministic layer; whether the model's strategy choice helps where no scripted choice is known was not tested. The results come from simulation, small samples and one VLM in the live comparisons. The lasting contribution is a way to measure the model's share: per-dispatch plan-audit labels, re-grounding without the plan, and a scripted default-plan arm on identical code.

== Future Work <sec:concl-future>

- *Test scene use:* complete the improved-annotation replay and randomise listing order in every live study #ev("6.10") #ev("6.09").
- *Let verified plans act:* a plan grammar the model can meet, plans that set more than the back-out order, `reverse` and `reroute` grounded from the plan, and correct plan feedback, each in a registered comparison with the default plan #ev("6.02") #ev("6.39") #ev("6.51") #ev("6.80").
- *Recover latched clusters, test the convoy yielder correction live, report refusals to the model,* and dispatch the per-cluster format, so far run only as a shadow #ev("6.40") #ev("6.85") #ev("6.15") #ev("6.47").
- *Close the obstacle gaps:* check static obstacles on every straight manoeuvre (back-out, release, backup, pull-off), decide the escort guard's margin rule, test that guard live, repeat the scripted safety tests, and cover the untested stall cases (turns, escorts, latch-held robots) #ev("6.13") #ev("6.17") #ev("6.18") #ev("6.86").
- *Compare live again and more widely:* after the fixes, on the registered seed positions with every mechanism keyed identically in all dispatching arms (exploratory, never pooled with the registered pilot), or run the remaining 15 registered seed pairs as the confirmatory test #ev("6.60") #ev("6.14")\; add a classical coordinator, a second live VLM, and other layouts and robot counts.
- *Make the failure-cause rule decide more units* (12 of 18, 13 of 33 and 2 of 4 undetermined by stratum): record what the reproduce check lacks, anchor the coordination-layer-off clock, and order codes within a class #ev("6.63").
- *Semantic advantage* (moved from the research questions, @sec:intro-rq): whether the VLM uses information no classical baseline has, such as what a blocker is, needs scenes whose correct strategy depends on the blocker's kind, that kind scored against ground truth, and an arm that cannot see it.
- *Closed-loop adaptation* (moved likewise): whether feedback about a failed command changes the next decision needs forced-failure episodes with and without that feedback, once the feedback shown to the model is correct (@sec:disc-limits) #ev("6.80").

The physical demonstration (@sec:impl-physical) showed the chain running end to end; four steps would make it an evaluation:

- *Repeat the physical tests* per arrangement, varying distance, angle, lighting and network load, to estimate a success rate with its uncertainty #ev("4.30").
- *Test mission resumption:* give every robot a goal, and count a recovery only when the robots disperse and continue to it; the demonstration had no goals #ev("4.29").
- *Try the other strategies:* yielding, phased junction clearing, priority-based coordination and re-routing are untested on hardware, which ran only bounded `reverse` #ev("4.38").
- *Strengthen localisation and communication:* fuse overhead ArUco localisation with wheel odometry, and monitor latency, packet loss, reconnection and state delay.
