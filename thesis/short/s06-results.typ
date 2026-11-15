#import "../lib.typ": *
#import "../figures/vlm-flow-take5-simple.typ": vlm-flow-simple-figure

#let demo-frame(path) = layout(size => {
  let w = size.width
  box(width: w, height: w * 871 / 1182, clip: true, place(top + left, dy: -w * 86 / 1182, image(path, width: w)))
})

= Results <sec:s-results>

Each section names its evidence grade (@tab:s-studies); nothing is pooled across studies. The Extended Report, Chapter 6, gives every result in full.

== Intersection: Coordination Layer On vs Off, and vs a Scripted Default Plan <sec:s-res-ib>

Intersection run 1 (13 November 2026) compared the full pipeline with ER-2 against the coordination layer switched off, five counted episodes per arm (@tab:s-ib-ab)#ev("6.05"). With the layer off the four robots stopped at jam formation and never moved again. No dispatched plan was accepted unchanged, and re-grounding every repaired decision without its plan reproduces the recorded commands, so the grounder's default ran in all four resolved episodes#ev("6.05")#ev("6.02"). In the unresolved episode the model first answered `yield`, then a two-robot `junction_clear`, after which all four robots stood still for 120.1 s#ev("6.31").

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
  caption: flex-caption([Intersection run 1: coordination layer on against off.], [Intersection run 1 (13 Nov 2026), coordination layer on against off, five counted episodes per arm (slots e01 to e10). Exploratory pilot; near-repeat episodes, so no p-value or interval is given.#fig-source("6.05")]),
) <tab:s-ib-ab>

Intersection run 2 (14 November 2026), never pooled with run 1, compared the live-VLM arm with the scripted default-plan arm (@tab:s-ib-c)#ev("6.06"). Every live-VLM first dispatch re-grounds to exactly the plan the scripted arm executed, so the arms are indistinguishable in outcome: the trigger plus the grounder's default plan clears this jam, and the model's remaining role is the strategy and robot set, which the scripted arm was given#ev("6.06"). The live arm's first check episode counts only in its 5 of 5, and the scripted arm's slot e02, which formed no jam, was re-run post hoc#ev("6.32")#ev("6.34"). *Caveat:* exploratory pilots of five near-repeat episodes on one scene; the scripted arm cannot re-plan after a failure, so the run does not show that the model is useless.

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
) <tab:s-ib-c>

== Registered Five-Robot Pilot <sec:s-res-t1>

The registered pilot (21 October 2026) ran five seed pairs on the five-robot scene, coordination layer on and off, interleaved and counterbalanced as registered (@tab:s-t1)#ev("6.14"). No episode of either arm completed all 25 tasks (0 of 10). The throughput interval includes zero; the delay interval excludes it by 0.6 s. *Caveat:* five pairs, every episode censored and no registered direction, so these are interval estimates for this scene, not a test; the robot-pair gate does not cover the rack islands.

