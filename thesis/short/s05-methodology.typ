#import "../lib.typ": *

= Methodology <sec:s-method>

== Studies <sec:s-method-studies>

Every scored episode ran in Isaac Sim. The studies differ in what they can show, so @tab:s-studies lists each with its size, evidence grade and registration status; no study is pooled with another, and strata within a study are kept apart. Only the registered five-robot pilot was registered as confirmatory; it is reported as a pilot because only 5 of the 20 planned seed pairs ran, after the authors decided on 13 November 2026 to run the intersection experiment instead #ev("5.03") #ev("5.04"). Each study's full design, measures and procedure are in the Extended Report, Chapter 5.

#[
#show figure: set block(breakable: true)
#figure(
  {
  set text(size: 8.5pt)
  set par(justify: false)
  table(
    columns: (1.5fr, 1.4fr, 0.9fr, 1fr, 1fr, 0.55fr),
    align: left,
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    inset: 3.5pt,
    table.header([*Study*], [*What it compares*], [*n*], [*Evidence grade*], [*Registered before data?*], [*RQ*]),
    [Registered five-robot pilot, 21 Oct 2026 (prereg-v3 tranche 1) #ev("5.03") #ev("5.04")], [Coordination layer on vs off, five-robot scene], [5 seed pairs, 10 episodes], [Registered as confirmatory, reported as pilot], [Yes], [RQ1, RQ2],
    [Exploratory five-robot pilots, 10–17 Oct 2026 (E6–E26) #ev("5.36") #ev("6.61")], [Coordination layer on only, during design tuning], [21 episodes], [Exploratory pilot], [Some batches, as pilots], [RQ2],
    [Intersection run 1: coordination layer on vs off, 13 Nov 2026 (IB10 run 1) #ev("5.17") #ev("5.29")], [On vs off, four-robot intersection], [5 + 5 counted episodes], [Exploratory pilot], [Yes], [RQ2],
    [Intersection run 2: live VLM vs scripted default plan, 14 Nov 2026 (IB10 run 2) #ev("5.20") #ev("5.30") #ev("5.31")], [Live VLM vs scripted default-plan arm, four-robot intersection], [5 + 5 slots, plus one post hoc re-run], [Exploratory pilot], [Yes; re-run registered after the results, before it ran], [RQ2],
    [Offline decision benchmark (v4 bench) #ev("5.36") #ev("5.37")], [Prompt variants and a rule-based chooser on recorded five-robot analyses], [187 analyses, 31 episodes], [Decision-level offline], [Specification only], [RQ1, RQ3],
    [Live per-group shadow run (Stage 1) #ev("5.42")], [Per-group question grounded beside the live loop, never dispatched], [7 episodes], [Exploratory pilot, decision-level], [Design specification before the run], [RQ2],
    [Head-on re-score of recorded decisions #ev("6.08")], [Recorded first yielder vs the correct yielder and three references], [All recorded live head-on runs], [Decision-level offline], [No (post hoc)], [RQ3],
    [Swapped-ID, improved-annotation and JSON-only replays #ev("6.09") #ev("6.10") #ev("6.11")], [One prompt input changed at a time, recorded two-robot standoffs], [First decision per scene, up to three models], [Decision-level offline], [Yes, before the first paid call; two amended while running], [RQ3],
    [Plan-influence trace #ev("6.02")], [Recorded four-robot decisions re-grounded with and without the plan], [41 analyses, 39 past the fidelity gate], [Decision-level offline], [No (post hoc)], [RQ2, RQ3],
    [Plan-order and convoy held-robot prompt checks #ev("6.03") #ev("6.04")], [Prompt conditions on recorded intersection and convoy scenes], [Offline calls; 22 answers per convoy condition], [Decision-level offline], [Held-robot check yes; order check in part], [RQ2, RQ3],
    [Offline contact recompute #ev("6.12")], [Footprint gaps from recorded poses to boxes and robots], [44 bundles], [Offline (geometric); method validated live once], [Threshold fixed before cases were examined], [Safety],
    [Demonstration campaign, 14–15 Nov 2026 #ev("5.51") #ev("6.01")], [Full pipeline, live, four scenes], [13 valid takes], [Illustrative demonstration], [Yes], [RQ2, RQ3],
    [Scripted safety tests, 15 Nov 2026 #ev("6.86")], [One new mechanism per take, scripted decision, no model call], [n = 1 per mechanism (2 takes)], [Scripted safety test], [Yes], [Safety],
    [Five-robot validation take, 15 Nov 2026 #ev("6.17")], [Escort guard armed, contact logging on], [1 take], [Illustrative demonstration (validation only)], [Yes], [Safety],
    [Earlier recorded head-on run, 30 Sep 2026 #ev("6.38")], [One live run on older code, yield gate on], [1 run], [Illustrative demonstration], [No; selected because it qualifies], [RQ3],
    [Physical TurtleBot3 demonstration, 12 Nov 2026 #ev("4.28")], [Pipeline on hardware, no navigation goals], [4 scenarios, one run each], [Illustrative demonstration], [None recorded], [None],
    [Failure-cause classification and interception analysis #ev("6.60") #ev("6.61") #ev("6.63")], [Primary cause per failure unit; interception by later mechanisms], [55 failure units, 33 episodes, three strata], [Post hoc classification], [Rules frozen before coding, after outcomes were known], [RQ2],
  )
  },
  caption: flex-caption([Studies in this report.], [Studies in this report, "Registered" means written down before the study ran; only the registered five-robot pilot was registered as confirmatory. RQ: the research questions (@sec:s-intro-rq) a study informs; "Safety" marks studies that inform none.]),
) <tab:s-studies>
]

== Scenes, Arms and Measures <sec:s-method-scenes>

*Scenes.* The *four-robot intersection* stages a jam at the centre of a cross aisle, one robot per arm, each bound for the opposite arm #ev("5.16"). The *five-robot pickup-and-delivery scene* has two rack islands and a stream of five tasks per robot, in which conflicts arise on their own #ev("1.14"). The demonstration campaign adds a *four-robot convoy counterflow* scene (a counter-flow robot meets a platoon of three in a narrow gap) and a *two-robot head-on corridor with an obstacle*, where only one robot has room to back out #ev("5.52").

*Arms.* The control in every live comparison is the *coordination layer off* on identical code: only each robot's local navigation runs. Intersection run 2 adds a *scripted default-plan arm* that skips the VLM call, is handed `junction_clear` for all four robots and runs the grounder's own default plan #ev("5.20"). It therefore isolates the content of the model's plan, not its choice of strategy.

*Measures.* The intersection runs score resolution (all four robots at their goals by the horizon), arrivals and time from jam onset #ev("5.17"). The registered pilot estimates, with paired bootstrap intervals and no registered direction, the effect on completion, throughput and delay, and scores detection, type accuracy and the involved set of the coordination-layer-on arm against ground-truth conflicts #ev("5.02") #ev("5.03"). Safety is gated on ground-truth robot-pair centre distance (no pair below 0.18 m, no floor stop); the simulator's contact lists were a stub, so contact with static obstacles was not measured live #ev("6.20").

== Failure-Cause Classification <sec:s-method-fc>

To ask where unfinished five-robot episodes stopped, a post hoc rubric divides 33 episodes into failure units (a conflict, or a robot that stopped moving) and assigns each a primary cause: the model's decision, grounding and verification, execution, environment geometry, or undetermined; contributing causes are recorded beside it #ev("6.60"). Two independent raters, both language-model agents with no recorded human check, coded every unit from frozen evidence sheets; their codes were reconciled, with both raters' codes kept #ev("6.61") #ev("6.63"). The rule was frozen before coding but after the outcomes were known, the authors had read earlier diagnoses of some episodes, and the blinding was not clean #ev("6.63"). The three strata (the registered pilot, 21 exploratory pilot episodes from October 2026, and two November takes) are never pooled. A separate interception analysis asks which recorded legs the later obstacle guards and stall abort would have refused or aborted, not whether the scenes would then have resolved #ev("6.63").

== Threats to Validity <sec:s-method-threats>

- *Small, near-repeat samples.* Five episodes or seed pairs per arm on one scene per live study; the intersection episodes are near repeats, so no p-value is given.
- *One model live.* ER-2 ran every live comparison; other models ran only offline or earlier #ev("6.16").
- *Listing order.* Robots were listed in ascending order in the live studies, so a model's yielder choice cannot be separated from a slot prior #ev("1.15").
- *Analyses defined after the data.* The head-on re-score, the plan-influence trace, the plan-dispatch recomputation and the failure-cause rule came after the live data #ev("6.08") #ev("6.02") #ev("6.51") #ev("6.61").
- *Selected demonstrations.* The take rule stopped each scene at the first take meeting its goal, and the intersection take shown was selected for its label #ev("5.51") #ev("6.45").
- *Unreviewed sources.* The source reports were on unpushed, unreviewed branches when this report was written #ev("6.16").
