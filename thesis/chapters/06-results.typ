#import "../lib.typ": *
#import "../figures/vlm-flow-take5-simple.typ": vlm-flow-simple-figure

= Results <sec:res>

This chapter reports what the experiments of Chapter 5 and the later checks found. The results carry four different grades of evidence, and the chapter keeps them apart #ev("6.16"):

- *Exploratory pilots.* The two IB10 runs on the four-robot intersection, five episodes per arm on one near-deterministic scene, reported as counts without inferential statistics.
- *Registered pilot.* prereg-v3 tranche 1 on the five-robot S1b scene, registered as confirmatory and reported as a pilot (@sec:ch5-rq).
- *Decision-level offline evidence.* Re-scores, replays and traces of recorded decisions, and the v4 bench. Nothing in them is executed in simulation.
- *Illustrative demonstrations.* The demonstration campaign in simulation, one earlier recorded run, and the physical TurtleBot3 demonstration. They show what the pipeline does in single takes. They are not controlled evidence, and no rate is drawn from them.

Nothing is pooled across these grades, across experiments, or between the two IB10 runs. Safety evidence throughout is the ground-truth (GT) robot-pair centre distance, because the simulator's contact lists were hard-coded empty in the evaluated runtime #ev("6.20") (@sec:res-safety).

== IB10: Layer 2 On vs Off <sec:res-ib10-ab>

The first IB10 run (2026-11-13) compared Arm A, the full Layer 2 pipeline with ER-2, against Arm B, Layer 2 switched off, on the four-robot intersection #ev("6.05"). @tab:res-ib10-ab gives the pooled outcome.