#figure(
  table(
    columns: (1.4fr, 0.8fr, 0.8fr, 1.4fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Measure*], [*On*], [*Off*], [*Difference on − off, bootstrap interval*]),
    [Complete episodes], [0/5], [0/5], [both arms censored at the horizon],
    [Tasks completed], [16/125], [12/125], [],
    [Throughput at the common window], [0.128], [0.096], [+0.032 [−0.008, +0.080]],
    [Mean delay lower bound], [323.4 s], [354.9 s], [−31.5 s [−71.6, −0.6]],
    [Detection recall], [0.818 (9 of 11 conflicts)], [0 of 10 (no analyses)], [degenerate for off],
    [Type accuracy; involved-set F1], [0.778; 0.915], [n/a], [degenerate for off],
    [False positives], [0 in 26 positive analyses], [n/a], [],
    [Analyses dispatched / withheld per seed], [5/4, 2/2, 2/3, 1/4, 2/1], [n/a], [],
    [Robot-pair gate (GT centre distance ≥ 0.18 m, no floor stop)], [PASS 5/5], [PASS 5/5], [GT minimum 0.225–0.424 m over all ten],
  ),
  caption: flex-caption([Registered five-robot pilot: registered measures.], [Registered five-robot pilot (21 Oct 2026), coordination layer on and off, five seed pairs. The interval is the registered paired percentile bootstrap over seed pairs; no direction was registered. Dispatched and withheld counts are corrected against the command log of the execution and safety monitor (M4). Registered pilot.#fig-source("6.14")]),
) <tab:s-t1>

*Failure causes.* The post hoc classification of the five-robot episodes (@tab:s-fc) names no dominant cause: no class leads in both raters' codes and after reconciliation in every stratum#ev("6.63"). Undetermined are 12 of the 18 registered-pilot units (2 of 8 on, all 10 off), 13 of the 33 exploratory-pilot units and 2 of the 4 November units: with the layer off no clock anchor exists, and elsewhere the recorded command could mostly not be reproduced from the rule's inputs#ev("6.63"). The raters agreed on the final class for 53 of 55 units (35 of 55 in the first round), which measures consistent application, not correctness; 3 of 5 final disagreements rest on one reader's ruling#ev("6.63"). The zero for environment geometry is a property of the rule, which cannot assign that class at onset, not a finding about the scenes#ev("6.63"). Interception (@tab:s-intercept): the later obstacle guards and stall abort would have refused or aborted some recorded legs, but no mechanism applies to 5 of 8, 19 of 33 and 1 of 4 coordination-layer-on units by stratum, and the reverse guard's false-positive share is high (15 of 29 pilot legs)#ev("6.63"). The registered pilot's 0 of 10 stands.

#figure(
  table(
    columns: (1.7fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Primary cause*], [*Registered pilot, on*], [*Registered pilot, off*], [*Pilots, to horizon*], [*Pilots, early stop*], [*November takes*]),
    table.cell(colspan: 6, fill: luma(245))[*Primary cause, failure units (episodes whose episode-level primary cause is this class)*],
    [Decision (V)], [2 (0)], [n/a by construction], [5 (2)], [0 (0)], [2 (1)],
    [Grounding and verification (G)], [1 (1)], [n/a by construction], [4 (1)], [3 (2)], [0 (0)],
    [Execution (X)], [3 (2)], [0 (0)], [7 (4)], [1 (1)], [0 (0)],
    [Environment geometry (EG)], [0 (0)], [0 (0)], [0 (0)], [0 (0)], [0 (0)],
    [Undetermined (U)], [2 (2)], [10 (5)], [9 (8)], [4 (3)], [2 (1)],
    [*All failure units*], [8 (5)], [10 (5)], [25 (15)], [8 (6)], [4 (2)],
    [Parked robots excluded, not units], [2], [1], [0], [0], [0],
  ),
  caption: flex-caption([Primary causes of failure units, by stratum.], [Primary causes of failure units, never pooled across strata (contributing causes and sensitivity analyses: Extended Report, Chapter 6). Brackets: episodes whose episode-level primary cause is the class (total row: episodes with a unit). With the layer off, decision and grounding are not applicable and every unit carries the context code N0. Exploratory, post hoc, two raters.#fig-source("6.63")]),
) <tab:s-fc>

#figure(
  table(
    columns: (1.6fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Legs and units*], [*Registered pilot, on*], [*Exploratory pilots*], [*November takes*]),
    [Dispatched escort and reverse legs], [3], [47], [7],
    [Refused by the escort guard], [0], [1], [1],
    [Refused by the reverse guard], [0], [29 (9 justified, 15 false positives, 5 untested)], [2 (both justified)],
    [Aborted by the stall abort], [0], [7 (all in contact)], [1],
    [Any of the three], [0], [31 (10 justified, 15 false positives, 6 untested)], [3 (all justified)],
    [Failure units with no linked escort or reverse leg], [5 of 8], [19 of 33], [1 of 4],
  ),
  caption: flex-caption([Interception analysis by stratum.], [What the later obstacle guards and stall abort would have refused or aborted among the recorded escort and reverse legs, by stratum (never pooled); not whether the scenes would then have resolved. A refusal is justified when the leg met an obstacle, a false positive when it completed clear of every declared box. Exploratory, post hoc.#fig-source("6.63")]),
) <tab:s-intercept>

== Head-on Yielder Choice <sec:s-res-headon>

In the head-on corridor with obstacle only one robot has room to back out. A post hoc, decision-level re-score covered every recorded live head-on analysis (@tab:s-headon)#ev("6.08"). In no row does the model beat the better trivial baseline. With the yield feasibility gate in `swap` mode the grounded yielder was correct in all 79 runs that had the gate on (across gpt-4o, ER-2 and eight other models), and in 37 the gate overturned the model's pick#ev("6.08"). In three offline replays that changed one prompt input at a time, no tested model met the pre-registered rule for choosing the yielder from the scene rather than from labels or listing order: gpt-4o followed the first-listed slot in 85 of 96 grey-pair yields, and several cells could not be assessed (@tab:s-replay)#ev("6.09")#ev("6.10")#ev("6.11"). *Caveat:* decision-level, post hoc or offline.

#figure(
  table(
    columns: (1fr, 0.8fr, 2.2fr, 1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Replay*], [*Model*], [*Result*], [*Verdict*]),
    [Swapped-ID replay (pre-registered)], [gpt-4o], [follows the first-listed slot in 85 of 96 grey-pair yields], [scene-use rule not met],
    [], [ER-2], [answers `reverse` in 129 of 144 runs in the original- and swapped-label arms], [scene-use rule not met],
    [], [Sonnet 5.5], [refused 30 of 48 real-frame runs], [not assessable],
    [JSON-only replay (pre-registered)], [Sonnet 5.5], [146 of 146 answered, 0 refusals; 46 of 96 correct in the grey pair; names `robot_2` in 76 of 96], [scene use not supported],
    [], [ER-2], [50 of 96 runs completed (provider limit)], [not assessable],
    [Improved-annotation replay], [ER-2, gpt-4o], [stopped by provider limits before completion], [every verdict not assessable],
  ),
  caption: flex-caption([Offline replays on yielder choice and scene use.], [Offline replays of the yielder choice on the head-on scene family, two robots, first decision only. Small, decision-level, never pooled with live data.#fig-source("6.09")]),
) <tab:s-replay>

#figure(
  table(
    columns: (0.8fr, 0.7fr, 0.6fr, 0.9fr, 0.9fr, 0.9fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Model*], [*Side*], [*Runs*], [*Model correct*], [*Always `robot_1`*], [*First-come-first-served rule*]),
    [gpt-4o], [west], [23], [5/23], [0/23], [23/23],
    [gpt-4o], [east], [12], [10/12], [12/12], [0/12],
    [ER-2], [west], [30], [12/30], [0/30], [30/30],
    [ER-2], [east], [13], [11/13], [13/13], [0/13],
    [8 other models], [west], [14], [11/14], [0/14], [14/14],
  ),
  caption: flex-caption([Head-on yielder: model against trivial baselines.], [Head-on yielder correct at run level, against always naming `robot_1` and the manifest's first-come-first-served label. Post hoc, decision-level re-score of recorded live decisions; not pre-registered.#fig-source("6.08")]),
) <tab:s-headon>

== Plan Influence <sec:s-res-plan>

A trace of every live four-robot congestion analysis asked whether the audited plan changed the commands M4 received (@tab:s-plan)#ev("6.02"). It changed them in none of the 39 analyses that pass the trace's fidelity gate: the grounder grounds from the decision fields and audits the plan afterwards#ev("6.02"). The decision fields did change execution, in 18 dispatches in four episodes; where the effect can be judged, in run 1's e09 and the October gpt-4o pilot, neither episode resolved#ev("6.49")#ev("6.02"). The audit label also over-states agreement: for `reverse` and `reroute` the grounder acts on the model's involved-robots list and never reads the plan, so in the recorded decisions 10 of 33 dispatched `reverse` legs went to robots whose plan said something else#ev("6.51"). Counting a plan as accepted only when the commands sent match it, the campaign's 6 recorded becomes 5 and the registered pilot's 2 becomes 1#ev("6.51"). *Caveat:* a post hoc, decision-level trace, partly inferred; the corrected counts are an offline recomputation.

#figure(
  table(
    columns: (1.6fr, 1fr, 0.8fr, 0.7fr, 0.7fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Level*], [*Intersection, ER-2 (24)*], [*October gpt-4o pilot (13)*], [*Two head-on pairs, ER-2 (4)*], [*All (41)*]),
    [1. Valid response], [24], [13], [4], [41],
    [2. Plan accepted unchanged], [2 (0 of 20 `junction_clear`)], [11], [1], [14],
    [2. Accepted and dispatched as written], [2], [6], [0], [8],
    [3. Plan changed execution against no plan (gated)], [0 of 22], [0 of 13], [0 of 4], [0 of 39],
    [Decision fields changed execution against the grounder default (gated)], [5], [13], [n/a], [18, in 4 episodes],
  ),
  caption: flex-caption([Plan influence in live four-robot analyses.], [Three-level classification of the 41 live four-robot congestion analyses; 39 pass the trace's fidelity gate. Decision-level trace with verified and inferred labels, on the evaluated runtime.#fig-source("6.02")]),
) <tab:s-plan>

== Demonstration Campaign <sec:s-res-demo>

The demonstration campaign (14–15 November 2026) ran live ER-2 takes in four scenes to show the pipeline end to end, with a later prompt and, at the intersection, the plan-order switch, so not the evaluated runtime#ev("6.01")#ev("6.39"). It is illustrative: 1 to 6 takes per scene, nothing is a rate (@tab:s-demo, @tab:s-threeway)#ev("6.45").

#figure(
  table(
    columns: (1.1fr, 0.6fr, 2.3fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Scene*], [*Valid takes*], [*Outcome per take (label)*]),
    [Four-robot intersection], [5], [take 1 unresolved, 3/4 arrived; takes 2 to 4 grounder-default resolution; take 5 resolved 4/4, labelled VLM-driven execution],
    [Four-robot convoy counterflow], [6], [takes 1 to 3 unresolved, 0/4 arrived each; takes 4 and 5, with the queued-robot hold, unresolved, 1/4 arrived each; rerun take resolved 4/4 (resolved: grounder held the queued robots; model chose strategy and yielder)],
    [Two-robot head-on corridor with obstacle], [1], [resolved 2/2, grounder-default resolution (grounder-corrected)],
    [Five-robot pickup-and-delivery, seed position 21], [1], [unresolved, 1/5 arrived (limitation demonstration)],
  ),
  caption: flex-caption([Demonstration campaign: scenes and takes.], [Demonstration campaign, live ER-2 takes; one bring-up abort in the intersection scene and two in the convoy scene are not counted. Illustrative demonstration; nothing is a rate.#fig-source("6.45")]),
) <tab:s-demo>

#figure(
  table(
    columns: (1fr, 0.75fr, 1.15fr, 1.1fr, 1.1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Scene*], [*Valid response*], [*Accepted unchanged, recorded*], [*Accepted and dispatched as written, corrected*], [*Plan changed executed behaviour*]),
    [Intersection, 5 takes], [9 of 9], [1 (take 5)], [1], [1 (take 5, back-out order only)],
    [Convoy, 6 takes], [50 of 50], [takes 1 to 5: 3 (20 repaired, 25 grounder default); rerun: 1 repaired#ev("6.84")], [2 (takes 1 to 3: 2; takes 4 and 5: 0)], [not computed],
    [Head-on, 1 take], [2 of 2], [plan channel off], [n/a], [not computed],
    [Five robots, 1 take], [8 of 8], [2 (1 repaired, 5 grounder default)], [2], [not computed],
    [Total], [69 of 69], [6 of 65 plan-channel analyses (first twelve takes)], [5 of the 61 with a plan (first twelve takes)], [1],
  ),
  caption: flex-caption([Demonstration campaign: valid, accepted and executed.], [Demonstration campaign, per analysis (second-stage calls not counted): valid response; plan accepted unchanged (`vlm_verbatim`) as recorded and as recomputed offline (commands sent match the verified legs; recorded labels unchanged#ev("6.51")\; the 65 include four intersection "no congestion" answers with no plan, so the recomputation's base is 61#ev("6.16")); plan that changed the executed commands relative to the grounder's default for the same snapshot. Illustrative demonstration.#fig-source("6.44")]),
) <tab:s-threeway>

*Intersection take 5.* The plan was accepted with no edit, and its back-out order, `robot_3` before `robot_4`, replaced the default `robot_4` before `robot_3`; all four robots arrived (@fig:s-take5)#ev("6.39"). The prompt offered `reverse` only to these two robots, so this is a selection among offered actions, and the take was shown because it is the only one with this label#ev("6.03")#ev("6.39"). It is an end-to-end execution example, not evidence of improved performance.

#figure(
  vlm-flow-simple-figure(),
  kind: image,
  caption: flex-caption([Simplified decision flow of one live intersection take.], [Four-robot intersection, demonstration take 5 of 5, selected as the only take labelled VLM-driven execution: what the VLM proposed, what the grounder verified and computed, and what was executed. The model's contribution was the back-out order only (filled box), a near-tie: back-out costs 0.981 m (`robot_3`) and 0.971 m (`robot_4`) differ by 0.010 m, within the verifier's 0.15 m tolerance; the commanded back-out distances shown in the figure (0.781 m and 0.971 m) differ from these costs, for a reason not established. An end-to-end execution example, not controlled evidence of improved performance: the default plan resolved the same scene in takes 2 to 4. Safety rested on robot-pair centre distance; no stage checked paths against obstacles#ev("6.43")#ev("6.13").#fig-source("6.01")]),
) <fig:s-take5>

*Convoy counterflow.* In takes 1 to 3 the first decision was a `yield` naming only the two robots in the standoff; the two queued robots followed through the gap and the four latched (@fig:s-cv-latched), and the 33 later proposals all ran as 8 s waits#ev("6.40"). Takes 4 and 5 used the grounder's queued-robot hold, but the model named `robot_1`, the yielder the scene is built to defeat, and the escort latched against the held queue#ev("6.41"). A corridor yield works only if every queued robot is held and every later crosser starts opposite the yielder's park side#ev("6.85"). In a rerun take the model chose `robot_2`, again naming only the standoff pair; the hold added the queued robots and all four arrived#ev("6.84"). *Caveat:* one take; the resolution depended on the grounder's hold, and the new yielder correction was armed but did not fire, so it is untested live#ev("6.84")#ev("6.85").

*Head-on and five robots.* In the head-on take the model named `robot_1`, which had 0.70 m of retreat room against 1.08 m required, so the gate handed the yield to `robot_2` and both arrived (@fig:s-ho-yield)#ev("6.37"). In the five-robot take two decisions were executed and the six later proposals were refused by grounding; 1 of 5 robots arrived#ev("6.42"). Decision 2's straight escort segment drove `robot_3` into a rack island, where it stayed within 5 mm of the face in 4526 of 4534 ground-truth rows (@fig:s-escort)#ev("6.42").

#figure(
  image("../assets/images/fig_fiverobot_robot3_island_t147p30.png", width: 62%),
  caption: flex-caption([Five-robot take: an escort drives `robot_3` into a rack island.], [Five-robot pickup-and-delivery scene (scene file `mapd_5_s1b`, seed position 21), demonstration take 1 of 1 (unresolved), simulated time 147.3 s: `robot_3` against the east face of rack island `obstacle_2`, driven there by an unchecked straight escort segment. The contact rests on GT poses, not on this image, whose box is perception's last track before the island hid the marker. Isaac Sim, annotated overhead camera. Illustrative take, n = 1.#fig-source("6.42")]),
) <fig:s-escort>

#figure(
  image("../assets/images/fig_convoy_latched_t149p90.png", width: 75%),
  caption: flex-caption([Convoy take 1: the latched cluster.], [Four-robot convoy counterflow, demonstration take 1 of 6 (unresolved), simulated time 149.9 s: `robot_3` and `robot_4`, not named by the first decision, followed `robot_1` through the gap; all four stand east of it, two pairs inside the 0.45 m latch, unmoved from about 75 s to the end at 260 s; 0 of 4 arrived. Isaac Sim, annotated overhead camera. Illustrative take; takes 1 to 5 ended unresolved, the rerun take resolved#ev("6.41")#ev("6.84").#fig-source("6.40")]),
) <fig:s-cv-latched>

#figure(
  image("../assets/images/fig_headon_robot2_backing_t70p00.png", width: 75%),
  caption: flex-caption([Head-on take: `robot_2` yields after the gate swap.], [Two-robot head-on corridor with obstacle, demonstration take 1 of 1 (grounder-default resolution, grounder-corrected), simulated time 70.0 s: `robot_2` (green) backs out east after the gate replaced the model's yielder `robot_1` (0.70 m of retreat room against 1.08 m required). Isaac Sim, annotated overhead camera. Illustrative take, n = 1.#fig-source("6.37")]),
) <fig:s-ho-yield>

== Safety Findings <sec:s-res-safety>

The simulator's ground-truth contact lists were hard-coded empty in the evaluated runtime, so every zero read from them shows nothing#ev("6.20"). Safety evidence is ground-truth robot-pair centre distance plus an offline geometric recompute: over 44 recorded bundles the recompute found one bundle with a sustained robot-obstacle contact (the five-robot take, which also holds a brief graze), one bundle with a brief graze, and 42 bundles clear, with the closest robot-robot footprint gap 82.1 mm#ev("6.12")#ev("6.86"). No study logged a hard-floor stop (@tab:s-res-safety)#ev("6.05")#ev("6.06")#ev("6.14"). The grounder checked neither escort segments nor `reverse` legs against static obstacles, and the safety monitor ignores obstacles#ev("6.43"); October reverses pinned robots on box faces#ev("6.18")#ev("6.13"). Of the mechanisms built since, the reverse guard and the stall abort were each validated live once in a scripted safety test with no model call (the stall abort ended a pinned reverse 2.21 s after contact), and the escort guard is validated offline only#ev("6.86")#ev("6.17"). *Caveat:* no comprehensive obstacle-safety claim follows; this report never claims collision-free operation.

#figure(
  table(
    columns: (1fr, 1.2fr, 0.5fr, 1.8fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Study*], [*Lowest GT robot-pair centre distance*], [*Floor stops*], [*Robot-obstacle contact: measurement status*]),
    [Intersection run 1], [on 0.2633 m; off 0.2856 m], [0], [scene declares no obstacles; rack blocks and walls not logged; offline recompute only],
    [Intersection run 2], [live VLM 0.3008 m; scripted 0.2965 m], [0], [as run 1],
    [Registered five-robot pilot], [0.225–0.424 m over all ten episodes], [0], [not covered by the registered gate; offline recompute only],
    [Demonstration campaign], [lowest 0.2176 m (head-on take, before any command); convoy takes 4 and 5: 0.276 m and 0.370 m; convoy rerun 0.374 m (exempted pair)], [0], [one sustained contact confirmed (five-robot escort, @fig:s-escort); otherwise offline recompute only],
    [Five-robot validation take (n = 1)], [0.3101 m], [0], [contact fields logged on all 6001 rows and reproduced offline; no contact occurred],
  ),
  caption: flex-caption([Safety evidence per study and its measurement status.], [Safety evidence per study: GT robot-pair centre distance, floor stops in the log of the execution and safety monitor (M4), and the status of robot-obstacle contact measurement. The hard-contact floor (0.20 m) and the 0.18 m gate threshold are on centre distance.#fig-source("6.20")]),
) <tab:s-res-safety>


== Offline Decision Benchmark and Live Per-Group Shadow Run <sec:s-res-bench>

The offline decision benchmark replays recorded five-robot analyses, text only, never pooled with the registered pilot#ev("1.06")#ev("5.36"). Its per-cluster variant, one answer per conflict group, raised cluster coverage on 137 recorded positives from 0.496 to 0.832 for ER-2 and from 0.620 to 0.934 for Sonnet 5.5 against the grounding-first prompt, with every chosen option feasible (168 of 168, 181 of 181)#ev("6.46"). A chooser taking the first listed option reached 0.949, the generator's geometric heuristic#ev("5.41")\; on involvement the models match but do not beat it#ev("6.46"). The gain is the format's, without vision.

The live per-group shadow run asked the per-cluster question beside the ordinary loop in 7 episodes and never dispatched it#ev("1.11")#ev("5.42"). All 50 shadow blocks were valid, 12 analyses had more than one group, and no joint-feasibility flag fired; the ordinary loop dispatched 14, withheld 33 and had no decision in 3#ev("6.47"). *Caveat:* the path runs live; that per-group dispatch would resolve anything is not shown.

== Exploratory Findings <sec:s-res-exploratory>

*Presentation order.* In pilot probes gpt-4o's yielder followed the first-listed robot, also the lowest id under ascending listing; the first registered design randomised the order#ev("1.12"), but the later live studies listed robots ascending#ev("1.15"). Given the swapped-ID replay (@tab:s-replay)#ev("6.09"), the `robot_1` preference (@tab:s-headon)#ev("6.08") and take 5's order#ev("6.39"), no live result separates an identifier prior from a slot prior.

*Refusals.* An earlier offline replay found gpt-4o's refusals triggered by the real camera frame, not the prompt text or overlay#ev("4.37"). Sonnet 5.5 refused 30 of 48 real-frame runs under version 1's `<think>` ending#ev("6.09") and none of 146 under a JSON-only ending#ev("6.11")\; ER-2 answered validly in every campaign analysis#ev("6.44").

== Physical Demonstration <sec:s-res-physical>

In the kept run of each of four staged arrangements on the physical robots (@fig:s-physical) the model chose `reverse`#ev("6.48"). Earlier attempts in which it chose `priority_override` or `reroute` produced only waits or timed-out backups, and two unparsable replies, and are not counted#ev("4.31"). With two head-on pairs all four robots recorded `COMPLETED`; in a triangle of three with a fourth robot outside, the model named only the three, all `COMPLETED`; with four robots facing a shared centre, all four; in a tighter dual-lane variant three `COMPLETED` and `robot_3` `FAILED`#ev("4.30")#ev("4.38"). The robots had no navigation goals, so `COMPLETED` means the back-out finished, not that a conflict was resolved#ev("4.29"). *Caveat:* one run per arrangement; illustrative, not an evaluation.

#figure(
  grid(
    columns: (1fr, 1fr),
    column-gutter: 8pt,
    demo-frame("../assets/images/scenario_a_two_parallel_deadlocks.png"),
    demo-frame("../assets/images/scenario_c_three_robot_triangle.png"),
  ),
  caption: flex-caption([Annotated perception frames from the physical demonstration.], [Annotated perception frames saved by the physical demonstration run on 12 November 2026 (illustrative, one run per arrangement). Left: scenario A, two simultaneous head-on pairs. Right: scenario C, a three-robot triangle with a fourth robot outside the cluster.#fig-source("4.30")]),
) <fig:s-physical>
