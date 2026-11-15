#import "../lib.typ": *

= Discussion <sec:disc>

This chapter argues what the results of Chapter 6 support, where the model's proposals stop on their way to the robots, and what bounds every claim. The evidence grades of @tab:ch5-studies stay apart throughout.

== What the Evidence Supports <sec:disc-supports>

The claims form a ladder of six rungs: five that the evidence supports (a to d, and f) and one list of unsupported claims (e) #ev("6.16").

*a. The pipeline clears the intersection jam* (@sec:res-ib10-ab, @sec:res-ib10-c). The coordination layer (trigger, grounding and phased dispatch) cleared the four-robot intersection in 4 of 5 episodes against 0 of 5 with the layer off, where the robots never moved again once jammed #ev("6.05") #ev("6.30"). In intersection run 2 the live-VLM arm and the scripted default-plan arm resolved every valid episode in similar time, and every live-VLM first dispatch re-grounds to the scripted plan #ev("6.06"). This is a claim about the pipeline: the grounder's default plan clears this jam without the model's plan, and the model's remaining role is the strategy and robot set, which the scripted arm was handed. Both runs are exploratory pilots of five near-repeat episodes per arm on one scene.

*b. The model returns valid decisions* (@sec:res-demo, @sec:res-exploratory). ER-2 answered validly in all 69 campaign analyses #ev("6.84"), but valid is not usable (plans nulled for invalid structure in two intersection takes #ev("6.39")), and validity is model- and prompt-specific: Sonnet 5.5 refused 30 of 48 real-frame runs under the original ending and none under a JSON-only ending #ev("6.09") #ev("6.11"), and gpt-4o's refusals were triggered by the real camera frame #ev("4.37").

*c. In the two-robot head-on scenes, the gate, not the model, secures a feasible yielder* (@sec:res-headon). The model's yielder never beat the better trivial baseline; the feasibility gate made the grounded yielder correct in 79 of 79 runs, overturning 37 picks #ev("6.08"), and did the same once in the campaign's head-on take #ev("6.37").

*d. A plan is rarely accepted and executed, with small effect* (@sec:res-plan, @sec:res-demo-ib). Before the campaign the plan changed dispatch in 0 of 39 gated live analyses #ev("6.02"). In the campaign's first twelve takes, 6 of 65 plans were accepted unchanged as recorded, 5 dispatched as written by the offline recomputation #ev("6.44") #ev("6.51"), and at the intersection, the only scene where it was computed, a plan changed execution once: the order of two back-outs whose costs differ by 0.010 m against a 0.15 m tolerance, chosen from actions the prompt offered, in a take selected for its label #ev("6.39") #ev("6.03").

*e. Unsupported.* That the model's decision improves outcomes: the two arms of intersection run 2 are indistinguishable, and where the model's decision fields changed execution, neither judgeable episode resolved #ev("6.06") #ev("6.02"). That the model uses the scene: no model met the pre-registered scene-use rule, and the one lead is not assessable #ev("6.09") #ev("6.11") #ev("6.10"). That the pipeline handles congestion beyond the intersection: five of six convoy takes (the sixth resolved by the grounder's hold) and the five-robot take ended unresolved #ev("6.40") #ev("6.41") #ev("6.42") #ev("6.84"), and in the registered five-robot pilot no episode of either arm completed, with a throughput interval including zero #ev("6.14").

*f. Safety evidence is narrow* (@sec:res-safety). It is robot-pair centre distance only; the contact lists were a stub #ev("6.20"), and one sustained robot-obstacle contact is confirmed, where an escort drove `robot_3` into rack island `obstacle_2` #ev("6.42").

=== Answers to the Research Questions <sec:disc-rq>

Following @tab:intro-rq-map, and no broader than the rungs:

- *RQ1, perception and classification:* answered in part, at pilot scale. In the registered pilot the coordination layer detected 9 of 11 GT conflicts, with no false positive in 26 positive analyses, type accuracy 0.778 and involved-set F1 0.915 #ev("6.35") #ev("6.14"), on five seeds of one scene.
- *RQ2, strategy competence:* answered for the pipeline, not the model (rungs a, d, e).
- *RQ3, social reasoning:* informed only at decision level; the gate made the yielder correct, the model's choice followed labels or listing order where testable, and its one executed back-out order was a near-tie (rungs c to e).
- *RQ4, semantic advantage,* and *RQ5, closed-loop adaptation:* not tested.

== Where Proposals Stop: Grounding Refusals and Plan Use <sec:disc-grounding>

After detection, a proposal can stop in two places: grounding refuses it, or grounding dispatches a command that owes nothing to the plan. Chapter 6 shows both often.

*Refusals.* Re-grounding the recorded live five-robot analyses, 78 analyses gave 13 motion commands; grounder refusals withheld 47, 27 of them at the static gate of `junction_clear`, and 32 of the 47 re-asked an already refused scene; the model is not told of a refusal #ev("6.15"). The registered pilot withheld analyses in every seed #ev("6.14"), the live per-group shadow run's ordinary loop withheld 33 #ev("6.47"), the five-robot take withheld six of eight decisions #ev("6.42"), and in convoy takes 1 to 3 every proposal after the latch ran as a wait #ev("6.40"). The offline benchmark points the same way: its coverage gain belongs to the format and the grounder's option order, not the model #ev("6.46").

*Plan use.* In the evaluated runtime the grounder grounds from the decision fields and audits the plan afterwards, so the plan changed dispatch in 0 of 39 gated analyses #ev("6.02")\; with the plan-order switch on, it changed the timing of two back-outs once #ev("6.39"). The decision fields did change execution, in 18 dispatches in four episodes, without a judgeable success #ev("6.49") #ev("6.02").

*Plan versus dispatch.* The plan-audit label over-states agreement. For `reverse` and `reroute` the grounder acts on the involved-robots list, and the verifier constrains no `reverse` plan, so a plan accepted unchanged can coexist with a contradicting dispatch. In the campaign and October decisions recomputed (the convoy takes with the queued-robot hold excluded), 10 of 33 dispatched `reverse` legs went to robots whose plan said something else, and 3 of 3 reroutes rerouted a different robot than the plan named; of 15 accepted-unchanged decisions with a differing dispatch outside `junction_clear`, 9 are true overrides (5 `reverse`, 3 `reroute`, one convoy yield) and 6 a registered retreat-shield artefact #ev("6.51") #ev("6.80"). These are decision-level counts over recorded decisions from two series, describing a mechanism, not a rate or a comparison between series #ev("6.51"). The corrected counts (campaign 6 to 5, registered pilot 2 to 1) sit beside the recorded labels #ev("6.51"). A visibility fix, off by default, has not run live, and the plan state shown back to the model in later prompts stays wrong in these cases (for example "wait (done)" for a robot that backed out), because correcting it would change the prompt #ev("6.80").

*Execution paths.* Not every stop is a refusal: the five-robot escort into the rack island was a path no stage checked #ev("6.42") #ev("6.43"), and in convoy takes 4 and 5 the queued-robot hold worked but the model again chose the yielder the scene defeats #ev("6.41").

*What this does not show.* These results say where proposals stopped, not which stage caused the unfinished episodes. The failure-cause classification (@sec:res-failure-causes) names no dominant cause and leaves 27 of 55 units undetermined, 15 because the recorded command could not be reproduced from the rule's inputs #ev("6.63"). The refusal counts therefore describe where proposals stopped; they do not attribute failures to grounding.

== Limitations <sec:disc-limits>

