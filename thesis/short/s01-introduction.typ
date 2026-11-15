#import "../lib.typ": *

= Introduction <sec:s-intro>

== Motivation and Problem <sec:s-intro-problem>

Warehouse robots share narrow aisles and intersections, and when robots meet head-on or several reach a junction together the fleet can stop: each robot holds the floor it stands on while it waits for floor held by another, the classical "deadly embrace" @coffman1971system. Local navigation stacks such as Nav2 @macenski2020marathon plan for one robot at a time; reactive methods decide how to avoid a collision, not who should give way, and two robots running the same recovery policy can recreate the stall they try to escape @trautman2010unfreezing @grover2019deadlock. Remedies in the literature share one structure: a slower layer sets an order or a timing and a faster layer keeps motion safe.

A fixed overhead camera gives such a slow layer a view of the whole situation, and a vision-language model (VLM) can turn that view into a decision: name the kind of jam and choose a way out from a closed vocabulary of strategies, as closely related work does with a top-view image above a safe low-level controller @garg2024foundation @garg2026online. But language models do not plan reliably on their own @valmeekam2023planning, and their output should be treated as a candidate that external checks verify @kambhampati2024llms.

This report therefore studies a two-layer coordinator. *Local navigation* (Layer 1) runs per robot; the *coordination layer* (Layer 2) detects a stall, sends the annotated overhead frame and a text list of robot states to the VLM, which classifies the congestion and chooses one of eight strategies#ev("1.02"), and hands the decision to a deterministic *grounder* that checks it against the scene, repairs or replaces an infeasible plan, and refuses when no safe manoeuvre exists. An independent safety monitor enforces robot-to-robot distance and speed limits. With the *coordination layer off*, only local navigation runs. The robots always execute the grounder's output (one opt-in exception, used only in the demonstration campaign, lets a verified plan set the order of two back-out phases), so claims are made about the pipeline, and the model's share is measured apart.

== Research Questions <sec:s-intro-rq>

- *RQ1, perception and classification.* Does the VLM classify the congestion type and the kind of blocker correctly, and tell congestion apart from normal flow? Because the VLM is called only after the stall trigger fires, RQ1 concerns post-trigger classification and false positives.
- *RQ2, strategy competence.* Do the strategies the VLM chooses clear congestion?
- *RQ3, social reasoning.* Are the robot the VLM names to yield, and the crossing order it proposes, effective?

*Scope change.* The first registered design (tagged 30 September 2026) listed these and two further questions as a skeleton for this report, each with a planned test#ev("1.03"): whether the VLM uses information no classical baseline has, such as what a blocker is, and whether feedback about a failed command changes its next decision. No confirmatory data were collected under that design, and no later design tested the two. They were not tested in this work: no registered or controlled comparison addressed them. Exploratory runs before that design was tagged touched both, with first blocker-kind answers in a funded battery and two gpt-4o recovery runs on a blocked head-on scene#ev("1.16")\; they are not reported as evidence here. Both questions were moved to Future Work (@sec:s-future) when this report was finalised; the narrowing was made after the experiments, is part of no registered design, and changes no result.

RQ2 and RQ3 were not tested against the comparators the first design registered for them (a per-type policy table and a first-come-first-served rule); from the third design on, the control is the coordination layer switched off. RQ3 is informed only at the decision level, and the live comparisons listed robots in ascending order, so they cannot separate an identifier prior from a slot prior#ev("1.12")#ev("1.15").

== Contributions <sec:s-intro-contrib>

+ *A working closed loop in simulation* (detect, decide, ground, act, resolve) in Isaac Sim with ROS 2, Nav2 and a hosted VLM, with one key that switches the coordination layer off on identical code.
+ *A deterministic grounder with per-dispatch plan-audit labels*, and a way to measure the model's share: the label, a re-grounding of each decision without its plan, and a scripted default-plan arm. Verify-and-repair is not new; what the closest published systems do not report, as far as we found, is this per-dispatch measure.
+ *A safety layer that does not depend on the model*: robot pairs closer than 0.45 m are held, with a 0.20 m centre-distance floor in the live experiments#ev("1.04").
+ *Registered designs and an evidence trail*: every scored criterion of the registered studies was fixed before its data, and post hoc analyses are labelled as such#ev("1.05"); and every number in this report is traced to its source in the Evidence Index of the Extended Report.
+ *A physical demonstration* on TurtleBot3 robots, which is not an evaluation#ev("1.07").

== Summary of Findings <sec:s-intro-findings>

At a simulated four-robot intersection the full pipeline cleared the jam in 4 of 5 episodes, against 0 of 5 with the coordination layer off; a scripted default-plan arm with no VLM call did as well, so the clearing is credited to the trigger and the grounder (exploratory pilots, five episodes per arm)#ev("6.05")#ev("6.06"). In a registered five-robot pilot no episode of either arm completed its tasks (0 of 10)#ev("6.14"). In two-robot head-on scenes the grounder's feasibility gate, not the model, made the yielder correct#ev("6.08"). The model's plan changed the dispatched commands in 0 of 39 traced live four-robot analyses#ev("6.02"). An illustrative demonstration campaign shows the pipeline end to end, including its failures#ev("6.01")#ev("6.84"). RQ1 is answered in part; for RQ2 no added value of the model over a scripted strategy was shown; RQ3 is answered negatively (@sec:s-answers).

*Outline.* Chapter 2 places the work, Chapters 3 and 4 describe the system, Chapter 5 the studies, Chapter 6 the results, and Chapter 7 discusses them and concludes. The *Extended Report*, a companion document, holds the full methods and results, the prompts, the physical testbed configuration, further figures and the Evidence Index (@sec:s-sources).
