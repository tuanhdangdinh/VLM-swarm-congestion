# Thesis Report Change List (Evidence up to 2026-11-15)

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: statements to change in the thesis report, results to add, drop or relabel, new limitations, pending items and figures to make, mapped to the evidence of 2026-11-15.
- Rev 2 (2026-11-15): added section 10, "Scenario Images: What to Insert and Where" (15 extracted stills with md5s, a placement table, Typst snippets, reading order, outdated figures, missing figures).
- Rev 3 (2026-11-15): added section 10.8, the drawn take 5 decision-flow figure with real output and a head-on gate contrast strip (files with md5s, insertion point, caveats).
- Rev 4 (2026-11-15): added section 10.9, a simplified take 5 figure for the main text (four blocks; only the back-out order comparison marked as the VLM's contribution); the detailed 10.8 figure moves to a new appendix as the traceable reference, with one added caption sentence on the safety scope.

---

## How to Use This Note

- This is a working note for the thesis author. It contains no new data. Every number below is copied from the cited report and section.
- Short names for sources (full paths, branches and commits are in "Source Key" at the end):
  - `REG` = thesis evidence register (this branch); `DC` = demo campaign results; `PT` = plan-influence trace; `PC` = order-channel plan check; `CH` = convoy held-robot prompt check;
  - `IBL` = IB10 live resolution (Layer 2 on vs off); `IBS` = IB10 safety smoke and grounder-default arm; `SX` = safety-exemption fix;
  - `RS` = head-on VLM-vs-rule re-score; `SW` = swapped-ID replay; `IA` = improved-annotation replay; `JO` = JSON-only replay;
  - `T1` = prereg-v3 tranche-1 report; `GB` = S1b grounding-bottleneck report; `GC` = GT contact logging and recompute; `EG` = escort obstacle guard.
- Paste-ready wording follows the thesis's own style ("this report", `#ev("x.yy")` tags). Where a new source is cited, the text says `#ev(NEW: <short name>)`; section 7 lists the new Evidence Index rows these need.
- Rules carried from `REG` ("Wording to avoid"): no "the VLM resolves congestion", no "0 contacts" or "collision-free", no "the VLM uses the image", no rate from demo takes, never pool the two IB10 runs, never cite the audit's "about 110 decisions".

---

## 1. Which Thesis File This Refers To

| Item | Value |
|---|---|
| Thesis source | `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-thesis/thesis/main.typ` (Typst), which includes `thesis/chapters/00-front.typ` to `09-appendix-evidence.typ`; Evidence Index rows in `thesis/evidence/ch1.typ` to `ch6.typ` |
| Branch | `docs/thesis` (worktree `vgu-vlm-swarm-thesis`), HEAD `90b03d9` (2026-11-14 23:19 +0700) |
| Text read | Working tree on 2026-11-15, including the owner's uncommitted edit to `main.typ` (title page: "Bachelor Thesis" changed to "Project Report"; student name without diacritics). That edit was not touched |
| Language | English throughout, so all replacement wording is in English |
| State of the draft | Chapters 1 to 5 are written. Abstract, Chapter 6 (Results), Chapter 7 (Discussion) and Chapter 8 (Conclusion) are `#todo` skeletons; Chapter 1 has three held `#todo` items |
| Other drafts found | None that is a thesis report. `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/reports/` (untracked) holds nine literature research notes in Markdown (for example "Four way intersection robot congestion.md"); no `docs/thesis*`, and no other `*.typ` or `*.tex` thesis source in the worktrees searched |

Line numbers below are those of the working-tree files on 2026-11-15.

---

## 2. Statements in the Current Thesis That Must Change

Severity: **wrong** (contradicted by evidence), **over-claim** (says more than the evidence), **imprecise** (true but misleading or missing a needed qualifier), **outdated** (superseded by later work or numbers).

Counts: 49 rows: 1 wrong, 8 over-claim, 12 outdated (one of them an outdated number), 28 imprecise. Rows 48 and 49 were added after a review and sit at the end of 2.3.

### 2.1 Front Matter and Chapter 1 (Introduction)

| # | Location | Current text (short) | Why it must change (source) | Replacement (ready to paste) | Severity |
|---|---|---|---|---|---|
| 1 | `main.typ`, title page, line 76 | "Leveraging Vision-Language Models (VLM) for Congestion Management in Warehouse Swarm Robotics" | The evidence credits the pipeline (trigger plus grounder), not the VLM, with clearing jams (`REG` rung a). The title can stay as a topic, but abstract and conclusion must not echo it as a claim. Optional | Keep the title. If a subtitle is wanted: "A VLM-in-the-Loop Pipeline with Deterministic Grounding" | imprecise |
| 2 | `01-introduction.typ`, Problem Statement, line 17 | "an independent safety monitor enforces distance and speed limits on every command" | The monitor checks robot pairs only. No M3 or M4 stage checked an escort segment against static obstacles (`DC` 8.7.3, 8.8) | "...and an independent safety monitor enforces robot-to-robot distance and speed limits on every command, with one exemption for clearing manoeuvres that @sec:design-safety describes; it does not check clearance to static obstacles (@sec:design)." | imprecise |
| 3 | same, line 19 | "These labels record how far the executed command agrees with the model's proposal." | The audit runs after grounding and grounding never reads the plan (`PT` D). Of the 14 accepted four-robot plans (11 of them gpt-4o pilot plans), 6 were not dispatched as written; 0 of 20 ER-2 `junction_clear` plans were accepted (`PT` Answers 3). Parser-nulled plans show as "plan absent" (`PT` Answers 2) | "These labels record how the model's proposal fared in the grounder's audit. They do not show which commands came from the model: in the evaluated runtime the grounder never reads the proposed plan, none of the 20 ER-2 intersection plans was accepted unchanged, and 6 of the 14 accepted four-robot plans, most of them from an earlier gpt-4o pilot, were not dispatched as written #ev(NEW: PT)." | over-claim |
| 4 | same, line 19 | "the command the robots execute is always the grounder's output" | True for the evaluated runtime. The demo campaign switched on an opt-in mode in which a verified plan set the recede order once (`DC` 7.2; `PT` D) | Add after the sentence: "The one exception is an opt-in switch that lets a verified model plan set the order of the back-out phases; it was used only in the demonstration campaign (Chapter 6)." | imprecise |
| 5 | same, line 21 | "a VLM confirms and classifies it from an overhead view" | The model receives the annotated frame plus a text state list. Pre-registered replays found no evidence that the yielder choice follows the scene (`REG` rung e; `SW` What the Thesis Can and Cannot Claim) | "...and a VLM, given the annotated overhead frame and a text list of robot states, confirms and classifies it..." | imprecise |
| 6 | same, line 23 | "and with the grounder alone" | Arm C was handed the strategy and robot set, so it is not "the grounder alone" (`IBS` Interpretation) | "...and with a scripted arm that skips the VLM call, is handed the strategy and robot set, and runs the grounder's default plan." | imprecise |
| 7 | Research Questions, lines 35-40 | "The three live comparisons and the offline bench are kept strictly apart" (four bullets follow) | New work since: demo campaign, head-on re-score, three offline replays, plan-influence trace, order-channel and convoy checks, contact recompute (`REG` Citable Artifacts) | Change the sentence to "The three live comparisons, the offline bench, the demonstration campaign and the offline replays and traces are kept strictly apart and never pooled." Add bullets: "*Demonstration campaign (illustrative).* Ten live takes in four scenes, with all checks on, to show what the pipeline does; no rate is computed #ev(NEW: DC)." "*Head-on decisions (decision level).* A re-score of every recorded head-on decision and three pre-registered offline replays ask whether the model's choice of yielder follows the scene #ev(NEW: RS) #ev(NEW: SW)." "*Plan influence (decision level).* A trace of every live four-robot analysis asks whether the model's plan changed what was dispatched #ev(NEW: PT)." | outdated |
| 8 | same, table `tab:intro-rq-map`, lines 44-57 | four rows | Missing rows for the new evidence | Add rows: "Head-on re-score and replays" / "RQ3, decision level only" / "Position-only rule, always-`robot_1`, and the M3 gate; text and image variants, nothing executed". "Plan-influence trace" / "Model's share in executed plans" / "Counterfactual re-grounding without the plan". "Demonstration campaign" / "Illustration only" / "None; no comparison arm". | outdated |
| 9 | same, line 59 | "RQ4 and RQ5 are not tested by any experiment reported here. ... RQ3 is informed only at the decision level, by the bench and by the presentation-order finding" | The re-score and the offline replays now inform RQ3 (`RS` Conclusion; `SW` What the Thesis Can and Cannot Claim). No source maps them to RQ4, so the RQ4 and RQ5 sentence stays | Keep "RQ4 and RQ5 are not tested by any experiment reported here." Replace the RQ3 sentence: "RQ3 is informed only at the decision level, by the bench, the presentation-order finding, a re-score of all recorded head-on decisions, and pre-registered offline replays that asked whether the model's choice of yielder follows the scene; no tested model met the pre-registered rule #ev(NEW: RS) #ev(NEW: SW)." | outdated |
| 10 | same, line 59 | "so that the model's share in each executed plan is visible" | The label does not show the share: no executed element of the 11 repaired intersection plans came from the model, while decision fields changed execution in 18 dispatches whatever the label (`PT` B) | "...together with the plan-provenance label of its dispatches and, for the four-robot scenes, a re-grounding of each decision without its plan, because the label alone does not show which executed commands came from the model." | over-claim |
| 11 | Contributions, item 2, line 68 | "so the division of credit between model and grounder can be read from the record of each decision" | Same as row 10 (`PT` B, D) | "Every dispatch carries a provenance label and degradation tags. The label records the audit of the model's plan; which executed commands came from the model is established separately, by re-grounding each decision without its plan and comparing (Chapter 6)." | over-claim |
| 12 | Contributions, item 3, line 69 | "An independent monitor holds any pair of robots closer than 0.45 m ... a hard-contact floor at 0.20 m" | The floor acts on M1 centre-to-centre distance (`DC` 11.5). Nothing checked escorts against static obstacles (`DC` 8.7.3) | Append: "The floor acts on the centre-to-centre distance of tracked robot pairs. Neither the monitor nor the grounder checked an escort path against static obstacles, and in one demonstration take an escort drove a robot into a rack island (Chapter 6)." | imprecise |
| 13 | Empirical findings, Presentation order, line 79 | "the robot that one model named to yield followed the robot listed first" | Since confirmed by a pre-registered swapped-ID replay: gpt-4o followed the first-listed slot in 85/96 grey-pair yields (`SW` Results per Model, gpt-4o; quoted in `REG` Two Robots) | Append: "A later pre-registered replay that swapped the robots' labels confirmed this for gpt-4o: its choice moved with the listing, not with the scene #ev(NEW: SW)." | outdated |
| 14 | Empirical findings, "The grounder carries the plan", line 80 | "every plan the model proposed was repaired or replaced by the grounder" | Now stronger and with one exception: the plan changed dispatch in 0 of 39 gated live four-robot analyses (`PT` B); once in the demo, with the opt-in switch, recede order only (`DC` 7.2) | Append: "A later trace of all live four-robot analyses found that the model's plan changed the dispatched commands in 0 of 39 #ev(NEW: PT). In the demonstration campaign, with an opt-in switch on, it changed them once, by swapping the order of two near-equivalent back-out manoeuvres #ev(NEW: DC)." | outdated |
| 15 | Scope, Small samples, line 92 | "The live comparisons have five episodes or seed pairs per arm" | The demo campaign and replays are smaller still (`DC` Final Summary: n is 1 to 5 per scenario) | Append: "The demonstration campaign has one to five takes per scene and is illustrative only; no rate is computed from it." | outdated |
| 16 | Scope, Later extensions, line 93 | "(grounding-first prompts, per-cluster choice, refusal feedback and the fix to the safety exemption) are switched off by default and appear only as exploratory work" | The safety fix was switched on in the IB10 grounder-default run (Chapter 4, line 165 says so). The demo ran a later prompt with an options block and the order switch (`DC` 7.2 check 8; `PC` 10.3). Escort guard and contact logging are built, not run live (`DC` 10) | "Variants built after the pinned runtime are off by default. The safety-exemption fix was switched on in one exploratory IB10 run, and a later prompt that lists the actions the verifier accepts, with the plan-order switch, ran only in the demonstration campaign. An escort obstacle guard and contact logging were built afterwards and have not yet been run live (@sec:impl-later)." | imprecise |
| 17 | Scope, Safety is bounded, line 94 | "The safety gates bound contact in the episodes reported, and no more." | The gates measure robot-pair centre distance only; ground truth's contact lists are hard-coded empty; one sustained robot-obstacle contact was found offline (`REG` Erratum; `DC` 8.7) | "*Safety is bounded.* The safety gates bound the centre distance between robot pairs in the episodes reported, and no more. The simulator's contact fields were a stub that always logged an empty list, so no gate measured contact with static obstacles; an offline recompute found one sustained robot-obstacle contact in a demonstration take (Chapter 6). The 0.20 m floor limits a push at or near contact rather than preventing the approach #ev("1.04"), and passing the gates is not a general safety claim." | over-claim |
| 18 | Report Outline, Chapter 6 entry, line 106 | "the IB10 comparisons, the prereg-v3 tranche-1 pilot, the exploratory findings (presentation order, model refusals, the offline bench) and the physical demonstration" | Chapter 6 needs the new sections (section 3 below) | "...the IB10 comparisons, the prereg-v3 tranche-1 pilot, the head-on decision analyses (re-score and offline replays), the plan-influence trace, the demonstration campaign, the safety and contact findings, and the physical demonstration." | outdated |

### 2.2 Chapter 2 (Background)

| # | Location | Current text (short) | Why it must change (source) | Replacement (ready to paste) | Severity |
|---|---|---|---|---|---|
| 19 | `02-background.typ`, Detection, line 50 | "a stall trigger in the orchestrator decides when to call the model, and the model decides what to do" | The grounder decides what runs; it overturned 37 of 79 head-on yielder choices (`RS` Headline) | "...a stall trigger in the orchestrator decides when to call the model, the model proposes what to do, and the grounder decides what is executed (@sec:design)." | imprecise |
| 20 | Grounding, Gap, line 76 | "a deterministic, geometry-driven grounder that checks each proposed manoeuvre against the scene" | Escort segments were not checked against static obstacles (`DC` 8.7.3) | "...that checks each proposed manoeuvre against the scene (escort paths excepted, a gap found later; @sec:design-grounding), repairs or replaces it..." | imprecise |
| 21 | Research Gap, line 119 | "none reports the per-dispatch provenance of the executed plan as an experimental quantity" | The label is the provenance of the audited proposal, not of the executed plan (`PT` D) | "...as far as we found none reports, per dispatch, how a model's proposed plan fared in such a check and whether it changed what was executed." | imprecise |

### 2.3 Chapter 3 (System Design)

| # | Location | Current text (short) | Why it must change (source) | Replacement (ready to paste) | Severity |
|---|---|---|---|---|---|
| 22 | `03-system-design.typ`, Requirements, line 13 | "The design therefore uses the VLM where it adds information" | Design intent; the evidence does not show the model adds scene information (`REG` rung e) | "The design therefore uses the VLM where it is expected to add information..." | imprecise |
| 23 | Two-Layer Architecture, Effective decision rate, line 39 | "One stage-1 call to ER-2 took about 3.2–3.8 s" | Campaign calls on the later, longer prompts took 6.7–11.5 s (convoy, `DC` 5.1) and 7.0–13.0 s (five robots, `DC` 8.1); ER2LIVE 4.9 s (`DC` 11.1). Report both, different prompts | Append: "In the demonstration campaign, on longer prompts, calls took 6.7–11.5 s in the convoy scene and 7.0–13.0 s in the five-robot scene #ev(NEW: DC)." | outdated (number) |
| 24 | Intervention principle, line 41 | "every motion it causes remains subject to the Layer 1 safety monitor, within the limits of the clearing exemption" | Monitor covers robot pairs only (`DC` 8.7.3) | Append: "The monitor checks robot pairs; it does not check clearance to static obstacles." | imprecise |
| 25 | Modules, M6, line 89 | "records ground-truth poses for validation only" | GT's two contact lists are hard-coded empty (`REG` Erratum) | Append: "In the evaluated runtime its two contact lists are hard-coded empty, so ground truth supplies poses and pair distances, not contacts." | imprecise |
| 26 | Grounding, Feasibility checks, line 160 | "each retreat candidate is swept along its path against obstacles and other robots" | The passer's escort segment is checked against the parked yielder only, not against static obstacles (`DC` 8.7.3; `EG` 1) | Append: "The passer's escort segment is checked against the parked yielder only, not against static obstacles; Chapter 6 reports one escort that drove into a rack island for this reason." | imprecise |
| 27 | Grounding, Audit, not dispatch, line 177 | "The plan audit labels the model's proposed plan, records whether the dispatched command matches it, and seeds the `junction_clear` phase queue" | The phase queue is seeded in the same plan-channel step, but from `ground_junction_clear_phases(result, ...)`, which never reads the proposed plan (`PT` D, items 1-2; checked in `reasoning_pipeline.py` at `68e67b5`, about lines 1638-1680). So "the audit seeds the queue" suggests the plan sets the phases, which it does not. The flag is not reliable either: closure R1 recorded `dispatch_matches_plan=true` although the executed order differed (`PT` D) | "With the plan channel on, the audit runs after grounding. It labels the model's proposed plan, records its edits and a `dispatch_matches_plan` flag, and sets the legs the plan tracker follows; the same step seeds the `junction_clear` phase queue, but the phases are grounded from the decision fields, not from the proposed plan #ev(NEW: PT). The flag is not a strict match test: under the order tolerance, a plan whose back-out order differed from the executed one was still recorded as matching." | imprecise |
| 28 | Grounding, Later extensions, line 181 | three variants listed | Missing: the later prompt (options block, grammar sentences, `prompt_plan_grammar_rules`, default off) and the order switch used in the demo; escort guard; contact logging; held-robot prompt condition (`PC` Summary; `DC` 5.8, 10). The convoy queued-robot hold is still pending (section 6) and is left out | Append: "Later still, a prompt condition that lists the plan actions the verifier accepts was used with the plan-order switch in the demonstration campaign, and an escort obstacle guard, a geometric contact logger and a held-robot prompt condition were built. All are off by default, or not yet validated live (@sec:impl-later)." | outdated |
| 29 | Safety, table row "Hard-contact floor", line 198, and text line 214 | "Holds a pair below this distance" / "Any pair below 0.20 m is held" | The floor compares the M1 centre-to-centre distance (`DC` 11.5, `safety.py:981-982` at `8933863`) | Row: "Holds a pair whose centre-to-centre distance (M1 poses) is below this value, even while a clearing exemption covers it." Text: "Any pair whose centre distance is below 0.20 m is held, exempt or not." | imprecise |
| 30 | Safety, Hard-contact floor, line 214 | "The value is the footprint contact separation of 0.18 m" | Sources give two contact distances: 0.18 m footprint (`#ev("3.25")`) and 0.076 m nose to nose (`DC` Final Summary, safety scope; `GC` 5.4 positive control). Centre distance is only a proxy for contact | Append: "Centre distance is a proxy for contact: the distance at which two chassis touch depends on their relative heading, and nose to nose it is about 0.076 m #ev(NEW: DC)." | imprecise |
| 31 | Safety, Exemption scope, line 226 | "A later exploratory IB10 run enabled the key on top of the same runtime; it is reported separately" | The key was on but never fired: all key-on counters 0 in 10 episodes; not a live validation (`IBS` Safety-key evidence, Interpretation) | Append: "In that run the key was on but never fired, so the run is not a live validation of the fix #ev(NEW: IBS)." | imprecise |
| 32 | Safety, Summary, line 228 | "The model cannot select a motion that escapes the floor." | The floor covers robot pairs only; a model decision led to an escort into a rack island (`DC` 8.7, 8.7.5) | "The floor covers robot pairs only. A model decision can still lead to a grounded motion that meets a static obstacle, as one escort in the demonstration campaign did (Chapter 6); a guard for this case has been built but not yet run live #ev(NEW: EG)." | over-claim |
| 48 | Requirements, item 3, line 19 (the same clause is in `01-introduction.typ` line 19) | "A deterministic layer checks every proposed manoeuvre against the declared scene geometry and the robots' positions ... and refuses to move robots when no safe manoeuvre exists." | The escort segment of a yield was not checked against static obstacles, and one escort drove into a rack island (`DC` 8.7.3, 8.7.5) | Ch. 3: "A deterministic layer checks each proposed manoeuvre against the declared scene geometry and the robots' positions, repairs or replaces it where it is infeasible, and refuses to move robots when no safe manoeuvre exists. One part of a manoeuvre, the straight escort segment of a yield, was not checked against static obstacles in the evaluated runtime (@sec:design-grounding)." Ch. 1: add "(with one gap, escort paths, @sec:design-grounding)" after "checks the model's decision against the scene" | imprecise |
| 49 | Grounding, provenance labels, line 173 | "`m3_default` (absent, rejected, or not repairable within the bound)" | "Absent" also covers plans the model wrote but the parser nulled, for example for naming a robot twice (`PT` Answers 2; `IBL` and `IBS` Errata, Model Plan Statements) | "...or `m3_default` (absent, including plans the parser discarded for naming a robot twice; rejected; or not repairable within the bound) #ev("3.20") #ev(NEW: PT)." | imprecise |

### 2.4 Chapter 4 (Implementation)

| # | Location | Current text (short) | Why it must change (source) | Replacement (ready to paste) | Severity |
|---|---|---|---|---|---|
| 33 | `04-implementation.typ`, Execution, Yield as pull-off and escort, line 93 | "It is driven through the gap by a raw heading-and-distance primitive instead" | `drive_heading` drives the straight segment with no static-obstacle check (`DC` 8.7.3; `EG` 1) | Append: "This primitive drives a straight segment and does not check static obstacles; neither does the grounder (@sec:design-grounding)." | imprecise |
| 34 | VLM Backends, Grounding interface, line 121 | "checks every escort leg against the parked yielder" | Same gap | "...and checks every escort leg against the parked yielder, but not against static obstacles." | imprecise |
| 35 | Engineering Lessons, Fabric and USD, line 129 | "so the ground-truth log could serve as the metric source for distances and contacts" | GT contact lists are hard-coded `[]` (`isaac/vgu_sim/acceptance_logging.py:99-100`; `REG` Erratum; `GC` 1) | "...so the ground-truth log could serve as the metric source for positions and pair distances. It does not log contacts: its two contact lists are hard-coded empty, and contacts must be recomputed from poses (Chapter 6)." | wrong |
| 36 | Later Extensions, line 165 (list lines 167-169) | "Three groups of changes were written after the pin" | Now more: escort guard, GT contact logging, `prompt_plan_grammar_rules`, `prompt_held_robot_state`; the order switch existed since `a98574b` but ran first in the demo (`PT` D; `PC` 1; `CH` 1; `DC` 10). The convoy queued-robot hold stays pending (section 6) | Add bullets: "*Escort obstacle guard.* An M3 key, default off, refuses an escort whose straight segment crosses a declared obstacle; unit tests and offline replay only #ev(NEW: EG)." "*Geometric contact logging.* Ground truth computes footprint gaps to boxes and robots; not yet validated in Isaac Sim #ev(NEW: GC)." "*Plan-order prompt and switch.* A prompt condition listing the actions the verifier accepts, used with `plan_dispatch_order_source: model_when_verified` in the demonstration campaign only #ev(NEW: PC)." "*Held-robot prompt condition.* A default-off prompt condition that marks queued robots as not yet started; tested offline on the convoy scene and found no-go #ev(NEW: CH)." | outdated |
| 37 | Later Extensions, Safety-exemption scope fix, line 168 | "A later fix narrows the clearing exemption to partners that accepted their leg." | The fix stops honouring plan-`continue` partners (P1), drops rejected-leg robots (P3), changes the A19 waiver inputs, and adds a direction check on third-robot waivers (`SX` Behaviour) | "A later fix, behind the key `scoped_clearing_exemption`, stops honouring plan-`continue` partners, removes robots whose leg was rejected from the partner list, and ends a one-sided release of a third robot for good once the gap between them starts to close. It was tested with 64 unit tests and a replay over 68 recorded bundles, and was switched on in one exploratory IB10 run, where it never fired #ev(NEW: SX) #ev(NEW: IBS)." | imprecise |

### 2.5 Chapter 5 (Methodology)

| # | Location | Current text (short) | Why it must change (source) | Replacement (ready to paste) | Severity |
|---|---|---|---|---|---|
| 38 | `05-methodology.typ`, chapter intro, lines 9-16 | "Three live comparisons and one offline benchmark are described" | New methods need a home: demo campaign (registration, take rule, classifier), RS, SW, JO, IA, PT, PC, CH, GC recompute | Add bullets: "*the demonstration campaign*, ten live takes in four scenes, illustrative only;" "*the head-on decision analyses*, a re-score of recorded decisions and three pre-registered offline replays;" "*the plan-influence trace*, a counterfactual re-grounding of every live four-robot analysis;" "*the offline contact recompute*, a geometric check of recorded ground truth." Then one short section per item (method, registration commit, what it can and cannot show) | outdated |
| 39 | Scenes, line 77 | "Both scenes are scenario files..." | Convoy counterflow and head-on with obstacle (and five-robot seed 21) enter through the campaign and replays (`DC` sections 5, 6, 8) | "The scenes are scenario files..." and add short subsections for the head-on asymmetric scene and the convoy counterflow scene, or move them to the demo-campaign section | outdated |
| 40 | Arms, table `tab:ch5-arms` line 120, and text line 125 | "v3 pinned runtime plus a two-file safety fix" / "two safety-monitor files and a configuration key" | `IBS` Design says three files: `safety.py`, `safety_monitor_node.py` and a merged `safety.yaml` that carries the key. Same substance, different count | Table: "v3 pinned runtime plus the safety fix (three files: two monitor code files and a merged safety file carrying the key), switched on; 0.20 m floor." | imprecise |
| 41 | IB10 measures, Primary, line 173 | "the GT minimum distance between any two robots after time zero is at least 0.18 m" | Robot pairs, centre distance; IB10 declares no static obstacles and walls were not checked (`REG` Erratum, IB10 rows) | Append: "This is a centre-distance test on robot pairs; IB10 declares no static obstacles, and contact with walls or rack blocks is not checked." | imprecise |
| 42 | IB10 measures, Attribution, line 177 | "The provenance labels bound the model's contribution and are reported beside every outcome." | Labels do not bound it: decision fields changed execution in 18 dispatches whatever the label; no repaired plan fed dispatch (`PT` Answers 4, B) | "The provenance labels describe the audit of the model's proposed plan and are reported beside every outcome. They do not bound the model's contribution, which also reaches execution through the decision's strategy, robot set and yielder; Chapter 6 therefore adds a re-grounding of each decision without its plan #ev(NEW: PT)." | over-claim |
| 43 | Safety gates, tranche 1 contact gate, line 236 | "no robot pair below 0.18 m GT centre distance at any time ... because the simulator's contact field is a stub" | Robot pairs only; S1b has rack islands, not gated; a later recompute found a possible graze in E30 Arm A, not established (`REG` Erratum; `GC` 5.3; `DC` 8.7.4) | Append: "The gate covers robot pairs only; contact with the rack islands was not gated. A later offline recompute found one possible millimetre graze in tranche 1, not established (Chapter 6)." | imprecise |
| 44 | Threats, Internal validity, line 293 | "Provenance labels on every dispatch bound the model's share." | Same as row 42 | "Provenance labels on every dispatch record the audit of the model's plan, and a re-grounding without the plan shows which executed commands came from the model #ev(NEW: PT)." | over-claim |
| 45 | Threats, External validity, Safety evidence is narrow, line 323 | "The gates bound contact in these episodes only." | Gates bound robot-pair centre distance, not contact (`REG` Erratum) | "The gates bound the centre distance between robot pairs in these episodes only; no gate measured contact with static obstacles." | over-claim |

### 2.6 Evidence Index Rows

| # | Location | Current text (short) | Why it must change (source) | Replacement (ready to paste) | Severity |
|---|---|---|---|---|---|
| 46 | `thesis/evidence/ch3.typ`, row `3.20`, line 44 | "the plan audit records dispatch\_matches\_plan and seeds junction phases" | `PT` D: phase grounding never reads `proposed_plan`; the queue is seeded in the plan-channel step from the decision fields; see row 27 | "...the plan audit runs after grounding and records provenance, edits, tracked legs and dispatch\_matches\_plan; in the same plan-channel step, junction phases are grounded from the decision fields and seed the queue; only plan\_dispatch\_order\_source model\_when\_verified re-seats junction phase 0 on the model order." Add the `PT` path to the source cell | imprecise |
| 47 | `thesis/evidence/ch4.typ`, row `4.20`, line 42 | "GT then usable as metric source" | Positions and distances only; contacts are a stub (`REG` Erratum) | "GT then usable as metric source for positions and pair distances (its contact lists are hard-coded empty)." Add `isaac/vgu_sim/acceptance_logging.py:99-100` | imprecise |

### 2.7 Sections That Are Still Unwritten (What to Write, Not What to Change)

- **Abstract** (`00-front.typ` line 12): problem; the pipeline; the evaluation, worded with `REG` Recommended Thesis Wording 1, 2, 3 and 5; one sentence on scope (simulation, small n, one VLM live).
- **Chapter 1, evaluations held item** (line 75): one sentence per evaluation, from section 3 items 1, 2, 3, 4, 9 and 13.
- **Chapter 1, grounding as the limiting stage** (lines 81-82): `GB` Summary: 78 analyses gave 13 motion commands; 47 withheld by deterministic M3 refusals; one refusal class (the `junction_clear` static gate) gave 27 of the 47. Add the five-robot take (6 of 8 decisions withheld, `DC` 8.2) and the convoy takes (33 later proposals ran as 8 s waits, `DC` 5.4). Evidence type: decision-only re-grounding; illustrative demo.
- **Chapter 4, physical demonstration outcomes** (line 149): `REG` Hardware table (scenarios A, C, D, E; `reverse` each; E had one failed robot); robots had no goals.
- **Chapter 6**: sections listed in section 3 below.
- **Chapter 7**: "What the evidence supports" = `REG` Claims Ladder rungs a to f; "Grounding as the bottleneck" = item above plus `PT`; "Limitations" = section 5 below; "Threats" = Chapter 5 threats plus the new ones (selection of demo takes, unpushed branches).
- **Chapter 8**: conclusion from `REG` Recommended Thesis Wording 1 to 5; future work from section 5 below.

---

## 3. Results to Present

Each item: what, numbers (n, grade), form, thesis section, caveats, source.

**1. IB10, Layer 2 on against off (2026-11-13).**

- Numbers: Arm A (ER-2) resolved 4/5, 16/20 arrivals, times from onset 112.9, 115.5, 116.5, 116.6 s, e09 censored. Arm B (Layer 2 off) 0/5, 0/20, frozen to the horizon. Attribution 4 `repaired`, 1 `m3_default`, 0 `vlm_verbatim`. Lowest GT pair A 0.2633 m, B 0.2856 m; 0 floor stops. Grade: exploratory pilot, n = 5 per arm.
- Form: table (per arm, with the per-episode rows in an appendix).
- Section: Chapter 6, "IB10 Arm A vs Arm B".
- Caveats: one scene, near-repeat trajectories, no p-value; Arm B is a latch baseline; the repaired plans did not feed dispatch (`IBL` Erratum, Model Plan Statements); e09 failed after an off-pattern model choice; distances are robot-pair centre distance only.
- Source: `IBL` Pooled per arm; Erratum sections.

**2. IB10, VLM against the scripted grounder-default arm (2026-11-14).**

- Numbers: Arm A 5/5, 20/20 arrivals, 114.3-116.9 s from onset, mean 115.96 s. Arm C 4/4 valid, mean 117.80 s; after the post hoc e02 re-run 5/5, mean 117.86 s. Every Arm A first dispatch re-grounds to exactly the Arm C plan. Spend A $0.056, C $0. Grade: exploratory pilot.
- Form: table with Arm C shown before and after the re-run (the registration requires both).
- Section: Chapter 6, "IB10 Arm C".
- Caveats: Arm C was handed the strategy and robot set, so the VLM's remaining role in this scene is choosing them; Arm C dispatches about 3.4 s later, so times are not strictly comparable; never pooled with run 1; the e02 re-run is post hoc.
- Source: `IBS` Pooled per arm; Plan equality; Interpretation; Re-run of Slot e02.

**3. Safety-exemption fix.**

- What was fixed: P1 (plan-`continue` partners not honoured), P2 (moot), P3 (rejected leg not a partner), A19 waiver inputs, and a direction check on third-robot waivers; P4 and P5 unchanged.
- Tested how: 64 unit tests; replay over 68 recorded bundles (key-off timelines identical to `68e67b5` in 68/68, 673 changes); with the key on, 6 exemptions lost (1 in IB10 e09, 5 in older bundles), itemised.
- Live: switched on in the 2026-11-14 IB10 run; all key-on counters 0 in 10 episodes, so not exercised.
- Grade: unit tests, offline replay and a what-if on recorded trajectories; no live run (`SX` Scope).
- Form: one paragraph plus a small table of what the key changes.
- Section: Chapter 6 (safety findings) with a pointer from Chapter 3.
- Caveats: replay is a what-if on trajectories recorded under key-off behaviour; no live validation; P4 and P5 out of scope.
- Source: `SX` Behaviour, Tests, Replay Regression, Open Items; `IBS` Safety-key evidence.

**4. Head-on re-score and the feasibility gate.**

- Numbers (run level, first positive analysis): gpt-4o west 5/23, east 10/12; ER-2 west 12/30, east 11/13. Always-`robot_1`: 0/23, 12/12, 0/30, 13/13. Manifest rule: 23/23, 0/12, 30/30, 0/13. Gate `swap` on: grounded yielder correct in 79/79 runs, 37 of them overturning the model's pick.
- Grade: pilot data, post hoc, decision-only.
- Form: table (the `RS` Headline table, trimmed to gpt-4o and ER-2) plus one sentence on the gate.
- Section: Chapter 6, new section "Head-on yielder choice".
- Caveats: the VLM is never above the better trivial baseline; not pre-registered; the 79/79 column comes from artifact fields, not M4 logs; the gate exists only for yields (it was `off` in every IB10 run, `PT` D).
- Source: `RS` Headline; Conclusion.

**5. Demo campaign: scenarios, takes and outcomes.**

- Numbers: 10 valid takes, 1 bring-up abort. Intersection 5 takes: take 1 Unresolved (3/4), takes 2-4 M3-default resolution, take 5 VLM-driven execution (all 4/4). Convoy 3 takes, 0/4 each. Head-on with obstacle 1 take, 2/2, M3-default (grounder-corrected). Five robots 1 take, 1/5. Spend $2.6975 of $10; VM wall 18 203 s of 43 200 s.
- Grade: illustrative demo, not controlled evidence; n 1 to 5 per scene; nothing is a rate.
- Form: table (`DC` Final Summary "Scenarios and Videos" without the md5 column).
- Section: Chapter 6, new section "Demonstration campaign".
- Caveats: take 5 was selected for its label (disclosed); the campaign used a later prompt and the order switch, not the evaluated runtime's configuration.
- Source: `DC` Final Summary; Ledger Totals.

**6. Three-way count: valid response, accepted plan, changed execution.**

- Numbers: valid 55 of 55 analyses; accepted (`vlm_verbatim`) 6 of 53 plan-channel analyses; changed executed behaviour 1 (intersection take 5; computed for the intersection only). Convoy provenance 3 / 15 / 18; five robots 2 `vlm_verbatim`, 1 `repaired`, 5 `m3_default`.
- Before the campaign (`PT` B): 70/70 valid four-robot analyses; 14 verbatim, 8 dispatched as written; plan changed dispatch in 0 of 39.
- Grade: illustrative demo (`DC`); decision-only trace (`PT`).
- Form: table (`DC` "Valid Response, Accepted Plan, Changed Behaviour").
- Section: Chapter 6, demo campaign; repeat the sentence in Chapter 7.
- Caveats: valid is not usable (takes 1 and 3 parsed valid but plans were nulled, `DC` 2.1); stage-2 calls not counted; use 15 and 18 for convoy (the live-run agent said 16 and 17, `DC` 5.1).
- Source: `DC` Final Summary; `PT` B.

**7. Intersection take 5 (the one VLM-driven take).**

- What: ER-2's plan verified `vlm_verbatim` with 0 edits; its recede order robot_3 then robot_4 was dispatched (`dispatch_order_source=model`) against the default robot_4 then robot_3; 4/4 arrived; checks 1-8 passed.
- Caveats that must go with it, all from `DC` 7.2: chi margin 0.010 m against a 0.15 m tolerance (near-tie); only the timing of the two recedes changed (robot_3 backed out about 9 sim-s before robot_4); pockets, cross, release and crossing order stayed on chi; the model's `crossing_order` was not used; the order is ascending robot id; the prompt listed the accepted actions, so this is constrained selection (`PC` 10.3); 1 take of 5, chosen for its label; offline B3 rate 7/27 per first trigger (`PC` 10.3).
- Grade: illustrative demo, n = 1, verified from the raw bundle.
- Form: one paragraph plus a two-row timeline figure (model order vs default order).
- Section: Chapter 6, demo campaign.
- Source: `DC` 7.1, 7.2; `PC` 10.3.

**8. ER2LIVE (2026-09-30) as the accepted-yielder example.**

- What: model named robot_2 as yielder, the `swap` gate kept it, it was executed; 2/2 arrived; closest centre distance 0.2643 m.
- Caveats: n = 1, selected because it qualifies; older code `3959d7f`; the stage-2 pick was the first-listed of two mirror-equivalent options; robot_2's arrival needed about 22 sim-s of Nav2 stall and recovery; no feasibility numbers logged. Contrast: in the campaign head-on take the model named robot_1 (0.70 m room < 1.08 m required) and the gate swapped it (`DC` 6.2).
- Grade: illustrative, n = 1, not part of the campaign, verified offline from the bundle.
- Form: one paragraph, paired with the head-on take.
- Section: Chapter 6, head-on yielder choice or demo campaign.
- Source: `DC` 11.1-11.3, 11.5; `DC` 6.

**9. Convoy negative, its cause, and the held-robot prompt null.**

- Numbers: 3/3 takes unresolved, 0/4 arrived each. The first yield ran as the model named it in 3/3, but it named only the standoff pair; the two queued robots followed through the gate and latched; the 33 later proposals ran as 8 s waits (offline, 72 of 76 hypothetical decisions also became waits). Held-robot prompt check: 0 of 22 per condition grounded into the four-robot sequence; primary 0/18; no-go.
- Grade: illustrative demo; pre-registered offline check.
- Form: one paragraph plus a short cause list.
- Section: Chapter 6, demo campaign; cause in Chapter 7 (limitations).
- Caveats: cause is the first decision's content plus no recovery in legacy grounding (`DC` 5.5); one scripted smoke resolved 4/4 (n = 1, not owner-accepted); the grounding fix is pending (section 6).
- Source: `DC` 5.1-5.5, 5.8; `CH` 2, 4.

**10. Five-robot negative and the escort-into-obstacle finding.**

- Numbers: 1/5 arrived. 2 of 8 decisions executed as named; 6 withheld by grounding refusals ("no feasible yielder" 4, "no declared junction" 1, "no shared lane" 1); no analysis after sim 275.5 s. Decision 2's escort drove robot_3 into rack island `obstacle_2` from sim 146.7 s, within 5 mm in 4526 of 4534 GT rows.
- Grade: illustrative demo, n = 1 (limitation demonstration); the contact is confirmed from GT poses, URDF, scene-builder code and the recording.
- Form: one paragraph plus one still (`m5D_escort_147p30s_annotated.jpg`).
- Section: Chapter 6, demo campaign; safety findings.
- Caveats: "unresolved" partly reflects the escort path error, not only the model or the refusals (`DC` 8.7.5); seed 21 is an exploratory seed already seen in pilots.
- Source: `DC` 8.1-8.3, 8.7, 8.8.

**11. Offline replays on scene and image use.**

- Swapped-ID (`SW`): no model meets the pre-registered scene-use rule; gpt-4o follows the first-listed slot (85/96 grey-pair yields); ER-2 mostly answers `reverse` (129/144 in the A/B arms); Sonnet refused 30/48 real-frame runs, not assessable. Grade: small pre-registered offline replay.
- JSON-only ending (`JO`): Sonnet answered 146/146 with 0 refusals; 46/96 correct in the grey pair; names `robot_2` 76/96; ER-2 not assessable (50 of 96 runs); gpt-4o not run.
- Improved annotation (`IA`): stopped by provider limits; every verdict not assessable. Lead only: ER-2 with legible labels plus a neutral back-up line named the correct robot 55/67 (legible labels alone 11/64; grey control 7/66 vs 8/67).
- Form: one table (model × condition × verdict) plus one sentence each.
- Section: Chapter 6, head-on yielder choice.
- Caveats: one scene family, two robots, first decision only, no execution; never pooled with live data; `IA` is incomplete and must be called a lead.
- Source: `SW` Results per Model, What the Thesis Can and Cannot Claim; `JO` Results per Model, What the Thesis May and May Not Say; `IA` What the Thesis May and May Not Say (figures quoted in `REG` Two Robots rows).

**12. Plan-influence trace (0 of 39).**

- Numbers: 41 live four-robot congestion analyses, 39 pass the fidelity gate; the plan changed dispatch in 0 of 39; 0 of 20 ER-2 `junction_clear` plans verified `vlm_verbatim`; 14 verbatim plans overall, 8 dispatched as written; decision fields changed execution against the Arm C default in 18 dispatches in 4 episodes; where judged (e09, vp10) the outcome was worse.
- Grade: decision-only trace with verified and inferred labels.
- Form: table (`PT` B three-level classification).
- Section: Chapter 6, new section "Plan influence"; Chapter 7.
- Caveats: runtime `68e67b5`; the order switch was never on in these runs; the yield gate was `off` in every run.
- Source: `PT` Answers; B; D; E.

**13. prereg-v3 tranche 1, as a pilot.**

- Numbers: 10 episodes (5 seed pairs); 0/10 complete; tasks Arm A 16/125, Arm B 12/125; throughput delta +0.032 [−0.008, +0.080]; mean delay lower bound −31.5 s [−71.6, −0.6]; Arm A detection recall 0.818, type accuracy 0.778, involved-set F1 0.915, 0 false positives in 26 positive analyses. Robot-pair gate PASS 10/10 (GT min 0.225-0.424 m).
- Grade: registered confirmatory, reported as a pilot (owner decision 2026-11-13).
- Form: table (`T1` §5.3).
- Section: Chapter 6, "prereg-v3 Tranche 1 Pilot".
- Caveats: no directional hypothesis; the throughput CI includes 0; seeds were seen as pilots; the dispatched column in `T1` is wrong, use 5/2/2/1/2 dispatched with 4/2/3/4/1 withheld (`REG` Conflicts, item 1); the contact gate covers robot pairs only.
- Source: `T1` §2, §5.3, Erratum; `REG` Five Robots row and Conflicts item 1.

**14. Ground-truth contact finding and the offline recompute.**

- Finding (citable now): GT's `robot_static_contacts` and `robot_robot_contacts` are hard-coded `[]`, so every "0 GT contacts" read from them shows nothing; the sound channel is robot-pair centre distance (`REG` Erratum).
- Recompute over 44 bundles (NOT YET CITABLE as a measurement): one sustained robot-static contact (m5D robot_3 vs `obstacle_2`, minimum −0.16 mm); two brief grazes within noise (m5D robot_2 3.79 mm; tranche-1 E30 Arm A robot_2 0.97 mm); no robot-robot footprint contact (closest 82.1 mm); G4 positive control recovered.
- State clearly: the recompute is a planar URDF-footprint proximity at 10 Hz, offline, with no Isaac Sim run; it "becomes citable only after a live run confirms entries appear when a robot is pinned" (`GC` 6, 7.1; `DC` 10.2). The sustained m5D contact is independently confirmed (`DC` 8.7) and may be cited from `DC`.
- Form: one paragraph; put the 44-bundle table in an appendix marked "pending validation".
- Section: Chapter 6, safety findings; Chapter 7, limitations.
- Source: `REG` Erratum; `GC` 5.1-5.4, 6; `DC` 8.7, 10.2.

**15. Demo videos (illustrative material).**

- Exist only on the owner's Mac, `vgu-vlm-swarm-v7g/data/demo/campaign/` (git-ignored). md5 re-hashed 2026-11-15 (`REG` Citable Artifacts).

| Video | md5 | Shows |
|---|---|---|
| `ibD_t05_a1_panel.mp4` | `fdf07a82fcb657b738c44a89bfbe3dae` | intersection take 5, VLM-driven execution |
| `cvD_t01_a1_panel.mp4` | `824319447d05aaef6623158d00d2818f` | convoy take 1, unresolved |
| `hoD_t01_a1_panel.mp4` | `2aa6534ad508d3440e51822fdcd3f0f0` | head-on take 1, grounder-corrected |
| `m5D_t01_a1_panel.mp4` | `33e9f5eedd7fb56edd007d8b728ea8c0` | five robots, unresolved (escort caption) |
| `ER2LIVE_20260930_panel.mp4` | `93cbfe7108e6a9ca9a71fc4c7c79bd47` | 2026-09-30 head-on, model's yielder kept |
| `demo_campaign_combined.mp4` | `de8cb6ed07e42008b8acb3f9274352db` | all excerpts, v3 |

- Form: list in an appendix (file, md5, what it shows), plus stills as figures. Each must carry "illustrative demo, not controlled evidence".
- Source: `DC` Final Summary; 9; 11.5.

**16. Supporting results already planned in the Chapter 6 skeleton (no change in status).**

- v4 bench and Stage 1 shadow: the models "match, and do not beat" the default-ordered first option; shadow 50/50 valid blocks, never dispatched (`REG` Five Robots rows).
- Physical demonstration: four scenarios, `reverse` each, robots had no goals (`REG` Hardware).

---

## 4. Results to Drop, Demote or Relabel

| Item | Where it appears or would appear | Action | Reason (source) |
|---|---|---|---|
| Any "0 GT contacts", "no contact" or "collision-free" figure | Chapter 1 line 94, Chapter 5 lines 236 and 323 wording; any results table | Relabel as "no robot pair below 0.18 m centre distance" | GT contact lists are a stub (`REG` Erratum) |
| Provenance labels as a measure of the model's share | Chapters 1, 5 | Demote to "audit outcome"; add the re-grounding counterfactual | `PT` B, D |
| "vlm_verbatim" read as "model plan executed" | any results text | Relabel; the label can coexist with a different executed order (closure R1) and the yielder gap | `PT` D |
| tranche 1 as confirmatory | Chapter 6 | Report as pilot only (already planned) | `REG` Five Robots row |
| "Every IB10 plan repaired or replaced" (`#ev("1.13")`) as the strongest statement | Chapter 1 line 80 | Keep, but lead with the 0 of 39 trace | `PT` B |
| The "~110 uncorrected decisions" audit count | nowhere yet | Do not cite | Unverified; parts do not reconcile (`REG` "Could not verify"; `DC` 11.4) |
| Improved-annotation 55/67 | nowhere yet | Cite only as an incomplete lead, never as image use | `IA` What the Thesis May and May Not Say |
| GC 44-bundle recompute numbers | nowhere yet | Appendix, marked pending validation | `GC` 6; `DC` 10.2 |
| The scripted convoy smoke 4/4 | nowhere yet | Only as "the scene can be resolved", n = 1, not owner-accepted | `DC` 5.3 |
| Any rate or percentage from demo takes | Chapter 6 | Drop | `DC` Final Summary |
| `T1` dispatched column 9/4/5/5/3 | Chapter 6 if copied from `T1` | Replace by 5/2/2/1/2 dispatched, 4/2/3/4/1 withheld | `REG` Conflicts item 1 |
| Comparison table row "This report", safety cell (Chapter 2 line 108) | Chapter 2 | Keep; optionally add "(robot pairs)" after "Independent safety monitor" | `DC` 8.7.3 |

---

## 5. New Limitations and Future-Work Items

Limitations (Chapter 7) and the matching future work (Chapter 8):

- **The model does not use the scene for the yielder choice.** No tested model met the pre-registered scene-use rule; gpt-4o follows the listing slot; the gate, not the model, made the executed yielder correct (`SW`; `RS`). Future: complete the improved-annotation replay; counterbalanced real frames for ER-2.
- **Plans have almost no executed effect.** 0 of 39 live four-robot plans changed dispatch; once in the demo, recede timing only (`PT` B; `DC` 7.2). Future: a grammar the model can meet; let verified plans set more than the recede order, with a registered test.
- **Constrained selection.** The demo prompt listed the actions the verifier accepts, so take 5 is a choice among offered options, not free planning (`DC` 7.2 caveats; `PC` 10.3).
- **No recovery for latched clusters.** In the convoy scene no legacy strategy grounds motion after the latch (72 of 76 hypothetical decisions became waits) (`DC` 5.4). Future: fix option (b), hold queued robots, or a post-gate cluster template (`DC` 5.5); work on (b) is pending (section 6).
- **Grounding refuses most proposals on S1b.** 47 of 78 analyses withheld, 27 of them by one static gate (`GB` Summary); 6 of 8 in the five-robot take (`DC` 8.2). The model is not told a decision was withheld (`GB` Summary).
- **Escort has no obstacle check.** Neither M3 nor M4 checked the straight escort segment against static obstacles; one escort drove into a rack island (`DC` 8.7.3). Guard built, default off, offline replay only; declared obstacles only; no M4 backstop; E18 margin rule awaits the owner (`EG` 5; `DC` 10.1).
- **Contact logging was a stub.** GT contact lists hard-coded empty; static contact unmeasured in every live cell (`REG` Erratum). Geometric logger built, not validated in Isaac Sim (`GC` 7.1).
- **The safety-exemption fix is not validated live.** On in one run, never fired (`IBS` Safety-key evidence); P4 and P5 out of scope (`SX` Open Items).
- **Small n, exploratory, near-repeat episodes.** IB10 n = 5 per arm, one scene; demo n = 1 to 5; replays small (`IBL`; `IBS`; `DC`).
- **One VLM for all live runs.** ER-2 in every live comparison and every campaign take; other models only offline (`REG` rung b).
- **Valid does not mean usable.** ER-2 parsed 55 of 55, but plans were nulled for repeated robots or copied option text (`DC` 2.1; `PC` Summary).
- **Ascending listing order in live cells.** Yielder and recede-order choices cannot separate an id prior from a slot prior (`DC` 7.2; Chapter 1 line 79).
- **Demo selection.** Take 5 and ER2LIVE were chosen for their labels (`DC` 7.2, 11).

---

## 6. Pending Items That May Change This List

Each item is pending as of 2026-11-15.

- **Validation take for the escort guard and contact logging.** Registered on `demo/validation-guard-contacts` (worktree `v7n`, commit `9a68539`); no committed result as of this check (git log and status only; gitignored run data not inspected). A pass would make the `GC` recompute citable and turn the guard into live evidence. Pending as of 2026-11-15.
- **Convoy grounding fix and possible retake.** `REG` says the branch had no commit of its own; that is now out of date. Worktree `v7o` (`fix/convoy-hold-queued-robots`) has commit `10b4807` ("add default-off queued corridor-crosser hold to M3") and an uncommitted report draft, which was not read or cited here. No committed retake result as of this check (git log and status only; gitignored run data not inspected). Do not put the hold into thesis text until its report is committed. A resolving retake would be a grounding result, not a VLM one. Pending as of 2026-11-15.
- **The audit's "about 110 uncorrected decisions".** Unverified; do not cite. Pending as of 2026-11-15.
- **Improved-annotation replay.** Incomplete; every verdict not assessable. Completing it could change the scene-use limitation for ER-2. Pending as of 2026-11-15.
- **E18 margin rule for the escort guard.** Owner decision (`DC` 10.1). Pending as of 2026-11-15.
- **Branches unpushed and unreviewed.** Every source in "Source Key" is on a local branch; a review could change numbers (`REG` Citable Artifacts). Pending as of 2026-11-15.
- **Thesis items already marked VERIFY.** Pre- and post-arm gates (Chapter 3 line 216) and the reason no v1/v2 confirmatory data exist (Chapter 5 line 71). Owner input. Pending as of 2026-11-15.

---

## 7. Figures and Tables to Make or Remake

| # | Figure or table | Section | Data source |
|---|---|---|---|
| 1 | IB10 run 1: Arm A vs Arm B, per arm plus per episode | Ch. 6 | `IBL` Per-episode table and Pooled per arm; `vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/summary/episodes.jsonl` |
| 2 | IB10 run 2: Arm A vs Arm C, before and after the e02 re-run | Ch. 6 | `IBS` Pooled per arm; Pooled Arm C, Before and After the Re-run; `vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/summary/` |
| 3 | Head-on yielder: VLM vs baselines vs gate | Ch. 6 | `RS` Headline table |
| 4 | Offline replay verdicts (SW, JO, IA) | Ch. 6 | `SW`, `JO`, `IA` per-model sections |
| 5 | Plan influence, three-level classification | Ch. 6 | `PT` B table |
| 6 | Demo campaign: scenes, takes, outcomes, labels | Ch. 6 | `DC` Final Summary, Scenarios and Videos |
| 7 | Demo three-way count | Ch. 6 | `DC` Final Summary, Valid Response, Accepted Plan, Changed Behaviour |
| 8 | Take 5 timeline: model order vs default order | Ch. 6 | `DC` 7.1, 7.2 (GT times in check 3); take 5 stills next to `ibD_t05_a1_panel.mp4` in v7g |
| 9 | Escort into rack island (still and plan view) | Ch. 6 | `vgu-vlm-swarm-v7j/docs/reports/assets/2026-11-15-demo-campaign/m5D_escort_*.jpg`; `DC` 8.7.2 |
| 10 | Tranche-1 pilot table | Ch. 6 | `T1` §5.3; `REG` Conflicts item 1 for dispatches |
| 11 | Safety summary: closest centre distance and floor stops per cell, with the contact-measurement status | Ch. 6 or 7 | `IBL`, `IBS` Pooled; `DC` Final Summary (0.2176-0.3701 m per valid take); `T1` §2; `GC` 5.1 (appendix, pending) |
| 12 | Pipeline figure (`thesis/figures/pipeline.typ`) | Ch. 3 | Optional edits: label the M4 box "robot-pair distance check"; show the plan audit after grounding as a side box that does not feed Act |
| 13 | Evidence Index rows for the new sources | Appendix | Add one row per short name in "Source Key" (path, branch, commit), plus `isaac/vgu_sim/acceptance_logging.py:99-100` at `68e67b5` |

---

## 8. Could Not Map to Evidence

- Chapter 4 line 105 and `#ev("4.37")`: the gpt-4o refusal finding ("the annotation overlay itself was not the trigger"). Its source (`cbe3dcf:docs/reports/2026-09-25-gpt4o-refusa…`) is outside the sources read here; not re-checked.
- Chapter 3 line 216: pre- and post-arm gates (already marked VERIFY in the thesis).
- Chapter 5 line 71: why no v1 or v2 confirmatory data exist (already marked VERIFY).
- Chapter 4, physical demonstration: the hardware README is outside the repository (`REG` Scope); its code lineage is not in the repository.
- Chapter 2: literature statements were not checked; this list covers only claims about this project.

---

## 9. Where Sources Disagree

- robot_3 minimum gap: −0.2 mm (`DC` 8.7.2) vs −0.16 mm (`GC` 5.2).
- E30 Arm A graze: 1.2 mm (`DC` 8.7.4) vs 0.97 mm (`GC` 5.3). Both: possible graze, not established.
- Convoy provenance: 16 and 17 (live-run agent) vs 15 and 18 (artifacts, `DC` 5.1). Use 15 and 18.
- IB10 Arm C: 4/4, mean 117.80 s vs 5/5, mean 117.86 s after the re-run (`IBS`). Cite both.
- ER2LIVE closest approach: body gap 0.186 m vs centre distance 0.2643 m; the floor is on centre distance (`DC` 11.5).
- Safety-fix file count: "two-file" (thesis Chapter 5) vs "three safety files" (`IBS` Design). Same change.
- Contact distance: 0.18 m footprint (`#ev("3.25")`) vs 0.076 m nose to nose (`DC` Final Summary; `GC` 5.4).
- Convoy fix branch: "no commit of its own yet" (`REG`) vs commit `10b4807` present in `v7o` on 2026-11-15.

---

## 10. Scenario Images: What to Insert and Where

Added in Rev 2. It extends section 3 items 7, 10 and 15 and section 7 rows 8, 9 and 12; it does not replace them.

### 10.1 What Exists

- **Image files.** 15 PNG stills in `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7g/data/demo/campaign/thesis_figures/` (folder `P` below), with `MANIFEST.md` giving, for each file, the source recording, segment and frame index, sim time, md5 and what it shows. The folder is git-ignored (v7g `.gitignore:50`, `data/demo/`) and exists only on this Mac.
- **How they were made.** One decoded frame per file, chosen through the recording's per-frame time map. Full frame, unscaled, uncropped, nothing drawn on. Camera stills are 1280 x 960, the panel still 1920 x 1080, and all are under 1.5 MB. The yellow `t=… f=…` text in the corner of each camera still is burned in by the recorder. In every still, the burned-in frame number equals the map index plus 1 and the burned-in time equals the mapped time.
- **Streams.** Layout frames use the raw stream (`/camera/image_raw`) where it is clean and the robots can be named from their positions (intersection, convoy, head-on). The annotated stream (`/perception/annotated_frame`) is used where the figure must show which robot is which (all result frames, and the five-robot layout). In the annotated stream, M1 colours each box by status: green moving, yellow slow, red stopped, grey stale. Image right is world +x and image up is world +y.
- **Thesis figure conventions (read from the working tree, not edited).** Figures sit in `#figure(...)` with `caption: flex-caption([short], [long])` and end with `#fig-source("<Evidence Index id>")` (`thesis/lib.typ` lines 32, 56). Labels are `<fig:ch5-…>` in Chapter 5 and `<fig:impl-…>` in Chapter 4; Chapter 6 has no figures yet, so `<fig:ch6-…>` below is a proposal. The only photographs are in `fig:impl-physical` (`04-implementation.typ` lines 151-159): two images in a `grid(columns: (1fr, 1fr))`, stored in `thesis/assets/images/` and referenced as `../assets/images/<file>.png`. They use a `demo-frame` helper that clips an 86 px toolbar from 1182 x 957 screenshots. Do **not** reuse that helper for these 1280 x 960 frames: it would cut them wrongly. No photograph has an explicit width, so the widths below are proposals.
- **Where to copy files.** Copy each file to `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-thesis/thesis/assets/images/` under the same name. That folder is tracked (`thesis/.gitignore:3` un-ignores `assets/images/*.png`), so copying adds the files to the thesis branch when the owner commits them.
- **Source tag.** Every caption needs an Evidence Index row for the demo campaign report (`DC`, section 7 row 13). The snippets use the placeholder `#fig-source("NEW-DC")`. That will not compile until it is replaced by the real row id, because `ev()` links to a label that must exist.
- **Caption rules.** No caption may claim "collision-free", "no contact" or any success rate. Every result frame says it is an illustrative take and how many takes the scene had. Robot ids are written in backticks, as the thesis does.

### 10.2 Existing Thesis Figures and Scenario Coverage

| Label | File | Kind | Scenario shown |
|---|---|---|---|
| `fig:architecture` | `03-system-design.typ` line 30 (`figures/architecture.typ`) | drawn (CeTZ) | none (architecture) |
| `fig:pipeline` | `03-system-design.typ` line 95 (`figures/pipeline.typ`) | drawn | none (decision pipeline) |
| `fig:impl-physical` | `04-implementation.typ` line 151 | photographs | physical scenarios A and C |
| `fig:ch5-s1b` | `05-methodology.typ` line 85 (`figures/scene-s1b.typ`) | drawn | S1b layout, one start assignment |
| `fig:ch5-ib10` | `05-methodology.typ` line 96 (`figures/scene-ib10.typ`) | drawn | IB10 intersection layout |

- Scenarios that already have an image: IB10 and S1b (drawings only, no camera frame), physical A and C (photographs).
- No image in the thesis: the convoy counterflow scene, the head-on corridor scene (the thesis does not describe either scene yet; row 39), the five-robot seed position 21 start, the demonstration campaign, ER2LIVE, and physical scenarios D and E.

### 10.3 Placement Table

`P` = `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7g/data/demo/campaign/thesis_figures/`. Line numbers are those of the thesis working tree on 2026-11-15. "After line N" means the snippet goes on a new line after line N. For headings that do not exist yet, the row names the heading to add and where; the headings come from section 3 and row 39.

| # | File (md5) | Insert at | New or replaces | Proposed caption (long form) | Label | Width |
|---|---|---|---|---|---|---|
| 1 | `P/fig_intersection_jam_t30p10.png` (`19c6078f0f88659083d00170e48e2a2b`) | `05-methodology.typ`, "=== IB10: four-robot intersection", after line 99 (the end of `fig:ch5-ib10`), tied to line 92 "IB10 is a staged four-way jam" | New; a companion to the `fig:ch5-ib10` drawing, which it does not replace | Four-robot intersection (`intersection_bottleneck`, the IB10 scene file, seed 42), raw overhead camera frame at simulated time 30.1 s: the four robots jammed at the centre of the cross aisle before any command; `robot_1` left, `robot_2` right, `robot_3` bottom, `robot_4` top, each bound for the opposite arm. Simulation (Isaac Sim), overhead camera. Frame from demonstration take 5 (labelled VLM-driven execution), not from an IB10 experiment episode. | `fig:ch5-ib10-frame` | 75 % |
| 2 | `P/fig_convoy_standoff_t28p00.png` (`724072c58f3454f2eee2607555bc2ad0`) | `05-methodology.typ`, new subsection "=== Convoy counterflow" added after line 99, before "== Arms" (line 101), as row 39 proposes; after its first paragraph. No thesis sentence describes this scene yet | New | Convoy counterflow scene (`convoy_counterflow_slip`, seed 42), four robots, raw overhead camera frame at simulated time 28.0 s. Left to right: `robot_4` and `robot_3` queued behind `robot_1`, which stands nose to nose with the counter-flow robot `robot_2` in the 0.55 m wide, 1.0 m long gap between the two barrier blocks (yellow). Before any command. Simulation (Isaac Sim), overhead camera. Frame from demonstration take 1 of 3. | `fig:ch5-convoy` | 75 % |
| 3 | `P/fig_headon_standoff_t26p00.png` (`899b219fdeb63eca9053f11b75739293`) | `05-methodology.typ`, new subsection "=== Head-on corridor with obstacle" after the convoy subsection (same place, row 39); after its first paragraph. No thesis sentence describes this scene yet; the nearest is the feasibility gate at line 54 | New | Head-on corridor with an obstacle (`head_on_asymmetric_w0p2_eopen_bshort_o0`, seed 42), two robots, raw overhead camera frame at simulated time 26.0 s: `robot_1` (left) and `robot_2` (right) nose to nose in the 0.55 m wide, 2.0 m long corridor between the barrier blocks (yellow). The box at the left (`blocker_west`) leaves `robot_1` 0.70 m of retreat room against 1.08 m required, so only `robot_2` can yield. First standoff, before any command. Simulation (Isaac Sim), overhead camera. Frame from demonstration take 1 of 1. | `fig:ch5-headon` | 75 % |
| 4 | `P/fig_intersection_panel_dispatch_t33p07.png` (`41ab0420c52687d8a22f9969cc9585ad`) | `06-results.typ`, new heading "== Demonstration Campaign" added after line 18 (before "== Physical Demonstration", line 20); first figure of that section | New | Format of the demonstration videos: one frame of the panel video of the four-robot intersection, take 5 (labelled VLM-driven execution, chosen for that label), at simulated time 33.1 s. Left: the annotated overhead camera stream with the renderer's captions. Right: the run's own M5 and M4 log lines replayed in sync, here the decision (`junction_clear`, provenance `vlm_verbatim`) and the dispatch of `robot_3`'s back-out. Simulation (Isaac Sim), overhead camera. Illustrative demo, not controlled evidence; take 5 is 1 of 5 takes. | `fig:ch6-demo-panel` | 100 % |
| 5 | `P/fig_intersection_robot3_backing_t36p97.png` (`f142516cd8e1ad5c087b553c1379f521`) | same section, new subsection "=== Intersection, take 5", after the paragraph for section 3 item 7 | New | Four-robot intersection, demonstration take 5 (labelled VLM-driven execution), annotated overhead camera frame at simulated time 37.0 s: `robot_3` (green, moving) backs out along its own arm while `robot_1`, `robot_2` and `robot_4` (red, stopped) wait. `robot_4` starts its back-out at 41.9 s. This order is the model's verified plan. The default order (`robot_4` first) differed by 0.010 m in recede cost, so only the timing of the two back-outs changed. Simulation (Isaac Sim), overhead camera; box colours show the perception module's status. Illustrative take, 1 of 5, chosen for its label. | `fig:ch6-ib-backout` | 75 % |
| 6 | `P/fig_intersection_all_arrived_t154p83.png` (`b20eab1a2e7e8d22342cf959b80fc4d0`) | same subsection, after row 5 | New | Four-robot intersection, demonstration take 5 (labelled VLM-driven execution), annotated overhead camera frame at simulated time 154.8 s: all four robots stopped at their goals on the opposite arms (ground-truth arrivals between 95.1 s and 146.4 s). Simulation (Isaac Sim), overhead camera. Illustrative take, 1 of 5: take 1 was unresolved and takes 2 to 4 were resolved by the default plan. | `fig:ch6-ib-arrived` | 75 % |
| 7 | `P/fig_convoy_first_yield_t38p00.png` (`8953113fb44c6dfcd208568c7740121b`) | same section, new subsection "=== Convoy counterflow", after the paragraph for section 3 item 9 | New | Convoy counterflow, four robots, demonstration take 1 of 3 (unresolved), annotated overhead camera frame at simulated time 38.0 s: the first yield executes as the model named it. `robot_2` (green) backs out of the gap while `robot_1` waits in it and `robot_3` and `robot_4` stay queued. The decision named only the standoff pair. Simulation (Isaac Sim), overhead camera. Illustrative take, 1 of 3. | `fig:ch6-cv-yield` | 75 % |
| 8 | `P/fig_convoy_latched_t149p90.png` (`25565e204d9be152b32003d3c222f043`) | same subsection, after row 7 | New | Convoy counterflow, demonstration take 1 of 3 (unresolved), annotated overhead camera frame at simulated time 149.9 s: the final latched cluster. `robot_3` and `robot_4`, which the first decision did not name, followed `robot_1` through the gap. All four stand stopped east of the gap, two pairs closer than the 0.45 m safety distance, and none moved again from about 75 s to the end at 260 s; 0 of 4 arrived. Simulation (Isaac Sim), overhead camera. Illustrative take, 1 of 3; all three takes ended unresolved. | `fig:ch6-cv-latched` | 75 % |
| 9 | `P/fig_headon_robot2_backing_t70p00.png` (`2157e1599b99637266beeb8c07655a2f`) | same section, new subsection "=== Head-on with obstacle", after the paragraph on the take (`DC` 6) | New | Head-on corridor with obstacle, two robots, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead camera frame at simulated time 70.0 s: `robot_2` (green) backs out east. After a first `reverse` and a second standoff, the model named `robot_1` as the yielder. The feasibility gate replaced it with `robot_2`, because `robot_1` had 0.70 m of retreat room against 1.08 m required. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1. | `fig:ch6-ho-yield` | 75 % |
| 10 | `P/fig_headon_robot2_yield_pass_t99p00.png` (`ea1c87fee5065a4b45819e873f200eb3`) | same subsection, after row 9 | New | Head-on corridor with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead camera frame at simulated time 99.0 s: `robot_2` is parked at its pull-off point beside the lane (red, stopped) while `robot_1` (green) is escorted past it. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1. | `fig:ch6-ho-pass` | 75 % |
| 11 | `P/fig_headon_both_arrived_t147p93.png` (`0f91eab03385148feeaf8dd9bd858a92`) | same subsection, after row 10 | New | Head-on corridor with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead camera frame at simulated time 147.9 s: both robots stopped at their goals, `robot_2` at the left beside the obstacle and `robot_1` at the right edge of the frame (ground-truth arrivals at 112.5 s and 136.1 s). Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1. | `fig:ch6-ho-arrived` | 75 % |
| 12 | `P/fig_fiverobot_standoff_t43p67.png` (`06425619e2fbc53fd9526bed3dc41cd4`) | same section, new subsection "=== Five robots", after the paragraph for section 3 item 10 | New | Five-robot pickup-and-delivery scene (S1b, seed position 21, an exploratory seed outside the registered list), demonstration take 1 of 1 (unresolved; a limitation demonstration), annotated overhead camera frame at simulated time 43.7 s. Two rack islands; `robot_1` and `robot_4` meet head-on at the bottom (yellow, slow), and the other three are moving. Before the first decision. The start assignment differs from @fig:ch5-s1b. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1. | `fig:ch6-m5-start` | 75 % |
| 13 | `P/fig_fiverobot_after_decision1_t101p40.png` (`bd9ea395d65f34e99cdef4d7e734c31e`) | same subsection, after row 12 | New | Five robots, seed position 21, demonstration take 1 of 1 (unresolved), annotated overhead camera frame at simulated time 101.4 s, after decision 1. That decision was executed as the model named it: `robot_1` yielded and `robot_4` passed, and both now stand at the left edge. `robot_2` and `robot_3` are stopped beside the east island, the conflict of decision 2. Of eight decisions in this take, two were executed and six were withheld by grounding refusals; 1 of 5 robots arrived. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1. | `fig:ch6-m5-after1` | 75 % |
| 14 | `P/fig_fiverobot_robot3_island_t147p30.png` (`c38f9a5f9d587e3a68842aff1bc823dc`) | same subsection, after row 13; reference it from the Chapter 6 safety findings and the Chapter 7 "Limitations" (`07-discussion.typ` line 11) | New. A full-frame alternative to the existing crop `m5D_escort_147p30s_annotated.jpg` (section 3 item 10, section 7 row 9); use one of the two | Five robots, seed position 21, demonstration take 1 of 1 (unresolved), annotated overhead camera frame at simulated time 147.3 s: `robot_3` against the east face of rack island `obstacle_2`. The straight escort segment of decision 2 drove it there; no stage checked that segment against static obstacles. The box is the perception module's last track of `robot_3` before the island's edge hid its marker, so its colour and arrow do not show motion. The contact rests on ground-truth poses (stopped at 146.9 s; within 5 mm of the face in 4526 of 4534 ground-truth rows to the end of the run), not on this image. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1. | `fig:ch6-m5-escort` | 75 % |
| 15 | `P/fig_er2live_robot2_aside_robot1_passing_t86p30.png` (`216af8e35139e6270c32c640c0da22b0`) | `06-results.typ`, new heading "== Head-on Yielder Choice" added after line 18 (section 3 items 4 and 8), after the ER2LIVE paragraph | New | Head-on corridor with obstacle, two robots, from an earlier recorded run (2026-09-30, older code, not part of the demonstration campaign), annotated overhead camera frame at simulated time 86.3 s. `robot_2`, the yielder the model named and the feasibility gate kept, has backed out and parked beside the lane, and `robot_1` is escorted past it. 2 of 2 arrived, `robot_2` only after a navigation-stack stall and recovery. Simulation (Isaac Sim), overhead camera. Illustrative, n = 1, chosen because the model's yielder was kept. | `fig:ch6-er2live` | 75 % |

### 10.4 Typst Snippets

Each snippet follows `fig:ch5-ib10` and `fig:impl-physical`: `flex-caption`, a source tag at the end of the long caption, and the label after the closing parenthesis. Replace `NEW-DC` with the Evidence Index id of the `DC` row. Two neighbouring frames can be paired in `grid(columns: (1fr, 1fr), column-gutter: 8pt, image(...), image(...))` like `fig:impl-physical`, with one merged caption.

Row 1:

```text
#figure(
  image("../assets/images/fig_intersection_jam_t30p10.png", width: 75%),
  caption: flex-caption([Overhead camera frame of the four-robot intersection in a jam.], [Four-robot intersection (`intersection_bottleneck`, the IB10 scene file, seed 42), raw overhead camera frame at simulated time 30.1 s: the four robots jammed at the centre of the cross aisle before any command; `robot_1` left, `robot_2` right, `robot_3` bottom, `robot_4` top, each bound for the opposite arm. Simulation (Isaac Sim), overhead camera. Frame from demonstration take 5 (labelled VLM-driven execution), not from an IB10 experiment episode.#fig-source("NEW-DC")]),
) <fig:ch5-ib10-frame>
```

Row 2:

```text
#figure(
  image("../assets/images/fig_convoy_standoff_t28p00.png", width: 75%),
  caption: flex-caption([Overhead camera frame of the convoy counterflow scene.], [Convoy counterflow scene (`convoy_counterflow_slip`, seed 42), four robots, raw overhead camera frame at simulated time 28.0 s. Left to right: `robot_4` and `robot_3` queued behind `robot_1`, which stands nose to nose with the counter-flow robot `robot_2` in the 0.55 m wide, 1.0 m long gap between the two barrier blocks (yellow). Before any command. Simulation (Isaac Sim), overhead camera. Frame from demonstration take 1 of 3.#fig-source("NEW-DC")]),
) <fig:ch5-convoy>
```

Row 3:

```text
#figure(
  image("../assets/images/fig_headon_standoff_t26p00.png", width: 75%),
  caption: flex-caption([Overhead camera frame of the head-on corridor with an obstacle.], [Head-on corridor with an obstacle (`head_on_asymmetric_w0p2_eopen_bshort_o0`, seed 42), two robots, raw overhead camera frame at simulated time 26.0 s: `robot_1` (left) and `robot_2` (right) nose to nose in the 0.55 m wide, 2.0 m long corridor between the barrier blocks (yellow). The box at the left (`blocker_west`) leaves `robot_1` 0.70 m of retreat room against 1.08 m required, so only `robot_2` can yield. First standoff, before any command. Simulation (Isaac Sim), overhead camera. Frame from demonstration take 1 of 1.#fig-source("NEW-DC")]),
) <fig:ch5-headon>
```

Row 4:

```text
#figure(
  image("../assets/images/fig_intersection_panel_dispatch_t33p07.png", width: 100%),
  caption: flex-caption([Format of the demonstration videos.], [Format of the demonstration videos: one frame of the panel video of the four-robot intersection, take 5 (labelled VLM-driven execution, chosen for that label), at simulated time 33.1 s. Left: the annotated overhead camera stream with the renderer's captions. Right: the run's own M5 and M4 log lines replayed in sync, here the decision (`junction_clear`, provenance `vlm_verbatim`) and the dispatch of `robot_3`'s back-out. Simulation (Isaac Sim), overhead camera. Illustrative demo, not controlled evidence; take 5 is 1 of 5 takes.#fig-source("NEW-DC")]),
) <fig:ch6-demo-panel>
```

Row 5:

```text
#figure(
  image("../assets/images/fig_intersection_robot3_backing_t36p97.png", width: 75%),
  caption: flex-caption([Intersection take 5: `robot_3` backs out first.], [Four-robot intersection, demonstration take 5 (labelled VLM-driven execution), annotated overhead camera frame at simulated time 37.0 s: `robot_3` (green, moving) backs out along its own arm while `robot_1`, `robot_2` and `robot_4` (red, stopped) wait. `robot_4` starts its back-out at 41.9 s. This order is the model's verified plan. The default order (`robot_4` first) differed by 0.010 m in recede cost, so only the timing of the two back-outs changed. Simulation (Isaac Sim), overhead camera; box colours show the perception module's status. Illustrative take, 1 of 5, chosen for its label.#fig-source("NEW-DC")]),
) <fig:ch6-ib-backout>
```

Row 6:

```text
#figure(
  image("../assets/images/fig_intersection_all_arrived_t154p83.png", width: 75%),
  caption: flex-caption([Intersection take 5: all four robots at their goals.], [Four-robot intersection, demonstration take 5 (labelled VLM-driven execution), annotated overhead camera frame at simulated time 154.8 s: all four robots stopped at their goals on the opposite arms (ground-truth arrivals between 95.1 s and 146.4 s). Simulation (Isaac Sim), overhead camera. Illustrative take, 1 of 5: take 1 was unresolved and takes 2 to 4 were resolved by the default plan.#fig-source("NEW-DC")]),
) <fig:ch6-ib-arrived>
```

Row 7:

```text
#figure(
  image("../assets/images/fig_convoy_first_yield_t38p00.png", width: 75%),
  caption: flex-caption([Convoy take 1: the first yield.], [Convoy counterflow, four robots, demonstration take 1 of 3 (unresolved), annotated overhead camera frame at simulated time 38.0 s: the first yield executes as the model named it. `robot_2` (green) backs out of the gap while `robot_1` waits in it and `robot_3` and `robot_4` stay queued. The decision named only the standoff pair. Simulation (Isaac Sim), overhead camera. Illustrative take, 1 of 3.#fig-source("NEW-DC")]),
) <fig:ch6-cv-yield>
```

Row 8:

```text
#figure(
  image("../assets/images/fig_convoy_latched_t149p90.png", width: 75%),
  caption: flex-caption([Convoy take 1: the latched cluster.], [Convoy counterflow, demonstration take 1 of 3 (unresolved), annotated overhead camera frame at simulated time 149.9 s: the final latched cluster. `robot_3` and `robot_4`, which the first decision did not name, followed `robot_1` through the gap. All four stand stopped east of the gap, two pairs closer than the 0.45 m safety distance, and none moved again from about 75 s to the end at 260 s; 0 of 4 arrived. Simulation (Isaac Sim), overhead camera. Illustrative take, 1 of 3; all three takes ended unresolved.#fig-source("NEW-DC")]),
) <fig:ch6-cv-latched>
```

Row 9:

```text
#figure(
  image("../assets/images/fig_headon_robot2_backing_t70p00.png", width: 75%),
  caption: flex-caption([Head-on take: `robot_2` yields after the gate swap.], [Head-on corridor with obstacle, two robots, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead camera frame at simulated time 70.0 s: `robot_2` (green) backs out east. After a first `reverse` and a second standoff, the model named `robot_1` as the yielder. The feasibility gate replaced it with `robot_2`, because `robot_1` had 0.70 m of retreat room against 1.08 m required. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("NEW-DC")]),
) <fig:ch6-ho-yield>
```

Row 10:

```text
#figure(
  image("../assets/images/fig_headon_robot2_yield_pass_t99p00.png", width: 75%),
  caption: flex-caption([Head-on take: `robot_1` passes the parked `robot_2`.], [Head-on corridor with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead camera frame at simulated time 99.0 s: `robot_2` is parked at its pull-off point beside the lane (red, stopped) while `robot_1` (green) is escorted past it. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("NEW-DC")]),
) <fig:ch6-ho-pass>
```

Row 11:

```text
#figure(
  image("../assets/images/fig_headon_both_arrived_t147p93.png", width: 75%),
  caption: flex-caption([Head-on take: both robots at their goals.], [Head-on corridor with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead camera frame at simulated time 147.9 s: both robots stopped at their goals, `robot_2` at the left beside the obstacle and `robot_1` at the right edge of the frame (ground-truth arrivals at 112.5 s and 136.1 s). Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("NEW-DC")]),
) <fig:ch6-ho-arrived>
```

Row 12:

```text
#figure(
  image("../assets/images/fig_fiverobot_standoff_t43p67.png", width: 75%),
  caption: flex-caption([Five-robot take: the first standoff.], [Five-robot pickup-and-delivery scene (S1b, seed position 21, an exploratory seed outside the registered list), demonstration take 1 of 1 (unresolved; a limitation demonstration), annotated overhead camera frame at simulated time 43.7 s. Two rack islands; `robot_1` and `robot_4` meet head-on at the bottom (yellow, slow), and the other three are moving. Before the first decision. The start assignment differs from @fig:ch5-s1b. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("NEW-DC")]),
) <fig:ch6-m5-start>
```

Row 13:

```text
#figure(
  image("../assets/images/fig_fiverobot_after_decision1_t101p40.png", width: 75%),
  caption: flex-caption([Five-robot take: after the first decision.], [Five robots, seed position 21, demonstration take 1 of 1 (unresolved), annotated overhead camera frame at simulated time 101.4 s, after decision 1. That decision was executed as the model named it: `robot_1` yielded and `robot_4` passed, and both now stand at the left edge. `robot_2` and `robot_3` are stopped beside the east island, the conflict of decision 2. Of eight decisions in this take, two were executed and six were withheld by grounding refusals; 1 of 5 robots arrived. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("NEW-DC")]),
) <fig:ch6-m5-after1>
```

Row 14:

```text
#figure(
  image("../assets/images/fig_fiverobot_robot3_island_t147p30.png", width: 75%),
  caption: flex-caption([Five-robot take: an escort drives `robot_3` into a rack island.], [Five robots, seed position 21, demonstration take 1 of 1 (unresolved), annotated overhead camera frame at simulated time 147.3 s: `robot_3` against the east face of rack island `obstacle_2`. The straight escort segment of decision 2 drove it there; no stage checked that segment against static obstacles. The box is the perception module's last track of `robot_3` before the island's edge hid its marker, so its colour and arrow do not show motion. The contact rests on ground-truth poses (stopped at 146.9 s; within 5 mm of the face in 4526 of 4534 ground-truth rows to the end of the run), not on this image. Simulation (Isaac Sim), overhead camera. Illustrative take, n = 1.#fig-source("NEW-DC")]),
) <fig:ch6-m5-escort>
```

Row 15:

```text
#figure(
  image("../assets/images/fig_er2live_robot2_aside_robot1_passing_t86p30.png", width: 75%),
  caption: flex-caption([Earlier head-on run: the model's yielder kept and executed.], [Head-on corridor with obstacle, two robots, from an earlier recorded run (2026-09-30, older code, not part of the demonstration campaign), annotated overhead camera frame at simulated time 86.3 s. `robot_2`, the yielder the model named and the feasibility gate kept, has backed out and parked beside the lane, and `robot_1` is escorted past it. 2 of 2 arrived, `robot_2` only after a navigation-stack stall and recovery. Simulation (Isaac Sim), overhead camera. Illustrative, n = 1, chosen because the model's yielder was kept.#fig-source("NEW-DC")]),
) <fig:ch6-er2live>
```

### 10.5 Reading Order by Chapter

- **Chapter 5 (Methodology), `== Scenes`:** row 1 (IB10 camera frame, beside the drawing), then the two new subsections that row 39 proposes, with row 2 (convoy layout) and row 3 (head-on layout). If the owner instead moves those scenes to a demo-campaign section of Chapter 5, rows 2 and 3 move with them.
- **Chapter 6 (Results), `== Head-on Yielder Choice` (new, section 3 items 4 and 8):** row 15 (ER2LIVE), with a cross-reference to rows 9 and 10 for the contrast case (gate swap).
- **Chapter 6, `== Demonstration Campaign` (new, section 3 items 5 to 10):** row 4 (panel format) at the top; "=== Intersection, take 5": rows 5 and 6, plus the timeline figure of section 7 row 8 when made; "=== Convoy counterflow": rows 7 and 8; "=== Head-on with obstacle": rows 9, 10 and 11; "=== Five robots": rows 12, 13 and 14.
- **Chapter 6, safety findings (section 3 items 10 and 14) and Chapter 7, "Limitations" (`07-discussion.typ` line 11):** cite row 14 by label; do not repeat the image.
- **Appendix:** the video list of section 3 item 15; no stills needed there.

### 10.6 Existing Figures That Become Outdated or Duplicate

- `fig:ch5-ib10` (drawing): not outdated. Row 1 shows the same scene file as a camera frame, so the two partly duplicate each other. Keep the drawing for the dimensions and goals. Row 1 is optional.
- `fig:ch5-s1b` (drawing): shows one start assignment, not that of seed position 21. Rows 12 to 14 must therefore not be presented as the layout of that drawing; row 12's caption says so.
- `fig:pipeline` (`figures/pipeline.typ`): the edits in section 7 row 12 still apply (M4 box "robot-pair distance check"; plan audit after grounding as a side box). The opt-in plan-order switch used in the demonstration campaign is not drawn. Add it as a dashed path only if the text describes it there.
- `fig:architecture`: no change implied by this section.
- `fig:impl-physical`: not affected (physical robots, different scene).
- Section 7 row 9 ("Escort into rack island, still and plan view"): row 14 supplies the still, and the crop remains an alternative; the plan view still has to be made.

### 10.7 Still Missing for a Complete Figure Set (List Only; Nothing Created)

- **Drawn layouts of the convoy and head-on scenes,** in the style of `figures/scene-ib10.typ`: barrier gap and length, `blocker_west`, start poses and goals, and the head-on retreat-room figures (0.70 m against 1.08 m). The camera frames show the scenes but give no dimensions or goals.
- **Seed position 21 start layout** for the five-robot take, if Chapter 6 keeps rows 12 to 14: a variant of `scene-s1b.typ` with the seed's starts and first goals, or a caption-only statement.
- **Take 5 timeline** (model order against default order; section 7 row 8).
- **Escort plan view** (escort segment, island box and ground-truth track; section 7 row 9).
- **Pipeline figure edits** (section 7 row 12).
- **Physical demonstration scenarios D and E:** the thesis describes them in text (`04-implementation.typ` line 149) but has no image of them. Files `scenario_d_four_robot_central.png` and `scenario_e_compact_dual_lane.png` exist in `~/Downloads/verified_scenarios_12-11-2026/verified_scenarios_images_2026-11-12/`, outside the repository and the thesis. They were not viewed, hashed or prepared here.
- **No usable image anywhere checked here** for the scenes of the IB10 experiment episodes and the prereg-v3 tranche-1 episodes. Their recordings were not searched; the IB10 camera frame (row 1) comes from a demonstration take of the same scene file.
- **Contact and safety figure** (section 7 row 11): a table or chart, not an image.

### 10.8 Drawn Figure: Take 5 Decision Flow With Real Output (Added in Rev 3)

- **What it is.** The figure shows the decision flow in six stages: trigger, request, VLM response, check, grounding into phases, and dispatch and execution. Each stage is annotated with the real output of intersection take 5 (request `df397030…`). A side rail shows the M4 safety monitor beside every stage. Boxes with a solid border and a filled background mark what the model decided: the strategy, the plan legs and the back-out order. Dashed boxes mark what the system decided: the actions offered, the yielder, the distances, the waits, the crossing chain, the release and the safety rules. Grey text marks model output that the system did not use (`crossing_order`). Fill and border style keep the two classes apart in greyscale. A bottom strip compares the two outcomes of stage 4. On the left, the take 5 plan was accepted unchanged by the plan verifier. On the right, the head-on take (decision 2, `f40c0537…`) was corrected by the yield feasibility gate, and the strip quotes the gate's `m5.log` line verbatim. The figure is drawn with Typst built-ins and needs no package; all text is at least 7 pt. It was compiled with the Typst 0.15.1 compiler bundled in the VS Code Tinymist extension, because no `typst` binary is installed.
- **Files** (folder `P/flow_diagram/`, git-ignored, on this Mac only):

| File | md5 |
|---|---|
| `vlm_flow_take5.typ` (figure function `vlm-flow-figure()` plus a standalone A4 preview with the thesis page setup) | `595d889e61c92f90eb7f660f3daaa1d2` |
| `vlm_flow_take5.pdf` (standalone preview, 1 page) | `cbdfcaf2ec203cc1c39a276cacffe5d8` |
| `vlm_flow_take5.png` (same page, 300 ppi, 2480 x 3508) | `359b3c7d152e392fa2d853094b054338` |
| `SOURCES.md` (every value with its file, JSON path or log line) | `0c963b8e53600b7071c486f968ded967` |
| `INSERT.md` (copy step, import line, snippet, placement) | `bd538fad8043edae1cebccc183a55418` |

- **Where to insert.** Copy the `.typ` file to `thesis/figures/vlm-flow-take5.typ` and add `#import "../figures/vlm-flow-take5.typ": vlm-flow-figure` after line 1 of `06-results.typ`. Place the figure in Chapter 6, under "== Demonstration Campaign" → "=== Intersection, take 5", the headings that rows 4 to 6 add after line 18; it goes after rows 5 and 6. The label is `fig:ch6-flow-take5`, and the figure call needs `kind: image`. In a scratch copy of the thesis with a stub `NEW-DC` row, the figure and its caption fit on one page (page 55 of that build), and the build compiled with no errors or warnings.
- **Source tag.** Like every snippet in 10.4, the figure uses `#fig-source("NEW-DC")` and does not compile until the demo-campaign Evidence Index row exists (section 7 row 13).
- **Caveats carried by the caption.** Illustrative, not controlled evidence. Take 5 of 5, selected because it is the only take labelled VLM-driven execution. Only the back-out order was the model's, and it was a near-tie: 0.010 m in recede cost against the verifier's 0.15 m tolerance. The head-on strip comes from a different take, with n = 1. The caption makes no contact or rate claims.
- **Found while checking the values** (`SOURCES.md` has details):
  - In phase 3, `robot_2`'s own command is a `temporary_wait` linked to the yield as its passer, not a `cross` action. The figure says "passes, escorted 2.024 m".
  - The GT speed of robot_3 and robot_4 first rises above 0 at 32.3 s and 41.4 s. `DC` 7.2 gives the back-out starts as 32.9 s and 41.9 s, which matches the first sample displaced more than 0.05 m from the standing pose. The figure keeps the report's values.
  - The take 5 request ran with `grounding_yield_feasibility=off`. Its plan was accepted by the plan verifier, not by the yield gate.
  - The M4 startup line of take 5 shows `scoped_clearing_exemption=True`, unlike the runtime that the thesis evaluates. The rail says so.
- **Superseded in part by 10.9 (Rev 4).** The figure files are unchanged, but the figure moves from Chapter 6 to a new appendix with label `fig:app-flow-take5`. Its caption gains one sentence on the safety scope.

### 10.9 Simplified Take 5 Figure for the Main Text; Detailed Figure Moves to an Appendix (Added in Rev 4)

- **Why.** The owner judged the 10.8 figure too dense for the main text. It stays unchanged as the traceable reference in an appendix. A simplified figure replaces it in Chapter 6.
- **What the simplified figure shows.** Four blocks, top to bottom, with arrows between them:
  - **1 VLM proposed** (M2, `gemini-robotics-er-2-preview`): `strategy: junction_clear` and the condensed plan `robot_3 reverse, robot_4 reverse, robot_1 yield, robot_2 cross`.
  - **2 M3 verified** (plan verifier): "Plan accepted unchanged, no edits", then the order comparison. The model's back-out order `robot_3` → `robot_4` (dispatched) is set against the default order `robot_4` → `robot_3`; the recede-cost difference is 0.010 m, within the 0.15 m tolerance, a near-tie.
  - **3 Grounding computed** (M3, system): the back-out set comes from the scene geometry and the yielder `robot_1` is M3's own. Grounding computed the commanded back-out distances (0.781 m, 0.971 m), the waits, and the crossing and release phases.
  - **4 Dispatched and executed:** `robot_3` backed out from sim 32.9 s, then `robot_4` from 41.9 s. The crossing and release then ran as in the default plan. "In this run, all four robots reached their goals between sim 95.1 s and 146.4 s", with no success marks or colour.
  - **Styling and notes.** Only the order comparison is filled (accent fill, solid border), as the VLM's contribution to the executed commands. Every other block is unfilled, so the proposal is not styled as decided by the model; the fill stays distinct in greyscale. A slim note under the blocks reads: "Safety monitor (M4) in this run: robot-pair distance only (0.45 m latch, with robots in the same reverse or yield command exempt; 0.20 m hard floor on centre distance). It has no obstacle check, and the escort path was not checked against obstacles." A one-line legend explains the two styles.
  - **Omitted** (left to the appendix figure): `crossing_order`, the options block, log lines, request ids, the head-on strip and the safety rail.
- **Files** (`P/flow_diagram/`, git-ignored, on this Mac only; the 10.8 files were verified byte-identical before and after this work):

| File | md5 |
|---|---|
| `vlm_flow_take5_simple.typ` (figure function `vlm-flow-simple-figure()` plus a standalone A4 preview) | `e49262a9a443a15cbadb89a3322383dd` |
| `vlm_flow_take5_simple.pdf` (standalone preview, 1 page) | `f0933aa00205b87db1cab2ac519a25e5` |
| `vlm_flow_take5_simple.png` (same page, 300 ppi, 2480 x 3508) | `b837b64c7727c344ef5338a9338f86bf` |
| `SOURCES_simple.md` (each value with its source in `SOURCES.md` or `DC` sections 1, 7, 8.7, 10) | `96da6783473a45ea6ee55d1d3da4f019` |
| `INSERT_simple.md` (snippets, placement for both figures, appendix caption) | `f485b8619c730d95a417eed9b5726f97` |

- **Main-text placement.** Copy the file to `thesis/figures/vlm-flow-take5-simple.typ` and import `vlm-flow-simple-figure` after line 1 of `06-results.typ`. The figure goes in Chapter 6, "== Demonstration Campaign" → "=== Intersection, take 5" (the headings rows 4 to 6 add after line 18). It comes first in that subsection, after its first paragraph and before the stills of rows 5 and 6, because their captions rely on the order comparison. Label `fig:ch6-flow-take5-simple`, `kind: image`.
- **Size.** In a scratch copy of the thesis (stub `NEW-DC` row, deleted afterwards), the figure and caption take 135 mm of the 250 mm text block, about 54 % of a page. All figure text is at least 8 pt. The build compiled with no errors or warnings.
- **Caption caveats.**
  - One live run, take 5 of 5, selected because it is the only take labelled VLM-driven execution.
  - The model's contribution to execution was the back-out order only, a near-tie (0.010 m within 0.15 m).
  - "An end-to-end execution example, not controlled evidence of improved performance: the four arrivals do not show that the VLM outperforms the default plan." The default plan resolved the same scene in takes 2 to 4, and take 1 was unresolved (`DC` 1, 7.1, 7.2).
  - Only robot-pair distance was checked for safety; there was no obstacle verification.
  - A pointer to the appendix figure.
  - No contact or rate claims.
- **Safety-note wording, narrower than the brief's "No obstacle check was active".** `DC` 8.7.3 supports only two statements: the M4 monitor has no obstacle check, and no stage checks the escort segment against obstacles. The same table lists one M3 check that does use static boxes (the yielder's retreat room; the intersection declares no boxes). `DC` says nothing about Nav2's obstacle handling. The escort obstacle guard (`DC` 10.1) was built after take 5 and has not been run live.
- **Detailed figure moves to an appendix.** Add a new file `thesis/chapters/10-appendix-traces.typ` with "= Decision Trace of Intersection Take 5" and the 10.8 figure, label `fig:app-flow-take5`. Include it in `main.typ` after line 116, the Evidence Index include, which makes it Appendix B. Drop the `vlm-flow-figure` import from `06-results.typ`. The appendix caption is the 10.8 caption plus this sentence: "Safety in this run was checked by robot-pair distance only (the M4 safety monitor); no obstacle verification was active." In the scratch build, the figure with the longer caption still fits on one page.
- **Source tag.** Both snippets use `#fig-source("NEW-DC")` and need the demo-campaign Evidence Index row (section 7 row 13).

