#import "../lib.typ": *
#import "../figures/scene-s1b.typ": s1b-figure
#import "../figures/scene-ib10.typ": ib10-figure

= Experimental Methodology <sec:ch5>

This chapter states how the system was evaluated; all results are in Chapter 6. @tab:ch5-studies lists the studies with their evidence grades, which the rest of the report uses without further explanation. *Registered as confirmatory, reported as pilot*: the analysis plan was fixed before any data, but too few episodes ran for the confirmatory claim. *Exploratory pilot*: live runs, reported as counts without inferential statistics. *Decision-level offline*: recorded decisions re-scored, replayed or re-grounded, with nothing executed. *Illustrative demonstration*: single live takes that show what the pipeline does, with no rates. *Post hoc classification*: causes assigned after the outcomes were known, under rules frozen before coding. No study is pooled with any other, and strata within a study are never pooled.

#[
#show figure: set block(breakable: true)
#set text(size: 8pt)
#figure(
  table(
    columns: (1.6fr, 1.5fr, 1fr, 1fr, 1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    inset: 3.5pt,
    table.header([*Study*], [*What it compares*], [*n*], [*Evidence grade*], [*Registered before data?*]),
    [Registered five-robot pilot, 21 Oct 2026 (prereg-v3 tranche 1) #ev("5.03") #ev("5.04")], [Coordination layer on vs off, five-robot scene], [5 seed pairs, 10 episodes], [Registered as confirmatory, reported as pilot], [Yes],
    [Exploratory five-robot pilots, 10–17 Oct 2026 (E6–E26) #ev("5.36") #ev("6.61")], [Coordination layer on only, during design tuning], [21 episodes], [Exploratory pilot], [Some batches, as pilots],
    [Intersection run 1: coordination layer on vs off, 13 Nov 2026 (IB10 run 1) #ev("5.17") #ev("5.29")], [On vs off, four-robot intersection], [5 + 5 counted episodes], [Exploratory pilot], [Yes],
    [Intersection run 2: live VLM vs scripted default plan, 14 Nov 2026 (IB10 run 2) #ev("5.20") #ev("5.30") #ev("5.31")], [Live VLM vs scripted default-plan arm, four-robot intersection], [5 + 5 slots, plus one post hoc re-run], [Exploratory pilot], [Yes; re-run registered after the results, before it ran],
    [Offline decision benchmark (v4 bench) #ev("5.36") #ev("5.37")], [Prompt variants and a rule-based chooser on recorded five-robot analyses], [187 analyses, 31 episodes], [Decision-level offline], [Specification only],
    [Live per-group shadow run (Stage 1) #ev("5.42")], [Per-group question grounded beside the live loop, never dispatched], [7 episodes], [Exploratory pilot, decision-level], [Design specification before the run],
    [Head-on re-score of recorded decisions #ev("6.08")], [Recorded first yielder vs the correct yielder and three references], [All recorded live head-on runs], [Decision-level offline], [No (post hoc)],
    [Swapped-ID, improved-annotation and JSON-only replays #ev("6.09") #ev("6.10") #ev("6.11")], [One prompt input changed at a time, recorded two-robot standoffs], [First decision per scene, up to three models], [Decision-level offline], [Yes, before the first paid call; two amended while running],
    [Plan-influence trace #ev("6.02")], [Recorded four-robot decisions re-grounded with and without the plan], [41 analyses, 39 past the fidelity gate], [Decision-level offline], [No (post hoc)],
    [Plan-order and convoy held-robot prompt checks #ev("6.03") #ev("6.04")], [Prompt conditions on recorded intersection and convoy scenes], [Offline calls; 22 answers per convoy condition], [Decision-level offline], [Held-robot check yes; order check in part],
    [Offline contact recompute #ev("6.12")], [Footprint gaps from recorded poses to boxes and robots], [44 bundles], [Offline (geometric), pending validation], [Threshold fixed before cases were examined],
    [Demonstration campaign, 14–15 Nov 2026 #ev("5.51") #ev("6.01")], [Full pipeline, live, four scenes], [13 valid takes], [Illustrative demonstration], [Yes],
    [Five-robot validation take, 15 Nov 2026 #ev("6.17")], [Escort guard armed, contact logging on], [1 take], [Illustrative demonstration (validation only)], [Yes],
    [Earlier recorded head-on run, 30 Sep 2026 #ev("6.38")], [One live run on older code, yield gate on], [1 run], [Illustrative demonstration], [No; selected because it qualifies],
    [Physical TurtleBot3 demonstration, 12 Nov 2026 #ev("4.28")], [Pipeline on hardware, no navigation goals], [4 scenarios, one run each], [Illustrative demonstration], [None recorded],
    [Failure-cause classification and interception analysis #ev("6.60") #ev("6.61") #ev("6.63")], [Primary cause per failure unit; interception by later mechanisms], [55 failure units, 33 episodes, three strata], [Post hoc classification], [Rules frozen before coding, after outcomes were known],
  ),
  caption: flex-caption([Studies in this report.], [Studies in this report, with each internal id once in parentheses. "Registered" means written down before the study ran; only the registered five-robot pilot was registered as confirmatory. No study is pooled with any other.]),
) <tab:ch5-studies>
]

== Research Questions <sec:ch5-rq>

The five research questions of the first registration are stated in @sec:intro-rq; RQ2 and RQ3 were registered against a per-type policy table and a first-come-first-served rule with a commitment tiebreak #ev("5.01").

The studies that ran answer narrower questions. The *registered five-robot pilot* estimates, with intervals and no directional hypothesis, the coordination layer's effect on completion, throughput, delay and per-conflict decision quality #ev("5.02") #ev("5.03"). Its registered sample was 20 episodes per arm #ev("5.04")\; 5 ran #ev("5.03"), and on 13 November 2026 the owner decided not to run the remaining 15 seed pairs and to run the intersection experiment instead #ev("5.04"). A quarter of the sample cannot carry a confirmatory claim, so it is reported as a pilot. *Intersection run 1* asks whether the full pipeline physically clears a jam that stays frozen with the coordination layer off; its registration states that a resolved episode shows the pipeline, not the model's own choice, resolving the jam #ev("5.17"). *Intersection run 2* asks whether the runtime still runs cleanly with a safety fix on and the floor armed, and whether the jam clears the same way with no VLM call and the grounder's default plan #ev("5.20"). The *offline decision benchmark* ranks variants and does not estimate effects #ev("5.37").

== Registered Designs <sec:ch5-prereg>

Every scored criterion was registered before its collection, and pilot episodes never enter confirmatory counts #ev("5.08"). The first registered design (v1, tagged 30 September 2026) was a two-robot battery with a classical reasoner as control #ev("5.05") #ev("5.06")\; four of its amendments carried forward: a random, seeded, recorded listing order (A2), the yield feasibility gate with the yielder scored before the gate (A3), position-verified arrival as primary outcome (A4) and distance channels instead of contact flags (A5) #ev("5.06"). The second (v2, from 30 September 2026) added `junction_clear`, the plan channel with plan-audit labels and a statistics block, with a "no congestion" mock as control #ev("5.07") #ev("5.46"). The third (v3, 6 October 2026) took the navigation stack, changed by a costmap fix, as fixed and moved to congestion emerging from a task stream #ev("5.08"). Its addenda froze the intersection remedy (0.33 m pull-off) and ruled the 0.20 m floor a push limiter (A8, A9) #ev("5.09"), made two robots latching while passing the five-robot conflict class (A15) #ev("5.10"), and, before the registered pilot, froze the scene (A32), defined the measures (A33), ruled the proposals at their defaults and made the control coordination layer off (A34) and built that switch (A35); A36 records the outcome and one deviation #ev("5.11"). Only that control applies to reported data #ev("5.46"). No confirmatory v1 or v2 data is reported #ev("5.12"). #todo[[VERIFY] Owner to confirm why no v1 or v2 confirmatory data exists (collection stopped, or never completed) and add one sentence stating it with its source.] The intersection runs were registered separately, each before its first episode #ev("5.17") #ev("5.20").

== Scenes <sec:ch5-scenes>

Scenes are scenario files of the pinned runtime, built into Isaac Sim stages with a Nav2 map from the same file. The decision layer takes poses from perception (M1); ground truth (GT) comes from the simulator.

=== Five-Robot Pickup-and-Delivery Scene

The scene (file `mapd_5_s1b`) fills the 5.0 m by 3.6 m band one camera can track with two staggered rack islands of 0.55 m by 1.60 m, 0.30 m high, covering 9.78 % of the band and leaving gaps of at least 0.90 m, room for two robots to pass under the latch #ev("5.13") (@fig:ch5-s1b). It is a small multi-agent pickup-and-delivery (MAPD) stream structured after a published study @asadi2025congestion at a much harsher density, a recorded deviation #ev("5.14"). Five robots each serve five tasks, 25 in all, with a 5 sim-s dwell, released 2.5 sim-s apart, over 600 sim-s. A seed from a registered list of 100 fixes starts and task sequence; the first 20 are the confirmatory seeds #ev("5.14"). Conflicts are not scripted #ev("5.10").

#figure(
  s1b-figure(),
  caption: flex-caption([Layout of the five-robot pickup-and-delivery scene.], [Layout of the five-robot pickup-and-delivery scene: tracked band, rack islands, start poses and first goals (G$n$ is robot $n$'s first goal; G2 and G4 share one point).#fig-source("5.13")]),
) <fig:ch5-s1b>

=== Four-Robot Intersection

In this staged jam (file `intersection_bottleneck`) four robots start 1.75 m from the centre, one per arm of a cross aisle between racks, and each drives to the opposite arm, meeting at the centre #ev("5.16"). It runs 300 sim-s with seed label 42 and nothing randomised, so its episodes are repeats of one near-deterministic scene #ev("5.16") #ev("5.17") (@fig:ch5-ib10, @fig:ch5-ib10-frame). A run counts only if the validity gate passes: onset between 8 and 40 sim-s, at least 2.0 s active, all four robots within 1.0 m of the centre; otherwise it is invalid, not failed. The oracle is `junction_clear`: the cross-axis pair backs out, the other pair runs one yield, and the backed-out robots re-enter #ev("5.16").

#figure(
  ib10-figure(),
  caption: flex-caption([Layout of the four-robot intersection.], [Layout of the four-robot intersection, cropped to the cross aisle and the tracked band.#fig-source("5.16")]),
) <fig:ch5-ib10>

#figure(
  image("../assets/images/fig_intersection_jam_t30p10.png", width: 75%),
  caption: flex-caption([Overhead camera frame of the four-robot intersection in a jam.], [Four-robot intersection jammed before any command, raw overhead frame at simulated time 30.1 s; `robot_1` left, `robot_2` right, `robot_3` bottom, `robot_4` top. From demonstration take 5 of 5.#fig-source("6.01")]),
) <fig:ch5-ib10-frame>

The next two scenes carry no scored live comparison; they appear in the demonstration campaign and, for the head-on family, the offline analyses.

=== Four-Robot Convoy Counterflow Scene

`robot_1` drives east into a gap 0.55 m wide and 1.0 m long and meets `robot_2` nose to nose; `robot_3` and `robot_4` queue behind it, held at their start for 120 s of wall-clock time; seed 42, 260 sim-s #ev("5.52") #ev("6.01") (@fig:ch5-convoy). The oracle is a convoy: `robot_2` yields once and `robot_1`, `robot_3`, `robot_4` pass in order; the scene file states that an answer omitting the queued robots ends in a latch #ev("5.52").

#figure(
  image("../assets/images/fig_convoy_standoff_t28p00.png", width: 75%),
  caption: flex-caption([Overhead camera frame of the four-robot convoy counterflow scene.], [Four-robot convoy counterflow scene (`convoy_counterflow_slip`) before any command, raw overhead frame at simulated time 28.0 s: `robot_4` and `robot_3` queue behind `robot_1`, which faces `robot_2` in the gap. From demonstration take 1 of 6.#fig-source("6.01")]),
) <fig:ch5-convoy>

=== Two-Robot Head-On Corridor With Obstacle

In this member of the head-on scene family, two-robot corridors that differ in where a blocking box stands, `robot_1` and `robot_2` meet nose to nose in a corridor 0.55 m wide and 2.0 m long; a box behind `robot_1` leaves it 0.70 m of the 1.08 m it needs to park, so only `robot_2` can yield and the oracle names it; seed 42, 300 sim-s #ev("5.52") (@fig:ch5-headon). The mirrored scenes make `robot_1` the correct yielder.

#figure(
  image("../assets/images/fig_headon_standoff_t26p00.png", width: 75%),
  caption: flex-caption([Overhead camera frame of the two-robot head-on corridor with obstacle.], [Two-robot head-on corridor with obstacle (`head_on_asymmetric_w0p2_eopen_bshort_o0`), first standoff, raw overhead frame at simulated time 26.0 s: `robot_1` (left) faces `robot_2`; the box at the left (`blocker_west`) blocks `robot_1`'s retreat. From demonstration take 1 of 1.#fig-source("6.01")]),
) <fig:ch5-headon>

== Arms <sec:ch5-arms>

Perception, base missions, the safety monitor and the simulator are the same in every arm (@tab:ch5-arms).

*Coordination layer on (live VLM)*: stall trigger, VLM call, grounding and dispatch, with Gemini Robotics-ER 2 (ER-2) in all three live comparisons #ev("5.22") #ev("5.17") #ev("5.20").

*Coordination layer off*: `reasoning_enabled`, true by default, is false #ev("5.18")\; the orchestrator returns before the detector and also forces off the classical shadow, off-trigger probes and the contradiction trigger #ev("5.48"). No analysis, dispatch or bill can occur, while logs, registry, arrival gate and task stream run; the overlay is the on overlay plus this key #ev("5.19") #ev("5.17").

*Scripted default-plan arm (no VLM call)*: a mock backend #ev("5.20") answers "no congestion" first, so the decision lands on the formed jam after one 15 s cool-down; then `junction_clear` for all four robots with no plan, so the grounder uses its default plan; then "no congestion". Handed strategy and robots, it isolates plan content only and cannot re-plan #ev("5.20").

#figure(
  table(
    columns: (0.9fr, 1.3fr, 1.3fr, 0.9fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Comparison*], [*Arms*], [*Runtime and safety*], [*Status*]),
    [Registered five-robot pilot (21 Oct 2026)], [On: ER-2. \ Off: `reasoning_enabled: false`.], [Commit that added the off switch, contained in the pinned runtime; 0.20 m floor.], [Registered as confirmatory; reported as pilot.],
    [Intersection run 1 (13 Nov 2026)], [On: ER-2. \ Off: `reasoning_enabled: false`.], [Pinned runtime, no code deployed; 0.20 m floor.], [Exploratory.],
    [Intersection run 2 (14 Nov 2026)], [On: ER-2. \ Scripted: mock backend, grounder default plan.], [Pinned runtime plus the safety-exemption scope fix (two monitor code files, a merged safety file with the key), on; 0.20 m floor.], [Exploratory.],
  ),
  caption: flex-caption([The three live comparisons.], [The three live comparisons. Arms are compared only within a row.#fig-source("5.21")]),
) <tab:ch5-arms>

The prompt differs between studies (@tab:ch5-prompts): the live comparisons share one version, each demonstration scene kept its earlier record's prompt, and the offline replays changed one part of an older prompt. @sec:app-prompts prints three recorded prompts.

#figure(
  table(
    columns: (1fr, 1.6fr, 0.8fr, 0.6fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Experiment*], [*Prompt*], [*Robot order*], [*Source*]),
    [Registered five-robot pilot, coordination layer on], [Version 3.4, plan channel on.], [Ascending id.], [#ev("4.17") #ev("5.22") #ev("5.47")],
    [Intersection runs 1 and 2 (live VLM; the scripted arm's mock receives the same prompt)], [Version 3.4, plan channel on.], [Ascending id.], [#ev("4.32") #ev("5.47") #ev("6.82")],
    [Demonstration, intersection takes 1-5], [Version 3.4 text, plan channel on, plus two later additions that are not part of the pinned version: the list of plan actions the verifier accepts for each robot, and three plan-ordering sentences.], [Ascending id.], [#ev("5.51") #ev("6.82")],
    [Demonstration, convoy takes 1-5 and five-robot take], [Version 3.4, plan channel on, no list of accepted actions.], [Ascending id.], [#ev("6.82")],
    [Demonstration, head-on take], [Version 2, plan channel off, obstacle text on.], [Random draw per episode.], [#ev("5.51") #ev("6.82")],
    [Swapped-ID replay (offline)], [Version 1, the version the scenes ran live; robot labels exchanged; arms with a grey image and without obstacle text.], [Both orders.], [#ev("6.09") #ev("6.83")],
    [Improved-annotation replay (offline)], [Version 1, obstacle text off, legible labels on the frame, with and without a neutral back-up sentence.], [Both orders.], [#ev("6.10") #ev("6.83")],
    [JSON-only replay (offline)], [Version 1 with its answer-format block replaced by a single JSON-only line.], [Both orders.], [#ev("6.11") #ev("6.83")],
    [Offline decision benchmark], [Baseline: each item's recorded live prompt, rebuilt and checked against the stored hash; other variants append a list of options; grey image.], [See source.], [#ev("5.36") #ev("5.37") #ev("5.38")],
  ),
  caption: flex-caption([Prompt used by each experiment.], [Prompt used by each experiment. "Plan channel on" means that the prompt invites an ordered proposed plan, which the grounder (M3) verifies (@sec:impl-vlm). The demonstration rows were checked against every recorded decision artifact of the four demonstration scenes.]),
) <tab:ch5-prompts>

== Measures <sec:ch5-measures>

=== Five-Robot Measures

The registered measure definitions (v3 addendum A33), with values ruled by the owner, were fixed in code before any confirmatory episode; the scorer cites the paragraph each function implements #ev("5.23") (@tab:ch5-a33).

#figure(
  table(
    columns: (auto, 1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Measure*], [*Registered definition*]),
    [Clock], [One GT-to-ROS offset per run (0–1 s in 0.01 s steps, minimising moving robots' median position error); time zero at robot 1's release; an uncut episode observes about 570 s, to $T_"end"$; every time-to-event right-censored at $T_"end"$ with its reason, no episode dropped #ev("5.23").],
    [Completeness], [Completed dwells by $T_"end"$ out of 25: complete, failed (ran to the horizon) or censored (cut short) #ev("5.23").],
    [Makespan], [Last completed dwell if complete, else censored at $T_"end"$; equals time to full resolution #ev("5.23").],
    [Throughput $Theta_e (t)$], [Fraction of the 25 tasks done by $t$, 1.0 s grid, only up to $T_"end"$ #ev("5.23").],
    [Delay], [Leg travel time minus its solo time from a frozen 18-leg table harvested on a different machine #ev("5.25")\; departure at the first GT sample above 0.03 m/s, arrival at the first sample within 0.35 m after which the robot stays within 0.5 m; a leg that never arrives gives a lower bound #ev("5.23").],
    [Conflict episode], [GT pair encounter below 0.45 m (the latch); encounters sharing a robot that overlap or lie at most 2.0 s apart merge; no minimum duration; dwelling robots included #ev("5.24").],
    [Per-conflict scoring], [A positive analysis matches a conflict if its snapshot lies from onset to 5.0 s after the end and it names one of its robots (one conflict per analysis; ties by robot overlap, then onset); unmatched positives are false positives; latency to first match, censored at the earlier of 5.0 s after the end and $T_"end"$; type accuracy against {deadlock}, label distribution reported #ev("5.24").],
  ),
  caption: flex-caption([Registered five-robot measures.], [Registered five-robot measures and scorer parameters, ruled before collection.#fig-source("5.24")]),
) <tab:ch5-a33>

The involved-set F1, $ F_1 = (2 |D inter I|) / (|D| + |I|), $ <eq:ch5-f1>
with $D$ the robots the decision names and $I$ the conflict's robots, is reported conditional on detection with the unconditional form beside it #ev("5.24"). The v2 plan-quality measures are scored on every matched analysis. With the coordination layer off there are no analyses, so per-conflict measures are degenerate for that arm #ev("5.24").

=== Intersection Measures

Both runs use criteria frozen before either, through one pinned scorer #ev("5.26"). An episode is *resolved* when the jam gate passes and all four robots arrive (within 0.35 m, never beyond 0.5 m afterwards), and a *success* when, in addition, the execution and safety monitor (M4) logged no floor stop and the GT minimum robot-pair distance stays at least 0.18 m #ev("5.26")\; the scene declares no static obstacles, and contact with racks is not checked #ev("6.20"). Secondary measures are the censored time from GT jam onset to the last arrival, minimum pair distance, floor stops, arrivals and an outcome rank #ev("5.26"). Each dispatched live-VLM decision is reported with strategy, plan-audit label and `dispatch_matches_plan`; the episode takes the label of its `junction_clear` dispatch, or of its last dispatch before the final arrival #ev("5.26"). The labels audit the plan (@sec:design-grounding) but do not bound the model's contribution, which also reaches execution through strategy, robots and yielder, hence the re-grounding without the plan in Chapter 6 #ev("6.02")\; for `reverse` and `reroute` a label can record agreement while the dispatch contradicts the plan (@sec:res-demo, @sec:disc-grounding). The scripted arm is grounder default by construction #ev("5.20"). Run 2 also counts the safety fix's log lines and deadline-ended commands #ev("5.33").

== Procedure <sec:ch5-procedure>

Each episode runs on one GPU virtual machine from a run kit that deploys, launches, gates and restores. The kit checks the MD5 sums of the deployed files before every episode, and the scorer reads the arm from the condition record, never from the episode name #ev("5.27"). The pinned safety file has no floor (0.0 m), so the kit installs a floor variant and restores the pinned file afterwards #ev("5.43")\; the deploy check confirms the variant, an episode counts only if M4's start-up line reports `hard_contact_floor_m=0.2`, and the restore is verified by checksum #ev("3.26"). The v3 addenda also require pre- and post-arm gates in live five-robot cells, which the sources read here do not define. #todo[[VERIFY] owner to define what the pre-arm and post-arm gates check]

#figure(
  table(
    columns: (auto, 1fr, 1fr, 1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([], [*Registered five-robot pilot*], [*Intersection run 1*], [*Intersection run 2*]),
    [Order], [Seed positions 1–5, on then off for 1, 3 and 5, off then on for 2 and 4 #ev("5.27").], [Slots e01–e10 alternating on, off, …, off #ev("5.29").], [e01 on, then e02 scripted, e03 on, …, e10 scripted #ev("5.30").],
    [First episode], [—], [e01 ran alone as the first check episode; counted if its harness gates passed; the rest only after the owner accepted it #ev("5.29").], [Likewise, with the safety fix on #ev("5.30").],
    [Configuration], [ER-2, plan channel on, registered shield-and-escort grounding, churn bound off, sequential Nav2 bring-up (180 s per robot), no analysis cap #ev("5.22").], [Parallel bring-up, because the jam window is in absolute sim time #ev("5.17").], [As run 1; one overlay, arms differ only in backend #ev("5.30").],
    [Caps], [600 sim-s; \$0.25 per episode, \$1.30 total, on episodes start only with \$0.25 left; pin rule at 300 sim-s #ev("5.28").], [6 h per invocation; \$0.50 per episode, \$3.00 total #ev("5.29").], [5 h cumulative; \$1.00 total, \$0.25 per live-VLM episode #ev("5.30").],
    [Attempts], [Up to three bring-up attempts per seed and arm, then stop for a ruling #ev("5.27").], [@tab:ch5-exclusions.], [As run 1, plus one post hoc re-run.],
  ),
  caption: flex-caption([Procedure of the three live comparisons.], [Procedure of the three live comparisons, as registered. A cut episode is censored, never dropped, and none is added after seeing data #ev("5.28").]),
) <tab:ch5-procedure>

All 20 registered five-robot seeds had already run as pilots #ev("5.44"). Robots were listed in ascending identifier order in all three live comparisons, not in the random order the first design had registered #ev("5.47"). Pilot episodes enter no count #ev("5.03").

#figure(
  table(
    columns: (1fr, 1.4fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Case*], [*Treatment*]),
    [Nav2 bring-up abort], [Not counted; the same slot is retried, up to 3 attempts. Three aborts skip the slot; two skipped slots in a row stop the run.],
    [Invalid jam (validity gate fails)], [Excluded from the primary denominator and reported.],
    [Harness failure (missing log line, failed restore, failed condition gate, refused arm check)], [Excluded and reported; the chain stops. A later invocation started by the owner may re-run the slot under a new attempt label.],
    [Live-VLM episode with the orchestrator running but no analysis], [Counted as data.],
    [Truncated by a cost or wall-clock stop], [Counted only if all four robots had arrived; otherwise excluded and reported. Not re-run.],
    [Model probe failure before a live-VLM episode], [The episode never starts; the run stops.],
  ),
  caption: flex-caption([Intersection exclusion and attempt rules.], [Intersection exclusion and attempt rules, registered before the first episode.#fig-source("5.29")]),
) <tab:ch5-exclusions>

*Post hoc re-run.* After run 2's results, the owner asked for one scripted slot in the registered exclusion class to be re-run; an amendment registered first allowed one launch without retry, kept the invalid-jam rule, and requires the scripted arm to be reported before and after #ev("5.31").

*Safety gates* are validity conditions: a breach is a safety finding, and the episode is scored as it ran #ev("5.32"). Three distances stay apart: the 0.45 m latch, which also defines a conflict; the 0.20 m floor; and the 0.18 m GT centre distance used as a proxy for robot-robot contact #ev("5.43") #ev("5.32"). The registered pilot gated #ev("5.32") robot pairs below 0.18 m in an all-pairs GT scan (the simulator's contact field is a stub) and floor stops; the floor on M4's start-up line; per-arm conditions (for the off arm, no artifact, one status line and a non-empty scene log, so a crashed orchestrator cannot pass as silence); escort legs against the 0.45 m park clearance; and the checksum pin gate. Rack contact was not gated; a later recompute flagged one possible millimetre graze, not established as a contact #ev("6.01"). In the intersection runs floor stops count as failures while the run continues, and run 2's first check episode also needed no GT pair below 0.18 m, no floor stop and no command stalled by a hold only the safety fix can cause #ev("5.33")\; condition gates check the served model, or that the scripted arm served none #ev("5.20"). A `junction_clear` phase names all four robots, so the floor is the only backstop between them #ev("5.33").

== Analysis Plan <sec:ch5-analysis>

*Registered five-robot pilot.* The estimand is the mean paired difference per measure, pairs formed by seed #ev("5.34"). A cost guard can stop only the arm that spends, so each pair is compared on the window $tau_i = min(T_("end",A,i), T_("end",B,i))$ ($A$ on, $B$ off). The interval is a paired percentile bootstrap over seed pairs (10000 resamples, seed 20261021, 95 %) #ev("5.34") @Efron1994introduction; per-conflict measures are degenerate #ev("5.24"). Within each arm, completeness gets a Wilson 95 % interval @wilson1927probable with the censored count, makespan a Kaplan-Meier curve @kaplan1958nonparametric and restricted mean, and throughput the mean of $Theta_e (t)$ with the number at risk; a naive mean over censored runs is never reported #ev("5.34"). Five pairs give few distinct resamples, so the interval is coarse with unassured coverage, and as no direction is registered it is not a test #ev("5.02").

*Intersection runs.* Repeats of one near-deterministic scene are not independent samples, so the registrations report counts only, with no p-values, no intervals and no quantitative reading of live-versus-scripted times, since the scripted arm skips model latency and dispatches one cool-down later #ev("5.35"). No exact test is reported.

== Failure-Cause Classification <sec:ch5-failure-cause>

This post hoc classification assigns causes to the five-robot episodes that did not finish. It was designed after the outcomes were known, with rules frozen before any coding #ev("6.60") #ev("6.61")\; results are in @sec:res-failure-causes. Round 1 coded all 55 failure units and showed missing evidence rows; round 2, declared after round-1 codes were seen but before any round-2 coding, added the rows without changing the rule, and both raters re-coded the same 34 units. A rater's final code is its round-2 code where the unit was in scope and its round-1 code otherwise. A clock mapping for the coordination-layer-off sheets failed its pre-set tolerance in 5 of 28 validation bundles and was not applied #ev("6.65"). Agreement is reported on final codes with round 1 beside it, and reconciliation resolved remaining disagreements against the rule text #ev("6.63").

=== Failure Units <sec:ch5-fc-units>

A *failure unit*, defined from ground truth so it exists in every arm, is a scorer conflict episode still open at the last GT sample, or a *lone stall*: a robot that moved under 0.05 m in the last 60 s, not waiting at a task node and not in a conflict unit. Each unit has an onset, the start of its conflict or stall; robots parked after their last task are listed apart #ev("6.60").

=== Cause Classes <sec:ch5-fc-classes>

Each unit gets one *primary* and any number of *contributing* causes, assigned to events #ev("6.60"): *decision* (V; answer missing, conflict missed, a needed robot omitted, an infeasible role named while another robot had room, or a self-contradiction); *grounding and verification* (G; a sound decision refused, replaced or altered, or an unsafe manoeuvre let through); *execution* (X; a command dispatched as intended but not carried out: failure, timeout, no navigation progress, a lost robot, or a latch pinning two robots); *environment geometry* (EG; no robot has a clearing straight move and no hypothetical decision grounds to motion, or an undeclared obstacle); and *undetermined* (U; missing evidence, named, with no guessing). The *decision-substitution test* grounds a fixed set of hypothetical decisions on each analysis's snapshot and asks whether any would move a unit robot, after a fidelity check that the recorded decision re-grounds to its recorded command; it passed for 139 of 154 recorded positive decisions as written (governing the primary coding) and 151 with the stored second-stage label and task intents #ev("6.62") #ev("6.63"). The *straight-move test* asks whether any unit robot has a straight move in one of eight headings that reaches the required distance without passing within 0.14 m of a box or robot #ev("6.60").

=== Primary-Cause Rule <sec:ch5-fc-rule>

The first applicable step decides. Missing evidence gives undetermined. If a unit robot received a dispatched command in the 60 simulated seconds before onset, or was executing one at onset, the walk starts at that command, so a state a command produced is coded by it; otherwise a geometry check at onset applies. Events are then read in time order and the first deviation decides; on one event the most upstream class wins, except that an unsafe leg precedes the execution failure of the same leg #ev("6.60").

=== Raters, Blinding and Agreement <sec:ch5-fc-raters>

Two independent raters, both language-model agents with no recorded human check, code every unit from the frozen rule and mechanically computed sheets #ev("6.60") #ev("6.61") #ev("6.63"). Neither sees the other's output, a report's stated cause or the scorer's labels, and the sheets hide arm, episode, seed, outcome and request identifiers #ev("6.62")\; because a decision's content reveals the arm, only GT-derived fields are coded blind to arm, before the events sheet is opened #ev("6.61"). Primary-class agreement is reported as raw agreement and Cohen's kappa, full-code agreement as raw agreement, per stratum; an unresolved disagreement stays undetermined, and identifiers are mapped back only after reconciliation #ev("6.61"). Blinding was incomplete: both raters read a rule section meant to be withheld, one episode and the off-arm sheets were identifiable, one rater opened events sheets early, round 2 was designed after round-1 codes were seen, and one reader made the reconciliation rulings #ev("6.63") #ev("6.65").

=== Strata, Frozen Outcomes and the Coordination-Layer-Off Arm <sec:ch5-fc-strata>

The 33 episodes form three strata that are never pooled: the 10 registered-pilot episodes, the 21 exploratory pilot episodes (those ended by the pilots' early-stop rule tabulated apart), and two November takes (one demonstration, one validation), tabulated together for coding only; echo-model episodes and shadow-run bundles are excluded #ev("6.61") #ev("6.62"). Outcome fields were copied from the scorer files and frozen before coding; nothing is rescored #ev("6.60"). With the coordination layer off, decision and grounding codes are not applicable by construction; such units take environment, execution or undetermined codes plus a context code, and whether an action was available is reported but never used for a decision or grounding code #ev("6.60"). In these data every off-arm unit is undetermined for lack of a clock anchor, so the arms cannot be compared on causes (@sec:res-failure-causes).

=== Interception Analysis <sec:ch5-fc-intercept>

The analysis asks offline which of three later mechanisms (@sec:impl-later) would have refused or aborted each dispatched leg linked to a unit by the chain rule: the escort and reverse obstacle guards, which refuse a leg whose straight path, grown by the robot half-width plus a margin, crosses a declared obstacle #ev("6.13"), and the stall abort, which ends a primitive that commands motion without movement #ev("6.18") #ev("6.61"). In scope are the 57 escort and reverse legs in 25 of the 28 coordination-layer-on episodes; the other three dispatched only waits. A guard refuses a whole command, so all its legs count as refused, with each leg's own blocking reported beside it #ev("6.63"). Physical outcomes come from GT poses recomputed against the footprint geometry, because the October contact fields were empty #ev("6.12"). A refusal or abort is *justified* when the leg made contact (gap at most 0.005 m), was pinned, or came within the guards' 0.05 m margin; a *false positive* when the leg completed at or above the margin; *untested* when it did not complete and stayed at or above it #ev("6.13") #ev("6.63"). Guard gaps are to declared boxes only; for the stall abort a robot contact also counts and "untested" does not apply #ev("6.63"). A unit is intercepted when any mechanism would have stopped any linked leg; the stall-abort column uses the committed detector #ev("6.61").

Three sensitivity analyses stand beside the primary coding: the *persistent-state link* (S1) also links a command whose robot stayed pinned against the same box or robot until onset, reported as changed links only; the *start-inside rule* (S2) recomputes the straight-move test with the guards' rule for a robot starting inside the clearance; both were declared before rating #ev("6.61")\; and the *extra-inputs analysis* (S3), declared with round 2, reruns the substitution test with the stored second-stage label and task intents #ev("6.65").

== Offline Decision Benchmark <sec:ch5-bench>

The benchmark replays recorded five-robot decisions through the production grounder and scores them against the registered GT definitions; nothing is executed, and its scenes are neither unseen nor representative #ev("5.37"). The corpus is 187 analyses from 31 live episodes (exploratory pilots and registered pilot), 149 with a valid decision and 137 positive as recorded; no frames were kept, so replays send a grey image and are text-only #ev("5.36"). It scores stored answers, re-runs the v1 classical chooser (first-come-first-served, the last robot to arrive yields; a decision-level reference only) #ev("5.49"), or replays rebuilt requests whose hash matches the stored prompt #ev("5.37"). Metrics: grounder feasibility, cluster coverage of active GT conflicts, involved-robot F1 (@eq:ch5-f1), yielder agreement with the executable yielders, false-positive rate, cost and latency #ev("5.37"). Variants: the *baseline* live prompt #ev("5.39")\; *grounding-first*, offering as a numbered list only the pairwise `yield`, `reverse`, `reroute` and `temporary_wait` options the grounder executes #ev("5.38")\; the same *with cluster candidates*, from groups of stopped, slow or stale robots within 1.5 m, with rules tuned on the same 187 items #ev("5.40")\; and *per-cluster choice*, one answer slot per group, each grounded alone #ev("5.41"). ER-2 and Claude Sonnet 5.5 were replayed with a shuffled-option control (seed 20261023), neither at temperature 0.0, so each call records the sampling sent #ev("5.39")\; the reference takes each group's first listed option, a default-ordered, not blind, baseline #ev("5.41").

The *live per-group shadow run* asked the per-cluster question after each ordinary analysis, grounded it and never dispatched it, in 7 five-robot episodes on seed positions 21 to 27 on the later (v4) code #ev("5.42")\; it shows whether the path runs live, not whether dispatching it would help.

== Offline Analyses <sec:ch5-decision>

*Head-on re-score.* Post hoc, it asks whether the model names the correct yielder more often than a first-come-first-served rule, and whether a preference for `robot_1` or for the first-listed robot explains any edge #ev("6.08"). Each run's first positive analysis is scored against the oracle beside the first-come-first-served rule, an always-`robot_1` chooser and the yielder the feasibility gate would ground, derived from artifact fields without checking dispatch; counts only #ev("6.08").

*Pre-registered replays* each vary one input on recorded head-on-family standoffs, half with the box on each side, first decision only #ev("6.09") #ev("6.10") #ev("6.11"). The *swapped-ID replay* exchanges the robots' labels, with grey-image and no-obstacle-text arms (the latter and the image-use rule added by an amendment during the run), under both orders with two replicates; its scene-use rule needs a high share of correct choices in every label and slot combination #ev("6.09"). The *JSON-only replay* reduces the answer format to one JSON-only line #ev("6.11"). The *improved-annotation replay* uses legible labels without obstacle text, with and without a sentence that a backing robot needs free floor #ev("6.10"). Stop rules for provider limits mark thin cells "not assessable"; none bears on execution.

*Plan-influence trace.* Every recorded four-robot analysis with a real model is re-grounded with the recorded parameters; if the recorded decision reproduces its dispatch (the fidelity gate), it is re-grounded without its plan and with the scripted decision, and the commands compared, each claim marked verified or inferred #ev("6.02"). It shows which commands depended on the plan, not whether another plan would have changed the outcome.

*Offline contact recompute.* Ground truth logged empty contact lists #ev("6.20"), so at 10 Hz each robot's planar URDF footprint is placed at its recorded pose and the gap to every declared box and robot measured; at most 5 mm (fixed before suspected cases were examined) is a contact entry, one second of entries a sustained contact, and a recorded robot-robot contact the positive control #ev("6.12"). It measures geometric proximity, not physics contact; one live take reproduced its values but its lists stayed empty #ev("6.17"), so its figures are pending validation and only independently confirmed contacts are cited.

== Demonstration Campaign <sec:ch5-demo>

The campaign recorded live takes of the full pipeline to show what it does, not how well. It was registered before any machine time, capped at 12 machine-hours and \$10, and every take, aborts included, is archived and labelled #ev("5.51"). Scenes: the four-robot intersection, the convoy counterflow scene, the head-on corridor with obstacle, and the five-robot scene at seed position 21, outside the confirmatory list and already used by pilots and the shadow run. Every take runs the coordination layer on with live ER-2, the safety-exemption fix and the 0.20 m floor confirmed on M4's start-up line; there is no off or scripted arm. Each scene keeps its earlier record's settings: the 14 November 2026 intersection configuration (yield feasibility gate off), the registered legacy convoy grounding, the September head-on configuration (prompt version 2, plan channel off, gate in `swap` mode, obstacle text on) and the registered pilot's live-VLM procedure; only the intersection adds the plan-order prompt condition and switch (@sec:impl-later) #ev("5.51"). Amendments moved machine-time shares and added convoy takes 4 and 5 with the queued-robot hold on #ev("5.51") #ev("6.19"). One further convoy take, requested by the owner and registered separately before the machine started, also armed the yielder correction #ev("6.84").

A scene stops at the first take meeting its goal or after five valid takes; unchosen takes are listed and each video's choice disclosed #ev("5.51"). Every take gets one label #ev("5.51"): *unresolved failure* (not every robot reached its goal); *VLM-driven execution*, at the intersection only, for a resolved take whose every decision is a `junction_clear` with a plan accepted unchanged and dispatched as written, with no fallback or second-stage command, and a back-out order different from the grounder's default for the same snapshot, recomputed offline, however small the difference (so it says the model's order ran, not that it helped); and *grounder-default resolution* for every other resolved take, including gate swaps and fallbacks. The takes give no rate and no comparison with the coordination layer off; recording changes the real-time factor, so no timing compares with an experiment.

== Threats to Validity <sec:ch5-threats>

These threats were known before the data they affect was collected.

=== Internal Validity

*The grounder repairs or replaces the model's plan.* The intersection run 1 registration states that in an earlier live intersection pilot every plan was repaired or replaced, so claims are worded about the pipeline, VLM plus grounding #ev("5.17")\; the trace confirms this for live ER-2 `junction_clear` plans (0 of 20 accepted unchanged), not for the October gpt-4o pilot (11 of 13) #ev("6.02"). Plan-audit labels and the re-grounding without the plan show which commands came from the model #ev("6.02")\; the scripted arm isolates the default plan's content, but not strategy or robot selection, and cannot re-plan #ev("5.20").

*The coordination-layer-off control is a deterministic freeze.* At the intersection nothing acts on a formed jam once it is off, so the contrast is pipeline on against off, not a VLM against a classical coordinator #ev("5.17").

*The scripted arm's timing differs*: it dispatches one cool-down later and without model latency #ev("5.35").

*Seeds were not unseen*: all 20 registered seeds had run as pilots #ev("5.44").

*Measurement.* The delay baseline came from another machine #ev("5.25"), type accuracy rests on a ruled accepted set #ev("5.24"), and several parameters were proposals ruled at their defaults, all before any confirmatory number #ev("5.11").

*Post hoc decisions.* One scripted slot's re-run was decided after the results, registered before it ran, and is reported both ways #ev("5.31").

=== Statistical Conclusion Validity

*Small n.* Five pairs, and five episodes per arm per intersection run, show only large, consistent differences; a null is not evidence of no effect, and the bootstrap has few distinct resamples #ev("5.34"). The failure-cause strata hold 10, 21 and 2 episodes.

*Why five per arm, and why coordination layer off as the only live control.* Five is the first quarter of 20 seeds per arm, not the result of a power analysis #ev("5.04"). Machine time was the constraint: at a real-time factor of about 0.18 a full-horizon five-robot episode took about 55 min, the ten pilot episodes 9 h 18 min, and the registered outcome record estimated the remaining 30 episodes at about 28 GPU-hours #ev("5.50")\; the intersection registration fixed five per arm without a stated rationale at 28–35 min per episode #ev("5.50"). Model spend was capped at \$1.30 and \$3.00 #ev("5.28") #ev("5.29"). The control is coordination layer off by an owner ruling registered before the pilot, replacing the v1 classical reasoner #ev("5.46")\; no classical rule ran live, and each further arm would have cost the same machine time.

*Non-independence.* Intersection episodes are near-repeats of one scene #ev("5.35").

*Exploratory status.* Only the registered five-robot pilot was registered as confirmatory, and it is reported as a pilot (@tab:ch5-studies) #ev("5.04") #ev("5.37").

=== External Validity

*One scene per experiment.* The registered pilot uses the five-robot scene and both intersection runs a staged, symmetric jam with one correct strategy; neither transfers to other layouts, robot counts or congestion types.

*Simulation only.* Every scored episode ran in Isaac Sim with simulated sensors; the physical demonstration is not an experiment.

*One model, one runtime.* The live comparisons use ER-2 on one runtime; the benchmark's second model is text-only, decision-level, with grouping tuned on the same items #ev("5.40").

*Safety evidence is narrow.* The gates bound robot-pair centre distance only; no gate measured contact with static obstacles #ev("6.20"). The floor fires at or after contact and is the only protection between the robots of one command #ev("5.09") #ev("5.33"). Passing the gates is not a general safety claim.
