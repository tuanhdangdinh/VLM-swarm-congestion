#import "../lib.typ": *
#import "../figures/vlm-flow-take5-simple.typ": vlm-flow-simple-figure

= Results <sec:res>

This chapter reports what the studies of Chapter 5 found. Each result carries the evidence grade given in @tab:ch5-studies (exploratory pilot, registered pilot, decision-level offline, or illustrative demonstration), and nothing is pooled across studies or between the two intersection runs #ev("6.16"). The coordination layer (Layer 2) is the slow loop that detects a stall, asks the VLM, and passes the decision to the grounder (M3), which turns it into commands. Safety evidence throughout is the ground-truth (GT) robot-pair centre distance, because the simulator's contact lists were hard-coded empty in the evaluated runtime #ev("6.20") (@sec:res-safety).

== Intersection Run 1: Coordination Layer On vs Off <sec:res-ib10-ab>

Intersection run 1 (13 November 2026) compared the full pipeline with Gemini Robotics-ER 2 (ER-2) against the coordination layer switched off, on the four-robot intersection, five counted episodes per arm #ev("6.05").

#figure(
  table(
    columns: (1.1fr, 1.4fr, 1.1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Measure*], [*Coordination layer on (ER-2)*], [*Coordination layer off*]),
    [Counted episodes], [5], [5],
    [Resolved], [4/5], [0/5],
    [Arrivals], [16/20], [0/20],
    [Time from onset to last arrival], [112.9, 115.5, 116.5, 116.6 s; e09 censored], [all five censored at the horizon],
    [Lowest GT robot-pair centre distance], [0.2633 m (e09)], [0.2856 m],
    [Floor stops], [0], [0],
    [Plan-audit labels of the dispatches], [repaired 4, grounder default 1, accepted unchanged 0], [no dispatch],
  ),
  caption: flex-caption([Intersection run 1: coordination layer on against off.], [Intersection run 1 (13 Nov 2026), coordination layer on against off, five counted episodes per arm (slots e01 to e10). Exploratory pilot; the episodes are near-repeats, so no p-value or interval is given.#fig-source("6.05")]),
) <tab:res-ib10-ab>

With the layer off the four robots stopped at jam formation and never moved again, a latch baseline rather than a classical coordinator; the excluded first attempt of slot e01 (a harness failure in the condition gate) also resolved, on the grounder default #ev("6.30"). The unresolved episode, e09, began off-pattern: the model answered `yield`, then a two-robot `junction_clear`, after which all four robots stood still for 120.1 s; its third plan named two robots twice and was nulled, and the grounder's default plan had not finished by the horizon. The run's lowest pair distance, 0.2633 m, occurred in e09 inside a pair that the command still exempted #ev("6.31").

No dispatched plan was accepted unchanged, and re-grounding every repaired decision without its plan reproduces the recorded commands, so the grounder's default ran in all four resolved episodes #ev("6.05") #ev("6.02"). *Caveat:* the run supports a claim about the pipeline (trigger, grounding and phased dispatch), not about the model's plan, and it is five near-repeat episodes per arm on one scene.

== Intersection Run 2: Live VLM vs Scripted Default Plan <sec:res-ib10-c>

Intersection run 2 (14 November 2026), never pooled with run 1, compared the live-VLM arm with a scripted default-plan arm that skips the VLM call and hands the grounder `junction_clear` for all four robots, so that it runs its own default plan; the safety-exemption fix was on #ev("6.06").

#figure(
  table(
    columns: (1.1fr, 1.1fr, 1.1fr, 1.1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Measure*], [*Live VLM (ER-2)*], [*Scripted, before the re-run*], [*Scripted, after the re-run*]),
    [Valid episodes], [5], [4 (e02 formed no jam)], [5 (e02 a2 counted)],
    [Resolved], [5/5 (4/4 without the first check episode)], [4/4], [5/5],
    [Arrivals], [20/20], [16/16], [20/20],
    [Time from onset (s)], [114.3, 115.7, 116.2, 116.7, 116.9; mean 115.96], [115.5, 118.5, 118.6, 118.6; mean 117.80], [115.5, 118.1, 118.5, 118.6, 118.6; mean 117.86],
    [Lowest GT robot-pair centre distance], [0.3008 m], [0.2965 m], [0.2965 m],
    [Floor stops], [0], [0], [0],
    [Plan-audit labels], [repaired 4, grounder default 1], [grounder default], [grounder default],
  ),
  caption: flex-caption([Intersection run 2: live VLM against the scripted default plan.], [Intersection run 2 (14 Nov 2026), live-VLM arm against the scripted default-plan arm, shown before and after the post hoc re-run of slot e02. Exploratory pilot; never pooled with run 1.#fig-source("6.06")]),
) <tab:res-ib10-c>

Scripted slot e02 formed no jam (map server never activated) and was excluded under the invalid-jam rule. The live-VLM arm is 5 of 5 counting its first check episode and 4 of 4 without it, because that episode's acceptance was written under a conditional instruction rather than by the owner #ev("6.32"). The re-run of e02, decided after the results were seen and registered before it ran, resolved in 118.1 s #ev("6.34").

Every live-VLM first dispatch re-grounds to exactly the plan the scripted arm executed, apart from dispatch time, a degradation tag, small snapshot-dependent distances and, twice, the retreat side #ev("6.06"). The scripted arm dispatches about 3.4 s later (it answers the first trigger with "no congestion"), so times are not strictly comparable #ev("6.33"); the safety-exemption fix never fired. The arms are indistinguishable in outcome: the trigger plus the grounder's default plan clears this jam, and the model's remaining role is the strategy and robot set, which the scripted arm was given #ev("6.06"). *Caveat:* the scripted arm cannot re-plan after a failure, so the run does not show that the model is useless; across both runs, e09 of run 1 is the one case where an off-pattern model choice changed what ran, and it did not resolve #ev("6.31").

== Registered Five-Robot Pilot <sec:res-t1>

The registered five-robot pilot (21 October 2026) ran five seed pairs on the five-robot pickup-and-delivery scene, coordination layer on and off, interleaved and counterbalanced as registered #ev("6.14"). It was registered as confirmatory and is reported as a pilot, because only 5 of the 20 planned seed pairs ran.

#figure(
  table(
    columns: (1.4fr, 0.8fr, 0.8fr, 1.4fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Measure*], [*On*], [*Off*], [*Difference on − off, bootstrap interval*]),
    [Complete episodes], [0/5], [0/5], [both arms censored at the horizon],
    [Tasks completed], [16/125], [12/125], [],
    [Tasks per seed (positions 1 to 5)], [8, 2, 0, 5, 1], [5, 1, 0, 6, 0], [],
    [Throughput at the common window], [0.128], [0.096], [+0.032 [−0.008, +0.080]],
    [Restricted makespan], [569.88 s], [569.88 s], [0.0 [0.0, 0.0]],
    [Mean delay lower bound], [323.4 s], [354.9 s], [−31.5 s [−71.6, −0.6]],
    [Detection recall], [0.818 (9 of 11 conflicts)], [0 of 10 (no analyses)], [degenerate for off],
    [Type accuracy; involved-set F1], [0.778; 0.915], [n/a], [degenerate for off],
    [False positives], [0 in 26 positive analyses], [n/a], [],
    [Analyses dispatched / withheld per seed], [5/4, 2/2, 2/3, 1/4, 2/1], [n/a], [],
    [Robot-pair gate (GT centre distance ≥ 0.18 m, no floor stop)], [PASS 5/5], [PASS 5/5], [GT minimum 0.225–0.424 m over all ten],
  ),
  caption: flex-caption([Registered five-robot pilot: registered measures.], [Registered five-robot pilot (21 Oct 2026), coordination layer on and off, five seed pairs. The interval is the registered paired percentile bootstrap over seed pairs; no direction was registered. Dispatched and withheld counts are corrected against the M4 command log. Registered pilot.#fig-source("6.14")]),
) <tab:res-t1>

No episode completed all 25 tasks, so completeness is "failed" and makespan is censored in all ten #ev("6.35"). The throughput interval includes zero; the delay interval excludes it by 0.6 s, on-arm lower #ev("6.14"). With the layer on, 9 of 11 GT conflicts were detected with a mean latency of 17.6 s, and none of 26 positive analyses was a false positive #ev("6.35"). The source report counted a refused yield, which degrades to a wait, as dispatched; the table's per-seed counts are corrected against the commands M4 received #ev("6.14"). An offline recomputation beside the registered results finds 1 of the 2 recorded accepted-unchanged plans dispatched as written; in the other a `reroute` rerouted a different robot than the plan named #ev("6.51"). *Caveat:* five pairs, every episode censored and no registered direction, so these are interval estimates for this scene only, not a test; the robot-pair gate does not cover the rack islands.

== Failure Causes of the Five-Robot Episodes <sec:res-failure-causes>

#[
#show figure.where(kind: table): set block(breakable: true)
#set par(justify: false)

This post hoc classification (@sec:ch5-failure-cause) covers 33 episodes in strata that are never pooled: the registered pilot (10), the exploratory five-robot pilots of October 2026 (21, split into those that ran to the horizon and those the pilots' early-stop rule ended) and two November takes. It explains outcomes reported elsewhere without changing them; the registered pilot's 0 of 10 complete stands #ev("6.14"). The two raters coded the same 55 failure units and listed the same 3 robots that had finished their tasks and are not units #ev("6.63").

#figure(
  table(
    columns: (1.7fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Primary cause*], [*Registered pilot, on*], [*Registered pilot, off*], [*Exploratory pilots, horizon*], [*Exploratory pilots, early stop*], [*November takes*]),
    table.cell(colspan: 6, fill: luma(245))[*Primary cause, failure units (episodes whose episode-level primary cause is this class)*],
    [Decision (V)], [2 (0)], [n/a by construction], [5 (2)], [0 (0)], [2 (1)],
    [Grounding and verification (G)], [1 (1)], [n/a by construction], [4 (1)], [3 (2)], [0 (0)],
    [Execution (X)], [3 (2)], [0 (0)], [7 (4)], [1 (1)], [0 (0)],
    [Environment geometry (EG)], [0 (0)], [0 (0)], [0 (0)], [0 (0)], [0 (0)],
    [Undetermined (U)], [2 (2)], [10 (5)], [9 (8)], [4 (3)], [2 (1)],
    [*All failure units*], [8 (5)], [10 (5)], [25 (15)], [8 (6)], [4 (2)],
    [Parked robots excluded, not units], [2], [1], [0], [0], [0],
    table.cell(colspan: 6, fill: luma(245))[*Contributing causes, failure units carrying the code (never summed with the primary counts)*],
    [Decision (V)], [4], [n/a by construction], [13], [7], [3],
    [Grounding and verification (G)], [5], [n/a by construction], [20], [7], [3],
    [Execution (X)], [5], [0], [22], [8], [4],
    [Environment geometry (EG)], [0], [0], [5], [0], [0],
    table.cell(colspan: 6, fill: luma(245))[*Sensitivity analyses, failure units whose primary cause changes*],
    [Persistent-state link], [not re-rated], [n/a, nothing dispatched], [not re-rated], [not re-rated], [not re-rated],
    [Start-inside rule], [0], [0], [0], [0], [0],
  ),
  caption: flex-caption([Primary and contributing causes of failure units, by stratum.], [Primary and contributing causes of the failure units of the five-robot episodes, by stratum; strata are never pooled. Brackets: episodes whose episode-level primary cause is the class (total row: episodes with a unit). With the layer off, decision and grounding are not applicable and every unit carries the context code N0. Contributing codes are those both raters recorded; the geometry ones are undeclared obstacles meeting a robot (offline contact recompute). The persistent-state link relinks one November unit, which would need a new rating. Exploratory, post hoc, two raters.#fig-source("6.63")]),
) <tab:ch6-fc-primary>

#figure(
  table(
    columns: (1.6fr, 0.8fr, 1fr, 0.9fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Stratum*], [*Units rated*], [*Raw agreement, primary class*], [*Cohen's kappa, primary class*], [*Raw agreement, full code*], [*Disagreements*], [*Disagreements left undetermined*]),
    [Registered pilot, on], [8], [0.875], [0.830], [0.875], [1], [0],
    [Registered pilot, off], [10], [1.000], [n/a], [1.000], [0], [0],
    [Exploratory pilots, horizon], [25], [1.000], [1.000], [0.880], [3], [2],
    [Exploratory pilots, early stop], [8], [0.875], [0.800], [0.875], [1], [0],
    [November takes], [4], [1.000], [1.000], [1.000], [0], [0],
    [All strata (agreement statistic only; no outcome is pooled)], [55], [0.964], [0.948], [0.909], [5], [2],
  ),
  caption: flex-caption([Agreement between the two raters, by stratum.], [Agreement between the two independent raters before reconciliation, on each rater's final codes (second round for the 34 units in its scope, first round otherwise). Kappa is n/a where undefined (with the layer off every unit falls in one code). Disagreements are counted on the full code; the last column gives those reconciled as undetermined. A measure of rating quality only.#fig-source("6.63")]),
) <tab:ch6-fc-agree>

*No dominant cause.* In the registered pilot's on arm and in the exploratory pilots taken together, the two raters' own codes put different classes first (execution against decision; execution against grounding), and after reconciliation the determined units of both spread over execution, decision and grounding (@tab:ch6-fc-primary); the two determined November units, both decision, are too few to be a finding #ev("6.63").

*Undetermined units.* 27 of the 55 units are undetermined, for three reasons. In 15 the recorded command could not be reproduced from the inputs the rule lists (5 at the onset, 10 at the decision where the walk starts). The 10 off-arm units have no anchor placing the execution log on the simulation clock, because nothing was dispatched, and a mapping built for them failed its pre-declared acceptance test; so the two arms are not compared on cause codes. In 2 pilot units the raters chose different grounding codes that the rule's tie order does not separate #ev("6.63") #ev("6.65").

*Agreement.* The final codes agreed on the class for 53 of 55 units (kappa 0.948), on the full code for 50 of 55 (kappa 0.895) and on determinedness for all 55 (@tab:ch6-fc-agree); in the first round, before the second round supplied missing evidence, on 35 of 55 (kappa 0.507) and 32 of 55 (kappa 0.551), with 18 of 23 disagreements from opposite handling of a decision with no counterfactual row. Of the 5 final disagreements, 3 were settled by one reader's ruling and 2 left undetermined #ev("6.63") #ev("6.65"). One ruling, on where an execution code sits in time, decides two units; left open, the on arm would read 2 execution, 2 decision, 1 grounding and 3 undetermined, and the horizon pilots 6 execution and 10 undetermined #ev("6.63").

*Sensitivity analyses* (beside, never replacing, the primary coding). The persistent-state link gives one November unit an extra linked escort after which its robot stayed within 0.05 m of a box until onset. Under the start-inside rule the straight-move test changes at 4 of 233 snapshots and no primary changes. With extra recorded inputs (stored second-stage label, rebuilt task intents) only 2 units stay not reproducible and 13 change code (2 on, 5 and 4 in the horizon and early-stop pilots, 2 November); the classes become 4 execution, 2 decision, 2 grounding on; 9 execution, 5 decision, 4 grounding, 7 undetermined in the horizon pilots; 5 grounding, 2 execution, 1 decision in the early-stop pilots; 3 decision, 1 undetermined in the November takes #ev("6.63") #ev("6.65").

*Interception.* This analysis asks what the escort obstacle guard, the reverse obstacle guard and the stall abort would have refused or aborted among the 57 escort and reverse legs dispatched in 25 of the 28 coordination-layer-on episodes (the other three dispatched only waits; @tab:ch6-fc-intercept-a, @tab:ch6-fc-intercept-p, @tab:ch6-fc-intercept-n). For 25 of the 45 coordination-layer-on units no escort or reverse leg is linked, so the mechanisms do not apply #ev("6.63"). In the pilots the reverse guard's false-positive share is high (15 of the 29 legs it would refuse completed clear of every declared box, one of them within 0.015 m of another robot), and only 18 of the 29 were blocked themselves, because the guard refuses a whole command. The stall abort would have ended its 7 pilot legs 9.1 to 20.9 simulated seconds after start; one, an escort pushing a parked robot, is invisible to the guards. Nine failed pilot legs escape every mechanism: seven escorts that never moved and two that failed while the proximity latch held the robot. The November reverse-guard refusals came at box gaps of 5.5 mm and 19 mm #ev("6.63") #ev("6.13") #ev("6.18").

#let intercept-header = table.header([*Mechanism*], [*Legs refused or aborted*], [*Justified*], [*False positive*], [*Untested*], [*Units with such a linked leg*], [*Same, persistent-state link*])

#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    intercept-header,
    [Dispatched escort and reverse legs], [3], [n/a], [n/a], [n/a], [n/a], [n/a],
    [Escort obstacle guard (refuses)], [0], [0], [0], [0], [0], [0],
    [Reverse obstacle guard (refuses)], [0], [0], [0], [0], [0], [0],
    [Stall abort (aborts)], [0], [0], [0], [n/a], [0], [0],
    [Any of the three], [0], [0], [0], [0], [0], [0],
    [*No mechanism applies*], [n/a], [n/a], [n/a], [n/a], [8], [8],
    [#h(1em)no linked leg], [n/a], [n/a], [n/a], [n/a], [5], [5],
    [#h(1em)linked leg, none intercepted], [n/a], [n/a], [n/a], [n/a], [3], [3],
    [*All failure units*], [n/a], [n/a], [n/a], [n/a], [8], [8],
  ),
  caption: flex-caption([Interception analysis, registered pilot, coordination layer on.], [Interception analysis, registered pilot, coordination layer on: what three mechanisms written after the pinned runtime would have refused or aborted, and how many failure units have such a leg linked. Rows overlap; "any" is not their sum. Justified: contact, pinned or within the 0.05 m margin; false positive: completed at or above the margin; untested: did not complete, stayed at or above it (undefined for the stall abort). Not a resolution count. The off arm dispatched nothing. All 3 legs were escorts that completed at 0.16 m or more from the boxes.#fig-source("6.63")]),
) <tab:ch6-fc-intercept-a>

#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    intercept-header,
    [Dispatched escort and reverse legs], [47], [n/a], [n/a], [n/a], [n/a], [n/a],
    [Escort obstacle guard (refuses)], [1], [0], [0], [1], [0], [0],
    [Reverse obstacle guard (refuses)], [29], [9], [15], [5], [8], [8],
    [Stall abort (aborts)], [7], [7], [0], [n/a], [4], [4],
    [Any of the three], [31], [10], [15], [6], [9], [9],
    [*No mechanism applies*], [n/a], [n/a], [n/a], [n/a], [24], [24],
    [#h(1em)no linked leg], [n/a], [n/a], [n/a], [n/a], [19], [19],
    [#h(1em)linked leg, none intercepted], [n/a], [n/a], [n/a], [n/a], [5], [5],
    [*All failure units*], [n/a], [n/a], [n/a], [n/a], [33], [33],
  ),
  caption: flex-caption([Interception analysis, exploratory five-robot pilots.], [Interception analysis, exploratory five-robot pilots (ER-2); columns and terms as in @tab:ch6-fc-intercept-a.#fig-source("6.63")]),
) <tab:ch6-fc-intercept-p>

#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    intercept-header,
    [Dispatched escort and reverse legs], [7], [n/a], [n/a], [n/a], [n/a], [n/a],
    [Escort obstacle guard (refuses)], [1], [1], [0], [0], [0], [1],
    [Reverse obstacle guard (refuses)], [2], [2], [0], [0], [1], [1],
    [Stall abort (aborts)], [1], [1], [0], [n/a], [0], [1],
    [Any of the three], [3], [3], [0], [0], [1], [2],
    [*No mechanism applies*], [n/a], [n/a], [n/a], [n/a], [3], [2],
    [#h(1em)no linked leg], [n/a], [n/a], [n/a], [n/a], [1], [0],
    [#h(1em)linked leg, none intercepted], [n/a], [n/a], [n/a], [n/a], [2], [2],
    [*All failure units*], [n/a], [n/a], [n/a], [n/a], [4], [4],
  ),
  caption: flex-caption([Interception analysis, November takes.], [Interception analysis, November takes; columns and terms as in @tab:ch6-fc-intercept-a.#fig-source("6.63")]),
) <tab:ch6-fc-intercept-n>

*Caveats for every table of this section.*

- *Interception is not resolution.* A refused reverse becomes a short wait, which changes every later state; only new live runs can show resolution.
- *Validation state.* None of the three mechanisms has fired live (@sec:res-safety); the reverse guard has false positives at square box corners and declared walls spanning open arms, the stall-abort replay reconstructs command streams, and the plan-dispatch visibility logging is offline only #ev("6.13") #ev("6.18") #ev("6.12") #ev("6.17") #ev("6.51").
- *Structural zeros.* The first geometry code and the missing-strategy code fire only when no hypothetical decision grounds to motion at the onset, which holds at none of the 58 onset snapshots, so the 0 in environment geometry is a property of the rule #ev("6.61") #ev("6.63"); one decision code never fired for a similar reason #ev("6.63").
- *Rule limits.* Only commands dispatched within 60 simulated seconds before the onset, or executing at it, are linked; both raters' codes are kept beside the single reader's rulings, for recomputation #ev("6.63").
- *Blinding was not clean.* The rule's authors had read earlier diagnoses of some episodes #ev("6.60") #ev("6.61"); both raters read a worked example meant to be withheld, some sheets were identifiable, events sheets were seen early, and the second round was designed after the first-round codes #ev("6.63") #ev("6.65").
- *Evidence and scope.* October contacts are offline 10 Hz footprint recomputations #ev("6.12"); the guards see declared boxes only #ev("6.13") #ev("6.63"); the strata are small, no test is registered, and no outcome record was changed #ev("6.63").
]

== Head-on Yielder Choice <sec:res-headon>

In the two-robot head-on corridor with obstacle, only one robot has room to back out. A post hoc, decision-level re-score covered every recorded live analysis of the head-on scene family, first positive analysis per run #ev("6.08"); the correct yielder is `robot_2` in the west variants and `robot_1` in the east ones #ev("6.36").

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
  caption: flex-caption([Head-on yielder: model against trivial baselines.], [Head-on scene family, yielder correct at run level, against always naming `robot_1` and the scene manifest's first-come-first-served label. Post hoc, decision-level re-score of recorded live decisions; not pre-registered.#fig-source("6.08")]),
) <tab:res-headon>

In no row does the model beat the better baseline #ev("6.36"); its east-side edge over the manifest rule is its `robot_1` preference meeting a variant where `robot_1` is correct. With the yield feasibility gate in `swap` mode the grounded yielder was correct in 79 of 79 runs, and in 37 the gate overturned the model's pick #ev("6.08"); that column comes from artefact fields, not M4 logs, and the gate was off at the intersection #ev("6.49"). In one earlier recorded head-on run (30 September 2026, older code), selected because it qualifies, the gate kept the model's yielder `robot_2` and it was executed, arriving only after about 22 sim-s of navigation stall and recovery (@fig:ch6-er2live) #ev("6.38"); in the campaign's head-on take the gate swapped an infeasible yielder (@sec:res-demo-headon) #ev("6.37").

Three offline replays asked whether a model chooses the yielder from the scene rather than from labels or listing order (first decision only, nothing executed, never pooled with live data).

#figure(
  table(
    columns: (1fr, 0.8fr, 2.2fr, 1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Replay*], [*Model*], [*Result*], [*Verdict*]),
    [Swapped-ID replay (pre-registered)], [gpt-4o], [follows the first-listed slot in 85 of 96 grey-pair yields], [scene-use rule not met],
    [], [ER-2], [answers `reverse` in 129 of 144 runs in the label-swap arms], [scene-use rule not met],
    [], [Sonnet 5.5], [refused 30 of 48 real-frame runs], [not assessable],
    [JSON-only replay (pre-registered)], [Sonnet 5.5], [146 of 146 answered, 0 refusals; 46 of 96 correct in the grey pair; names `robot_2` in 76 of 96], [scene use not supported],
    [], [ER-2], [50 of 96 runs completed (provider limit)], [not assessable],
    [Improved-annotation replay], [ER-2, gpt-4o], [stopped by provider limits before completion], [every verdict not assessable],
  ),
  caption: flex-caption([Offline replays on yielder choice and scene use.], [Offline replays of the yielder choice on the head-on scene family, two robots, first decision only. Small, decision-level, never pooled with live data.#fig-source("6.09")]),
) <tab:res-replay>

No tested model met the pre-registered scene-use rule #ev("6.09") #ev("6.11"). The improved-annotation replay leaves only a lead: with legible labels plus a neutral sentence that a backing robot needs free floor behind it, ER-2 named the correct robot in 55 of 67 runs, against 11 of 64 with labels alone, and the sentence did not move the grey control (7 of 66 against 8 of 67) #ev("6.10"). *Caveat:* decision-level and post hoc or offline; the lead is not evidence that the model uses the image.

== Plan Influence <sec:res-plan>

The plan-audit label (provenance) records how an audited plan relates to the model's proposal. A trace of every live four-robot congestion analysis asked whether the plan changed the commands M4 received #ev("6.02").

#figure(
  table(
    columns: (1.6fr, 1fr, 0.8fr, 0.7fr, 0.7fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Level*], [*Intersection, ER-2 (24)*], [*Earlier gpt-4o pilot (13)*], [*Two head-on pairs, ER-2 (4)*], [*All (41)*]),
    [1. Valid response], [24], [13], [4], [41],
    [2. Plan accepted unchanged], [2 (0 of 20 `junction_clear`)], [11], [1], [14],
    [2. Accepted and dispatched as written], [2], [6], [0], [8],
    [3. Plan changed execution against no plan (gated)], [0 of 22], [0 of 13], [0 of 4], [0 of 39],
    [Decision fields changed execution against the grounder default (gated)], [5], [13], [n/a], [18, in 4 episodes],
  ),
  caption: flex-caption([Plan influence in live four-robot analyses.], [Three-level classification of the 41 live four-robot congestion analyses; 39 pass the trace's fidelity gate. Decision-level trace with verified and inferred labels, on the evaluated runtime.#fig-source("6.02")]),
) <tab:res-plan>

The plan changed the dispatched commands in none of the 39 gated analyses: in this runtime the grounder grounds from the decision fields and audits the plan afterwards #ev("6.02"). The plan-order switch was never on in these runs; in each of the 11 repaired intersection plans the back-out set and order, yielder and passer came from the grounder, and 6 of the 14 accepted plans were not dispatched as written #ev("6.49"). The decision fields did change execution, in 18 dispatches in four episodes (run 1's e09, the gpt-4o pilot, and three answers in two development-era first check episodes) #ev("6.49"); where the effect can be judged, in e09 and the gpt-4o pilot, neither resolved #ev("6.02"). *Caveat:* a post hoc, decision-level trace whose labels are partly inferred.

== Demonstration Campaign <sec:res-demo>

The demonstration campaign (14–15 November 2026) ran live ER-2 takes in four scenes to show the pipeline end to end on video (format in @fig:ch6-demo-panel, Appendix B) #ev("6.01"), with a later prompt and, at the intersection, the plan-order switch, so it is not the evaluated runtime #ev("6.39"). It is illustrative: 1 to 5 takes per scene, the intersection take shown was selected for its label, and nothing is a rate #ev("6.45").

#figure(
  table(
    columns: (1.1fr, 0.6fr, 2.3fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Scene*], [*Valid takes*], [*Outcome per take (label)*]),
    [Four-robot intersection], [5], [take 1 unresolved, 3/4 arrived; takes 2 to 4 grounder-default resolution; take 5 resolved 4/4, labelled VLM-driven execution],
    [Four-robot convoy counterflow], [5], [takes 1 to 3 unresolved, 0/4 arrived each; takes 4 and 5, with the queued-robot hold, unresolved, 1/4 arrived each],
    [Two-robot head-on corridor with obstacle], [1], [resolved 2/2, grounder-default resolution (grounder-corrected)],
    [Five-robot pickup-and-delivery, seed position 21], [1], [unresolved, 1/5 arrived (limitation demonstration)],
  ),
  caption: flex-caption([Demonstration campaign: scenes and takes.], [Demonstration campaign, live ER-2 takes; one bring-up abort each in the intersection and convoy scenes is not counted. Illustrative demonstration; nothing is a rate.#fig-source("6.45")]),
) <tab:res-demo>

#figure(
  table(
    columns: (1fr, 0.75fr, 1.15fr, 1.1fr, 1.1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Scene*], [*Valid response*], [*Accepted unchanged, recorded*], [*Accepted and dispatched as written, corrected*], [*Plan changed executed behaviour*]),
    [Intersection, 5 takes], [9 of 9], [1 (take 5)], [1], [1 (take 5, back-out order only)],
    [Convoy, 5 takes], [48 of 48], [3 (20 repaired, 25 grounder default)], [2 (takes 1 to 3: 2; takes 4 and 5: 0)], [not computed],
    [Head-on, 1 take], [2 of 2], [plan channel off], [n/a], [not computed],
    [Five robots, 1 take], [8 of 8], [2 (1 repaired, 5 grounder default)], [2], [not computed],
    [Total], [67 of 67], [6 of 65 plan-channel analyses], [5], [1],
  ),
  caption: flex-caption([Demonstration campaign: valid, accepted and executed.], [Demonstration campaign, per analysis (second-stage calls not counted): valid response; plan accepted unchanged (`vlm_verbatim`) as recorded and as recomputed offline (commands sent match the verified legs; recorded labels unchanged #ev("6.51")); plan that changed the executed commands relative to the grounder's default for the same snapshot. Illustrative demonstration.#fig-source("6.44")]),
) <tab:res-threeway>

Valid is not usable: in intersection takes 1 and 3 the plans parsed but were nulled for invalid structure #ev("6.39"). The recorded count over-states agreement, because for `reverse` and `reroute` the grounder acts on the model's involved-robots list and never reads the plan #ev("6.02") #ev("6.51"). Counting a plan only when the commands sent match its verified legs, minus two registered artefacts (retreat-shield waits on robots planned `continue`; back-out orders within tolerance), 6 becomes 5: one convoy decision planned waits for two queued robots that were never commanded (motion differences only: 6; no exclusions: 3). In the campaign and October decisions recomputed (convoy takes 4 and 5 excluded), 10 of 33 dispatched `reverse` legs went to robots whose plan said something else #ev("6.51"). *Caveat:* illustrative takes; the corrected counts are an offline recomputation #ev("6.44").

=== Intersection, Take 5 <sec:res-demo-ib>

Take 1 was unresolved: a one-frame identity glitch in perception (M1) triggered the analysis on an approach snapshot and the default plan for that pre-jam geometry held one robot past the horizon; takes 2 to 4 were grounder-default resolutions. In take 5 the plan was accepted with no edit and its back-out order, `robot_3` before `robot_4`, replaced the default `robot_4` before `robot_3`; all four robots arrived #ev("6.39") (@fig:ch6-flow-take5-simple; full trace in @fig:app-flow-take5).

#figure(
  vlm-flow-simple-figure(),
  kind: image,
  caption: flex-caption([Simplified decision flow of one live intersection take.], [Four-robot intersection, demonstration take 5 of 5, selected as the only take labelled VLM-driven execution: what the VLM proposed, what the grounder verified and computed, and what was executed. The model's contribution was the back-out order only (filled box), a near-tie: back-out costs 0.981 m (`robot_3`) and 0.971 m (`robot_4`) differ by 0.010 m, within the verifier's 0.15 m tolerance; the distances in the figure are commanded distances, and the reason for the difference was not established. An end-to-end execution example, not controlled evidence of improved performance: the default plan resolved the same scene in takes 2 to 4. Safety rested on robot-pair distance only; no stage checked paths against obstacles #ev("6.43") #ev("6.13").#fig-source("6.01")]),
) <fig:ch6-flow-take5-simple>

The order changed only when the two back-outs started (`robot_3` at 32.9 s, `robot_4` at 41.9 s; @fig:ch6-ib-backout); pockets, cross phase, release and crossing order stayed on the grounder's ranking, and everything after both back-outs is the default's (@fig:ch6-ib-arrived). The prompt offered `reverse` only to `robot_3` and `robot_4`, so the model chose among offered actions; offline the same prompt produced such an event in 7 of 27 first triggers, no rate for the live takes #ev("6.03"). The order is ascending robot id, inseparable from a slot prior (@sec:res-exploratory). *Caveat:* one take of five, chosen for its label, and a near-tie by construction #ev("6.39").

#figure(
  image("../assets/images/fig_intersection_robot3_backing_t36p97.png", width: 75%),
  caption: flex-caption([Intersection take 5: `robot_3` backs out first.], [Four-robot intersection, demonstration take 5 of 5 (labelled VLM-driven execution), simulated time 37.0 s: `robot_3` (green, moving) backs out along its arm while the others (red, stopped) wait; `robot_4` follows at 41.9 s. Only the timing of the two back-outs changed. Isaac Sim, annotated overhead camera; box colours show perception status. Illustrative take, chosen for its label.#fig-source("6.39")]),
) <fig:ch6-ib-backout>

=== Convoy Counterflow <sec:res-demo-convoy>

In the four-robot convoy counterflow scene, `robot_1` meets the counter-flow `robot_2` nose to nose in a gap while `robot_3` and `robot_4` queue behind `robot_1`; a first decision that leaves out the queued robots ends in a latch #ev("6.40"). In takes 1 to 3 the first decision was a `yield` naming only `robot_1` and `robot_2`, executed as named (@fig:ch6-cv-yield); the queued robots followed through the gap and latched by about 75 s (@fig:ch6-cv-latched). The 33 later proposals all ran as 8 s waits (grounding refused yields and reverses, and the legacy grounding has no template for the rest); offline, 72 of 76 hypothetical post-latch decisions also became waits. One scripted four-robot decision resolved the scene in a first check run (n = 1, not accepted by the owner) #ev("6.40"). Stating the queued robots' hold-back state in the prompt did not help offline: 0 of 22 answers per condition grounded into the four-robot sequence, primary count 0 of 18 #ev("6.04").

Takes 4 and 5 used the queued-robot hold, a grounder key (off by default) that holds unnamed queued robots whose goals lie across the corridor #ev("6.19"). It held both as built, but the model named `robot_1` as yielder, the variant the scene is built to defeat: `robot_2`'s escort west stopped 0.418 m and 0.419 m from the held `robot_3` and latched; 1 of 4 arrived in each #ev("6.41"). *Caveat:* five takes, illustrative; a resolving take would have been a grounding result, not a VLM one.

#figure(
  image("../assets/images/fig_convoy_latched_t149p90.png", width: 75%),
  caption: flex-caption([Convoy take 1: the latched cluster.], [Four-robot convoy counterflow, demonstration take 1 of 5 (unresolved), simulated time 149.9 s: `robot_3` and `robot_4`, not named by the first decision, followed `robot_1` through the gap; all four stand east of it, two pairs inside the 0.45 m proximity latch, unmoved from about 75 s to the end at 260 s; 0 of 4 arrived. Isaac Sim, annotated overhead camera. Illustrative take; all five convoy takes ended unresolved #ev("6.41").#fig-source("6.40")]),
) <fig:ch6-cv-latched>

=== Head-on With Obstacle <sec:res-demo-headon>

The head-on take ran with obstacle text and the feasibility gate on #ev("6.37"). The first decision, `reverse`, separated the robots, which then drove back together and re-triggered. The second was a `yield` naming `robot_1`, which had 0.70 m of retreat room against 1.08 m required, so the gate handed the yield to `robot_2` (@fig:ch6-ho-yield); it parked beside the lane while `robot_1` was escorted past (@fig:ch6-ho-pass), and both arrived (@fig:ch6-ho-arrived). *Caveat:* n = 1; the resolution is grounder-corrected, and what the infeasible yield would have done is not shown #ev("6.37").

#figure(
  image("../assets/images/fig_headon_robot2_backing_t70p00.png", width: 75%),
  caption: flex-caption([Head-on take: `robot_2` yields after the gate swap.], [Two-robot head-on corridor with obstacle, demonstration take 1 of 1 (grounder-default resolution, grounder-corrected), simulated time 70.0 s: `robot_2` (green) backs out east after the gate replaced the model's yielder `robot_1` (0.70 m of retreat room against 1.08 m required). Isaac Sim, annotated overhead camera. Illustrative take, n = 1.#fig-source("6.37")]),
) <fig:ch6-ho-yield>

=== Five Robots <sec:res-demo-five>

The five-robot take ran the pickup-and-delivery scene on seed position 21, outside the 20 confirmatory seeds #ev("6.42"). Decisions 1 and 2 were executed as named (`robot_1` yielded to `robot_4`; `robot_2` yielded and `robot_3` was escorted; @fig:ch6-m5-start, @fig:ch6-m5-after1). The six later proposals were refused by grounding and withheld (no feasible yielder four times, no declared junction once, no shared lane once); no analysis ran after 275.5 s, and 1 of 5 robots arrived #ev("6.42"). This matches the earlier live five-robot analyses, where grounder refusals withheld 47 of 78 and the model is not told of a withheld decision #ev("6.15").

Decision 2's straight escort segment crossed rack island `obstacle_2`: `robot_3` stopped against its east face at 146.9 s and stayed within 5 mm of it in 4526 of 4534 GT rows, while the escort ran on to its deadline (@fig:ch6-m5-escort). This sustained contact is confirmed from GT poses, the URDF collision box, the scene builder and the recording, so "unresolved" partly reflects an escort path error #ev("6.42"). *Caveat:* a limitation demonstration, n = 1.

#figure(
  image("../assets/images/fig_fiverobot_robot3_island_t147p30.png", width: 75%),
  caption: flex-caption([Five-robot take: an escort drives `robot_3` into a rack island.], [Five-robot pickup-and-delivery scene (scene file `mapd_5_s1b`, seed position 21), demonstration take 1 of 1 (unresolved), simulated time 147.3 s: `robot_3` against the east face of rack island `obstacle_2`, driven there by an unchecked straight escort segment. The box is perception's last track before the island hid the marker; the contact rests on GT poses, not on this image. Isaac Sim, annotated overhead camera. Illustrative take, n = 1.#fig-source("6.42")]),
) <fig:ch6-m5-escort>

== Safety Findings <sec:res-safety>

The simulator's GT contact lists were hard-coded empty in the evaluated runtime, so every zero read from them shows nothing #ev("6.20"). Safety evidence is the GT robot-pair centre distance; an offline footprint-gap recompute, pending validation, is in @tab:app-contacts.

#figure(
  table(
    columns: (1fr, 1.2fr, 0.5fr, 1.8fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Study*], [*Lowest GT robot-pair centre distance*], [*Floor stops*], [*Robot-obstacle contact: measurement status*]),
    [Intersection run 1], [on 0.2633 m; off 0.2856 m], [0], [scene declares no obstacles; rack blocks and walls not logged; offline recompute pending validation],
    [Intersection run 2], [live VLM 0.3008 m; scripted 0.2965 m], [0], [as run 1],
    [Registered five-robot pilot], [0.225–0.424 m over all ten episodes], [0], [not covered by the registered gate; offline recompute pending validation],
    [Demonstration campaign], [lowest 0.2176 m (head-on take, before any command); convoy takes 4 and 5: 0.276 m and 0.370 m], [0], [one sustained contact confirmed (five-robot escort, @fig:ch6-m5-escort); otherwise offline recompute pending validation],
    [Five-robot validation take (n = 1)], [0.3101 m], [0], [contact fields logged on all 6001 rows and reproduced offline; partially validated],
  ),
  caption: flex-caption([Safety evidence per study and its measurement status.], [Safety evidence per study: GT robot-pair centre distance, floor stops in M4's log, and the status of robot-obstacle contact measurement. The hard-contact floor (0.20 m) and the 0.18 m gate threshold are on centre distance.#fig-source("6.20")]),
) <tab:res-safety>

The pair values come from the studies' own reports #ev("6.05") #ev("6.06") #ev("6.14") #ev("6.37") #ev("6.41") #ev("6.17"). Most minima occurred during the standoff or jam, before any command; run 1's e09 #ev("6.31"), run 2's first check episode #ev("6.32") and convoy take 5 #ev("6.41") are exceptions. No campaign take logged a floor stop #ev("6.39") #ev("6.40") #ev("6.42").

*Obstacles.* The confirmed five-robot contact #ev("6.42") exposed a gap: the grounder checked neither escort segments nor `reverse` legs against static obstacles (only the yielder's retreat room and candidates use the declared boxes), and the execution and safety monitor (M4) ignores obstacles #ev("6.43"). The validation take came within 5.5 mm of a declared box under a `reverse` #ev("6.17"), and October `reverse` legs pinned robots against box faces #ev("6.18"). The offline recompute is a 10 Hz footprint proximity, not a physics contact, pending validation, because no robot was pinned in the validation take #ev("6.12") #ev("6.17").

*Safety-exemption fix.* A coordination command exempts its robots from each other in M4's proximity check, and that exemption proved wider than intended. A fix behind a key that is off by default narrows it (@tab:res-sx) #ev("6.50"); 64 unit tests and a replay over 68 bundles show identical timelines with the key off and 6 exemptions lost with it on #ev("6.07"). It was on in intersection run 2, where it never fired #ev("6.06"), and in the demonstration takes, where its firings were not counted #ev("5.51"), so it is not validated live.

#figure(
  table(
    columns: (1.4fr, 1.2fr, 1.4fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Exemption path*], [*Key off (evaluated runtime)*], [*Key on*]),
    [Robots the plan marks `continue`], [exempt, also in other clusters], [not honoured],
    [A leg rejected before it started], [still a member, still exempt], [not a partner],
    [Bystander waiver at command start], [unhonoured partner counts as own], [both count as third robots; the waiver ends once the gap closes by more than 0.05 m on 3 readings],
    [Mutual waivers, own-command scope], [unchanged], [unchanged],
  ),
  caption: flex-caption([What the safety-exemption key changes.], [M4's coordination exemption with the scoped-exemption key off and on. Unit tests and offline replay; not validated live.#fig-source("6.50")]),
) <tab:res-sx>

*Guards built later, each off by default.* The escort obstacle guard refuses an escort whose straight segment crosses a declared obstacle; offline it refuses the five-robot escort and one earlier escort and no other campaign escort, with no M4 backstop #ev("6.13"); live it ran once, armed, without firing, because no escort was grounded #ev("6.17"). The reverse obstacle guard has unit tests and an offline replay of 17 reverse commands, no live run #ev("6.13"). The stall abort (M4) has unit and node tests and an offline replay of 221 primitives, no live run #ev("6.18"). The queued-robot hold ran in convoy takes 4 and 5 only #ev("6.19"). *Caveat:* no comprehensive obstacle-safety claim follows.

== Offline Decision Benchmark and Live Per-Group Shadow Run <sec:res-bench>

The offline decision benchmark (v4) replays recorded five-robot analyses, text only, never pooled with the registered pilot #ev("1.06") #ev("5.36"). Its per-cluster variant, one answer per conflict group, raised cluster coverage on 137 recorded positives from 0.496 to 0.832 for ER-2 and from 0.620 to 0.934 for Sonnet 5.5 against the grounding-first prompt, with every chosen option feasible (168 of 168, 181 of 181) #ev("6.46"). A chooser taking the first listed option reached 0.949, and that order is the generator's geometric heuristic #ev("5.41"); on involvement the models match it and do not beat it #ev("6.46"). The gain is the format's, shown without vision.

The live per-group shadow run asked the per-cluster question beside the ordinary loop in 7 episodes (seed positions 21 to 27) and never dispatched it #ev("1.11") #ev("5.42"). All 50 shadow blocks were valid, 12 analyses had more than one group, and no joint-feasibility flag fired; the ordinary loop dispatched 14, withheld 33 and had no decision in 3 #ev("6.47"). *Caveat:* the path runs live; that per-group dispatch would resolve anything is not shown.

== Exploratory Findings <sec:res-exploratory>

*Presentation order.* In pilot probes gpt-4o's yielder followed the first-listed robot, also the lowest id under ascending listing; the first registered design (v1) randomised the order #ev("1.12"), yet the later live studies listed robots ascending #ev("1.15"). Offline the swapped-ID replay ties gpt-4o to the slot #ev("6.09"); the re-score finds a `robot_1` preference for both models #ev("6.08"), and take 5's order is ascending #ev("6.39"). No live result separates an identifier prior from a slot prior.

*Refusals.* An earlier offline replay found gpt-4o's refusals triggered by the real camera frame, not the prompt text or the overlay, which motivated the grey-image fallback after two refusals #ev("4.37"). Sonnet 5.5 refused 30 of 48 real-frame runs under the original prompt ending #ev("6.09") and none of 146 under a JSON-only ending #ev("6.11"). ER-2 returned a valid answer in every campaign analysis #ev("6.44").

== Physical Demonstration <sec:res-physical>

On 12 November 2026 the detect-to-dispatch chain ran on physical TurtleBot3 robots under an overhead camera, with `gemini-3.1-flash-lite` #ev("1.07") #ev("4.28"). In all four staged arrangements the model chose `reverse` #ev("6.48"): two head-on pairs (deadlock, 4/4 commands completed); a triangle of three with a fourth outside (deadlock, 3/3); four robots facing a shared centre (crowding, 4/4); a tighter dual-lane variant (deadlock, 3 completed, robot 3 failed). Two unparsable replies are excluded #ev("4.31"). With no navigation goals, "completed" means the reverse finished #ev("4.29"). *Caveat:* one run per arrangement, code not in this repository's history (@sec:impl-physical); not an evaluation.
