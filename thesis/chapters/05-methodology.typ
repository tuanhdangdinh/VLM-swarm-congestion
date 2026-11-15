#import "../lib.typ": *
#import "../figures/scene-s1b.typ": s1b-figure
#import "../figures/scene-ib10.typ": ib10-figure

= Experimental Methodology <sec:ch5>

This chapter states how the system described in Chapters 3 and 4 was evaluated. It covers the research questions, the history of the preregistration, the simulated scenes, the experimental arms, the outcome measures, the run procedure, the analysis plan, the offline benchmark used for the v4 extensions, the offline analyses, the demonstration campaign, and the threats to validity that were known before any data was seen. It reports no outcome; every result belongs to Chapter 6.

Three live comparisons, one offline benchmark, three offline analyses, one demonstration campaign and one post hoc classification are described. Their evidential status differs, and the chapter keeps them apart:

- *prereg-v3 tranche 1* on the five-robot S1b scene, Layer 2 on against Layer 2 off. It was registered as confirmatory. This report reports it as a *pilot*, for the reason given in the section on research questions.
- *IB10 live resolution* on the four-robot intersection, Layer 2 on against Layer 2 off. Exploratory.
- *IB10 grounder-default arm*, a separate run on the same scene, Layer 2 on against a grounder-only arm with no VLM call. Exploratory.
- *the v4 offline bench*, a replay of recorded decisions. Exploratory and decision-level only.
- *the head-on decision analyses*, a re-score of recorded head-on decisions and three pre-registered offline replays. Decision-level only (@sec:ch5-decision).
- *the plan-influence trace*, a counterfactual re-grounding of every live four-robot analysis. Decision-level only (@sec:ch5-decision).
- *the offline contact recompute*, a geometric check of recorded ground truth. Offline, pending live validation (@sec:ch5-decision).
- *the demonstration campaign*, twelve valid live takes in four scenes. Illustrative only (@sec:ch5-demo).
- *the failure-cause classification and interception analysis* of the five-robot episodes, in three strata. Exploratory and post hoc (@sec:ch5-failure-cause).

The IB10 runs and the v4 bench are never pooled with prereg-v3 data, and the two IB10 runs are never pooled with each other. None of the offline analyses or demonstration takes is pooled with any experiment, and the classification keeps its three strata apart.

== Research Questions and Hypotheses <sec:ch5-rq>

=== Questions registered at prereg-v1

The research design frozen with the first preregistration states five research questions #ev("5.01"). They were first written as hypotheses and renamed RQ1 to RQ5 to avoid a clash with an older run label.

- *RQ1, perception and classification.* The VLM classifies the congestion type and the kind of blocker correctly from the annotated scene, and tells congestion apart from normal flow on negative probes. Both arms share the same stall trigger, so the VLM only ever sees post-trigger scenes; RQ1 therefore measures post-trigger classification and false positives, not open-world detection recall.
- *RQ2, strategy competence.* The strategies the VLM chooses resolve congestion, compared with a per-type policy table.
- *RQ3, social reasoning.* The robot the VLM names to yield, and the crossing order it proposes, are effective, compared with a first-come-first-served rule with a commitment tiebreak.
- *RQ4, semantic advantage.* The VLM uses information that no classical baseline has, such as what a blocker is.
- *RQ5, closed-loop adaptation.* Feedback about a failed command changes the VLM's next decision, compared with re-analysis without that feedback. (Here "closed loop" means re-analysis that receives feedback about the failed command, not the pipeline cycle defined in @sec:intro-contributions.)

These questions frame the report. The experiments that were finally run answer narrower questions, set out next.

=== Questions of the experiments that ran

*prereg-v3, S1b.* prereg-v3 registered the Layer 2 on against Layer 2 off comparison as *confidence-interval estimation of the difference per regime*. The expectation that the difference is largest at intermediate difficulty was recorded as interpretation, not as a directional hypothesis #ev("5.02"). The tranche-1 registration adds no hypothesis and no threshold; it collects the registered measures for both arms on the first five registered seeds #ev("5.03"). The question is therefore descriptive: how large is the Layer 2 effect on task completion, throughput, delay and per-conflict decision quality in the S1b scene, and how uncertain is that estimate?

*Why tranche 1 is reported as a pilot.* The registered confirmatory sample was 20 episodes per arm, drawn from the first 20 seeds #ev("5.04"). Tranche 1 ran 5 seeds per arm #ev("5.03"). On 2026-11-13 the owner decided not to run tranche 2 and to run the IB10 experiment instead #ev("5.04"). A quarter of the registered sample cannot carry the confirmatory claim it was designed for, so this report calls tranche 1 a pilot throughout.

*IB10 live resolution.* The registered question is whether the full Layer 2 pipeline physically clears the four-way intersection jam, which stays frozen when Layer 2 is off. The pipeline is the M5 trigger, a live M2 call, M3 `junction_clear` grounding and phased M4 dispatch #ev("5.17"). The registration states in advance that a resolved episode shows the *pipeline* resolving the jam, not the model's own choice, because M3 can repair or replace the model's plan.

*IB10 grounder-default arm.* The addendum asks two questions #ev("5.20"). First, a smoke question: does the IB10 Layer 2 path still run cleanly with a safety fix switched on and the hard-contact floor armed? Second, under the same runtime and safety settings, does the jam clear in the same way when no VLM is called and the plan is M3’s default?

*v4 bench.* The bench ranks prompt and input variants for M2 on recorded scenes. Its own specification says that it ranks candidates and does not estimate effects #ev("5.37").

== Preregistration History <sec:ch5-prereg>

The project registered its scoring rules before collecting the data they score: every scored criterion is written down before its collection, and pilot episodes are excluded from confirmatory counts #ev("5.08"). The design went through three versions, and later changes were made as numbered, append-only addenda. Two documents number their items with the same letter, so this chapter writes "v1 amendment A3" for the first set and "v3 addendum A33" for the second.

=== prereg-v1: two-robot battery and a classical control

The first version was frozen with a repository tag on 2026-09-30 #ev("5.05"). It froze the research design together with ten amendments that a pilot campaign had made necessary. The control, Arm B, was a *classical reasoner*: the same stall trigger, grounding and execution as Arm A, with decisions taken by a per-type policy table and a first-come-first-served yield rule #ev("5.06"). Four amendments shaped the later designs #ev("5.06"):

- *v1 amendment A2* made the order in which robots are listed in the prompt random, seeded and recorded (the later live cells nevertheless used ascending order; @sec:ch5-procedure), after pilots showed that one model's choice of yielder followed the first listed robot, which under the default order was also the lowest robot identifier (the two priors are confounded), rather than the geometry.
- *v1 amendment A3* adopted the M3 yield feasibility gate (`swap`), which replaces an infeasible yielder, and scored the social-reasoning question on the model's answer *before* the gate. Otherwise the gate would rescue both arms and hide their difference.
- *v1 amendment A4* made the position-verified arrival the primary outcome, because a navigation stack reporting success is not the same as a robot at its goal.
- *v1 amendment A5* replaced simulator contact flags with distance channels, using the 0.45 m safety distance.

=== prereg-v2: recovery from a formed jam

The second design was written on the day the first was tagged, and was revised six times #ev("5.07"). It changed because v1 could only *classify* a four-way jam; no single-yield command could clear one. v2 added the composite `junction_clear` command; a plan channel in which the VLM proposes a full ordered plan and M3 verifies and minimally repairs it; and a provenance label on each audited plan (`vlm_verbatim`, `repaired` or `m3_default`). It also added a statistics block: paired tests on binary outcomes, Wilson intervals, Kaplan-Meier curves with the restricted mean survival time for censored times, and bootstrap intervals #ev("5.07"). In v2 the Layer-2-off control was a mock decision layer that always answered "no congestion" #ev("5.46").