- *Model contribution not shown* (rungs c to e, @sec:disc-grounding): no tested model met the scene-use rule, the gate made the yielder correct, and the replay that could change this for ER-2 was stopped by provider limits #ev("6.09") #ev("6.08") #ev("6.10")\; plans had almost no executed effect, the one effect being a constrained selection among offered actions #ev("6.02") #ev("6.39") #ev("6.03")\; plan-audit labels over-state agreement, the corrected counts are offline, and the feedback shown to the model is still wrong after overrides #ev("6.51") #ev("6.80")\; and grounding refuses most five-robot proposals without telling the model #ev("6.15").
- *Nothing recovers a latched convoy cluster;* the queued-robot hold resolved the scene only in the rerun take, where the model named the workable yielder; the yielder correction has not fired live #ev("6.40") #ev("6.19") #ev("6.41") #ev("6.84") #ev("6.85").
- *Static obstacles were not checked along escort segments or reverse legs;* only the yielder's retreat room used declared boxes, and the execution and safety monitor (M4) ignores obstacles #ev("6.43"). A validation take came within 5.5 mm of a box under a `reverse` #ev("6.17"), and October reverses pinned robots on boxes #ev("6.18"). The guards built afterwards are off by default, see declared obstacles only, and have not fired live #ev("6.17") #ev("6.13") #ev("6.18").
- *Contact measurement is partial:* contact lists were a stub #ev("6.20"), the logger is partly validated #ev("6.17"), and the offline recompute is pending validation #ev("6.12").
- *The safety-exemption fix is not validated live* #ev("6.07") #ev("6.06") #ev("5.51").
- *Small, near-repeat samples, one VLM live, ascending listing, configuration drift.* Five episodes or seed pairs per arm, one scene per live study and one to six demonstration takes per scene #ev("6.05") #ev("6.06") #ev("6.14") #ev("6.45")\; ER-2 ran every live comparison #ev("6.16")\; ascending listing cannot separate an identifier prior from a slot prior, and the campaign ran a later prompt and the plan-order switch #ev("6.39").
- *No classical comparator;* RQ4 and RQ5 are untested (@sec:intro-rq).

=== Failure-Cause Classification <sec:disc-failure-cause>

The classification is exploratory and post hoc, written by authors who had read earlier diagnoses of some episodes and applied by two language-model raters to small strata, with blinding that was not clean #ev("6.60") #ev("6.61") #ev("6.63") #ev("6.65"). Its result is shaped by the rule as much as by the episodes: the zero for environment geometry and one decision code that never fired are structural, the reproduce gate drives most undetermined units, and the 60 s link window misses long pins. The final agreement of 53 of 55, against 35 of 55 in the first round, measures consistent application once evidence was supplied, not correctness, and 3 of the 5 final disagreements rest on one reader's ruling #ev("6.63"). The interception analysis shows what three mechanisms would have refused, not resolution; for 25 of 45 coordination-layer-on units no mechanism applies, and the reverse guard's false-positive share is high (15 of 29 pilot legs) #ev("6.63"). The registered pilot's 0 of 10 stands #ev("6.14").

== Threats to Validity <sec:disc-threats>

The threats stated before the data in @sec:ch5-threats all stand. The following arose afterwards.

- *Selected demonstrations.* The take rule stopped each scene at the first take meeting its goal, take 5 was shown for its label, and the earlier head-on run was chosen because it qualifies #ev("5.51") #ev("6.45") #ev("6.38"). The campaign shows what the pipeline can do, not what it usually does.
- *Analyses defined after the data.* The head-on re-score, the plan-influence trace, the plan-dispatch recomputation and the failure-cause rule came after the live data #ev("6.08") #ev("6.02") #ev("6.51") #ev("6.60") #ev("6.61").
- *Reconstructed counterfactuals.* Guard and stall-abort replays run recorded inputs through later code, the latter on regenerated command streams #ev("6.13") #ev("6.18")\; re-groundings are trusted only where a fidelity check reproduces the recorded dispatch #ev("6.02").
- *Source errors and review.* The registered pilot's report miscounted dispatches, corrected here #ev("6.14")\; the source reports were on unpushed, unreviewed branches when the evidence register was compiled, and review could change numbers #ev("6.16").