---

## Source Key

All branches are local and unpushed. Commit = last commit touching the report.

| Short name | Report path | Branch (worktree under `/Users/tuanhdangdinh/Documents/`) | Commit |
|---|---|---|---|
| `REG` | `docs/reports/2026-11-13-thesis-evidence-register.md` (sections: 2026-11-15 Erratum; VLM Contribution; Conflicts) | `feat/v4-per-cluster-parity` (`vgu-vlm-swarm-v6d`) | `586e881` |
| `GB` | `docs/reports/2026-11-13-s1b-grounding-bottleneck.md` | `feat/v4-per-cluster-parity` (`vgu-vlm-swarm-v6d`) | `b534d17` |
| `DC` | `docs/reports/2026-11-15-demo-campaign-results.md` | `demo/campaign-kits` (`vgu-vlm-swarm-v7j`) | `4e5476b` |
| `PC` | `docs/reports/2026-11-15-vlm-order-channel-plan-check.md` | `demo/campaign-kits` (`vgu-vlm-swarm-v7j`) | `7586857` |
| `CH` | `docs/reports/2026-11-15-convoy-held-robot-prompt-check.md` | `demo/campaign-kits` (`vgu-vlm-swarm-v7j`) | `4d6f057` |
| `T1` | `docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` | `demo/campaign-kits` (`vgu-vlm-swarm-v7j`) | `d076a54` |
| `PT` | `docs/reports/2026-11-15-vlm-plan-influence-trace.md` | `docs/vlm-plan-influence-trace` (`vgu-vlm-swarm-v7i`) | `1400533` |
| `IBL` | `docs/reports/2026-11-13-ib10-live-resolution-results.md` | `feat/ib10-live-resolution` (`vgu-vlm-swarm-v7a`) | `3cb947e` |
| `IBS` | `docs/reports/2026-11-14-ib10-safety-default-arm-results.md` | `feat/ib10-safety-default-arm` (`vgu-vlm-swarm-v7d`) | `04a1956` |
| `SX` | `docs/reports/2026-11-14-safety-exemption-fix.md` | `fix/safety-exemption-scope` (`vgu-vlm-swarm-v7c`) | `8933863` |
| `RS` | `docs/reports/2026-11-14-head-on-vlm-vs-rule-rescore.md` (read with `git show`) | `docs/head-on-vlm-vs-rule` (main checkout `vgu-vlm-swarm`) | `1f77bf1` |
| `SW` | `docs/reports/2026-11-14-head-on-swapped-id-replay-results.md` | `exp/head-on-swapped-id-replay` (`vgu-vlm-swarm-swapid`) | `bc26ae0` |
| `IA` | `docs/reports/2026-11-14-improved-annotation-replay-results.md` | `exp/head-on-swapped-id-replay` (`vgu-vlm-swarm-swapid`) | `abc28fe` |
| `JO` | `docs/reports/2026-11-14-head-on-json-only-replay-results.md` | `exp/head-on-json-only-replay` (`vgu-vlm-swarm-jsononly`) | `29696f9` |
| `GC` | `docs/reports/2026-11-15-gt-contact-logging.md` | `feat/gt-contact-logging` (`vgu-vlm-swarm-v7m`) | `b5eaee5` |
| `EG` | `docs/reports/2026-11-15-escort-obstacle-guard.md` | `fix/escort-obstacle-guard` (`vgu-vlm-swarm-v7l`) | `72c08c8` |

Commits for `REG`, `GB`, `DC`, `PC`, `CH`, `PT`, `IBL`, `IBS`, `RS`, `SW`, `IA`, `JO`, `GC` and `EG` are as listed in `REG` Citable Artifacts or re-read with `git log -1` on 2026-11-15.