=== prereg-v3: fixed stack, emergent congestion

The third design dates from 2026-10-06 #ev("5.08"). Two things forced it. First, a fix to the navigation costmap changed the reactive layer itself, so v3 treated the fixed stack as ground truth and required outcome checks instead of assuming that earlier results carried over #ev("5.08"). Second, the project wanted congestion that *emerges* from a stream of tasks rather than being staged, which led to the S1 scene family and its sparse variant S1b. v3 then grew through append-only addenda. For the claims of this report, A32 to A35 matter most, because they fixed the S1b configuration, the measures and the Arm B control before tranche 1 ran. A8, A9 and A15 explain the IB10 remedy and the S1b conflict class, and A36 records the tranche-1 outcome and one deviation. The relevant addenda are:

- *v3 addenda A8 and A9* froze the IB10 release-lane remedy, a 0.33 m lateral pull-off for the held robot, and ruled the 0.20 m hard-contact floor a push limiter, not a contact preventer #ev("5.09").
- *v3 addendum A15* recorded that two opposing robots could not pass each other under the 0.45 m proximity latch, and registered this "latch-on-pass" event as S1b's conflict class #ev("5.10").
- *v3 addendum A32* froze the S1b configuration for confirmatory collection. *A33* defined every registered measure operationally before any confirmatory episode ran, labelling each choice as registered text or as a proposal. *A34* ruled every A33 proposal at its default and redefined Arm B as Layer 2 off. *A35* built that mode as the M5 key `reasoning_enabled: false`. *A36* recorded the tranche-1 outcome and one deviation, the GPU wall-clock, and left the design of tranche 2 to the owner #ev("5.11").

The meaning of "Arm B" therefore changed. In v1 it was a classical reasoner, in v2 a no-congestion mock, and from v3 addendum A34 onward it is Layer 2 switched off #ev("5.46"). Only the last meaning applies to the experiments in this report.

No confirmatory data from the v1 or v2 collection tracks is reported in this report #ev("5.12"). #todo[[VERIFY] Owner to confirm why no v1 or v2 confirmatory data exists (collection stopped, or never completed) and add one sentence stating it with its source.]

The IB10 experiment and its grounder-default addendum are registered separately from prereg-v3, each written before its first episode #ev("5.17") #ev("5.20").

== Scenes <sec:ch5-scenes>

The scenes are scenario files of the v3 pinned runtime, built into Isaac Sim stages, with Nav2 running on a map generated from the same file. Robot poses for the decision layer come from M1’s overhead ArUco tracking; ground truth (GT) positions come from the simulator.

=== S1b: five-robot task-stream scene

S1b is the sparse-warehouse member of the S1 family #ev("5.13"). It uses the area one overhead camera can track, a band of 5.0 m by 3.6 m, with the racks removed from it. Two staggered rack islands, each 0.55 m by 1.60 m and 0.30 m high, stand off-centre. They cover 9.78 % of the band, and every gap around them is at least 0.90 m wide, which in geometric terms leaves room for two robots to pass under the proximity latch #ev("5.13"). @fig:ch5-s1b shows the layout.

The scene is a small multi-agent pickup-and-delivery (MAPD) stream. Its structure follows a published MAPD study @asadi2025congestion, at a much harsher density, which the design records as a deviation rather than a match #ev("5.14"). Five robots serve five task nodes. Each robot receives five tasks, 25 in all, with a dwell of 5 sim-s at each node. Robots are released one after another, 2.5 sim-s apart, and the horizon is 600 sim-s #ev("5.14"). A seed fixes the start assignment and the task sequence. Seeds come from a registered list of 100, of which the first 20 are the confirmatory seeds #ev("5.14"). Conflicts are not scripted: the registered conflict class is two robots latching while trying to pass #ev("5.10").