#figure(
  table(
    columns: (1.1fr, 1.4fr, 1.1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Measure*], [*Arm A, Layer 2 on (ER-2)*], [*Arm B, Layer 2 off*]),
    [Counted episodes], [5], [5],
    [Resolved], [4/5], [0/5],
    [Arrivals], [16/20], [0/20],
    [Time from onset to last arrival], [112.9, 115.5, 116.5, 116.6 s; e09 censored], [all five censored at the horizon],
    [Lowest GT robot-pair centre distance], [0.2633 m (e09)], [0.2856 m],
    [Floor stops], [0], [0],
    [Plan provenance of the dispatches], [`repaired` 4, `m3_default` 1, `vlm_verbatim` 0], [no dispatch],
  ),
  caption: flex-caption([IB10 run 1: Layer 2 on against off.], [IB10 run 1 (2026-11-13), Layer 2 on against Layer 2 off, five counted episodes per arm. Exploratory pilot on one scene; the episodes are near-repeats, so no p-value or interval is given.#fig-source("6.05")]),
) <tab:res-ib10-ab>

Arm A resolved four of five episodes and Arm B none. In every Arm B episode the four robots stopped at jam formation and did not move again before the horizon #ev("6.30"). Arm B is therefore a latch baseline: it shows that nothing in Layer 1 releases a formed jam, not how a classical coordinator would do (@sec:ch5-threats). The excluded first attempt of e01, a harness failure in the condition gate, also resolved, on `m3_default` #ev("6.30").

The one unresolved Arm A episode, e09, began with an off-pattern answer. Instead of `junction_clear` for all four robots, the model answered `yield`, and its second answer was a two-robot `junction_clear`, after which all four robots stood still for 120.1 s. The third answer's plan named two robots twice and was nulled by the parser, and M3’s default plan had not finished by the horizon #ev("6.31"). The lowest robot-pair distance of the run, 0.2633 m, occurred in this episode inside a pair that the command still exempted #ev("6.31").

The provenance labels bound the model's share. No dispatched plan was `vlm_verbatim`. Re-grounding every `repaired` decision without its plan gives the recorded commands, so the commands that ran were M3’s default in all four resolved episodes #ev("6.05") #ev("6.02"). The run therefore supports the claim that the pipeline, a Layer 2 trigger plus M3 grounding and phased dispatch, clears a jam that Layer 1 alone never clears. It does not show that the model's plan clears it.

== IB10: VLM vs Grounder Default (Arm C) <sec:res-ib10-c>

The second IB10 run (2026-11-14) is separate and is never pooled with the first. It ran with the safety-exemption fix switched on, and compared Arm A (live ER-2) with Arm C, which runs the same pipeline but replaces the VLM by a script that hands M3 the strategy `junction_clear` and all four robots, so that M3 executes its default plan #ev("6.06") (@sec:ch5-arms). The registration requires Arm C to be reported both before and after the post hoc re-run of slot e02 (@sec:ch5-procedure); @tab:res-ib10-c does so.

#figure(
  table(
    columns: (1.1fr, 1.1fr, 1.1fr, 1.1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Measure*], [*Arm A (ER-2)*], [*Arm C, before the re-run*], [*Arm C, after the re-run*]),
    [Valid episodes], [5], [4 (e02 formed no jam)], [5 (e02 a2 counted)],
    [Resolved], [5/5 (4/4 without the smoke)], [4/4], [5/5],
    [Arrivals], [20/20], [16/16], [20/20],
    [Time from onset (s)], [114.3, 115.7, 116.2, 116.7, 116.9; mean 115.96], [115.5, 118.5, 118.6, 118.6; mean 117.80], [115.5, 118.1, 118.5, 118.6, 118.6; mean 117.86],
    [Lowest GT robot-pair centre distance], [0.3008 m], [0.2965 m], [0.2965 m],
    [Floor stops], [0], [0], [0],
    [Plan provenance], [`repaired` 4, `m3_default` 1], [`m3_default`], [`m3_default`],
  ),
  caption: flex-caption([IB10 run 2: live VLM against the grounder default.], [IB10 run 2 (2026-11-14), Arm A against the grounder-default Arm C, with Arm C shown before and after the post hoc re-run of slot e02. Exploratory pilot; never pooled with run 1.#fig-source("6.06")]),
) <tab:res-ib10-c>

*Before the re-run.* In Arm C's slot e02 the map server of the navigation stack was never activated and no jam formed, so the slot was excluded under the registered invalid-jam rule. Arm C then resolved 4 of 4 valid episodes, against 5 of 5 for Arm A #ev("6.32"). Arm A is 5 of 5 counting the smoke episode and 4 of 4 without it, because the smoke acceptance was written under a conditional instruction rather than by the owner #ev("6.32").

*After the re-run.* The re-run of e02, decided after the results were seen and registered before it ran, formed a valid jam and resolved in 118.1 s on `m3_default`. Arm C became 5 of 5, mean 117.86 s #ev("6.34").

*What the arms share.* Every Arm A first dispatch re-grounds to exactly the plan Arm C executed. Only the dispatch time, a degradation tag, small snapshot-dependent distances and, in two Arm A episodes, the retreat side differ #ev("6.06"). Arm C dispatches about 3.4 s later than Arm A, because its script answers the first trigger with "no congestion" and the next analysis follows one cool-down later, so the times of the two arms are not strictly comparable #ev("6.33"). The safety-exemption fix was on in all ten episodes and never fired #ev("6.06").

*Reading.* In this run the live-VLM arm and the scripted default-plan arm are indistinguishable in outcome. The narrowed claim is that a Layer 2 trigger plus M3’s default `junction_clear` plan clears this jam, and that the VLM's remaining role in this scene is to choose the strategy and the robot set, which Arm C was given #ev("6.06"). Arm C cannot re-plan after a failure, so the run does not show that the model is useless either; run 1's e09 is the one case in which an off-pattern model choice changed what ran, and that episode did not resolve #ev("6.31").

== prereg-v3 Tranche 1 Pilot <sec:res-t1>

Tranche 1 ran ten episodes on the five-robot S1b scene, five seed pairs of Arm A (Layer 2 on, ER-2) and Arm B (Layer 2 off), interleaved and counterbalanced as registered #ev("6.14"). It was registered as confirmatory and is reported as a pilot (@sec:ch5-rq). @tab:res-t1 gives the registered measures.

#figure(
  table(
    columns: (1.4fr, 0.8fr, 0.8fr, 1.4fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Measure*], [*Arm A*], [*Arm B*], [*Difference A − B, bootstrap interval*]),
    [Complete episodes], [0/5], [0/5], [both arms censored at the horizon],
    [Tasks completed], [16/125], [12/125], [],
    [Tasks per seed (positions 1 to 5)], [8, 2, 0, 5, 1], [5, 1, 0, 6, 0], [],
    [Throughput at the common window], [0.128], [0.096], [+0.032 [−0.008, +0.080]],
    [Restricted makespan], [569.88 s], [569.88 s], [0.0 [0.0, 0.0]],
    [Mean delay lower bound], [323.4 s], [354.9 s], [−31.5 s [−71.6, −0.6]],
    [Detection recall], [0.818 (9 of 11 conflicts)], [0 of 10 (no analyses)], [degenerate for Arm B],
    [Type accuracy; involved-set F1], [0.778; 0.915], [n/a], [degenerate for Arm B],
    [False positives], [0 in 26 positive analyses], [n/a], [],
    [Analyses dispatched / withheld per seed], [5/4, 2/2, 2/3, 1/4, 2/1], [n/a], [],
    [Robot-pair gate (GT centre distance ≥ 0.18 m, no floor stop)], [PASS 5/5], [PASS 5/5], [GT minimum 0.225–0.424 m over all ten],
  ),
  caption: flex-caption([prereg-v3 tranche 1, reported as a pilot.], [prereg-v3 tranche 1 on S1b, five seed pairs, registered measures. The interval is the registered paired percentile bootstrap over seed pairs (@sec:ch5-analysis); no directional hypothesis was registered. The dispatched and withheld counts are corrected against the M4 command log (see text). Registered pilot.#fig-source("6.14")]),
) <tab:res-t1>

No episode of either arm completed all 25 tasks, so completeness is "failed" and makespan is censored at the horizon in all ten #ev("6.35"). The throughput interval includes zero. The interval of the mean delay lower bound excludes zero by 0.6 s, with Arm A lower #ev("6.14"). With five pairs, every run censored and no registered direction, these are interval estimates for this scene only, not a test.

On the decision side, Arm A detected 9 of the 11 ground-truth conflicts with a mean detection latency of 17.6 s, and none of its 26 positive analyses was a false positive #ev("6.35"). The source report's dispatched column is wrong: it counted a refused yield, which degrades to a wait, as dispatched. Checked against the commands M4 received, the Arm A analyses that reached M4 were 5, 2, 2, 1 and 2 per seed, and 4, 2, 3, 4 and 1 were withheld #ev("6.14"). The same offline recomputation of plan-dispatch agreement, run beside the registered results and not as a rescore of them, finds 1 of the tranche's 2 recorded `vlm_verbatim` plans dispatched as written; in the other, a `reroute` rerouted a different robot than the plan named #ev("6.51"). The robot-pair gate passed in all ten episodes. It covers robot pairs only; contact with the rack islands is not covered by it (@sec:res-safety).

== Failure Causes of the Five-Robot Episodes <sec:res-failure-causes>

#[
#show figure.where(kind: table): set block(breakable: true)

This section reports the classification of @sec:ch5-failure-cause. It is an exploratory, post hoc analysis of 33 episodes in three strata that are never pooled, and it is meant to explain outcomes that are reported in the other sections of this chapter without changing any of them. The original tranche-1 outcome, 0 of 10 episodes complete, stands as reported #ev("6.14"). The rating was not complete when this report was written; every value below is a placeholder.

#figure(
  table(
    columns: (1.7fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Primary cause*], [*Tranche 1, Arm A*], [*Tranche 1, Arm B*], [*Pilots, horizon*], [*Pilots, stop rule*], [*November takes*]),
    table.cell(colspan: 6, fill: luma(245))[*Primary cause, failure units (episodes whose episode-level primary cause is this class)*],
    [Decision (V)], [#todo[TBD-T1-V-A]], [n/a by construction], [#todo[TBD-T1-V-H]], [#todo[TBD-T1-V-S]], [#todo[TBD-T1-V-N]],
    [Grounding and verification (G)], [#todo[TBD-T1-G-A]], [n/a by construction], [#todo[TBD-T1-G-H]], [#todo[TBD-T1-G-S]], [#todo[TBD-T1-G-N]],
    [Execution (X)], [#todo[TBD-T1-X-A]], [#todo[TBD-T1-X-B]], [#todo[TBD-T1-X-H]], [#todo[TBD-T1-X-S]], [#todo[TBD-T1-X-N]],
    [Environment geometry (EG)], [#todo[TBD-T1-EG-A]], [#todo[TBD-T1-EG-B]], [#todo[TBD-T1-EG-H]], [#todo[TBD-T1-EG-S]], [#todo[TBD-T1-EG-N]],
    [Undetermined (U)], [#todo[TBD-T1-U-A]], [#todo[TBD-T1-U-B]], [#todo[TBD-T1-U-H]], [#todo[TBD-T1-U-S]], [#todo[TBD-T1-U-N]],
    [*All failure units*], [#todo[TBD-T1-TOT-A]], [#todo[TBD-T1-TOT-B]], [#todo[TBD-T1-TOT-H]], [#todo[TBD-T1-TOT-S]], [#todo[TBD-T1-TOT-N]],
    [Parked robots excluded, not units], [#todo[TBD-T1-PARK-A]], [#todo[TBD-T1-PARK-B]], [#todo[TBD-T1-PARK-H]], [#todo[TBD-T1-PARK-S]], [#todo[TBD-T1-PARK-N]],
    table.cell(colspan: 6, fill: luma(245))[*Contributing causes, failure units carrying the code (never summed with the primary counts)*],
    [Decision (V)], [#todo[TBD-T1-cV-A]], [n/a by construction], [#todo[TBD-T1-cV-H]], [#todo[TBD-T1-cV-S]], [#todo[TBD-T1-cV-N]],
    [Grounding and verification (G)], [#todo[TBD-T1-cG-A]], [n/a by construction], [#todo[TBD-T1-cG-H]], [#todo[TBD-T1-cG-S]], [#todo[TBD-T1-cG-N]],
    [Execution (X)], [#todo[TBD-T1-cX-A]], [#todo[TBD-T1-cX-B]], [#todo[TBD-T1-cX-H]], [#todo[TBD-T1-cX-S]], [#todo[TBD-T1-cX-N]],
    [Environment geometry (EG)], [#todo[TBD-T1-cEG-A]], [#todo[TBD-T1-cEG-B]], [#todo[TBD-T1-cEG-H]], [#todo[TBD-T1-cEG-S]], [#todo[TBD-T1-cEG-N]],
    table.cell(colspan: 6, fill: luma(245))[*Sensitivity analyses, failure units whose primary cause changes (reported beside the primary coding)*],
    [S1, persistent-state chain rule], [#todo[TBD-T1-S1-A]], [n/a, nothing dispatched], [#todo[TBD-T1-S1-H]], [#todo[TBD-T1-S1-S]], [#todo[TBD-T1-S1-N]],
    [S2, start-inside straight-move check], [#todo[TBD-T1-S2-A]], [#todo[TBD-T1-S2-B]], [#todo[TBD-T1-S2-H]], [#todo[TBD-T1-S2-S]], [#todo[TBD-T1-S2-N]],
  ),
  caption: flex-caption([Primary and contributing causes of failure units, by stratum.], [Primary and contributing causes of the failure units of the five-robot S1b episodes, by stratum. The strata are never pooled. A primary-cause cell gives failure units and, in brackets, the episodes whose episode-level primary cause is that class; the total row gives, in brackets, the episodes with at least one unit. Pilot episodes that the batch stop rule ended early are shown apart from those that ran to the horizon. In the Layer-2-off arm the decision and grounding classes are not applicable by construction, and every unit carries the context code N0. Exploratory, post hoc classification by two raters (@sec:ch5-failure-cause).#fig-source("6.63")]),
) <tab:ch6-fc-primary>

#figure(
  table(
    columns: (1.6fr, 0.8fr, 1fr, 0.9fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Stratum*], [*Units rated*], [*Raw agreement, primary class*], [*Cohen's kappa, primary class*], [*Raw agreement, full code*], [*Disagreements*], [*Still undetermined after reconciliation*]),
    [Tranche 1 Arm A], [#todo[TBD-T2-A-U]], [#todo[TBD-T2-A-RC]], [#todo[TBD-T2-A-K]], [#todo[TBD-T2-A-RF]], [#todo[TBD-T2-A-D]], [#todo[TBD-T2-A-DU]],
    [Tranche 1 Arm B], [#todo[TBD-T2-B-U]], [#todo[TBD-T2-B-RC]], [#todo[TBD-T2-B-K]], [#todo[TBD-T2-B-RF]], [#todo[TBD-T2-B-D]], [#todo[TBD-T2-B-DU]],
    [Pilots, horizon], [#todo[TBD-T2-H-U]], [#todo[TBD-T2-H-RC]], [#todo[TBD-T2-H-K]], [#todo[TBD-T2-H-RF]], [#todo[TBD-T2-H-D]], [#todo[TBD-T2-H-DU]],
    [Pilots, stop rule], [#todo[TBD-T2-S-U]], [#todo[TBD-T2-S-RC]], [#todo[TBD-T2-S-K]], [#todo[TBD-T2-S-RF]], [#todo[TBD-T2-S-D]], [#todo[TBD-T2-S-DU]],
    [November takes], [#todo[TBD-T2-N-U]], [#todo[TBD-T2-N-RC]], [#todo[TBD-T2-N-K]], [#todo[TBD-T2-N-RF]], [#todo[TBD-T2-N-D]], [#todo[TBD-T2-N-DU]],
    [All strata (agreement statistic only; no outcome is pooled)], [#todo[TBD-T2-ALL-U]], [#todo[TBD-T2-ALL-RC]], [#todo[TBD-T2-ALL-K]], [#todo[TBD-T2-ALL-RF]], [#todo[TBD-T2-ALL-D]], [#todo[TBD-T2-ALL-DU]],
  ),
  caption: flex-caption([Agreement between the two raters, by stratum.], [Agreement between the two independent raters before reconciliation, by stratum. Kappa is reported as n/a where it is undefined, for example where every unit of a stratum falls in one class. Disagreements are listed one by one with both codes and the reconciled code in the reconciliation report.#fig-source("6.63")]),
) <tab:ch6-fc-agree>

The ten registered tranche-1 episodes held #todo[TBD-R04: failure units, tranche 1 Arm A] failure units in Arm A and #todo[TBD-R05: failure units, tranche 1 Arm B] in Arm B; the 21 pilot episodes held #todo[TBD-R06: failure units, ER-2 pilots] and the two November takes #todo[TBD-R07: failure units, November takes] (@tab:ch6-fc-primary). #todo[TBD-R08: one sentence per stratum naming the class or classes with most primary units, or stating that none stands out, reconciliation table 1] Contributing causes are counted apart and are not added to the primary counts. The two raters agreed on the primary class for #todo[TBD-R09: units on which raters agreed on primary class, all strata] of #todo[TBD-R10: units rated, all strata] units, with a kappa of #todo[TBD-R11: Cohen kappa on primary class, all strata, or n/a], and the #todo[TBD-R12: disagreements before reconciliation, count] disagreements were reconciled as listed in the reconciliation report (@tab:ch6-fc-agree) #ev("6.63"). The units whose primary cause changes under the sensitivity analyses S1 and S2 are given per stratum in the last rows of @tab:ch6-fc-primary #todo[TBD-R13: one sentence on the S1 and S2 rows, per stratum, without summing across strata].

Interception is reported per stratum, and only for the strata in which commands were dispatched (@tab:ch6-fc-intercept-a, @tab:ch6-fc-intercept-p and @tab:ch6-fc-intercept-n). Under the primary chain rule, a linked dispatched leg that at least one of the three mechanisms would have refused or aborted exists for #todo[TBD-R15A: intercepted units, tranche 1 Arm A] of #todo[TBD-R16A: failure units, tranche 1 Arm A] failure units in tranche 1 Arm A, #todo[TBD-R15P: intercepted units, ER-2 pilots] of #todo[TBD-R16P: failure units, ER-2 pilots] in the ER-2 pilots and #todo[TBD-R15N: intercepted units, November takes] of #todo[TBD-R16N: failure units, November takes] in the November takes; under S1 the three counts are #todo[TBD-R17: the same three counts under S1]. Of the legs that the mechanisms would have refused or aborted (#todo[TBD-R18: per stratum, legs that at least one mechanism would refuse or abort]), #todo[TBD-R19: per stratum, of those, legs in contact or pinned (justified)] were in contact or pinned and #todo[TBD-R20: per stratum, of those, false positives] were false positives, with #todo[TBD-R21: per stratum, of those, untested legs] untested. For #todo[TBD-R22: per stratum, units to which none of the mechanisms applies] units none of the mechanisms applies, because no dispatched leg is linked to them or because no linked leg would have been intercepted.


#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Mechanism*], [*Legs it would have refused or aborted*], [*of which in contact or pinned (justified)*], [*of which false positives*], [*of which never reached an obstacle (untested)*], [*Units with such a linked leg, primary chain rule*], [*Units with such a linked leg, S1*]),
    [Dispatched escort and reverse legs in the stratum], [#todo[TBD-T3A-DEN-L]], [n/a], [n/a], [n/a], [n/a], [n/a],
    [Escort obstacle guard (refuses)], [#todo[TBD-T3A-ESC-L]], [#todo[TBD-T3A-ESC-J]], [#todo[TBD-T3A-ESC-F]], [#todo[TBD-T3A-ESC-UT]], [#todo[TBD-T3A-ESC-P]], [#todo[TBD-T3A-ESC-S]],
    [Reverse obstacle guard (refuses)], [#todo[TBD-T3A-REV-L]], [#todo[TBD-T3A-REV-J]], [#todo[TBD-T3A-REV-F]], [#todo[TBD-T3A-REV-UT]], [#todo[TBD-T3A-REV-P]], [#todo[TBD-T3A-REV-S]],
    [Stall abort (aborts)], [#todo[TBD-T3A-STL-L]], [#todo[TBD-T3A-STL-J]], [#todo[TBD-T3A-STL-F]], [#todo[TBD-T3A-STL-UT]], [#todo[TBD-T3A-STL-P]], [#todo[TBD-T3A-STL-S]],
    [Any of the three], [#todo[TBD-T3A-ANY-L]], [#todo[TBD-T3A-ANY-J]], [#todo[TBD-T3A-ANY-F]], [#todo[TBD-T3A-ANY-UT]], [#todo[TBD-T3A-ANY-P]], [#todo[TBD-T3A-ANY-S]],
    [*None of these mechanisms applies*], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3A-NONE-P]], [#todo[TBD-T3A-NONE-S]],
    [#h(1em)of which no dispatched leg is linked to the unit], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3A-NOL-P]], [#todo[TBD-T3A-NOL-S]],
    [#h(1em)of which a linked leg exists but none would be intercepted], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3A-LNI-P]], [#todo[TBD-T3A-LNI-S]],
    [*All failure units in the stratum*], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3A-TOT-P]], [#todo[TBD-T3A-TOT-S]],
  ),
  caption: flex-caption([Interception analysis, tranche 1, Arm A.], [Interception analysis, tranche 1, Arm A: what three mechanisms written after the pinned runtime would have refused or aborted among the legs the episodes dispatched, and how many failure units have such a leg linked to them, under the primary chain rule and under sensitivity analysis S1. The rows for the mechanisms overlap, so the row for any of the three is not their sum. The counts say what would have been refused or aborted, not that the scene would then have resolved. The Layer-2-off arm dispatched no command, so no mechanism applies to it by construction; its units are in the first table of this section.#fig-source("6.63")]),
) <tab:ch6-fc-intercept-a>

#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Mechanism*], [*Legs it would have refused or aborted*], [*of which in contact or pinned (justified)*], [*of which false positives*], [*of which never reached an obstacle (untested)*], [*Units with such a linked leg, primary chain rule*], [*Units with such a linked leg, S1*]),
    [Dispatched escort and reverse legs in the stratum], [#todo[TBD-T3P-DEN-L]], [n/a], [n/a], [n/a], [n/a], [n/a],
    [Escort obstacle guard (refuses)], [#todo[TBD-T3P-ESC-L]], [#todo[TBD-T3P-ESC-J]], [#todo[TBD-T3P-ESC-F]], [#todo[TBD-T3P-ESC-UT]], [#todo[TBD-T3P-ESC-P]], [#todo[TBD-T3P-ESC-S]],
    [Reverse obstacle guard (refuses)], [#todo[TBD-T3P-REV-L]], [#todo[TBD-T3P-REV-J]], [#todo[TBD-T3P-REV-F]], [#todo[TBD-T3P-REV-UT]], [#todo[TBD-T3P-REV-P]], [#todo[TBD-T3P-REV-S]],
    [Stall abort (aborts)], [#todo[TBD-T3P-STL-L]], [#todo[TBD-T3P-STL-J]], [#todo[TBD-T3P-STL-F]], [#todo[TBD-T3P-STL-UT]], [#todo[TBD-T3P-STL-P]], [#todo[TBD-T3P-STL-S]],
    [Any of the three], [#todo[TBD-T3P-ANY-L]], [#todo[TBD-T3P-ANY-J]], [#todo[TBD-T3P-ANY-F]], [#todo[TBD-T3P-ANY-UT]], [#todo[TBD-T3P-ANY-P]], [#todo[TBD-T3P-ANY-S]],
    [*None of these mechanisms applies*], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3P-NONE-P]], [#todo[TBD-T3P-NONE-S]],
    [#h(1em)of which no dispatched leg is linked to the unit], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3P-NOL-P]], [#todo[TBD-T3P-NOL-S]],
    [#h(1em)of which a linked leg exists but none would be intercepted], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3P-LNI-P]], [#todo[TBD-T3P-LNI-S]],
    [*All failure units in the stratum*], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3P-TOT-P]], [#todo[TBD-T3P-TOT-S]],
  ),
  caption: flex-caption([Interception analysis, ER-2 pilots.], [Interception analysis, ER-2 pilots: what three mechanisms written after the pinned runtime would have refused or aborted among the legs the episodes dispatched, and how many failure units have such a leg linked to them, under the primary chain rule and under sensitivity analysis S1. The rows for the mechanisms overlap, so the row for any of the three is not their sum. The counts say what would have been refused or aborted, not that the scene would then have resolved.#fig-source("6.63")]),
) <tab:ch6-fc-intercept-p>

#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Mechanism*], [*Legs it would have refused or aborted*], [*of which in contact or pinned (justified)*], [*of which false positives*], [*of which never reached an obstacle (untested)*], [*Units with such a linked leg, primary chain rule*], [*Units with such a linked leg, S1*]),
    [Dispatched escort and reverse legs in the stratum], [#todo[TBD-T3N-DEN-L]], [n/a], [n/a], [n/a], [n/a], [n/a],
    [Escort obstacle guard (refuses)], [#todo[TBD-T3N-ESC-L]], [#todo[TBD-T3N-ESC-J]], [#todo[TBD-T3N-ESC-F]], [#todo[TBD-T3N-ESC-UT]], [#todo[TBD-T3N-ESC-P]], [#todo[TBD-T3N-ESC-S]],
    [Reverse obstacle guard (refuses)], [#todo[TBD-T3N-REV-L]], [#todo[TBD-T3N-REV-J]], [#todo[TBD-T3N-REV-F]], [#todo[TBD-T3N-REV-UT]], [#todo[TBD-T3N-REV-P]], [#todo[TBD-T3N-REV-S]],
    [Stall abort (aborts)], [#todo[TBD-T3N-STL-L]], [#todo[TBD-T3N-STL-J]], [#todo[TBD-T3N-STL-F]], [#todo[TBD-T3N-STL-UT]], [#todo[TBD-T3N-STL-P]], [#todo[TBD-T3N-STL-S]],
    [Any of the three], [#todo[TBD-T3N-ANY-L]], [#todo[TBD-T3N-ANY-J]], [#todo[TBD-T3N-ANY-F]], [#todo[TBD-T3N-ANY-UT]], [#todo[TBD-T3N-ANY-P]], [#todo[TBD-T3N-ANY-S]],
    [*None of these mechanisms applies*], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3N-NONE-P]], [#todo[TBD-T3N-NONE-S]],
    [#h(1em)of which no dispatched leg is linked to the unit], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3N-NOL-P]], [#todo[TBD-T3N-NOL-S]],
    [#h(1em)of which a linked leg exists but none would be intercepted], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3N-LNI-P]], [#todo[TBD-T3N-LNI-S]],
    [*All failure units in the stratum*], [n/a], [n/a], [n/a], [n/a], [#todo[TBD-T3N-TOT-P]], [#todo[TBD-T3N-TOT-S]],
  ),
  caption: flex-caption([Interception analysis, November takes.], [Interception analysis, November takes: what three mechanisms written after the pinned runtime would have refused or aborted among the legs the episodes dispatched, and how many failure units have such a leg linked to them, under the primary chain rule and under sensitivity analysis S1. The rows for the mechanisms overlap, so the row for any of the three is not their sum. The counts say what would have been refused or aborted, not that the scene would then have resolved.#fig-source("6.63")]),
) <tab:ch6-fc-intercept-n>

*How to read these tables.* The following caveats apply to every table of this section.

- *What interception means.* The counts say what would have been refused or aborted. They do not say that the scene would then have resolved: a refused reverse is replaced by a short wait for the robots involved, which changes every later state, and whether the scene then resolves can only be shown by new live runs.
- *Validation state of the mechanisms.* The escort obstacle guard was run live in one validation take in which no escort was grounded, so it never fired live; its blocking behaviour rests on unit tests and an offline replay of recorded decisions. The reverse obstacle guard rests on unit tests and an offline replay of recorded reverse commands, with false positives at square box corners and at declared walls that span open arms, and it has not been run live. The stall abort rests on unit and node tests and an offline replay of recorded primitives whose command streams were reconstructed, because the commands were not recorded, and it has not been run live. The ground-truth contact logger ran in one live take and reproduced its offline recompute row by row, but no robot was pinned during that take, so it does not show that entries appear when one is. The plan-dispatch visibility logging has been tested offline only #ev("6.13") #ev("6.18") #ev("6.12") #ev("6.17") #ev("6.51").
- *Geometry at the onset.* The rule assigns the first environment-geometry code and the code for a missing strategy only at the onset, and only when the set of hypothetical decisions that ground to motion is empty. In these data that set is never empty at an onset, so neither code can fire there #ev("6.61"). A small count in the environment-geometry class therefore does not show that geometry played no part. #todo[TBD-M05: state whether any other route of the rule can assign the environment-geometry class as primary, once checked against the rubric.]
- *The 60-second link window.* A command is linked to a unit only when it was dispatched in the 60 simulated seconds before the onset or was executing at the onset. A robot that stayed pinned for longer than that before the onset is not linked to the command that pinned it. The sensitivity analysis S1 relaxes this and is reported beside the primary counts, never in place of them.
- *Prior knowledge of the authors.* The authors of the rule and of the application notes had read earlier diagnoses of some of the episodes before writing them, so the rule is not blind to those episodes. The raters were not shown those diagnoses #ev("6.60") #ev("6.61").
- *Reconstructed replays.* The guard replays re-ground recorded decisions on a later tree and do not ask the second stage again, and the stall-abort replay regenerates the command stream with the primitive's own logic on recorded poses. Neither is a recording of what a live run would have done.
- *Contact evidence.* The ground-truth contact fields were empty in the October runs, so every contact in them is an offline geometric recomputation of the planar footprint at 10 Hz, not a logged event #ev("6.12").
- *Size and status.* The strata hold 10, 21 and 2 episodes, so the counts are small. The analysis is exploratory and not confirmatory, no test is registered for it, and the registered tranche-1 episodes are never pooled with the exploratory runs.
- *Original outcome.* The registered pilot's original outcome, 0 of 10 episodes complete, stands as reported.
]

== Head-on Yielder Choice <sec:res-headon>

In the two-robot head-on scenes one robot must back out, and in the asymmetric variants only one of the two has room to do so. This section asks whether the model picks that robot.

*Re-score of recorded live decisions.* A post hoc, decision-level re-score covered every recorded live analysis of the asymmetric head-on family, counting the first positive analysis of each run #ev("6.08"). In the west variants the correct yielder is `robot_2`, in the east variants `robot_1` #ev("6.36"). @tab:res-headon compares the model with two trivial baselines: always naming `robot_1`, and the scene manifest's first-come-first-served label.

#figure(
  table(
    columns: (0.8fr, 0.7fr, 0.6fr, 0.9fr, 0.9fr, 0.9fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Model*], [*Side*], [*Runs*], [*Model correct*], [*Always `robot_1`*], [*Manifest rule*]),
    [gpt-4o], [west], [23], [5/23], [0/23], [23/23],
    [gpt-4o], [east], [12], [10/12], [12/12], [0/12],
    [ER-2], [west], [30], [12/30], [0/30], [30/30],
    [ER-2], [east], [13], [11/13], [13/13], [0/13],
  ),
  caption: flex-caption([Head-on yielder: model against trivial baselines.], [Head-on asymmetric family, yielder correct at run level (first positive analysis per run). Post hoc, decision-level re-score of recorded live decisions; not pre-registered.#fig-source("6.08")]),
) <tab:res-headon>

In no row does the model beat the better of the two baselines #ev("6.36"). On the west side both models are below the manifest rule; on the east side they are below always naming `robot_1`. Their east-side advantage over the manifest rule is the `robot_1` preference meeting a variant in which `robot_1` happens to be correct. The yielder that M3 grounded was made correct by its feasibility gate: with the gate in `swap` mode, the grounded yielder was correct in 79 of 79 runs, and in 37 of them the gate overturned the model's pick #ev("6.08"). That column is derived from artifact fields, not from M4 logs, and the gate exists for yields only; it was off in every IB10 run #ev("6.49").

*One accepted yielder, and its contrast.* An earlier recorded run on the same scene (ER2LIVE, 2026-09-30, older code) is the one recorded example examined here in which the gate kept the yielder the model named, `robot_2`, and it was executed (@fig:ch6-er2live) #ev("6.38"). It was selected because it qualifies, so it says nothing about how often this happens. The model named the second-listed robot, its stage-2 retreat pick was the first-listed of two mirror-equivalent options, and `robot_2` reached its goal only after about 22 sim-s of navigation-stack stall and recovery #ev("6.38"). In the demonstration campaign's head-on take, on the same scene, the model named `robot_1`, which had 0.70 m of retreat room against 1.08 m required, and the gate swapped the yield to `robot_2` (@fig:ch6-ho-yield) #ev("6.37"). Both are single takes; no rate follows.

#figure(
  image("../assets/images/fig_er2live_robot2_aside_robot1_passing_t86p30.png", width: 75%),
  caption: flex-caption([Earlier head-on run: the model's yielder kept and executed.], [Head-on corridor with obstacle, two robots, from an earlier recorded run (2026-09-30, older code, not part of the demonstration campaign), annotated overhead camera frame at simulated time 86.3 s. `robot_2`, the yielder the model named and the feasibility gate kept, has backed out and parked beside the lane, and `robot_1` is escorted past it. 2 of 2 arrived, `robot_2` only after a navigation-stack stall and recovery. Simulation (Isaac Sim), overhead camera. Illustrative, n = 1, chosen because the model's yielder was kept.#fig-source("6.38")]),
) <fig:ch6-er2live>

*Offline replays on scene use.* Three offline replays asked whether a model chooses the yielder from the scene rather than from robot labels or listing order, on standoff scenes of one head-on family, first decision only and with nothing executed (@tab:res-replay). They are never pooled with live data.

#figure(
  table(
    columns: (1fr, 0.8fr, 2.2fr, 1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Replay*], [*Model*], [*Result*], [*Verdict*]),
    [Swapped identifiers (pre-registered)], [gpt-4o], [follows the first-listed slot in 85 of 96 grey-pair yields], [scene-use rule not met],
    [], [ER-2], [answers `reverse` in 129 of 144 runs in the A/B arms], [scene-use rule not met],
    [], [Sonnet 5.5], [refused 30 of 48 real-frame runs], [not assessable],
    [JSON-only ending (pre-registered)], [Sonnet 5.5], [146 of 146 answered, 0 refusals; 46 of 96 correct in the grey pair; names `robot_2` in 76 of 96], [scene use not supported],
    [], [ER-2], [50 of 96 runs completed (provider limit)], [not assessable],
    [Improved annotation], [ER-2, gpt-4o], [stopped by provider limits before completion], [every verdict not assessable],
  ),
  caption: flex-caption([Offline replays on yielder choice and scene use.], [Offline replays of the yielder choice on one head-on scene family, two robots, first decision only. Small, decision-level, never pooled with live data.#fig-source("6.09")]),
) <tab:res-replay>

No tested model met the pre-registered rule for choosing the yielder from the scene #ev("6.09") #ev("6.11"). The improved-annotation replay was stopped by provider limits, and every one of its verdicts is not assessable. It leaves one lead, and no more than a lead: with legible labels plus a neutral sentence that a robot backing up needs free floor behind it, ER-2 named the correct robot in 55 of 67 runs, against 11 of 64 with legible labels alone; in the grey control the sentence did not move the answers (7 of 66 against 8 of 67) #ev("6.10"). The lead is not evidence that the model uses the image.

== Plan Influence <sec:res-plan>

The provenance labels record how an audited plan relates to the model's proposal. A trace of every live four-robot congestion analysis asked a stricter question: did the model's plan change the commands that M4 received? It classifies each analysis at three levels (@tab:res-plan) #ev("6.02").

#figure(
  table(
    columns: (1.6fr, 1fr, 0.8fr, 0.7fr, 0.7fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Level*], [*Intersection, ER-2 (24)*], [*vp10, gpt-4o (13)*], [*s6, ER-2 (4)*], [*All (41)*]),
    [1. Valid response], [24], [13], [4], [41],
    [2. Plan accepted unchanged (`vlm_verbatim`)], [2 (0 of 20 `junction_clear`)], [11], [1], [14],
    [2. Accepted and dispatched as written], [2], [6], [0], [8],
    [3. Plan changed execution against no plan (gated)], [0 of 22], [0 of 13], [0 of 4], [0 of 39],
    [Decision fields changed execution against the grounder default (gated)], [5], [13], [n/a], [18, in 4 episodes],
  ),
  caption: flex-caption([Plan influence in live four-robot analyses.], [Three-level classification of the 41 live four-robot congestion analyses; 39 pass the trace's fidelity gate. Decision-level trace with verified and inferred labels, on the evaluated runtime.#fig-source("6.02")]),
) <tab:res-plan>

The model's plan changed the dispatched commands in none of the 39 gated analyses #ev("6.02"). In this runtime the grounder never reads the proposed plan: it grounds from the decision fields, and the plan is audited afterwards #ev("6.02"). The one switch that lets a verified plan set the order of the recede phases was never on in these runs #ev("6.49"). In each of the 11 `repaired` intersection plans, the recede set, recede order, yielder and passer that ran all came from M3 #ev("6.49"). The 14 accepted plans came from strategies with weak or no leg constraints, and 6 of them were not dispatched as written #ev("6.49").

The model's other choices did change execution, through the decision fields, in 18 dispatches in four episodes: run 1's e09 and gpt-4o's vp10, plus three answers in two development-era smoke episodes #ev("6.49"). Where the effect can be judged, in e09 and vp10, neither episode resolved #ev("6.02").

== Demonstration Campaign <sec:res-demo>

The demonstration campaign ran live ER-2 takes in four simulated scenes to show the pipeline end to end on video #ev("6.01"). It used a later prompt and, at the intersection, an opt-in switch that lets a verified plan set the recede order, so its configuration is not that of the evaluated runtime #ev("6.39"). Every take is an illustrative demonstration, not controlled evidence: n is 1 to 5 per scene, the take shown for the intersection was selected for its label, and nothing here is a rate #ev("6.45"). @fig:ch6-demo-panel shows the video format.

#figure(
  image("../assets/images/fig_intersection_panel_dispatch_t33p07.png", width: 100%),
  caption: flex-caption([Format of the demonstration videos.], [Format of the demonstration videos: one frame of the panel video of the four-robot intersection, take 5 (labelled VLM-driven execution, chosen for that label), at simulated time 33.1 s. Left: the annotated overhead camera stream with the renderer's captions. Right: the run's own M5 and M4 log lines replayed in sync, here the decision (`junction_clear`, provenance `vlm_verbatim`) and the dispatch of `robot_3`'s back-out. Simulation (Isaac Sim), overhead camera. Illustrative demo, not controlled evidence; take 5 is 1 of 5 takes.#fig-source("6.01")]),
) <fig:ch6-demo-panel>

The campaign has 12 valid takes and two bring-up aborts (@tab:res-demo) #ev("6.45").

#figure(
  table(
    columns: (1.1fr, 0.6fr, 2.3fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Scene*], [*Valid takes*], [*Outcome per take (label)*]),
    [Four-robot intersection], [5], [take 1 unresolved, 3/4 arrived; takes 2 to 4 resolved by the M3 default plan; take 5 resolved 4/4, labelled VLM-driven execution],
    [Convoy counterflow, four robots], [5], [takes 1 to 3 unresolved, 0/4 arrived each; takes 4 and 5, with the queued-robot hold, unresolved, 1/4 arrived each],
    [Head-on corridor with obstacle], [1], [resolved 2/2, M3-default resolution (grounder-corrected)],
    [Five robots, S1b seed position 21], [1], [unresolved, 1/5 arrived (limitation demonstration)],
  ),
  caption: flex-caption([Demonstration campaign: scenes and takes.], [Demonstration campaign, live ER-2 takes. One bring-up abort each in the intersection and the convoy scene is not counted. Illustrative demo, not controlled evidence; nothing is a rate.#fig-source("6.45")]),
) <tab:res-demo>

*Valid, accepted, executed.* @tab:res-threeway separates three things that are easily conflated: a valid model response, a plan that the verifier accepted unchanged, and a plan that changed what was executed. Every one of the 67 analyses parsed as valid. A valid response is not a usable one: in intersection takes 1 and 3 the answers parsed, but their plans were nulled for invalid structure #ev("6.39"). The verifier accepted the plan unchanged in 6 of the 65 plan-channel analyses, as recorded. That label over-states agreement: for `reverse` and `reroute` the grounder acts on the model's list of involved robots and never reads the plan, so an accepted plan can coexist with a dispatch that contradicts it #ev("6.02") #ev("6.51"). An offline recomputation counts a plan as accepted and dispatched as written only when the commands actually sent match its verified legs, excluding two registered artefacts (retreat-shield waits on robots planned `continue`, and back-out orders within the verifier's tolerance). Under that definition the campaign's 6 becomes 5: one convoy decision planned waits for the two queued robots, which dispatch never commanded. Counting motion differences only gives 6, and the raw reading with no exclusions gives 3 #ev("6.51"). Across the recorded live decisions, 10 of 33 dispatched `reverse` legs went to robots whose plan said something else #ev("6.51"). A plan changed the executed commands once, in intersection take 5, the only scene where this was computed #ev("6.44").

#figure(
  table(
    columns: (1fr, 0.75fr, 1.15fr, 1.1fr, 1.1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Scene*], [*Valid response*], [*Accepted plan, recorded (`vlm_verbatim`)*], [*Accepted and dispatched as written, corrected*], [*Plan changed executed behaviour*]),
    [Intersection, 5 takes], [9 of 9], [1 (take 5)], [1], [1 (take 5, recede order only)],
    [Convoy, 5 takes], [48 of 48], [3 (20 `repaired`, 25 `m3_default`)], [2 (takes 1 to 3: 2; takes 4 and 5: 0)], [not computed],
    [Head-on, 1 take], [2 of 2], [plan channel off], [n/a], [not computed],
    [Five robots, 1 take], [8 of 8], [2 (1 `repaired`, 5 `m3_default`)], [2], [not computed],
    [Total], [67 of 67], [6 of 65 plan-channel analyses], [5], [1],
  ),
  caption: flex-caption([Demonstration campaign: valid, accepted and executed.], [Demonstration campaign, per analysis (stage-2 retreat calls not counted): valid model response, plan accepted unchanged by the verifier as recorded and as recomputed offline (commands sent match the verified legs), and plan that changed the executed commands relative to M3’s default for the same snapshot. The recorded column over-states agreement; the corrected column is an offline recomputation that leaves the recorded labels unchanged #ev("6.51"). Illustrative demo.#fig-source("6.44")]),
) <tab:res-threeway>

=== Intersection, Take 5 <sec:res-demo-ib>

Take 1 of the intersection was unresolved: a one-frame identity glitch in M1 triggered the analysis on an approach snapshot, the model's plan was nulled, and M3’s default plan for that pre-jam geometry held one robot past the horizon. Takes 2 to 4 were resolved by M3’s default plan #ev("6.39"). Take 5 is the only take labelled VLM-driven execution. ER-2's plan was accepted with no edit, and its recede order, `robot_3` before `robot_4`, was dispatched in place of the default `robot_4` before `robot_3`; all four robots arrived #ev("6.39"). @fig:ch6-flow-take5-simple shows what the model proposed and what the system computed.

#figure(
  vlm-flow-simple-figure(),
  kind: image,
  caption: flex-caption([Simplified decision flow of one live intersection take.], [One live run (four-robot intersection, demonstration take 5 of 5, selected because it is the only take labelled VLM-driven execution): what the VLM proposed, what M3 verified, what grounding computed and what was executed. The model's contribution to execution was the back-out order only (filled box), `robot_3` before `robot_4` instead of the default `robot_4` before `robot_3`, and it was a near-tie: the recede costs differ by 0.010 m, within the verifier's 0.15 m tolerance. This is an end-to-end execution example, not controlled evidence of improved performance: the four arrivals do not show that the VLM outperforms the default plan, which resolved the same scene in takes 2 to 4 (take 1 was unresolved). Safety in this run rested on robot-pair distance only: the M4 safety monitor has no obstacle check, no stage checked the escort or back-out paths against obstacles, and the intersection scene declares no static boxes #ev("6.43") #ev("6.13"). @fig:app-flow-take5 in the appendix gives the full trace.#fig-source("6.01")]),
) <fig:ch6-flow-take5-simple>

The take is an end-to-end execution example, not controlled evidence of improved performance. Its caveats bound what the model contributed #ev("6.39"):

- *A near-tie.* The two recede orders differ in M3’s recede cost by 0.010 m, against the verifier's tolerance of 0.15 m. Any accepted order that differs from the default is a near-tie by construction.
- *Timing only.* By design the order changes only when the two recede legs are dispatched: `robot_3` began backing out at 32.9 s, `robot_4` at 41.9 s (@fig:ch6-ib-backout). The pockets, the cross phase, the release and the crossing order stayed on M3’s ranking, and the model's own `crossing_order` was not used. The configuration after both recedes, and everything after it, is the default's (@fig:ch6-ib-arrived).
- *Constrained selection.* The prompt listed, for each robot, the plan actions the verifier accepts, and only `robot_3` and `robot_4` were offered `reverse`. The model chose among offered actions; it did not compose free motion #ev("6.03").
- *Ascending identifiers.* The model's order is ascending robot id, which under ascending listing cannot be separated from a slot prior (@sec:res-exploratory).
- *One take of five, chosen for its label.* Offline, the same prompt produced such an event in 7 of 27 first triggers #ev("6.03"); that is no rate for the live takes.

#figure(
  image("../assets/images/fig_intersection_robot3_backing_t36p97.png", width: 75%),
  caption: flex-caption([Intersection take 5: `robot_3` backs out first.], [Four-robot intersection, demonstration take 5 (labelled VLM-driven execution), annotated overhead camera frame at simulated time 37.0 s: `robot_3` (green, moving) backs out along its own arm while `robot_1`, `robot_2` and `robot_4` (red, stopped) wait. `robot_4` starts its back-out at 41.9 s. This order is the model's verified plan. The default order (`robot_4` first) differed by 0.010 m in recede cost, so only the timing of the two back-outs changed. Simulation (Isaac Sim), overhead camera; box colours show the perception module's status. Illustrative take, 1 of 5, chosen for its label.#fig-source("6.39")]),
) <fig:ch6-ib-backout>

#figure(
  image("../assets/images/fig_intersection_all_arrived_t154p83.png", width: 75%),
  caption: flex-caption([Intersection take 5: all four robots at their goals.], [Four-robot intersection, demonstration take 5 (labelled VLM-driven execution), annotated overhead camera frame at simulated time 154.8 s: all four robots stopped at their goals on the opposite arms (ground-truth arrivals between 95.1 s and 146.4 s). Simulation (Isaac Sim), overhead camera. Illustrative take, 1 of 5: take 1 was unresolved and takes 2 to 4 were resolved by the default plan.#fig-source("6.39")]),
) <fig:ch6-ib-arrived>

=== Convoy Counterflow <sec:res-demo-convoy>

In the convoy scene, `robot_1` and the counter-flow robot `robot_2` meet nose to nose in the gap between two barrier blocks, while `robot_3` and `robot_4` queue behind `robot_1`. The scene is built so that a first decision which leaves out the queued robots ends in a latch #ev("6.40").

*Takes 1 to 3.* In each of takes 1 to 3 the first decision was a `yield` naming only `robot_1` and `robot_2`, and it was executed as the model named it (@fig:ch6-cv-yield). The queued robots, never commanded, were then released by their own start delay, followed through the gap and latched against the others by about 75 s (@fig:ch6-cv-latched). The 33 later proposals all ran as 8 s waits: grounding refused the yields and reverses, and the other strategies have no template in the legacy grounding this scene used. Offline, 72 of 76 hypothetical decisions on post-latch snapshots also became waits #ev("6.40"). One scripted decision that names all four robots resolved the scene in a smoke run, which shows that the scene can be resolved, nothing more (n = 1, not accepted by the owner) #ev("6.40").

Stating the queued robots' hold-back state in the prompt did not change the first decision offline: in a pre-registered check, 0 of 22 answers per condition grounded into the four-robot sequence, and the primary count was 0 of 18 #ev("6.04").

*Takes 4 and 5.* These takes used a grounding change instead: an M3 key, off by default, that holds unnamed queued robots whose goals lie across the corridor #ev("6.19"). The hold worked as built. The model again named neither `robot_3` nor `robot_4`, and the hold added both and kept them in place, but the model named `robot_1` as the yielder both times. That is the variant the scene is designed to defeat: `robot_2`'s escort west stopped 0.418 m and 0.419 m from the held `robot_3` and latched. One of four robots arrived in each take #ev("6.41"). A resolving convoy take would in any case have been a grounding result, not a VLM one.

#figure(
  image("../assets/images/fig_convoy_first_yield_t38p00.png", width: 75%),
  caption: flex-caption([Convoy take 1: the first yield.], [Convoy counterflow, four robots, demonstration take 1 of 5 (unresolved), annotated overhead camera frame at simulated time 38.0 s: the first yield executes as the model named it. `robot_2` (green) backs out of the gap while `robot_1` waits in it and `robot_3` and `robot_4` stay queued. The decision named only the standoff pair. Simulation (Isaac Sim), overhead camera. Illustrative take, 1 of 5. All five convoy takes ended unresolved: takes 1 to 3 with 0 of 4 arrived, takes 4 and 5, with the queued-robot hold, with 1 of 4.#fig-source("6.40")]),
) <fig:ch6-cv-yield>

#figure(
  image("../assets/images/fig_convoy_latched_t149p90.png", width: 75%),
  caption: flex-caption([Convoy take 1: the latched cluster.], [Convoy counterflow, demonstration take 1 of 5 (unresolved), annotated overhead camera frame at simulated time 149.9 s: the final latched cluster. `robot_3` and `robot_4`, which the first decision did not name, followed `robot_1` through the gap. All four stand stopped east of the gap, two pairs closer than the 0.45 m safety distance, and none moved again from about 75 s to the end at 260 s; 0 of 4 arrived. Simulation (Isaac Sim), overhead camera. Illustrative take, 1 of 5. All five convoy takes ended unresolved: takes 1 to 3 with 0 of 4 arrived, takes 4 and 5, with the queued-robot hold, with 1 of 4.#fig-source("6.41")]),
) <fig:ch6-cv-latched>

=== Head-on With Obstacle <sec:res-demo-headon>

The head-on take ran in the corridor scene of @sec:res-headon with obstacle text and the feasibility gate on #ev("6.37"). The model's first decision, `reverse`, was dispatched as named; the robots separated and then drove back together, and the scene re-triggered. Its second decision was a `yield` with `robot_1` as yielder. `robot_1` had 0.70 m of retreat room against 1.08 m required, so the gate handed the yield to `robot_2` (@fig:ch6-ho-yield), which parked beside the lane while `robot_1` was escorted past (@fig:ch6-ho-pass). Both robots arrived (@fig:ch6-ho-arrived). The resolution is grounder-corrected, not VLM-driven; what the infeasible yield would have done is not shown #ev("6.37").

#figure(
  image("../assets/images/fig_headon_robot2_backing_t70p00.png", width: 75%),
  caption: flex-caption([Head-on take: `robot_2` yields after the gate swap.], [Head-on corridor with obstacle, two robots, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead camera frame at simulated time 70.0 s: `robot_2` (green) backs out east. After a first `reverse` and a second standoff, the model named `robot_1` as the yielder. The feasibility gate replaced it with `robot_2`, because `robot_1` had 0.70 m of retreat room against 1.08 m required. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("6.37")]),
) <fig:ch6-ho-yield>

#figure(
  image("../assets/images/fig_headon_robot2_yield_pass_t99p00.png", width: 75%),
  caption: flex-caption([Head-on take: `robot_1` passes the parked `robot_2`.], [Head-on corridor with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead camera frame at simulated time 99.0 s: `robot_2` is parked at its pull-off point beside the lane (red, stopped) while `robot_1` (green) is escorted past it. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("6.37")]),
) <fig:ch6-ho-pass>

#figure(
  image("../assets/images/fig_headon_both_arrived_t147p93.png", width: 75%),
  caption: flex-caption([Head-on take: both robots at their goals.], [Head-on corridor with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead camera frame at simulated time 147.9 s: both robots stopped at their goals, `robot_2` at the left beside the obstacle and `robot_1` at the right edge of the frame (ground-truth arrivals at 112.5 s and 136.1 s). Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("6.37")]),
) <fig:ch6-ho-arrived>

=== Five Robots <sec:res-demo-five>

The five-robot take ran the S1b pickup-and-delivery scene on seed position 21, an exploratory seed outside the 20 confirmatory seeds that earlier pilots had already used #ev("6.42"). It is a limitation demonstration. The first two decisions were executed as the model named them: in decision 1 `robot_1` yielded and `robot_4` passed (@fig:ch6-m5-start, @fig:ch6-m5-after1); in decision 2 `robot_2` yielded and `robot_3` was escorted. The six later proposals were all refused by grounding checks and withheld: no feasible yielder four times, no declared junction once and no shared lane once. No analysis ran after sim 275.5 s, and one of five robots arrived #ev("6.42"). The pattern matches the recorded S1b analyses of the earlier live episodes, where deterministic M3 refusals withheld 47 of 78 analyses and the model is not told that a decision was withheld #ev("6.15").

Decision 2's escort drove `robot_3` along a straight segment that crossed rack island `obstacle_2`. `robot_3` stopped against the island's east face at 146.9 s and stayed within 5 mm of it in 4526 of 4534 ground-truth rows to the end of the run, while the escort ran on until it failed on its deadline (@fig:ch6-m5-escort) #ev("6.42"). This is a sustained robot-obstacle contact, confirmed from ground-truth poses, the URDF collision box, the scene builder and the recording. The "unresolved" label therefore partly reflects an escort path error, not only the model's decisions or the grounding refusals #ev("6.42").

#figure(
  image("../assets/images/fig_fiverobot_standoff_t43p67.png", width: 75%),
  caption: flex-caption([Five-robot take: the first standoff.], [Five-robot pickup-and-delivery scene (S1b, seed position 21, an exploratory seed outside the 20 confirmatory seeds), demonstration take 1 of 1 (unresolved; a limitation demonstration), annotated overhead camera frame at simulated time 43.7 s. Two rack islands; `robot_1` and `robot_4` meet head-on at the bottom (yellow, slow), and the other three are moving. Before the first decision. The start assignment differs from @fig:ch5-s1b. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("6.42")]),
) <fig:ch6-m5-start>

#figure(
  image("../assets/images/fig_fiverobot_after_decision1_t101p40.png", width: 75%),
  caption: flex-caption([Five-robot take: after the first decision.], [Five robots, seed position 21, demonstration take 1 of 1 (unresolved), annotated overhead camera frame at simulated time 101.4 s, after decision 1. That decision was executed as the model named it: `robot_1` yielded and `robot_4` passed, and both now stand at the left edge. `robot_2` and `robot_3` are stopped beside the east island, the conflict of decision 2. Of eight decisions in this take, two were executed and six were withheld by grounding refusals; 1 of 5 robots arrived. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("6.42")]),
) <fig:ch6-m5-after1>

#figure(
  image("../assets/images/fig_fiverobot_robot3_island_t147p30.png", width: 75%),
  caption: flex-caption([Five-robot take: an escort drives `robot_3` into a rack island.], [Five robots, seed position 21, demonstration take 1 of 1 (unresolved), annotated overhead camera frame at simulated time 147.3 s: `robot_3` against the east face of rack island `obstacle_2`. The straight escort segment of decision 2 drove it there; no stage checked that segment against static obstacles. The box is the perception module's last track of `robot_3` before the island's edge hid its marker, so its colour and arrow do not show motion. The contact rests on ground-truth poses (stopped at 146.9 s; within 5 mm of the face in 4526 of 4534 ground-truth rows to the end of the run), not on this image. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("6.42")]),
) <fig:ch6-m5-escort>

== Safety Findings <sec:res-safety>

*What was measured.* The simulator's two ground-truth contact lists were hard-coded empty in the evaluated runtime, so every zero read from them shows nothing #ev("6.20"). The safety evidence is the GT centre distance between robot pairs; an offline geometric recompute of footprint gaps is listed, pending validation, in @tab:app-contacts. @tab:res-safety summarises the evidence per cell.

#figure(
  table(
    columns: (1fr, 1.2fr, 0.5fr, 1.8fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Cell*], [*Lowest GT robot-pair centre distance*], [*Floor stops*], [*Robot-obstacle contact: measurement status*]),
    [IB10 run 1], [A 0.2633 m; B 0.2856 m], [0], [scene declares no obstacles; rack blocks and walls not logged; offline recompute pending validation],
    [IB10 run 2], [A 0.3008 m; C 0.2965 m], [0], [as run 1],
    [prereg-v3 tranche 1], [0.225–0.424 m over all ten episodes], [0], [not covered by the registered gate; offline recompute pending validation],
    [Demonstration campaign], [lowest 0.2176 m (head-on take, before any command); convoy takes 4 and 5: 0.276 m and 0.370 m], [0], [one sustained contact confirmed (five-robot escort, @fig:ch6-m5-escort); otherwise offline recompute pending validation],
    [Validation take (n = 1)], [—], [—], [contact fields logged on all 6001 rows and reproduced offline; partially validated],
  ),
  caption: flex-caption([Safety evidence per cell and its measurement status.], [Safety evidence per cell: robot-pair centre distance from ground truth, floor stops in M4’s log, and the status of robot-obstacle contact measurement. The 0.20 m floor and the 0.18 m gate threshold are on centre distance.#fig-source("6.20")]),
) <tab:res-safety>

The robot-pair values come from the cells' own reports #ev("6.05") #ev("6.06") #ev("6.14") #ev("6.37") #ev("6.41"). In most IB10 and campaign episodes the lowest pair distance was reached during the standoff or jam, before any command; run 1's e09 #ev("6.31"), run 2's smoke episode #ev("6.32") and convoy take 5 #ev("6.41") are exceptions. No take of the campaign logged a floor stop #ev("6.39") #ev("6.40") #ev("6.42").

*Contact with obstacles.* One sustained robot-obstacle contact is confirmed: the five-robot escort described in @sec:res-demo-five #ev("6.42"). It exposed a gap in grounding. M3 checked neither escort segments nor `reverse` legs against static obstacles; only the yielder's retreat room and its retreat candidates use the declared boxes, and neither M4’s heading primitive nor its safety monitor looks at obstacles #ev("6.43"). A later validation take came within 5.5 mm of a declared box under a `reverse`, which M3 does not sweep against declared boxes #ev("6.17"), and earlier `reverse` legs in October had pinned robots against box faces until their deadline #ev("6.18").

*Offline contact recompute.* A geometric logger places the URDF collision shapes at each logged pose and measures the planar gap to every box and to every other robot. It was run offline over 44 recorded bundles; its per-bundle values are in @tab:app-contacts and are not used as safety evidence until validated #ev("6.12"). These figures are a footprint proximity at 10 Hz, not a physics contact, and they remain pending validation. The validation take confirmed that the new contact fields are written on every row and reproduced offline, but no robot was pinned during it, so it does not show that entries appear when one is #ev("6.17").

*Safety-exemption fix.* A coordination command exempts its robots from each other in M4’s proximity check, and that exemption proved wider than intended (@sec:design-safety). A fix behind a key that is off by default narrows it (@tab:res-sx) #ev("6.50"). It was tested with 64 unit tests and a replay over 68 recorded bundles: with the key off every timeline is identical, and with the key on 6 exemptions are lost #ev("6.07"). It was on in IB10 run 2, where it never fired #ev("6.06"), and in the demonstration takes, where the registration required it on M4's start-up line and its firings were not counted #ev("5.51"). It is therefore not validated live.

#figure(
  table(
    columns: (1.4fr, 1.2fr, 1.4fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Exemption path*], [*Key off (evaluated runtime)*], [*Key on*]),
    [Robots the plan marks `continue` (P1)], [exempt, also in other clusters], [not honoured],
    [A leg rejected before it started (P3)], [still a member, still exempt], [not a partner],
    [Bystander waiver at command start (A19)], [unhonoured partner counts as own], [both count as third robots; the waiver ends once the gap closes by more than 0.05 m on 3 readings],
    [Mutual waivers (P4), own-command scope (P5)], [unchanged], [unchanged],
  ),
  caption: flex-caption([What the safety-exemption key changes.], [Behaviour of M4’s coordination exemption with the scoped-exemption key off and on. Unit tests and offline replay; on in IB10 run 2 (never fired) and in the demonstration takes (firings not counted); not validated live.#fig-source("6.50")]),
) <tab:res-sx>

*Guards built after the campaign.* Three further checks were built, each off by default:

- *Escort obstacle guard* (M3): refuses an escort whose straight segment crosses a declared obstacle. Offline it refuses the five-robot escort and one earlier escort and leaves every other campaign escort unchanged. It sees declared obstacles only and has no M4 backstop #ev("6.13"). Live, it ran once, in the validation take: armed and harmless, but it never fired, because no escort was grounded #ev("6.17").
- *Stall abort* (M4): cancels a primitive whose commanded motion produces no measured movement and safe-stops the robot. It has unit and node tests and an offline replay over 221 recorded primitives, and no live run #ev("6.18").
- *Queued-robot hold* (M3): used only in convoy takes 4 and 5, where it held the queued robots as built (@sec:res-demo-convoy) #ev("6.19").

No comprehensive obstacle-safety claim follows from these checks.

== v4 Offline Bench and Stage 1 Shadow <sec:res-bench>

The v4 bench replays recorded S1b analyses at the decision level, text only, and is never pooled with prereg-v3 (@sec:ch5-bench) #ev("1.06") #ev("5.36"). Its last variant, per-cluster choice, asks for one answer per observed conflict group. On the 137 recorded positives it raised cluster coverage from 0.496 to 0.832 for ER-2 and from 0.620 to 0.934 for Sonnet 5.5, against the grounding-first prompt of the previous version, and every chosen option was feasible for M3 (168 of 168 and 181 of 181) #ev("6.46"). A chooser that takes the first listed option in every group reached a coverage of 0.949. That option order is itself the generator's geometric heuristic #ev("5.41"). On involvement the models match, and do not beat, this default ordering #ev("6.46"). The gain is the format's, not the models' choosing, and it is shown only without vision.

The Stage 1 live shadow ran the per-cluster call beside the ordinary loop in 7 episodes on seed positions 21 to 27, and never dispatched its answer #ev("1.11") #ev("5.42"). All 50 shadow blocks were valid, 12 analyses had more than one group, and none of the joint-feasibility flags fired in those 12. The ordinary loop in the same analyses dispatched 14, withheld 33 and had no decision in 3 #ev("6.47"). The shadow shows that the per-group path runs live; it does not show that per-group dispatch would resolve anything.

== Exploratory Findings <sec:res-exploratory>

*Presentation order.* In pilot probes, the robot gpt-4o named to yield followed the robot listed first in the prompt; under ascending listing that is also the lowest identifier, so the two priors are confounded. This led v1 amendment A2 to randomise the order #ev("1.12"). The later live cells nevertheless listed robots in ascending order #ev("1.15"). The offline swapped-identifier replay separates the two for gpt-4o: it followed the first-listed slot in 85 of 96 grey-pair yields #ev("6.09"). The head-on re-score finds a `robot_1` preference for both gpt-4o and ER-2 (@tab:res-headon) #ev("6.08"). The recede order of intersection take 5 is again ascending #ev("6.39"). No live result reported here can separate an identifier prior from a slot prior.

*Model refusals.* Refusals depend on the model and the prompt. An earlier offline replay of recorded gpt-4o analyses found that its refusals were triggered by the real camera frame rather than by the prompt text, and that the annotation overlay itself was not the trigger; this motivated the grey-image fallback after two refused attempts #ev("4.37"). Sonnet 5.5 refused 30 of 48 real-frame runs under the original prompt ending #ev("6.09"), and none of 146 under a JSON-only ending #ev("6.11"). ER-2 returned a valid answer in every analysis of the demonstration campaign #ev("6.44").

== Physical Demonstration <sec:res-physical>

The physical demonstration of 12 November 2026 ran the perception, reasoning, grounding and dispatch chain on TurtleBot3 robots under an overhead camera, with a different model (`gemini-3.1-flash-lite`) from the simulation experiments #ev("1.07") #ev("4.28"). In all four staged arrangements the model chose `reverse` #ev("6.48"):

- *A,* two simultaneous head-on pairs: deadlock, `reverse`, 4/4 commands completed;
- *C,* a three-robot triangle with a fourth robot outside it: deadlock, `reverse`, 3/3 completed;
- *D,* four robots facing a shared central region: crowding, `reverse`, 4/4 completed;
- *E,* a tighter dual-lane variant of A: deadlock, `reverse`, 3 completed and robot 3 failed.

Two attempts whose reply could not be parsed are excluded #ev("4.31"). The robots had no navigation goals, so "completed" means that the reverse command finished on the robot, not that a conflict was resolved toward task progress #ev("4.29"). One run per arrangement was recorded, and the code that ran is not in this repository's history (@sec:impl-physical). The demonstration shows that the chain runs end to end on real hardware; it is not an evaluation.