#figure(
  s1b-figure(),
  caption: flex-caption([Layout of the S1b scene.], [Layout of the S1b scene: tracked band, two rack islands, the five robot start poses and each robot’s first goal (G$n$ is robot $n$’s first goal; G2 and G4 share one point). Later goals come from the task stream.#fig-source("5.13")]),
) <fig:ch5-s1b>

=== IB10: four-robot intersection

IB10 is a staged four-way jam #ev("5.16"). Four robots start 1.75 m from the centre, one on each arm of a cross aisle, and each drives to the opposite arm. Equal approach distances make them reach the centre together. Rack blocks fill the four quadrants, so the aisles are the only free floor. The scene runs for 300 sim-s with seed label 42 #ev("5.16"). Nothing is randomised, so its episodes are repeated runs of one near-deterministic scene, not draws of different scenes #ev("5.17"). @fig:ch5-ib10 shows the layout.

A run counts only if a jam forms. The frozen validity gate requires a jam onset inside the window of 8 to 40 sim-s, an active interval of at least 2.0 s, and all four robots within 1.0 m of the centre at onset #ev("5.16"). A run that fails this gate is invalid, not failed. The scene's oracle names `junction_clear` as the correct strategy: the cross-axis pair recedes along its own arms, the yield-axis pair runs one yield, and the receded robots re-enter afterwards #ev("5.16").

#figure(
  ib10-figure(),
  caption: flex-caption([Layout of the IB10 intersection.], [Layout of the IB10 intersection: four robots, one per arm, each crossing to the opposite arm. The drawing is cropped to the area around the cross aisle and the tracked band.#fig-source("5.16")]),
) <fig:ch5-ib10>

@fig:ch5-ib10-frame shows the same scene as the overhead camera sees it when the jam has formed.

#figure(
  image("../assets/images/fig_intersection_jam_t30p10.png", width: 75%),
  caption: flex-caption([Overhead camera frame of the four-robot intersection in a jam.], [Four-robot intersection (`intersection_bottleneck`, the IB10 scene file, seed 42), raw overhead camera frame at simulated time 30.1 s: the four robots jammed at the centre of the cross aisle before any command; `robot_1` left, `robot_2` right, `robot_3` bottom, `robot_4` top, each bound for the opposite arm. Simulation (Isaac Sim), overhead camera. Frame from demonstration take 5 of 5, not from an IB10 experiment episode.#fig-source("6.01")]),
) <fig:ch5-ib10-frame>

The next two scenes were used only in the demonstration campaign and, for the head-on family, in the offline analyses. Neither carries a scored live comparison in this report.

=== Convoy counterflow

The convoy counterflow scene places four robots on one line through a narrow gap #ev("5.52"). The gap between two barrier blocks is 0.55 m wide and 1.0 m long. `robot_1` drives east into the gap and meets the counter-flow robot `robot_2` nose to nose; `robot_3` and `robot_4` queue behind `robot_1`, and their goals also lie past the gap. The two queued robots are held at their start for 120 s of wall-clock time and then released, so they reach the gap after the first decision. The scene runs for 260 sim-s with seed 42 #ev("5.52") #ev("6.01"). Its oracle is a convoy: `robot_2` yields once and the three eastbound robots pass in the order `robot_1`, `robot_3`, `robot_4`. The scene file states in advance that any answer that omits the queued robots ends in a latch of robots that the command did not name, so the first decision has to include all four robots #ev("5.52") #ev("6.01"). @fig:ch5-convoy shows the standoff.

#figure(
  image("../assets/images/fig_convoy_standoff_t28p00.png", width: 75%),
  caption: flex-caption([Overhead camera frame of the convoy counterflow scene.], [Convoy counterflow scene (`convoy_counterflow_slip`, seed 42), four robots, raw overhead camera frame at simulated time 28.0 s. Left to right: `robot_4` and `robot_3` queued behind `robot_1`, which stands nose to nose with the counter-flow robot `robot_2` in the 0.55 m wide, 1.0 m long gap between the two barrier blocks (yellow). Before any command. Simulation (Isaac Sim), overhead camera. Frame from demonstration take 1 of 5.#fig-source("6.01")]),
) <fig:ch5-convoy>

=== Head-on corridor with obstacle

The head-on corridor scene is one member of a family of two-robot head-on scenes that differ in which side a blocking box stands on #ev("5.52"). Two robots, `robot_1` from the west and `robot_2` from the east, meet nose to nose in a corridor between barrier blocks that is 0.55 m wide and 2.0 m long. A box behind `robot_1` (`blocker_west`) leaves it 0.70 m of retreat room from the corridor mouth, against the 1.08 m it needs to park, so only `robot_2` can yield. The scene's oracle therefore names `robot_2` as the yielder. It runs for 300 sim-s with seed 42 #ev("5.52"). @fig:ch5-headon shows the first standoff. The mirrored scenes of the family, with the box on the east side, make `robot_1` the correct yielder; the offline analyses of @sec:ch5-decision use both sides.

#figure(
  image("../assets/images/fig_headon_standoff_t26p00.png", width: 75%),
  caption: flex-caption([Overhead camera frame of the head-on corridor with an obstacle.], [Head-on corridor with an obstacle (`head_on_asymmetric_w0p2_eopen_bshort_o0`, seed 42), two robots, raw overhead camera frame at simulated time 26.0 s: `robot_1` (left) and `robot_2` (right) nose to nose in the 0.55 m wide, 2.0 m long corridor between the barrier blocks (yellow). The box at the left (`blocker_west`) leaves `robot_1` 0.70 m of retreat room against 1.08 m required, so only `robot_2` can yield. First standoff, before any command. Simulation (Isaac Sim), overhead camera. Frame from demonstration take 1 of 1.#fig-source("6.01")]),
) <fig:ch5-headon>

== Arms <sec:ch5-arms>

Three arm definitions are used, in three separate comparisons (@tab:ch5-arms). An arm is defined by what happens after M1 publishes a scene. Perception, the Nav2 base missions, M4’s safety monitor and the simulator are the same in every arm.

*Arm A, Layer 2 on.* The full pipeline runs. M5’s stall detector triggers an analysis, M2 calls the VLM, M3 grounds the decision into commands, and M4 dispatches them. The model is `gemini-robotics-er-2-preview` (ER-2) in all three live comparisons #ev("5.22") #ev("5.17") #ev("5.20").

*Arm B, Layer 2 off.* The M5 configuration key `reasoning_enabled` is set to false; its default is true #ev("5.18"). When it is false, M5 returns before the congestion detector, never constructs a VLM backend, and forces off three auxiliary Layer 2 paths #ev("5.48"): the _classical shadow_, which computes and logs the answer of the rule-based v1 classical reasoner beside every VLM analysis and never dispatches it; the _probes_, off-trigger VLM analyses of normal flow that are logged but never grounded or dispatched; and the _contradiction trigger_, which re-triggers analysis early when a dispatched leg fails or a robot measurably departs from what its leg implies. No analysis, decision artifact or dispatch can occur, and no model is billed #ev("5.19"). The scene log, task registry, arrival gate and task stream still run, so Arm B produces the same outcome records as Arm A. M5 logs one fixed status line at start-up, which the condition gate checks #ev("5.19"). In each experiment the Arm B overlay is the Arm A overlay plus this one key #ev("5.17") #ev("5.19").

*Arm C, grounder default, no VLM.* The Layer 2 trigger, M3 grounding and phased M4 dispatch are on, but M5’s backend is a scripted mock instead of the VLM #ev("5.20"). The script has three entries: "no congestion" for the first analysis; then `junction_clear` naming all four robots with no proposed plan; then "no congestion" for every later analysis. With no proposed plan, M3 derives the phases itself and labels the plan `m3_default`. The first answer is "no congestion" so that the decision lands on a later analysis of the formed jam rather than on a start-up stall; the re-trigger follows one 15 s cool-down #ev("5.20"). Arm C is handed the strategy and the robot set. It therefore isolates plan *content*, not strategy or robot selection, and it cannot re-plan after a failure #ev("5.20").

#figure(
  table(
    columns: (0.9fr, 1.3fr, 1.3fr, 0.9fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Comparison*], [*Arms*], [*Runtime and safety*], [*Status*]),
    [prereg-v3 tranche 1, S1b], [A: ER-2. \ B: `reasoning_enabled: false`.], [v3 runtime with the Arm B switch; 0.20 m floor.], [Registered confirmatory; reported as pilot.],
    [IB10 live resolution], [A: ER-2. \ B: `reasoning_enabled: false`.], [v3 pinned runtime; 0.20 m floor.], [Exploratory.],
    [IB10 grounder default], [A: ER-2. \ C: scripted mock, M3 default plan.], [v3 pinned runtime plus the safety fix (three files: two monitor code files and a merged safety file carrying the key), switched on; 0.20 m floor.], [Exploratory.],
  ),
  caption: flex-caption([The three live comparisons.], [The three live comparisons. Arms are compared only within a row.#fig-source("5.21")]),
) <tab:ch5-arms>

The rows differ in runtime. Tranche 1 ran on the commit that introduced the Arm B switch, which the v3 pinned runtime contains #ev("5.21"). The first IB10 run used the v3 pinned runtime with no code deployed #ev("5.17"). The grounder-default run added the safety fix, three files in all: two safety-monitor code files and a merged safety file carrying a configuration key that narrows the coordination exemption, with the floor armed #ev("5.21") #ev("6.06"). Arm C is therefore compared only with the Arm A episodes of its own run, never with the earlier IB10 arms.

== Measures <sec:ch5-measures>

=== S1b measures (v3 addendum A33)

v3 addendum A33 fixed every S1b measure in code before any confirmatory episode ran, and the scorer cites the paragraph each of its functions implements #ev("5.23"). The definitions below follow A33 in substance, with the parameter values ruled in v3 addendum A34.

*Clock and censoring.* Ground truth and ROS time are joined by one offset per run, fitted as the shift between 0 and 1 s, in 0.01 s steps, that minimises the median position error of moving robots #ev("5.23"). Time zero is robot 1’s release, and every time is relative to it. Isaac stops at 600 sim-s of absolute time, so an uncut episode observes about 570 s after release, and "by the horizon" means by the end of observation, $T_"end"$ #ev("5.23"). Every time-to-event quantity is right-censored at $T_"end"$ with a reason (horizon, stop flag or other abort), and no episode is dropped for being censored.

*Completeness.* The number of completed dwells by $T_"end"$, out of 25. An episode is complete if all 25 are done, failed if not and it ran to the horizon, and censored if it was cut short #ev("5.23").

*Makespan, identical to time to full resolution.* The time of the last completed dwell for a complete episode, otherwise censored at $T_"end"$. A33 treats the two registered names as one quantity #ev("5.23").

*Throughput curve.* $Theta_e (t)$ is the fraction of the 25 tasks completed by time $t$. It is a step function defined only up to $T_"end"$ and evaluated on a 1.0 s grid #ev("5.23"); it is never carried flat past censoring.

*Delay against free flow, per segment.* A segment is one robot's leg between consecutive task nodes. Departure is the first GT sample after the leg is issued with a speed above 0.03 m/s. Arrival is the first sample within 0.35 m of the target node after which the robot stays within 0.5 m. The delay is the travel time minus the time the same leg takes with the robot alone in the scene #ev("5.23"). The solo baseline is a frozen table of 18 legs, harvested before the tranche on a different machine #ev("5.25"). The arrival search for a segment ends at the segment's completed dwell, or at $T_"end"$ if there is none #ev("5.23"). A leg that departs but does not arrive gives a lower bound on its delay.

*GT conflict episodes.* A pair encounter is a run of GT samples in which two robots' centres are closer than 0.45 m, the distance at which M4’s latch fires #ev("5.24"). Encounters that share a robot and overlap, or are at most 2.0 s apart, merge into one conflict episode, with no minimum duration. Robots that are dwelling or parked are not excluded, because a dweller with a latched robot beside it *is* the conflict #ev("5.24").

*Per-conflict decision scoring.* Each decision artifact is one analysis. A positive analysis matches a conflict when its snapshot lies between the conflict's onset and 5.0 s after its end and it names at least one of the conflict's robots #ev("5.24"). An analysis matches at most one conflict; ties go to the largest overlap with the conflict's robots, then to the latest onset not after the analysis, then to the earliest onset. A positive analysis that matches no conflict is a false positive #ev("5.24"). A conflict is detected if any analysis matches it, and detection latency is the time from onset to the first match. The latency of an undetected conflict is right-censored at the earlier of 5.0 s after its end and $T_"end"$, minus its onset #ev("5.24"). The type label is scored against the accepted set {deadlock}, and the label distribution is always reported. The involved-set F1 is

$ F_1 = (2 |D inter I|) / (|D| + |I|), $ <eq:ch5-f1>

where $D$ is the set of robots the decision names and $I$ the set of robots in the conflict #ev("5.24"). It is reported conditional on detection, with the unconditional form, which scores an undetected conflict as 0, beside it. The plan-quality measures from v2 (plan emission rate, agreement, edit distance, provenance and replan count) are scored on every matched analysis. Arm B makes no analyses, so every per-conflict measure is degenerate for it by construction #ev("5.24").

#figure(
  table(
    columns: (auto, auto, 1fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Parameter*], [*Value*], [*Role*]),
    [encounter distance], [0.45 m], [pair encounter threshold, equal to the M4 latch],
    [`merge_gap_s`], [2.0 s], [merge encounters into one conflict episode],
    [`min_duration_s`], [0.0 s], [no minimum conflict length],
    [`pre_s`, `post_s`], [0.0 s, 5.0 s], [matching window around a conflict],
    [`min_overlap`], [1 robot], [minimum shared robots for a match],
    [accepted types], [{deadlock}], [type-label accuracy],
    [throughput grid], [1.0 s], [evaluation grid of $Theta_e (t)$],
  ),
  caption: flex-caption([S1b scorer parameters (v3 addenda A33 and A34).], [S1b scorer parameters as ruled before collection (v3 addenda A33 and A34).#fig-source("5.24")]),
) <tab:ch5-a33>

=== IB10 measures

All IB10 scoring uses the criteria frozen for the scene before either experiment, through the same pinned scorer #ev("5.26").

*Primary.* An episode is *resolved* when the formed-jam gate passes and all four robots arrive, by the GT position rule: within 0.35 m of the goal and never beyond 0.5 m afterwards #ev("5.26"). An episode is a *success* when it is resolved, M4 logged no hard-contact-floor stop, and the GT minimum distance between any two robots after time zero is at least 0.18 m #ev("5.26"). This is a centre-distance test on robot pairs; IB10 declares no static obstacles, and contact with walls or rack blocks is not checked #ev("6.20"). A floor stop or a GT robot pair below 0.18 m makes an episode a failure, whatever its arrivals.

*Secondary.* Time to full resolution is the last arrival minus the GT jam onset, censored at the horizon when the jam is not resolved. Also reported are the minimum pairwise GT distance, the floor-stop count, the number of arrivals out of four, and an outcome rank that orders episodes first by whether all robots arrived, then by the phase reached, then by arrivals #ev("5.26").

*Attribution.* For every dispatched decision of Arm A the scorer reports the strategy, the plan provenance and whether the dispatched command matches the audited plan (`dispatch_matches_plan`) #ev("5.26"). The provenance labels are `vlm_verbatim` (the model's proposed plan passed M3’s audit unchanged), `repaired` (it passed after M3’s edits) or `m3_default` (absent, rejected or not repairable, so M3’s own default plan is the reference). In every case the dispatched command is the grounder's output; the label records how that plan relates to the model's proposal (@sec:design-grounding). The episode's label is the provenance of its `junction_clear` dispatch, or of its last dispatch before the final arrival #ev("5.26"). The provenance labels describe the audit of the model's proposed plan and are reported beside every outcome. They do not bound the model's contribution, which also reaches execution through the decision's strategy, robot set and yielder; Chapter 6 therefore adds a re-grounding of each decision without its plan #ev("6.02"). Arm C is `m3_default` by construction, and its condition gate enforces it #ev("5.20"). For `reverse` and `reroute` the label can record agreement while the dispatch contradicts the plan (@sec:disc-failure-cause).

*Safety-fix signals.* The grounder-default run adds descriptive per-episode counts of the log lines that only the switched-on safety fix can write, and of commands that ended on a deadline rather than on completion #ev("5.33").

== Procedure <sec:ch5-procedure>

=== Common harness

Every episode runs on one GPU virtual machine with Isaac Sim, the ROS 2 stack in a container, and a kit of scripts that deploys the runtime, launches the episode, gates it and restores the machine. Each kit pins the md5 sums of the deployed files and checks them before every episode; a mismatch stops the run. Each episode writes a condition record naming its tag and arm, and the scorer reads the arm from that record, never from the episode's name #ev("5.27"). The 0.20 m hard-contact floor is not in the pinned safety configuration, whose floor is 0.0 m, so each kit swaps in a floor configuration for the run and restores the pinned one afterwards #ev("5.43").

=== prereg-v3 tranche 1

*Seeds and order.* The seeds were positions 1 to 5 of the registered list. The two arms were interleaved and counterbalanced by seed position, A then B for positions 1, 3 and 5 and B then A for positions 2 and 4, giving 10 episodes #ev("5.27"). All 20 registered seeds had already run as pilots, so they were not unseen; v3 addendum A33 records this as a limitation #ev("5.44").

*Arm A condition.* ER-2 with the plan channel on, the registered shield-and-escort grounding configuration, the re-analysis suppression and refusal handling of the pilots, the churn bound off, sequential Nav2 bring-up with a 180 s per-robot timeout, the 0.20 m floor, and no cap on the number of analyses #ev("5.22"). The robots were listed in the prompt in ascending identifier order, not in the random order of v1 amendment A2 #ev("5.47"); the same holds for both IB10 runs #ev("5.47").

*Horizon and caps.* Each episode ran to the 600 sim-s horizon. Dollars were a safety guard only. A per-episode guard of \$0.25 stopped an episode when the estimate plus one more call reached it, a tranche total of \$1.30 counted Arm A spend, and an Arm A episode started only with at least \$0.25 left. Arm B spends nothing and had no budget gate #ev("5.28"). A pre-registered pin rule stopped an episode in which a robot stayed physically pinned for 300 sim-s #ev("5.28"). An episode cut by the guard or by the pin rule is censored, never dropped, and no episode is added after seeing data.

*Attempts.* A Nav2 bring-up abort retried the same seed and arm, up to three attempts. If all three aborted, the tranche stopped for a ruling instead of skipping or substituting the seed #ev("5.27"). Pilot episodes were excluded from every count #ev("5.03").

=== IB10 live resolution

*Design.* Five episodes per arm, interleaved in a fixed order: E01 A, E02 B, E03 A, and so on to E10 B #ev("5.29"). E01 ran alone as a smoke. If it passed every harness gate it counted as Arm A's first episode whatever its outcome, and the follow-up ran only after the owner had inspected it and written an acceptance marker #ev("5.29"). Nav2 bring-up was parallel, as in every earlier IB10 run, because the jam gate's onset window is in absolute sim time #ev("5.17").

*Exclusions and attempts.* The registration fixed the treatment of every non-standard case before the first episode (@tab:ch5-exclusions) #ev("5.29").

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
    [Arm A with M5 running but no analysis], [Counted as data.],
    [Truncated by a cost or wall-clock stop], [Counted only if all four robots had arrived; otherwise excluded and reported. Not re-run.],
    [Model probe failure before an Arm A episode], [The episode never starts; the run stops.],
  ),
  caption: flex-caption([IB10 exclusion and attempt rules.], [IB10 exclusion and attempt rules, registered before the first episode.#fig-source("5.29")]),
) <tab:ch5-exclusions>

*Caps.* A wall-clock cap of 6 h per invocation, with an episode started only if it could finish before the deadline less a teardown reserve; a per-episode spend guard of \$0.50; a total of \$3.00; and no cap on analyses #ev("5.29").

=== IB10 grounder-default run

*Design.* The first episode was an Arm A smoke with the safety fix switched on. It counted as Arm A's first episode only if its harness gates passed and the owner accepted it. The arms then alternated, C first, from e02 C and e03 A to e10 C, for five Arm C episodes and five Arm A episodes including the smoke #ev("5.30"). Scene, seed label, bring-up, overlay, outcomes and exclusion rules are those of the first IB10 run unless the addendum states otherwise. Both arms use one overlay and differ only in the backend M5 starts with #ev("5.30").

*Caps.* A cumulative wall-clock cap of 5 h over all invocations, a total spend of \$1.00, and a per-episode guard of \$0.25 for Arm A; Arm C makes no calls #ev("5.30").

*Post hoc re-run.* After the results of the registered run were known, the owner asked for one Arm C slot in the registered exclusion class to be re-run. An amendment registered that re-run before it started. It allowed exactly one launch with no bring-up retry, kept the registered invalid-jam rule (the re-run counts only if it forms a valid jam), and required that Arm C be reported both before and after the re-run, with its post hoc status stated #ev("5.31"). This report follows that rule.

=== Safety gates

Safety gates are validity conditions, not hypotheses. A breach is reported as a safety finding and the episode is scored as it ran #ev("5.32"). Three distances must be kept apart: 0.45 m is M4’s proximity latch and the conflict definition, 0.20 m is the hard-contact floor at which M4 stops a pair, and 0.18 m is the GT centre-distance threshold that the gates use as a proxy for robot-robot contact #ev("5.43") #ev("5.32").

In tranche 1 the gates were #ev("5.32"):

- a *contact gate*: no robot pair below 0.18 m GT centre distance at any time, from an all-pairs scan of ground truth because the simulator's contact field is a stub, and no floor stop in M4’s log. The gate covers robot pairs only; contact with the rack islands was not gated, and a later offline distance recompute flagged one possible millimetre graze with a rack island in tranche 1, which is not established as a contact (Chapter 6) #ev("6.01");
- a *floor gate*: M4’s start-up line must show the 0.20 m floor, otherwise the chain stops;
- a *condition gate* per arm: for Arm A, every grounded artifact carries the escort and shield flags; for Arm B, no decision artifact, no analysis line, exactly one status line, one task log and a non-empty scene log, so that a crashed M5 cannot pass as silence;
- an *escort and park check*: the escort legs of every dispatched yield are compared with the 0.45 m park clearance and flagged when below it;
- a *pin gate* before every episode.

In both IB10 runs the floor was installed for every arm and gated on M4’s start-up line. Floor stops are outcomes: they make an episode a failure, but the run continues #ev("5.33"). The grounder-default run also had a smoke pass rule: harness gates passed, no floor stop, no GT frame with a pair below 0.18 m, and no command stalled to its deadline by a hold that only the safety fix can cause #ev("5.33"). Arm A's condition gate checks that every artifact names the expected served model. Arm C's checks that no model was served, no token was billed, and every dispatch is the scripted `junction_clear` with provenance `m3_default` #ev("5.20").

One safety caveat was known in advance. A coordination command exempts the robots inside it from M4’s proximity check against each other. A `junction_clear` phase names all four robots, so the latch does not protect them from each other, and the floor is the only backstop for those pairs #ev("5.33").

== Analysis Plan <sec:ch5-analysis>

=== prereg-v3 tranche 1

The estimand is the mean paired difference between Arm A and Arm B, per measure #ev("5.34"). Pairs are formed by seed. A cost guard can stop only the arm that spends, so each pair is compared on a common window $tau_i = min(T_("end",A,i), T_("end",B,i))$: the throughput difference at $tau_i$, the makespan difference with both truncated at $tau_i$, and the delay difference over segments departed before $tau_i$ #ev("5.34"). The interval is a paired percentile bootstrap over seed pairs, with 10000 resamples, random seed 20261021 and 95 % coverage #ev("5.34") @Efron1994introduction. Identical arms give a difference of 0 with the interval [0, 0]. Per-conflict measures enter a pair's difference only for conflicts with onset at or before $tau_i$, and they are reported as degenerate, because Arm B makes no analyses #ev("5.24").

Within each arm, completeness is the proportion of non-censored episodes that are complete, with a Wilson 95 % interval @wilson1927probable and the count of censored episodes. Makespan is summarised by a Kaplan-Meier curve @kaplan1958nonparametric and the restricted mean up to the arm's smallest $T_"end"$. The throughput curve is the mean of $Theta_e (t)$ over the episodes still observed at $t$, reported with the number at risk #ev("5.34"). A naive mean over censored runs is never reported.

Two properties of this plan matter for reading Chapter 6. With five pairs, a bootstrap over pairs can draw only a small number of distinct resamples, so its percentile interval is coarse and its nominal coverage is not assured. And the plan registers no directional test: the interval describes the size and uncertainty of the difference, and does not test a hypothesis #ev("5.02").

=== IB10

The IB10 registration rules out inferential statistics. The episodes are repeated runs of one near-deterministic scene on one machine, so they are not independent samples, and the registration therefore reports counts only, with no p-values and no confidence claims #ev("5.35"). The grounder-default addendum repeats the rule: no p-values, no intervals, and no quantitative reading of time differences between Arm A and Arm C, because Arm C dispatches without model latency and one cool-down later #ev("5.35").

The registered analysis is therefore descriptive. Per arm it reports resolved episodes out of valid ones, successes, arrivals out of four per episode, censored times to full resolution, the minimum GT distance, floor stops, and the provenance label of each Arm A episode. An exact test or an exact binomial interval could be computed on such counts, but it would rest on the independence assumption that the registration rejects. If Chapter 6 shows one, it is labelled as unregistered and illustrative only.

=== Separation of evidence

No measure is pooled across the three comparisons or with the bench. Arm C is compared only with the Arm A of its own run, and the first IB10 run is a separate, unpooled reference for the second #ev("5.20"). The failure-cause classification keeps the registered tranche, the pilots and the November takes apart in every table and pools no outcome.

== Failure-Cause Classification <sec:ch5-failure-cause>

The comparison of Layer 2 on against Layer 2 off says how many episodes of the five-robot S1b scene finished, not why the others did not. This section describes an additional analysis that assigns a cause to what did not finish. It is exploratory and post hoc: it was designed after the tranche-1 results were known and after the pilot episodes had run, and its rules were written down and frozen before any episode was coded #ev("6.60") #ev("6.61"). The section states the procedure as the rubric and the rating protocol specify it; the rating was not complete when this report was written, and its results are held in @sec:res-failure-causes. #todo[TBD-M01: state the final rating procedure, including any second rating round and how it differs from the first, once the reconciliation report exists.]

=== Failure units <sec:ch5-fc-units>

A *failure unit* is the thing that receives a cause. It is defined from ground truth alone, so that it exists in every arm. A unit is either a conflict episode of the scorer (@sec:ch5-measures) that is still open at the last ground-truth sample, or a *lone stall*: a robot that moved less than 0.05 m in the last 60 s of the episode while it was not waiting at a task node and was not part of a conflict unit. A robot that had finished its last task and was parked is not a failure unit and is listed separately. Each unit has an onset time, the start of the conflict or of the stall, and an episode can hold several units or none #ev("6.60").

=== Cause classes <sec:ch5-fc-classes>

Each unit receives one *primary* cause and any number of *contributing* causes. Codes are assigned to events, such as an analysis, a dispatched or withheld command, or a command that ended in failure. There are four classes of cause, and a fifth code for evidence that is missing #ev("6.60").

- *Decision (V).* The model's answer was missing or unusable, missed the conflict, left out a robot that had to act, named a role that the robot had no room to perform while another robot had room, or contradicted its own plan. Example: a decision names as yielder a robot with no room behind it while its partner has room.
- *Grounding and verification (G).* M3 or the plan verifier refused, replaced or altered a sound decision, or let an unsafe manoeuvre through. Example: a feasible yield is refused by a geometric check, or a retreat leg is dispatched through a declared rack.
- *Execution (X).* A command was dispatched as intended and the robots did not carry it out: a manoeuvre failed or timed out, navigation made no progress, perception lost a robot, or the proximity latch left two robots pinned. Example: a backing manoeuvre ends against the face of a rack.
- *Environment geometry (EG).* The scene left no way out: no robot of the unit has a straight move that clears its neighbours and no hypothetical decision would ground to motion, or an obstacle that the scene file does not declare meets a robot of the unit. Example: a robot boxed in by walls and two neighbours.
- *Undetermined (U).* The evidence needed to apply the rule is missing, and the code names what is missing. Raters do not guess.

Two offline tests support these codes. The first substitutes every hypothetical decision of a fixed set through the pinned grounder, on the scene snapshot of each analysis, and asks whether any of them would have produced a motion for a robot of the unit. Before it is used at a snapshot, the recorded decision must re-ground to its recorded command. This fidelity check passed for #todo[TBD-R01: fidelity check passes as written, all Layer-2-on episodes, count] of #todo[TBD-R02: recorded positive decisions re-grounded, count] recorded positive decisions as written, and for #todo[TBD-R03: fidelity passes with stage-2 label and task intents added, count] with the stored second-stage label and the task intents added #ev("6.62"). The second test is purely geometric: whether any robot of the unit has a straight move in one of eight headings that reaches the required distance from every other robot without passing within 0.14 m of a box or a robot #ev("6.60").

=== Primary-cause rule <sec:ch5-fc-rule>

The primary cause follows an ordered rule in which the first step that applies decides. A unit whose evidence is missing is undetermined. If a robot of the unit received a dispatched command in the 60 simulated seconds before the onset, or was executing one at the onset, the walk starts at that command, so that a state a command produced is coded by that command and not by geometry; otherwise a geometry check at the onset applies. The unit's events are then read in time order and the first deviation decides, whether it is an analysis coded as a decision cause, a grounding outcome, or a command outcome coded as an execution cause. When one event carries several codes the most upstream class wins, except that an unsafe leg is coded before the execution failure of the same leg, and all other codes seen on the unit are contributing #ev("6.60").

=== Raters, blinding and agreement <sec:ch5-fc-raters>

Two independent raters code every unit, each a separate agent given the frozen rule and evidence sheets computed mechanically from the run bundles #ev("6.60") #ev("6.61"). #todo[TBD-M02: state who or what the two raters are, and whether a human check was added.] Neither sees the other's output, any report's stated cause, or the scorer's attribution labels. The evidence sheets hide the arm, the episode label, the seed, the outcome and the request identifiers #ev("6.62"). The arm cannot be hidden completely, because the content of a decision reveals it, so only the fields derived from ground truth are coded blind to arm, and each rater codes these before opening the events sheet #ev("6.61"). Agreement on the primary class is reported as raw agreement and Cohen's kappa, and agreement on the full code as raw agreement, for each stratum. Disagreements are resolved by re-reading the rule, with the resolution and its reason recorded, and a case that stays open stays undetermined. Only after reconciliation are the opaque identifiers mapped back to episodes and arms #ev("6.61").

=== Strata, frozen outcomes and the Layer-2-off arm <sec:ch5-fc-strata>

The analysis covers 33 episodes in three strata that are never pooled: the 10 episodes of registered prereg-v3 tranche 1 (five seed pairs, Arm A and Arm B), the 21 ER-2 pilot episodes that preceded it, and two November takes, one demonstration and one validation (the two are tabulated together only for coding; no outcome is pooled). Pilot episodes that the batch stop rule ended early are tabulated apart from those that ran to the horizon. The pilot episodes with a scripted echo model and the bundles of the v4 shadow are excluded #ev("6.61") #ev("6.62"). The registered episodes are never pooled with the exploratory runs, in any table.

The outcome fields of every episode (tasks completed, completeness status, censor reason, end time, the conflict and detection measures and the ground-truth minimum pair distance) were copied from the scorer files and frozen before coding. No episode is rescored, no historical record is changed, and the original outcome of every episode stands as reported in Chapter 6 #ev("6.60").

In the Layer-2-off arm no analysis is made and no command is dispatched, so the decision and grounding codes are not applicable by construction, which is different from being absent. Its units are coded with the environment, execution and undetermined codes only, and each carries a context code that records the absence of a Layer 2 action by design. Whether a Layer 2 action was available is reported as a yes or no and is never used to assign a decision or grounding code. The arms are therefore compared only on these codes and on the outcome fields #ev("6.60").

=== Interception analysis <sec:ch5-fc-intercept>

Three mechanisms were written after the pinned runtime and were not in the runtime that produced the episodes (@sec:impl-later): an escort obstacle guard and a reverse obstacle guard in M3, which refuse a leg whose straight path, grown by the robot half-width plus a margin, crosses a declared obstacle #ev("6.13"), and a stall abort in M4, which ends a primitive that commands motion while the robot does not move #ev("6.18"). The interception analysis asks, offline and for each dispatched leg linked to a failure unit, which of them would have refused or aborted it #ev("6.61"). A leg is linked to a unit by the chain rule of the primary-cause rule. #todo[TBD-M03: state which dispatched legs are in scope of the interception analysis and why, from the reconciliation report.] The physical outcome of a leg comes from ground-truth poses recomputed against the footprint geometry of the scene, because the contact fields of the October logs were empty #ev("6.12"). Following the criterion of the guard replays, a refusal or abort is *justified* when the leg met an obstacle or was pinned, or came within the guards' 0.05 m margin, and a *false positive* when the leg ran to completion with clearance at or above the margin; legs that never reached an obstacle are *untested* #ev("6.13"). #todo[TBD-M04: confirm the justified and false-positive definitions, in particular for the stall abort, against the interception table of the reconciliation report.] A unit counts as intercepted when at least one linked leg would have been refused or aborted by at least one mechanism. The stall-abort column is computed from the committed detector #ev("6.61").

Two sensitivity analyses were declared before rating, are labelled post-freeze, and are reported beside the primary coding and never in place of it #ev("6.61"). *S1* also links a command to a unit when the commanded robot is in the unit and, from the end of the command's motion to the onset, stayed continuously within 0.05 m of the same box or within 0.45 m centre distance of the same robot with no later command to it. *S2* recomputes the straight-move test with the rule that the obstacle guards use, under which a robot that starts inside the required clearance may move along or away from the obstacle but never deeper.

== Offline v4 Bench <sec:ch5-bench>

The v4 bench is an offline test bed for M2. It replays decisions on S1b scenes recorded live, re-grounds them with the production M3, and scores them against the A33 ground-truth definitions, so a candidate is judged on what would happen downstream rather than on its text #ev("5.37"). Nothing in it is executed in simulation. It is exploratory, its scenes are neither unseen nor representative, and it is never pooled with prereg-v3 #ev("5.37").

*Corpus.* 187 recorded analyses from 31 live S1b episodes: the pilots E6 to E26 and the episodes of tranche 1. As recorded live, 149 of them carry a valid decision and 137 are positive; this is the composition of the corpus, not a bench result #ev("5.36"). No camera frame was kept in any batch, so every replay sends a neutral grey image and the bench is text-only on this data #ev("5.36"). Before scoring, the offline M3 and the classical chooser are checked against the live record for the same items. The _classical chooser_ re-runs the rule-based reasoner that served as Arm B in prereg-v1: a first-come-first-served passing order with a commitment tiebreak, in which the last robot to arrive yields #ev("5.49"). In the bench it is a decision-level reference only. Nothing it chooses is executed, and it does not serve as the comparator registered for RQ2 and RQ3 in any experiment reported here.

*Modes.* `recorded` scores the stored ER-2 answer without any call. `classical` re-runs the classical chooser on each item's history. `replay` rebuilds each item's request through the production prompt builder, checks that the prompt hashes to the stored live prompt, and calls a backend behind a content-hash cache #ev("5.37").

*Metrics.* M3 feasibility: a positive decision is feasible when the real grounder returns a command without a refusal. Cluster coverage: every GT conflict active at the item's time shares at least one robot with the decision. Involved-robot F1, as in @eq:ch5-f1. Yielder agreement with the set of yielders M3 can execute. False-positive rate on items with no active conflict. Cost and latency #ev("5.37").

*Variants.* Four prompt variants were defined:

- *baseline*: the live prompt, unchanged #ev("5.39");
- *grounding-first*: before the model is asked, the variant probes every pairwise `yield`, `reverse`, `reroute` and `temporary_wait` with the real offline M3, keeps only the options M3 executes as asked, and appends them as a numbered list ending in "none of the above"; the model answers with an option number #ev("5.38");
- *grounding-first with cluster candidates*: robots are grouped from the scene state alone (stopped, slow or stale robots within the classical conflict radius of 1.5 m form a group), and group-level options such as a multi-passer yield are added #ev("5.40"). The grouping rules were tuned on the same 187 items, so they are not independent of the ground truth #ev("5.40");
- *per-cluster choice*: one answer slot per observed group, each with its own "none feasible", validated against a per-item answer schema and re-asked on failure. Each chosen option is grounded alone; no merged command is ever grounded #ev("5.41").

Replays used ER-2 and Claude Sonnet 5.5. A shuffled-option control permuted the options with seed 20261023 to expose position effects. The replays could not be run at temperature 0.0: the ER-2 interface has no temperature field, and the Sonnet backend does not send non-default sampling because the model rejects it. Each call therefore records the sampling actually sent #ev("5.39"). A fixed chooser that takes the first listed option in every group serves as the reference. Options are ordered by the generator, so this is a default-ordered choice, not a blind baseline #ev("5.41").

*Live shadow (Stage 1).* The per-cluster variant was also run as a live shadow on S1b. In each analysis the ordinary Arm A loop decided and dispatched as before, and a second, per-group M2 call was grounded and checked but never dispatched. It ran 7 episodes on seed positions 21 to 27, on the v4 code rather than the v3 pinned runtime #ev("5.42"). It can show whether the per-group path runs live, not whether per-group dispatch would resolve anything.

== Offline Analyses <sec:ch5-decision>

Three analyses were made after the live comparisons, on recorded data or in offline replays. None executes anything in simulation, none is pooled with a live comparison, and each is described here only by its method and by what it can and cannot show.

=== Head-on decision analyses

*Re-score of recorded decisions.* The re-score asks whether, in the recorded head-on scenes, the model names the oracle-correct yielder more often than a position-only rule, and whether any advantage is explained by a preference for `robot_1` or for the robot listed first #ev("6.08"). It reads every recorded live head-on decision. The unit is the run: the first positive analysis of each run, that is, the first analysis that detects congestion and names a yielder. Each run's choice is scored against the scene's oracle yielder beside three references: a position-only rule (the classical first-come-first-served reasoner, recorded or recomputed from the scene log, and the static rule label of each scene file), a chooser that always names `robot_1`, and the yielder that M3's feasibility gate would ground, derived from the decision record #ev("6.08"). The analysis was not pre-registered, is post hoc, and reports counts only, with no p-values or intervals. The grounded yielder is derived from artifact fields; dispatch itself was not checked against M4’s logs #ev("6.08").

*Pre-registered offline replays.* Three replays were each registered before their first paid call; the swapped-ID and improved-annotation replays were amended, with dated entries, while they ran #ev("6.09") #ev("6.10") #ev("6.11"). They use recorded standoff scenes of the same family, half with the box on each side, two robots and the first decision only, and they vary one input at a time:

- the *swapped-ID replay* exchanges the labels of the two robots in the scene, and adds arms with a neutral grey image and with the obstacle text removed, under both listing orders and with two replicates, so that a choice driven by the scene can be told apart from one driven by the label or the listing slot. Its pre-stated scene-use rule requires a high share of correct choices in every label and slot combination; the arms without obstacle text and the rule for image use were added by its third amendment, during the run #ev("6.09");
- the *JSON-only replay* replaces the answer-format block of the prompt with a single JSON-only line for every model, to test whether one prompt text is usable by every provider and to make the models' answers assessable #ev("6.11");
- the *improved-annotation replay* shows the frame with legible labels and no obstacle text, with and without a neutral sentence that a robot backing up needs free floor behind it #ev("6.10").

Each replay states a stop rule for provider limits and labels any cell with too few decisions "not assessable". They can show whether a model's choice follows the scene in these two-robot scenes; they cannot show anything about execution or about other scene types.

=== Plan-influence trace

The trace asks whether the model's plan changed what the robots were commanded to do #ev("6.02"). It covers every recorded live four-robot analysis with a non-mock model. Each recorded decision is re-grounded with the runtime's own functions, using the artifact's recorded parameters, feasibility mode, stage-2 answer and scene geometry. A comparison is trusted only if re-grounding the recorded decision reproduces the recorded dispatch exactly (the fidelity gate). The trace then re-grounds the same decision without its proposed plan, and separately with the scripted Arm C decision, and compares the commands #ev("6.02"). Every claim is labelled as verified from a record or inferred. The trace shows which executed commands depended on the plan and which on the other decision fields; it cannot show whether a different plan would have changed the outcome, and it covers only the runtime and the switches that were active in the recorded runs.

=== Offline contact recompute

Because the ground truth's contact lists were a stub that always logged an empty list #ev("6.20"), contact was recomputed offline from recorded poses #ev("6.12"). For each ground-truth row, at 10 Hz, the recompute places the robot's planar collision footprint from its URDF at the logged pose and measures the signed gap to every declared box (walls, racks, barrier blocks, declared obstacles) and to every other robot. A gap of at most 5 mm counts as a contact entry, and one second of consecutive entries as a sustained contact; the 5 mm threshold was fixed before the suspected cases were examined #ev("6.12"). A recorded robot-robot contact serves as a positive control. The recompute is a geometric proximity measure, not a physics contact. The same computation was later added to the ground-truth logger on a separate branch and checked in one live validation take, which reproduced the offline values row by row, but its logged lists stayed empty, so the take did not show entries appearing at a real contact #ev("6.17"). The recompute can therefore flag where a robot met an obstacle; its figures are treated as pending validation, and only a contact confirmed independently, from poses, geometry and the recording, is cited as a finding.

== Demonstration Campaign <sec:ch5-demo>

The demonstration campaign recorded live takes of the full pipeline in four scenes to show what it does, not to measure how well it does it #ev("5.51"). It was registered before any machine time was used, with caps of 12 machine-hours and \$10 in all, and every take, including every aborted one, was archived and labelled #ev("5.51").

*Scenes and configuration.* The four scenes are the IB10 intersection, the convoy counterflow scene, the head-on corridor with obstacle, and the five-robot S1b scene at seed position 21, an exploratory seed outside the registered confirmatory list that earlier pilots and the live shadow had already used #ev("5.51"). Every take runs Layer 2 on with the live ER-2 model; there is no Layer-2-off or scripted arm. Every take runs with the safety settings of the second IB10 run, the safety-exemption fix and the 0.20 m floor, and M4’s start-up line must confirm both before a take counts #ev("5.51"). Grounding and feasibility checks follow each scene's earlier record, so the yield feasibility gate is on in the head-on corridor and off at the intersection, as in every IB10 run. Each scene uses the settings of that record: the 2026-11-14 IB10 configuration for the intersection, the registered legacy grounding for the convoy, the September production configuration (prompt version 2, plan channel off, feasibility gate in `swap` mode, obstacle text on) for the head-on corridor, and the tranche-1 Arm A procedure for the five robots. The intersection alone adds the prompt condition that lists the plan actions the verifier accepts, together with the plan-order switch (@sec:impl-later) #ev("5.51"). The registration was amended during the campaign: once to move machine-time shares between scenes, and once to add convoy takes 4 and 5, which ran with the queued-robot hold switched on (@sec:impl-later) #ev("5.51") #ev("6.19"). Its closing note records the remaining deviations from the planned takes.

*Take rule.* One take runs per invocation. After each take the operator reads its summary and either stops the scene, at the first take that meets the scene's demonstration goal, or runs another, up to five valid takes per scene. A start-up failure of the navigation stack is retried as a new attempt of the same take, up to three per scene. Takes that were not chosen are listed, and the choice of the take shown in a video is disclosed #ev("5.51").

*Labels.* Every take receives exactly one label #ev("5.51"):

- *Unresolved failure*: not every robot arrived at its goal.
- *VLM-driven execution*: at the intersection only, a resolved take in which every dispatched decision is a `junction_clear` whose plan passed the audit unchanged, whose dispatched back-out order, yielder and phases match that plan with no fallback or stage-2 command, and whose back-out order differs from the grounder's default order for the same snapshot. The default order is recomputed offline. A take earns this label as soon as the back-out order differs, however small the difference in cost, so the label says that the model's order was executed, not that it improved the outcome.
- *M3-default resolution*: every other resolved take, including any take whose yielder the feasibility gate swapped or in which a fallback command ran. Outside the intersection the label "VLM-driven" is not used.

*What the campaign can and cannot show.* With one to five takes per scene and the stop rule above, the takes give no rate and no comparison with Layer 2 off; nothing from them is reported as a percentage. Recording changes the real-time factor, so no timing from a take is comparable with an experiment. The configuration differs from the evaluated runtime in the ways listed above. The campaign shows what the pipeline did in these takes, and it can expose failure modes that the scored experiments did not exercise.

== Threats to Validity <sec:ch5-threats>

The threats below were known before the data they affect was collected. Each is stated with its consequence for the claims and with what the design does about it.

=== Internal validity

*M3 repairs or replaces the model's plan.* M3 verifies every plan and repairs or replaces it when it is infeasible. The IB10 registration records that in the earlier live pilot every IB10 plan was repaired or replaced by M3, and gives this as the reason for its claim wording #ev("5.17"). An Arm A success therefore shows that the *pipeline*, VLM plus grounding, clears the jam, not that the VLM's plan does. The design answers this in three ways. Provenance labels on every dispatch record the audit of the model's plan, and a re-grounding without the plan shows which executed commands came from the model #ev("6.02"). Arm C runs the same pipeline with no model, handed the strategy and robot set, so it isolates M3’s default plan content #ev("5.20"). And the claims of this report are worded about the pipeline. Arm C does not remove the confound completely: it does not test strategy or robot selection, which it receives from the script, and it cannot re-plan after a failure, which Arm A can #ev("5.20").

*The Layer-2-off control is a deterministic freeze.* Arm B is Layer 2 off, not a classical coordinator. In IB10 nothing acts on a formed jam once Layer 2 is off, so Arm B is expected to repeat one frozen state; it is a latch baseline. The B against A contrast is pipeline on against pipeline off, and says nothing about a VLM against a classical coordinator #ev("5.17").

*Arm C timing differs.* Arm C answers its first trigger with "no congestion" and dispatches one cool-down later without model latency, so its times are not directly comparable with Arm A's #ev("5.35").

*Seeds were not unseen.* All 20 registered S1b seeds had run as pilots before tranche 1, so pilot-informed expectations existed for them #ev("5.44").

*Measurement.* The S1b delay baseline was harvested on a different machine from the tranche, a recorded limitation #ev("5.25"). Type-label accuracy depends on an accepted set chosen by ruling #ev("5.24"). Several A33 parameters were proposals ruled at their defaults, but all were fixed before any confirmatory number was computed #ev("5.11").

*Post hoc decisions.* The re-run of one grounder-default slot was decided after the results were seen. It was registered before it ran and is reported both ways #ev("5.31").

=== Statistical conclusion validity

*Small n.* Tranche 1 has five pairs, the first IB10 run five episodes per arm, and the grounder-default run five per arm. Only large, consistent differences can be seen at all, and the absence of a difference is not evidence of no effect. The tranche-1 bootstrap over five pairs has few distinct resamples #ev("5.34"). The failure-cause classification has 10, 21 and 2 episodes in its three strata.

*Why five per arm, and why Layer 2 off as the only live control.* Five per arm is not the result of a power analysis. In prereg-v3 it is the first tranche of the registered 20 seeds per arm #ev("5.04"), and tranche 2 was not run (@sec:ch5-rq). The constraint the records name is machine time. At a real-time factor of about 0.18, a full-horizon S1b episode took about 55 min of wall-clock time and the ten tranche-1 episodes took 9 h 18 min on one GPU machine; v3 addendum A36 estimated the 30 episodes of tranche 2 at about 28 GPU-hours, with the model's own spend extra and small #ev("5.50"). The IB10 registration fixed five episodes per arm without a stated rationale and estimated 28–35 min per episode #ev("5.50"). The hosted model's spend was capped at \$1.30 for tranche 1 and \$3.00 for IB10 #ev("5.28") #ev("5.29"). Arm B is Layer 2 off because v3 addendum A34 ruled it so, replacing the classical reasoner of v1 #ev("5.46"). No classical rule, such as first-come-first-served or corridor-exit first, was run as a live arm, so every live comparison measures pipeline on against pipeline off, and each further live arm would have cost the same machine time per episode.

*Non-independence.* The IB10 episodes are near-repeats of one scene, which is why no p-values or intervals are registered for them #ev("5.35").

*Exploratory status.* Only prereg-v3 was registered as confirmatory, and its tranche is reported as a pilot. IB10, Arm C, Stage 1, the bench and the failure-cause classification are exploratory and are read as such #ev("5.04") #ev("5.37").

=== External validity

*One scene per experiment.* Each live result comes from one scene: S1b for tranche 1 and IB10 for both IB10 runs. IB10 is a staged, symmetric jam with one correct strategy, and S1b is one floor at one density. Neither result transfers to other layouts, robot counts or congestion types without new evidence.

*Simulation only.* Every scored episode runs in Isaac Sim with simulated sensors and Nav2. The physical TurtleBot3 demonstration described in Chapter 4 is not part of these experiments.

*One model, one runtime.* The live comparisons use one model (ER-2) on one pinned runtime. The bench adds a second model, but only text-only and at the decision level, with grouping rules tuned on the same items #ev("5.40").

*Safety evidence is narrow.* The gates bound the centre distance between robot pairs in these episodes only; no gate measured contact with static obstacles #ev("6.20"). The floor is a push limiter that fires at or after contact, and the coordination exemption leaves the robots inside one command protected only by that floor #ev("5.09") #ev("5.33"). Passing the gates is not a general safety claim.
