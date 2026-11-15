# Naming Glossary: Thesis Replacement List

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: every internal-shorthand occurrence in the thesis working tree, grouped by chapter, with replacements; first-use definitions; abbreviation-list changes; captions and paste-ready snippets of the change list (sections 10–11) that carry shorthand.

---

## Purpose and How to Use It

Hand-off to the report-writer session. The names come from `docs/guides/naming_glossary.md` (same branch); read its rules (section 1) first. Nothing in the thesis was edited.

- **Snapshot.** Thesis working tree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-thesis/thesis/`, branch `docs/thesis`, HEAD `266aaac`, working tree clean, scanned 2026-11-15T13:56Z. Another session is editing the thesis (HEAD moved from `7e589d8` to `266aaac` while this list was made), so **line numbers drift**: find each row by its anchor text, not by its line number.
- **How the list was made.** A scratch scanner (not committed) matched the terms of the glossary's replace list on every line of `main.typ`, `chapters/*.typ` and `evidence/*.typ`, one row per thesis line, every match on the line counted. Excluded: text inside backticks (config keys, file names, log values) except the plan-audit codes `vlm_verbatim` and `m3_default` and the four scene file names; `#ev(...)` and `#fig-source(...)` ids; `<labels>` and `@references`; `#import` lines. Module codes M1–M6 were counted only where no role word (perception, VLM, ground/verif, execut/safety/monitor, orchestr, simulat) stands within 40 characters.
- **Where.** "heading", "caption" and "table" rows are mandatory replacements (rule 1 of the glossary). "prose" rows of defined abbreviations (Layer 1, Layer 2, M1–M6, episode ids, shadow) are optional after the first-use definition; every other prose row is a replacement.
- **Key.** The last column names each term found on the line and its replacement key (legend below). "AMBIGUOUS" keys need the sentence read before replacing.

---

## 1. Counts by Chapter

| Chapter | File | Occurrences | headings | captions | table cells | prose |
|---|---|---|---|---|---|---|
| Front matter | `chapters/00-front.typ` | 8 | 0 | 0 | 7 | 1 |
| Ch. 1 Introduction | `chapters/01-introduction.typ` | 59 | 0 | 0 | 7 | 52 |
| Ch. 2 Background | `chapters/02-background.typ` | 2 | 0 | 0 | 0 | 2 |
| Ch. 3 System design | `chapters/03-system-design.typ` | 105 | 2 | 11 | 7 | 85 |
| Ch. 4 Implementation | `chapters/04-implementation.typ` | 52 | 0 | 0 | 0 | 52 |
| Ch. 5 Methodology | `chapters/05-methodology.typ` | 368 | 16 | 17 | 10 | 325 |
| Ch. 6 Results | `chapters/06-results.typ` | 237 | 8 | 43 | 45 | 141 |
| Ch. 7 Discussion | `chapters/07-discussion.typ` | 36 | 0 | 0 | 0 | 36 |
| Ch. 8 Conclusion | `chapters/08-conclusion.typ` | 16 | 0 | 0 | 0 | 16 |
| Appendix B Traces and demos | `chapters/10-appendix-traces.typ` | 37 | 0 | 1 | 34 | 2 |
| Evidence index, ch. 1 rows | `evidence/ch1.typ` | 51 | 0 | 0 | 0 | 51 |
| Evidence index, ch. 3 rows | `evidence/ch3.typ` | 28 | 0 | 0 | 0 | 28 |
| Evidence index, ch. 4 rows | `evidence/ch4.typ` | 43 | 0 | 0 | 0 | 43 |
| Evidence index, ch. 5 rows | `evidence/ch5.typ` | 163 | 0 | 0 | 0 | 163 |
| Evidence index, ch. 6 rows | `evidence/ch6.typ` | 111 | 0 | 0 | 0 | 111 |
|  | **total** | **1316** | 26 | 72 | 110 | 1108 |

The evidence files (`evidence/ch*.typ`) are the claim column of the Evidence Index appendix. They are reader-visible but lower priority than the chapters; their source column (paths, commits) stays as written.

By term (all files): `Mn`: 226; `An`: 102; `Arm A`: 101; `IB10`: 86; `Arm B`: 55; `S1b`: 51; `tranche 1`: 50; `Arm C`: 46; `Sn`: 42; `Layer 2`: 37; `en`: 37; `shadow`: 32; `En`: 30; `prereg-v3`: 27; `m3_default`: 25; `smoke`: 24; `Layer 2 off`: 21; `Layer-2-off`: 21; `Layer 2 on`: 19; `tranche-1`: 19; `vlm_verbatim`: 19; `Tranche 1`: 16; `Layer 1`: 14; `prereg-v3 tranche 1`: 14; `IB10 run 2`: 12; `tranche`: 11; `stage-2`: 10; `tranche 2`: 9; `Stage 1`: 9; `M3-default resolution`: 9; `prereg-v1`: 8; `prereg`: 8; `IB10 registration`: 8; `first IB10 run`: 7; `v4`: 7; `both IB10 runs`: 6; `chi`: 6; `kit`: 6; `v4 bench`: 6; `Layer-2-on`: 6; `IB10 run 1`: 6; `two IB10 runs`: 5; `Tranche-1`: 5; `second IB10 run`: 4; `IB10 intersection`: 4; `IB10 live resolution`: 4; `batch`: 4; `ER2LIVE`: 4; `mapd_5_s1b`: 4; `Layer-1`: 3; `IB10 experiment`: 3; `intersection_bottleneck`: 3; `IB10 runs`: 2; `IB10 grounder-default run`: 2; `IB10 grounder-default arm`: 2; `prereg-v2`: 2; `convoy_counterflow_slip`: 2; `head_on_asymmetric_w0p2_eopen_bshort_o0`: 2; `tranche-1 pilot`: 2; `prereg-v3, tranche 1`: 1; `prereg-v3 tranche-1`: 1; `v4 offline bench`: 1; `S1 scene`: 1; `S1 family`: 1; `IB10 grounder default`: 1; `Tranche 1 Pilot`: 1; `Stage-1`: 1; `tranche-2`: 1; `head_on_asymmetric_`: 1; `B3`: 1

---

## 2. The Five Worst Cases

1. **The results headings of Chapter 6** name three of the four live comparisons only by internal ids: "== IB10: Layer 2 On vs Off", "== IB10: VLM vs Grounder Default (Arm C)", "== prereg-v3 Tranche 1 Pilot", and "== v4 Offline Bench and Stage 1 Shadow". Replace with "== Intersection Run 1: Central Layer On vs Off", "== Intersection Run 2: Live VLM vs Scripted Default Plan", "== Registered Five-Robot Pilot", "== Offline Decision Benchmark and Live Per-Group Shadow Run". Their table captions repeat the ids ("IB10 run 1: Layer 2 on against off.", "IB10 run 2: live VLM against the grounder default.", "prereg-v3 tranche 1, reported as a pilot.", "Interception analysis, tranche 1, Arm A.").
2. **Chapter 1's research questions and contributions lists** (`01-introduction.typ`, anchors "*prereg-v3, tranche 1 (pilot).*", "*IB10, Layer 2 on against off (exploratory).*", "*IB10, grounder default (exploratory).*", and the same three in the contributions list) introduce the experiments to the reader by internal ids before any definition. Replace with "*Registered five-robot pilot.*", "*Intersection run 1: central layer on vs off (exploratory).*", "*Intersection run 2: live VLM vs scripted default plan (exploratory).*".
3. **The arms table of Chapter 5** (`tab:ch5-arms`, caption "The three live comparisons.") labels its rows "prereg-v3 tranche 1, S1b", "IB10 live resolution", "IB10 grounder default" and its arms "A:", "B:", "C:". Replace the rows with "Registered five-robot pilot (21 Oct 2026)", "Intersection run 1 (13 Nov 2026)", "Intersection run 2 (14 Nov 2026)" and the arms with "On: Gemini Robotics-ER 2. Off: `reasoning_enabled: false`." and "On: Gemini Robotics-ER 2. Scripted: mock backend, grounder default plan.". The section headings "=== Questions registered at prereg-v1", "=== prereg-v1/v2/v3: …", "=== S1b: …", "=== IB10: …", "=== prereg-v3 tranche 1", "=== IB10 live resolution", "=== IB10 grounder-default run" carry the same problem.
4. **The List of Abbreviations** (`00-front.typ`) defines internal ids as if they were terms: "IB10 — Name of the four-robot intersection scene", "S1b — Name of the five-robot task-stream scene", "A$n$ — Numbered amendment (prereg-v1) or addendum (prereg-v3), e.g. A33". Once the text uses the reader-facing names, delete the IB10 and S1b rows and reword the A$n$ row (section 4 below).
5. **Chapter 5's opening map of all studies** (anchor "*prereg-v3 tranche 1* on the five-robot S1b scene, Layer 2 on against Layer 2 off") and its separation sentence ("The IB10 runs and the v4 bench are never pooled with prereg-v3 data, and the two IB10 runs are never pooled with each other") use four internal ids per line; it is the reader's first full list of experiments. Replace with the glossary's experiment names (glossary section 2.2) and dates.

---

## 3. Suggested First-Use Definitions

Paste at the first use in each chapter where the term appears (Chapter 1 first; repeat briefly in Chapters 5 and 6, which readers open directly).

- **Central layer.** "The *central layer* (Layer 2 in @fig:architecture) is the slow, centralised loop that detects a stall, asks the VLM, grounds the decision and dispatches commands; *central layer off* means the orchestrator never starts an analysis, so only each robot's local navigation runs."
- **Registered five-robot pilot.** "The *registered five-robot pilot* (21 October 2026) compared the central layer on and off on five seed pairs of the five-robot pickup-and-delivery scene. It was registered as confirmatory, meaning its measures and analysis were fixed before any episode ran; because only 5 of the 20 planned seed pairs ran, this report calls it a pilot and never pools it with any other run."
- **Exploratory five-robot pilots.** "The 21 *exploratory pilot episodes* (E6 to E26, 10 to 17 October 2026) ran the central layer with the live VLM while the design was being tuned; they are reported separately and never pooled with the registered pilot."
- **Intersection runs.** "*Intersection run 1* (13 November 2026) compared the central layer on and off on the four-robot intersection; *intersection run 2* (14 November 2026) compared the live VLM with a scripted arm that skips the VLM call and runs the grounder's default plan. Both were registered before they ran, are exploratory, and are never pooled with each other."
- **Scripted default-plan arm.** "The *scripted default-plan arm* replaces the VLM with a scripted backend that names the strategy and the four robots but proposes no plan, so the grounder builds its own default plan."
- **The grounder.** "The *grounder* (M3) turns a validated decision into commands; it checks feasibility, audits and repairs or replaces the model's plan, and refuses manoeuvres that cannot be executed."
- **Plan-audit label.** "Each dispatch carries a *plan-audit label* (provenance in the logs): *accepted unchanged* (`vlm_verbatim`), *repaired* (`repaired`), or *grounder default* (`m3_default`). The dispatched command always comes from the grounder."
- **Grounder-default resolution.** "A demonstration take is labelled *grounder-default resolution* when it resolved but the executed plan was not the model's own, including when the feasibility gate replaced the model's yielder (*grounder-corrected*)."
- **Grounder's default order.** "The grounder orders the back-outs at the intersection by its own cost rule (*default order*; `chi` in the logs)."
- **Episode ids.** "Episode ids are kept as recorded: pilot episodes E6–E26, seed pairs E27–E31 of the registered pilot (one central-layer-on and one central-layer-off episode each), and intersection slots e01–e10."
- **Registered design versions.** "The study design was registered three times: the *first* (v1, tagged 30 September 2026), *second* (v2) and *third* (v3, 6 October 2026) registered designs. Numbered changes are cited by content with their number, e.g. 'the registered measure definitions (v3 addendum A33)'."
- **Sensitivity analyses.** "Two sensitivity analyses of the failure-cause classification are reported beside the primary coding: the *persistent-state link* and the *start-inside rule*; a third reruns the substitution test with *extra recorded inputs* (the stored second-stage label and the task intents)."

---

## 4. List of Abbreviations: Entries to Change

| Current row (`00-front.typ`) | Action | Suggested row |
|---|---|---|
| `[A$n$], [Numbered amendment (prereg-v1) or addendum (prereg-v3), e.g. A33]` | reword | `[A$n$], [Numbered amendment of the first registered design (v1) or addendum of the third (v3), cited with its content, e.g. "the registered measure definitions (v3 addendum A33)"]` |
| `[IB10], [Name of the four-robot intersection scene (Chapter 5)]` | delete once the text says "four-robot intersection" | none |
| `[S1b], [Name of the five-robot task-stream scene (Chapter 5)]` | delete once the text says "five-robot pickup-and-delivery scene" | none |
| `[M1--M6], [Modules 1 to 6 of the system]` | reword | `[M1--M6], [Modules of the system: perception (M1), VLM reasoning (M2), grounder (M3), execution and safety monitor (M4), orchestrator (M5), simulation (M6)]` |
| `[ER-2], [Gemini Robotics-ER 2, the hosted VLM of the live experiments]` | keep | unchanged |
| (missing) | add | `[Layer 1, Layer 2], [Local navigation and the central layer of the two-layer architecture]` |
| (missing) | add if kept in prose | `[E$n$, e$n$], [Recorded episode ids: five-robot episodes E6–E31, intersection slots e01–e10]` |

---

## 5. Legend of Replacement Keys

| Key | Replace with | Note |
|---|---|---|
| R01 | the registered five-robot pilot |  |
| R02 | registered five-robot pilot |  |
| R03 | the registered five-robot pilot | 'tranche-1 X' -> 'the registered pilot's X' |
| R04 | the remaining 15 registered seed pairs (never run) |  |
| R05 | the registered pilot (or 'the 10 registered episodes') | check meaning in context |
| R06 | the third registered design (v3) | for data: 'the registered five-robot pilot' |
| R07 | the second registered design (v2) |  |
| R08 | the first registered design (v1) |  |
| R09 | the registered design |  |
| R10 | intersection run 1 |  |
| R11 | intersection run 2 |  |
| R12 | intersection run 1 (central layer on vs off, 13 Nov 2026) |  |
| R13 | intersection run 2 (live VLM vs scripted default plan, 14 Nov 2026) |  |
| R14 | both intersection runs |  |
| R15 | the intersection runs | run 1 only if the 13 Nov registration is meant |
| R16 | the registration of intersection run 1 | or run 2's addendum; check |
| R17 | the four-robot intersection |  |
| R18 | the four-robot intersection (scene) / intersection runs (data) | AMBIGUOUS: scene vs runs |
| R19 | the five-robot pickup-and-delivery scene | keep `mapd_5_s1b` once as the file name |
| R20 | the central-layer-on arm (live VLM) | intersection run 2: 'live-VLM arm' |
| R21 | the central-layer-off arm | only the v3 meaning applies; v1/v2 meanings are history |
| R22 | the scripted default-plan arm (no VLM call) |  |
| R23 | central layer on | defined term: must in headings/captions/tables |
| R24 | central layer off | defined term: must in headings/captions/tables |
| R25 | the central layer (Layer 2) | defined term in ch1/ch3: change in headings/captions/tables; prose optional |
| R26 | local navigation (Layer 1) | defined term; prose optional |
| R27 | grounder-default resolution | demonstration outcome label |
| R28 | accepted unchanged (`vlm_verbatim`) | recorded value; reader name in captions/table headers |
| R29 | grounder default (`m3_default`) | recorded value; reader name in captions/table headers |
| R30 | the earlier recorded head-on run (30 Sep 2026) | keep `ER2LIVE_20260930_152222` only as a file id |
| R31 | two-robot head-on corridor with obstacle | keep the file name once in the scene caption |
| R32 | five-robot pickup-and-delivery scene | keep the file name once |
| R33 | four-robot intersection | keep the file name once |
| R34 | four-robot convoy counterflow scene | keep the file name once |
| R35 | the live per-group shadow run (Stage 1) |  |
| R36 | second-stage (retreat-side) question |  |
| R37 | the offline decision benchmark (v4) |  |
| R38 | the later (v4) code / benchmark | check context |
| R39 | the plan-order prompt condition (B3) |  |
| R40 | the grounder's default (cost) order |  |
| R41 | pilot series | 'batch stop rule' -> 'the pilots' early-stop rule' |
| R42 | first check episode (smoke) |  |
| R43 | run kit (deploy and launch scripts) |  |
| R44 | shadow (computed and logged, never dispatched) | define at first use per chapter |
| R45 | addendum by content (see glossary A-number table) |  |
| R46 | addendum/amendment by content (see glossary) | do not confuse with Arm A |
| R47 | episode id (define once: pilot episodes E6-E26; registered seed pairs E27-E31; intersection slots E01-E10) | keep as id |
| R48 | intersection slot id (e01-e10) | keep as id; define once |
| R49 | the five-robot scene family |  |
| R50 | sensitivity analysis by name (S1 persistent-state link, S2 start-inside rule, S3 stage-2 label and task intents) / S1 scene family | AMBIGUOUS: check context |
| R51 | decision-substitution test (T1) / straight-move test (T2) | AMBIGUOUS: never 'T1' for tranche 1 |
| R52 | role name first: perception (M1), VLM reasoning (M2), grounder (M3), execution and safety monitor (M4), orchestrator (M5), simulation (M6) | flag only where the role is not given |

---

## 6. Occurrences by Chapter

### Front matter (`chapters/00-front.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 71 | prose | …arm cleared it in 5 of 5 (4 of 4 without the smoke episode) and a scripted arm that skipped the… | `smoke` R42 |
| 88 | table | …[Numbered amendment (prereg-v1) or addendum (prereg-v3), e.g. A33],… | `prereg-v3` R06; `prereg-v1` R08; `A33` R45 |
| 103 | table | …[IB10], [Name of the four-robot intersection scene… | `IB10` R18 |
| 106 | table | …[M1--M6], [Modules 1 to 6 of the system],… | `M1` R52; `M6` R52 |
| 119 | table | …[S1b], [Name of the five-robot task-stream scene… | `S1b` R19 |

### Ch. 1 Introduction (`chapters/01-introduction.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 17 | prose | …ith a design target of 20–50 Hz #ev("1.01"). Layer 2 is slow and central, with a design target of… | `Layer 2` R25; `Layer 1` R26 |
| 23 | prose | …final experiments compare the pipeline with Layer 2 switched off on the same code, and with a sc… | `Layer 2` R25 |
| 27 | prose | …The research design frozen with the first preregistration states five research questions #ev(… | `prereg` R09 |
| 37 | prose | …- *prereg-v3, tranche 1 (pilot).* In a five-robot task-stream scene… | `prereg-v3, tranche 1` R01; `Tranche 1` R03; `tranche 2` R04; `Layer 2 on` R23 |
| 38 | prose | …- *IB10, Layer 2 on against off (exploratory).* In a… | `IB10` R18; `Layer 2 on` R23; `Layer 2` R25; `Layer 2` R25 |
| 39 | prose | …- *IB10, grounder default (exploratory).* In a secon… | `IB10` R18 |
| 40 | prose | …- *Offline bench and live shadow (exploratory).* How do prompt and input vari… | `shadow` R44; `shadow` R44 |
| 43 | prose | …ding settings and the safety settings of the second IB10 run, show what the pipeline does; no rate is com… | `second IB10 run` R11 |
| 54 | table | …[prereg-v3 tranche 1 (pilot)], [RQ2; RQ1 in part], [Layer 2 off.… | `prereg-v3 tranche 1` R01; `Arm A` R20; `Layer 2 off` R24 |
| 55 | table | …[IB10, Layer 2 on against off], [RQ2], [Layer 2 of… | `IB10` R18; `Layer 2 on` R23; `Layer 2 off` R24 |
| 56 | table | …[IB10, grounder default], [Share of RQ2 credited t… | `IB10` R18 |
| 65 | prose | …le with a commitment tiebreak), because from prereg-v3 the control is Layer 2 switched off. RQ3 is… | `prereg-v3` R06; `prereg-v1` R08; `Layer 2` R25 |
| 73 | prose | …hem out and reports back (Chapters 3 and 4). Layer 2 can be switched off by one configuration key… | `Layer 2` R25; `Layer-1` R26 |
| 82 | prose | …- *prereg-v3 tranche 1 (pilot).* No episode in either arm completed… | `prereg-v3 tranche 1` R01; `Arm A` R20; `Arm B` R21; `Arm B` R21; `Layer 2 on` R23 |
| 83 | prose | …- *IB10, Layer 2 on against off.* In the simulated f… | `IB10` R18; `Layer 2 on` R23; `Layer 2 off` R24; `Layer 2` R25 |
| 84 | prose | …- *IB10, grounder default.* In a separate run, the l… | `IB10` R18; `smoke` R42 |
| 88 | prose | …- *Offline bench and live shadow.* On 137 recorded positives, text only, a pe… | `shadow` R44; `shadow` R44; `shadow` R44; `shadow` R44 |
| 92 | prose | …he later live cells reported in this report (tranche 1 and both IB10 runs) nevertheless listed the… | `tranche 1` R03; `prereg` R09; `both IB10 runs` R14 |
| 94 | prose | …rs' own codes put different classes first in tranche 1 Arm A and in the pilot stratum as a whole, a… | `tranche 1` R03; `Arm A` R20 |
| 101 | prose | …ds control back to the robots' own planners. Layer 2 is not in the fast (20–50 Hz) control loop #… | `Layer 2` R25 |
| 102 | prose | …iments do not include them. Their control is Layer 2 switched off on the same code, so they measu… | `Layer 2` R25 |
| 104 | prose | …s registered as confirmatory, and its single tranche is reported as a pilot. The IB10 runs, the b… | `tranche` R05; `prereg-v3` R06; `IB10 runs` R14; `shadow` R44 |
| 105 | prose | …The safety-exemption fix was switched on in IB10 run 2, where it never fired, and in the demonstrat… | `IB10 run 2` R11; `M4` R52 |
| 116 | prose | …: the research questions, the history of the preregistration from v1 to v3, the simulated scenes… | `prereg` R09 |
| 118 | prose | …ports the results: the IB10 comparisons, the prereg-v3 tranche-1 pilot, the failure-cause classification and… | `prereg-v3 tranche-1` R01; `IB10` R18 |

### Ch. 2 Background (`chapters/02-background.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 33 | prose | …al motion, and this report keeps them as its Layer 1 for that reason. What they lack is a view of… | `Layer 1` R26 |
| 62 | prose | …of benchmarks is why this report builds and preregisters its own evaluation scenes (Chapter 5).… | `prereg` R09 |

### Ch. 3 System design (`chapters/03-system-design.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 7 | prose | …he main live experiments of this report, the prereg-v3 pilot on the five-robot scene and the IB10 i… | `prereg-v3` R06; `prereg-v3` R06; `prereg` R09; `IB10 intersection` R17 |
| 17 | prose | …+ *Layer 1 by default.* Robots navigate with their own… | `Layer 1` R26 |
| 22 | prose | …iguration key, which gives the experiments a Layer-1-only baseline on the same code.… | `Layer-1` R26 |
| 28 | prose | …n, are 20–50 Hz for Layer 1 and 0.5–2 Hz for Layer 2 #ev("3.01").… | `Layer 2` R25; `Layer 1` R26 |
| 32 | caption | …yer architecture.], [Two-layer architecture. Layer 2 (orange) observes the scene through M1 and d… | `Layer 2` R25; `Layer 1` R26; `M1` R52; `M5` R52; `M2` R52; `M3` R52 |
| 35 | prose | …*Layer 1: local reactive control.* Each robot runs it… | `Layer 1` R26; `Layer 1` R26 |
| 37 | prose | …*Layer 2: centralised semantic reasoning.* The orches… | `Layer 2` R25; `Layer 2` R25; `M5` R52; `M4` R52; `M5` R52; `M2` R52; `M3` R52; `M5` R52 |
| 39 | prose | …at the factor of about 0.18 recorded for the tranche-1 run to about 2.2 #ev("3.31").… | `tranche-1` R03; `Layer 2` R25 |
| 41 | prose | …ers meet at one point, the congestion event. Layer 2 does not steer robots continuously. It issue… | `Layer 2` R25; `Layer 1` R26 |
| 45 | heading | …== Modules M1–M6 and Their Contracts <sec:design-modules>… | `M1` R52; `M6` R52 |
| 58 | table | …); `/coordination/tasks` (task registry from M5)],… | `M5` R52 |
| 67 | table | …tatic obstacles; `GroundingParams`; optional stage-2 retreat choice],… | `stage-2` R36 |
| 79 | prose | …om the `DICT_4X4_50` dictionary #ev("3.07"). M1 detects the markers, maps their corners from… | `M1` R52; `M5` R52; `M1` R52; `M1` R52; `M2` R52 |
| 81 | prose | …onfiguration key, `reasoning_enabled`, turns Layer 2 off as a whole. With it set to false, detection,… | `Layer 2 off` R24; `Layer 2` R25; `Layer-1` R26; `M2` R52; `M3` R52 |
| 83 | prose | …ets one #ev("3.10"). If every attempt fails, M2 returns a result without a decision, and M5… | `M2` R52; `M5` R52; `M2` R52 |
| 85 | prose | …decision into a command that M4 can execute. M3 is a deterministic, geometry-driven grounder… | `M3` R52 |
| 100 | prose | …*1. Detect.* M5 tracks, for every robot with a goal, the sma… | `M5` R52 |
| 102 | prose | …*2. Decide.* For an admitted event, M5 saves the current annotated frame, builds a… | `M5` R52; `M2` R52; `M3` R52; `M3` R52 |
| 104 | prose | …schema-valid command or raises an error that M5 records as a grounding failure. A refused yi… | `M5` R52; `M5` R52 |
| 106 | prose | …*4. Act.* M5 fans the command out as one `CoordinationCom… | `M5` R52; `M5` R52 |
| 108 | prose | …*5. Resolve.* M4’s status messages update M5’s command lifecy… | `M4` R52; `M5` R52; `M4` R52; `M5` R52; `M3` R52 |
| 112 | prose | …M2’s answer is a `CongestionDecision` with the… | `M2` R52 |
| 114 | prose | …ch strategy, what M3 grounds it to and which M4 primitive finally moves the robots. The grou… | `M4` R52 |
| 123 | table | …table.header([*Strategy (M2)*], [*Grounding (M3)*], [*Execution (M4)*]),… | `M2` R52 |
| 127 | table | …imitives above, dispatched phase by phase by M5.],… | `M5` R52 |
| 140 | prose | …M3 is where the system's main safety-relevant j… | `M3` R52; `M3` R52 |
| 149 | table | …e.header([*Setting*], [*Shipped default*], [*S1b scene overlay*], [*Effect*]),… | `S1b` R19 |
| 155 | table | …`], [The recede order of `junction_clear` is M3’s cost order.],… | `M3` R52 |
| 157 | caption | …the five-robot S1b scene file declares. The prereg-v3 pilot ran with the plan channel and refusal-… | `prereg-v3` R06; `IB10 registration` R16; `S1b` R19; `S1b` R19; `M5` R52 |
| 160 | prose | …ndidates are ranked by a cost function (the "chi" order). The release phase lets the lowest-c… | `chi` R40 |
| 164 | prose | …o_action`, which the task-stream scene sets, M5 withholds that wait and dispatches nothing a… | `M5` R52 |
| 171 | prose | …legs, or substitutes one robot's action with M3’s own. The search is bounded at four edits #… | `M3` R52; `M3` R52 |
| 173 | prose | …an receives one of three provenance labels: `vlm_verbatim` (accepted unchanged), `repaired` (accepted… | `vlm_verbatim` R28; `m3_default` R29 |
| 175 | prose | …*The default plan.* `m3_default` names M3’s own scene-wide plan for the deci… | `m3_default` R29; `M3` R52 |
| 177 | prose | …s still recorded as matching #ev("6.02"). A `vlm_verbatim` label thus says that the model's plan passe… | `vlm_verbatim` R28; `stage-2` R36; `M4` R52; `M3` R52 |
| 179 | prose | …eld, a retreat chosen by default because the stage-2 answer was invalid, or a junction plan repla… | `stage-2` R36; `M3` R52 |
| 181 | prose | …ran in the live loop only as a decision-only shadow; and a feedback channel that tells the model… | `shadow` R44; `shadow` R44; `M3` R52 |
| 185 | prose | …mponent in the motion path. It subscribes to M1’s scene state and to the coordination comman… | `M1` R52; `M2` R52; `M3` R52 |
| 198 | table | …olds a pair whose centre-to-centre distance (M1 poses) is below this value, even while a cle… | `M1` R52 |
| 203 | prose | …narrow-aisle standoff geometry #ev("3.23"). M3 uses the same radius when it sizes escort an… | `M3` R52 |
| 205 | prose | …*STALE fail-safe.* A robot whose marker M1 can no longer detect has an unknown pose. Th… | `M1` R52; `M1` R52 |
| 211 | prose | …waits never exempt anything, and robots that M3 holds only to shield them from a retreat are… | `M3` R52 |
| 214 | prose | …ontact separation of 0.18 m plus about twice M1’s median static position error of 0.011 m #e… | `M1` R52 |
| 216 | prose | …nted as a safety finding of its episode. The preregistration addenda additionally require "pre-… | `prereg` R09; `M4` R52 |
| 226 | prose | …ted runtime does not contain the fix. In the prereg-v3 pilot and the main IB10 comparison the exemp… | `prereg-v3` R06; `IB10` R18; `IB10` R18 |
| 228 | prose | …mechanisms that do not depend on the model. M3 refuses or reshapes manoeuvres that the geom… | `M3` R52 |

### Ch. 4 Implementation (`chapters/04-implementation.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 12 | prose | …xperiments of this report were executed. The prereg-v3 tranche 1 pilot ran on a commit whose code is identica… | `prereg-v3 tranche 1` R01; `IB10` R18 |
| 41 | prose | …ine on 9 October 2026 #ev("4.02"). The later tranche 1 run used a different virtual machine, a snap… | `tranche 1` R03 |
| 47 | prose | …M1 turns overhead camera frames into a list of… | `M1` R52 |
| 51 | prose | …and writes them to the calibration file that M1 loads at start-up #ev("4.09"). Projecting on… | `M1` R52 |
| 57 | prose | …M5 is a single ROS 2 node that owns the task re… | `M5` R52 |
| 59 | prose | …ate starts an analysis. The analysis itself (M2 and M3) runs on a worker thread whose result… | `M2` R52; `M3` R52 |
| 63 | prose | …ev("4.11"). For the multi-task scenes of the prereg-v3 cells, an optional task stream replaces the… | `prereg-v3` R06; `M1` R52; `M1` R52 |
| 89 | prose | …M4 consists of a command bus, a per-robot coord… | `M4` R52 |
| 97 | prose | …command, and its execution is split between M3 and M5. M3 precomputes the whole phase seque… | `M3` R52; `M5` R52; `M3` R52; `M5` R52 |
| 99 | prose | …0.20 m in the safety file installed for the tranche 1 and IB10 cells #ev("4.16"). Navigation legs… | `tranche 1` R03; `IB10` R18; `M1` R52 |
| 107 | prose | …ace revision (v3.4), the version used by the prereg-v3 cells #ev("4.17"). The system prompt is a mi… | `prereg-v3` R06 |
| 119 | prose | …tempts fail, the result carries no decision, M5 records the stage at which it failed, and no… | `M5` R52 |
| 121 | prose | …rsion 2 and skips this step; it is on in the tranche 1 cells, and the registered IB10 overlay sets… | `tranche 1` R03; `IB10` R18; `vlm_verbatim` R28; `m3_default` R29; `M5` R52; `M3` R52; `M3` R52; `M4` R52; `M3` R52 |
| 127 | prose | …ere first stamped with wall time, which made M1’s speeds read at about 0.38 times their true… | `M1` R52; `M1` R52; `M5` R52 |
| 135 | prose | …was to make the rebuild a gated step. In the tranche 1 kit, the build step checks that every stage… | `tranche 1` R03; `kit` R43 |
| 139 | prose | …d, and the suite is not fully green. For the tranche 1 runtime the recorded unit-suite result was 5… | `tranche 1` R03 |
| 141 | prose | …or started with the 0.20 m floor, and that a Layer-2-off episode wrote no decision artifact #ev("4.26… | `Layer-2-off` R24; `kit` R43 |
| 165 | prose | …ng, which has no switch. None of them ran in tranche 1 or the first IB10 run; Chapter 6 reports an… | `tranche 1` R03; `tranche-1` R03; `first IB10 run` R10; `IB10 grounder-default run` R13 |
| 167 | prose | …- *v4 per-cluster choice and live shadow.* The cod… | `v4` R38; `shadow` R44; `shadow` R44; `shadow` R44 |
| 168 | prose | …68 recorded bundles, and was switched on in IB10 run 2, where it never fired, and in the demonstrat… | `IB10 run 2` R11; `M4` R52 |
| 172 | prose | …- *Escort obstacle guard.* An M3 key, default off, refuses an escort whose st… | `M3` R52 |
| 173 | prose | …- *Reverse obstacle guard.* An M3 key, default off, applies the same check to… | `M3` R52 |
| 176 | prose | …- *Convoy queued-robot hold.* An M3 key, default off, holds robots outside the c… | `M3` R52 |
| 178 | prose | …rts on them, they are kept separate from the prereg-v3 data and never pooled with it.… | `prereg-v3` R06 |

### Ch. 5 Methodology (`chapters/05-methodology.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 7 | prose | …s the research questions, the history of the preregistration, the simulated scenes, the experime… | `prereg` R09; `v4` R38 |
| 11 | prose | …- *prereg-v3 tranche 1* on the five-robot S1b scene, Layer 2 on aga… | `prereg-v3 tranche 1` R01; `S1b` R19; `Layer 2 on` R23; `Layer 2 off` R24 |
| 12 | prose | …- *IB10 live resolution* on the four-robot intersection, Layer 2 on… | `IB10 live resolution` R12; `Layer 2 on` R23; `Layer 2 off` R24 |
| 13 | prose | …- *IB10 grounder-default arm*, a separate run on the same scene, Layer 2… | `IB10 grounder-default arm` R13; `Layer 2 on` R23 |
| 14 | prose | …- *the v4 offline bench*, a replay of recorded decisions. Explorator… | `v4 offline bench` R37 |
| 21 | prose | …runs and the v4 bench are never pooled with prereg-v3 data, and the two IB10 runs are never pooled… | `prereg-v3` R06; `IB10 runs` R14; `two IB10 runs` R14; `v4 bench` R37 |
| 25 | heading | …=== Questions registered at prereg-v1… | `prereg-v1` R08 |
| 27 | prose | …The research design frozen with the first preregistration states five research questions #ev(… | `prereg` R09 |
| 39 | prose | …as a directional hypothesis #ev("5.02"). The tranche-1 registration adds no hypothesis and no thres… | `tranche-1` R03; `prereg-v3` R06; `prereg-v3` R06; `S1b` R19; `S1b` R19; `Layer 2 on` R23; `Layer 2 off` R24; `Layer 2` R25 |
| 41 | prose | …*Why tranche 1 is reported as a pilot.* The registered conf… | `tranche 1` R03; `Tranche 1` R03; `tranche 1` R03; `tranche 2` R04; `IB10 experiment` R15 |
| 43 | prose | …*IB10 live resolution.* The registered question is whether the ful… | `IB10 live resolution` R12; `Layer 2` R25; `Layer 2` R25; `M5` R52; `M2` R52; `M4` R52; `M3` R52 |
| 45 | prose | …*IB10 grounder-default arm.* The addendum asks two questions #ev("5.20"… | `IB10 grounder-default arm` R13; `IB10` R18; `Layer 2` R25; `smoke` R42; `M3` R52 |
| 47 | prose | …*v4 bench.* The bench ranks prompt and input variants… | `v4 bench` R37; `M2` R52 |
| 51 | prose | …dment A3" for the first set and "v3 addendum A33" for the second.… | `A33` R45; `A3` R46 |
| 53 | heading | …=== prereg-v1: two-robot battery and a classical control… | `prereg-v1` R08 |
| 55 | prose | …me stall trigger, grounding and execution as Arm A, with decisions taken by a per-type policy t… | `Arm A` R20; `Arm B` R21 |
| 57 | prose | …- *v1 amendment A2* made the order in which robots are listed i… | `A2` R46 |
| 58 | prose | …- *v1 amendment A3* adopted the M3 yield feasibility gate (`swa… | `A3` R46; `M3` R52 |
| 59 | prose | …- *v1 amendment A4* made the position-verified arrival the prim… | `A4` R46 |
| 60 | prose | …- *v1 amendment A5* replaced simulator contact flags with dista… | `A5` R46 |
| 62 | heading | …=== prereg-v2: recovery from a formed jam… | `prereg-v2` R07 |
| 64 | prose | …d bootstrap intervals #ev("5.07"). In v2 the Layer-2-off control was a mock decision layer that alway… | `Layer-2-off` R24; `vlm_verbatim` R28; `m3_default` R29 |
| 66 | heading | …=== prereg-v3: fixed stack, emergent congestion… | `prereg-v3` R06 |
| 68 | prose | …n, the measures and the Arm B control before tranche 1 ran. A8, A9 and A15 explain the IB10 remedy… | `tranche 1` R03; `tranche-1` R03; `IB10` R18; `S1b` R19; `S1b` R19; `S1b` R19; `Arm B` R21; `A32` R45; `A35` R45; `A36` R45; `A8` R46; `A9` R46; `A15` R46; `S1 scene` R49 |
| 70 | prose | …- *v3 addenda A8 and A9* froze the IB10 release-lane remedy, a 0.33 m lateral pull-o… | `IB10` R18; `A8` R46; `A9` R46 |
| 71 | prose | …and registered this "latch-on-pass" event as S1b's conflict class #ev("5.10").… | `S1b` R19; `A15` R46 |
| 72 | prose | …easoning_enabled: false`. *A36* recorded the tranche-1 outcome and one deviation, the GPU wall-cloc… | `tranche-1` R03; `tranche 2` R04; `S1b` R19; `Arm B` R21; `Layer 2 off` R24; `A32` R45; `A33` R45; `A34` R45; `A33` R45; `A35` R45; `A36` R45; `M5` R52 |
| 74 | prose | …The meaning of "Arm B" therefore changed. In v1 it was a classical… | `Arm B` R21; `Layer 2` R25; `A34` R45 |
| 78 | prose | …ault addendum are registered separately from prereg-v3, each written before its first episode #ev("… | `prereg-v3` R06; `IB10 experiment` R15 |
| 84 | heading | …=== S1b: five-robot task-stream scene… | `S1b` R19 |
| 86 | prose | …S1b is the sparse-warehouse member of the S1 fam… | `S1b` R19; `S1 family` R49 |
| 92 | caption | …caption: flex-caption([Layout of the S1b scene.], [Layout of the S1b scene: tracked b… | `S1b` R19; `S1b` R19 |
| 95 | heading | …=== IB10: four-robot intersection… | `IB10` R18 |
| 97 | prose | …IB10 is a staged four-way jam #ev("5.16"). Four r… | `IB10` R18 |
| 103 | caption | …caption: flex-caption([Layout of the IB10 intersection.], [Layout of the IB10 intersection: four ro… | `IB10 intersection` R17; `IB10 intersection` R17 |
| 110 | caption | …from demonstration take 5 of 5, not from an IB10 experiment episode.#fig-source("6.01")]),… | `IB10 experiment` R15; `IB10` R18; `intersection_bottleneck` R33 |
| 121 | caption | …terflow scene.], [Convoy counterflow scene (`convoy_counterflow_slip`, seed 42), four robots, raw overhead camera… | `convoy_counterflow_slip` R34 |
| 130 | caption | …acle.], [Head-on corridor with an obstacle (`head_on_asymmetric_w0p2_eopen_bshort_o0`, seed 42), two robots, raw overhead camera… | `head_on_asymmetric_w0p2_eopen_bshort_o0` R31 |
| 137 | prose | …*Arm A, Layer 2 on.* The full pipeline runs. M5’s s… | `Arm A` R20; `Layer 2 on` R23; `M5` R52; `M4` R52 |
| 139 | prose | …o Arm B produces the same outcome records as Arm A. M5 logs one fixed status line at start-up,… | `Arm A` R20; `Arm A` R20; `Arm B` R21; `Arm B` R21; `Arm B` R21; `Layer 2 off` R24; `Layer 2` R25; `M5` R52; `M5` R52; `M5` R52 |
| 141 | prose | …*Arm C, grounder default, no VLM.* The Layer 2 trig… | `Arm C` R22; `Arm C` R22; `Layer 2` R25; `m3_default` R29; `M4` R52; `M5` R52; `M3` R52 |
| 150 | table | …[prereg-v3 tranche 1, S1b], [A: ER-2. \ B: `reasoning_enabled: fa… | `prereg-v3 tranche 1` R01; `S1b` R19; `Arm B` R21 |
| 151 | table | …[IB10 live resolution], [A: ER-2. \ B: `reasoning_enabled: false`.… | `IB10 live resolution` R12 |
| 152 | table | …[IB10 grounder default], [A: ER-2. \ C: scripted mock, M3 default p… | `IB10 grounder default` R13; `M3` R52 |
| 157 | prose | …The rows differ in runtime. Tranche 1 ran on the commit that introduced the Arm B… | `Tranche 1` R03; `first IB10 run` R10; `IB10` R18; `Arm A` R20; `Arm B` R21; `Arm C` R22 |
| 161 | heading | …=== S1b measures (v3 addendum A33)… | `S1b` R19; `A33` R45 |
| 163 | prose | …v3 addendum A33 fixed every S1b measure in code before any confirmatory epis… | `S1b` R19; `A33` R45; `A33` R45; `A34` R45 |
| 169 | prose | …te episode, otherwise censored at $T_"end"$. A33 treats the two registered names as one quant… | `A33` R45 |
| 173 | prose | …rozen table of 18 legs, harvested before the tranche on a different machine #ev("5.25"). The arri… | `tranche` R05 |
| 175 | prose | …re closer than 0.45 m, the distance at which M4’s latch fires #ev("5.24"). Encounters that s… | `M4` R52 |
| 181 | prose | …count) are scored on every matched analysis. Arm B makes no analyses, so every per-conflict mea… | `Arm B` R21 |
| 190 | table | …m], [pair encounter threshold, equal to the M4 latch],… | `M4` R52 |
| 198 | caption | …caption: flex-caption([S1b scorer parameters (v3 addenda A33 and A34).]… | `S1b` R19; `S1b` R19; `A33` R45; `A34` R45; `A33` R45; `A34` R45 |
| 201 | heading | …=== IB10 measures… | `IB10` R18 |
| 203 | prose | …All IB10 scoring uses the criteria frozen for the sce… | `IB10` R18 |
| 205 | prose | …is is a centre-distance test on robot pairs; IB10 declares no static obstacles, and contact wi… | `IB10` R18; `M4` R52 |
| 209 | prose | …tribution.* For every dispatched decision of Arm A the scorer reports the strategy, the plan pr… | `Arm A` R20; `Arm C` R22; `vlm_verbatim` R28; `m3_default` R29; `m3_default` R29; `M3` R52; `M3` R52; `M3` R52 |
| 217 | prose | …c Sim, the ROS 2 stack in a container, and a kit of scripts that deploys the runtime, launche… | `kit` R43; `kit` R43; `kit` R43 |
| 219 | heading | …=== prereg-v3 tranche 1… | `prereg-v3 tranche 1` R01 |
| 221 | prose | …pilots, so they were not unseen; v3 addendum A33 records this as a limitation #ev("5.44").… | `A33` R45 |
| 223 | prose | …amendment A2 #ev("5.47"); the same holds for both IB10 runs #ev("5.47").… | `both IB10 runs` R14; `Arm A` R20; `A2` R46 |
| 225 | prose | …he estimate plus one more call reached it, a tranche total of \$1.30 counted Arm A spend, and an… | `tranche` R05; `Arm A` R20; `Arm A` R20; `Arm B` R21 |
| 227 | prose | …to three attempts. If all three aborted, the tranche stopped for a ruling instead of skipping or… | `tranche` R05 |
| 229 | heading | …=== IB10 live resolution… | `IB10 live resolution` R12 |
| 231 | prose | …2 bring-up was parallel, as in every earlier IB10 run, because the jam gate's onset window is… | `IB10` R18; `Arm A` R20; `smoke` R42; `E01` R47; `E02` R47; `E03` R47; `E10` R47; `E01` R47 |
| 245 | table | …[Arm A with M5 running but no analysis], [Counted a… | `Arm A` R20; `M5` R52 |
| 247 | table | …[Model probe failure before an Arm A episode], [The episode never starts; the run… | `Arm A` R20 |
| 249 | caption | …caption: flex-caption([IB10 exclusion and attempt rules.], [IB10 exclusi… | `IB10` R18; `IB10` R18 |
| 254 | heading | …=== IB10 grounder-default run… | `IB10 grounder-default run` R13 |
| 256 | prose | …utcomes and exclusion rules are those of the first IB10 run unless the addendum states otherwise. Both a… | `first IB10 run` R10; `Arm A` R20; `Arm A` R20; `Arm A` R20; `Arm C` R22; `smoke` R42; `smoke` R42; `e02` R48; `e03` R48; `e10` R48; `M5` R52 |
| 258 | prose | …$1.00, and a per-episode guard of \$0.25 for Arm A; Arm C makes no calls #ev("5.30").… | `Arm A` R20; `Arm C` R22 |
| 260 | prose | …ered run were known, the owner asked for one Arm C slot in the registered exclusion class to be… | `Arm C` R22; `Arm C` R22 |
| 264 | prose | …hree distances must be kept apart: 0.45 m is M4’s proximity latch and the conflict definitio… | `M4` R52; `M4` R52 |
| 266 | prose | …In tranche 1 the gates were #ev("5.32"):… | `tranche 1` R03 |
| 268 | prose | …sible millimetre graze with a rack island in tranche 1, which is not established as a contact (Chap… | `tranche 1` R03; `M4` R52 |
| 269 | prose | …- a *floor gate*: M4’s start-up line must show the 0.20 m floor,… | `M4` R52 |
| 270 | prose | …- a *condition gate* per arm: for Arm A, every grounded artifact carries the escort… | `Arm A` R20; `Arm B` R21; `M5` R52 |
| 274 | prose | …In both IB10 runs the floor was installed for every arm and ga… | `both IB10 runs` R14; `Arm A` R20; `Arm C` R22; `m3_default` R29; `smoke` R42; `M4` R52 |
| 276 | prose | …on command exempts the robots inside it from M4’s proximity check against each other. A `jun… | `M4` R52 |
| 280 | heading | …=== prereg-v3 tranche 1… | `prereg-v3 tranche 1` R01 |
| 282 | prose | …timand is the mean paired difference between Arm A and Arm B, per measure #ev("5.34"). Pairs ar… | `Arm A` R20; `Arm B` R21; `Arm B` R21 |
| 288 | heading | …=== IB10… | `IB10` R18 |
| 290 | prose | …The IB10 registration rules out inferential statistics. The episod… | `IB10 registration` R16; `Arm A` R20; `Arm C` R22; `Arm C` R22 |
| 292 | prose | …loor stops, and the provenance label of each Arm A episode. An exact test or an exact binomial… | `Arm A` R20 |
| 296 | prose | …re-cause classification keeps the registered tranche, the pilots and the November takes apart in… | `tranche` R05; `first IB10 run` R10; `Arm A` R20; `Arm C` R22 |
| 300 | prose | …tory and post hoc: it was designed after the tranche-1 results were known and after the pilot episo… | `tranche-1` R03; `S1b` R19; `Layer 2 on` R23; `Layer 2 off` R24 |
| 302 | prose | …lock lines onto the simulation clock for the Layer-2-off sheets, with an acceptance tolerance fixed i… | `Layer-2-off` R24 |
| 318 | prose | …39 of 154 recorded positive decisions of the Layer-2-on episodes as written, and for 151 with the st… | `Layer-2-on` R23 |
| 326 | prose | …le meant to be withheld, one episode and the Layer-2-off sheets were identifiable from the method not… | `Layer-2-off` R24 |
| 328 | heading | …=== Strata, frozen outcomes and the Layer-2-off arm <sec:ch5-fc-strata>… | `Layer-2-off` R24 |
| 330 | prose | …never pooled: the 10 episodes of registered prereg-v3 tranche 1 (five seed pairs, Arm A and Arm B), the 21 E… | `prereg-v3 tranche 1` R01; `Arm A` R20; `Arm B` R21; `v4` R38; `batch` R41; `shadow` R44 |
| 334 | prose | …In the Layer-2-off arm no analysis is made and no command is di… | `Layer-2-off` R24; `Layer-2-off` R24; `Layer 2` R25; `Layer 2` R25 |
| 338 | prose | …he escort and reverse legs dispatched in the Layer-2-on episodes, 57 legs in 25 of the 28 episodes,… | `Layer-2-on` R23; `M3` R52; `M4` R52 |
| 340 | prose | …the primary coding and never in place of it. S1 and S2 were declared before rating and are l… | `S1` R50; `S2` R50; `S3` R50; `S1` R50; `S2` R50; `S3` R50; `S1` R50; `S1` R50 |
| 342 | heading | …== Offline v4 Bench <sec:ch5-bench>… | `v4` R38 |
| 344 | prose | …representative, and it is never pooled with prereg-v3 #ev("5.37").… | `prereg-v3` R06; `S1b` R19; `v4 bench` R37; `A33` R45; `M2` R52 |
| 346 | prose | …es: the pilots E6 to E26 and the episodes of tranche 1. As recorded live, 149 of them carry a valid… | `tranche 1` R03; `prereg-v1` R08; `S1b` R19; `Arm B` R21; `batch` R41; `E6` R47; `E26` R47; `M3` R52 |
| 350 | prose | …*Metrics.* M3 feasibility: a positive decision is feasible… | `M3` R52; `M3` R52 |
| 355 | prose | …` and `temporary_wait` with the real offline M3, keeps only the options M3 executes as asked… | `M3` R52; `M3` R52 |
| 361 | prose | …ter variant was also run as a live shadow on S1b. In each analysis the ordinary Arm A loop de… | `S1b` R19; `Arm A` R20; `Stage 1` R35; `v4` R38; `shadow` R44; `shadow` R44; `M2` R52 |
| 369 | prose | …lds; dispatch itself was not checked against M4’s logs #ev("6.08").… | `M4` R52 |
| 381 | prose | …posed plan, and separately with the scripted Arm C decision, and compares the commands #ev("6.0… | `Arm C` R22; `stage-2` R36 |
| 391 | prose | …e text on) for the head-on corridor, and the tranche-1 Arm A procedure for the five robots. The int… | `tranche-1` R03; `second IB10 run` R11; `IB10 intersection` R17; `IB10` R18; `IB10` R18; `S1b` R19; `Arm A` R20; `Layer 2 on` R23; `Layer-2-off` R24; `shadow` R44; `M4` R52 |
| 398 | prose | …d phases match that plan with no fallback or stage-2 command, and whose back-out order differs fr… | `stage-2` R36 |
| 399 | prose | …- *M3-default resolution*: every other resolved take, including any t… | `M3-default resolution` R27 |
| 401 | prose | …he takes give no rate and no comparison with Layer 2 off; nothing from them is reported as a percenta… | `Layer 2 off` R24 |
| 409 | prose | …rs or replaces it when it is infeasible. The IB10 registration records that in the earlier live pilot every… | `IB10 registration` R16; `IB10` R18; `Arm A` R20; `Arm A` R20; `Arm C` R22; `Arm C` R22; `M3` R52; `M3` R52; `M3` R52 |
| 411 | prose | …Layer 2 off, not a classical coordinator. In IB10 nothing acts on a formed jam once Layer 2 is… | `IB10` R18; `Arm B` R21; `Arm B` R21; `Layer-2-off` R24; `Layer 2 off` R24; `Layer 2` R25 |
| 413 | prose | …o its times are not directly comparable with Arm A's #ev("5.35").… | `Arm A` R20; `Arm C` R22; `Arm C` R22 |
| 415 | prose | …egistered S1b seeds had run as pilots before tranche 1, so pilot-informed expectations existed for… | `tranche 1` R03; `S1b` R19 |
| 417 | prose | …as harvested on a different machine from the tranche, a recorded limitation #ev("5.25"). Type-lab… | `tranche` R05; `S1b` R19; `A33` R45 |
| 423 | prose | …*Small n.* Tranche 1 has five pairs, the first IB10 run five epis… | `Tranche 1` R03; `tranche-1` R03; `first IB10 run` R10 |
| 425 | prose | …about 55 min of wall-clock time and the ten tranche-1 episodes took 9 h 18 min on one GPU machine;… | `tranche-1` R03; `tranche 1` R03; `tranche 2` R04; `tranche 2` R04; `tranche` R05; `prereg-v3` R06; `IB10 registration` R16; `IB10` R18; `S1b` R19; `Arm B` R21; `Layer 2 off` R24; `Layer 2 off` R24; `A36` R45; `A34` R45 |
| 427 | prose | …*Non-independence.* The IB10 episodes are near-repeats of one scene, whic… | `IB10` R18 |
| 429 | prose | …g-v3 was registered as confirmatory, and its tranche is reported as a pilot. IB10, Arm C, Stage 1… | `tranche` R05; `prereg-v3` R06; `IB10` R18; `Arm C` R22; `Stage 1` R35 |
| 433 | prose | …ch live result comes from one scene: S1b for tranche 1 and IB10 for both IB10 runs. IB10 is a stage… | `tranche 1` R03; `both IB10 runs` R14; `IB10` R18; `IB10` R18; `S1b` R19; `S1b` R19 |

### Ch. 6 Results (`chapters/06-results.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 8 | prose | …- *Exploratory pilots.* The two IB10 runs on the four-robot intersection, five episode… | `two IB10 runs` R14 |
| 9 | prose | …- *Registered pilot.* prereg-v3 tranche 1 on the five-robot S1b scene, registered as c… | `prereg-v3 tranche 1` R01; `S1b` R19 |
| 10 | prose | …ys and traces of recorded decisions, and the v4 bench. Nothing in them is executed in simulation.… | `v4 bench` R37 |
| 13 | prose | …e grades, across experiments, or between the two IB10 runs. Safety evidence throughout is the ground-tr… | `two IB10 runs` R14 |
| 15 | heading | …== IB10: Layer 2 On vs Off <sec:res-ib10-ab>… | `IB10` R18; `Layer 2` R25 |
| 17 | prose | …The first IB10 run (2026-11-13) compared Arm A, the full Layer… | `first IB10 run` R10; `Arm A` R20; `Arm B` R21; `Layer 2` R25; `Layer 2` R25 |
| 25 | table | …table.header([*Measure*], [*Arm A, Layer 2 on (ER-2)*], [*Arm B, Layer 2 off*]… | `Arm A` R20; `Arm B` R21; `Layer 2 on` R23; `Layer 2 off` R24 |
| 29 | table | …ast arrival], [112.9, 115.5, 116.5, 116.6 s; e09 censored], [all five censored at the horizon… | `e09` R48 |
| 30 | table | …t GT robot-pair centre distance], [0.2633 m (e09)], [0.2856 m],… | `e09` R48 |
| 32 | table | …dispatches], [`repaired` 4, `m3_default` 1, `vlm_verbatim` 0], [no dispatch],… | `vlm_verbatim` R28; `m3_default` R29 |
| 34 | caption | …caption: flex-caption([IB10 run 1: Layer 2 on against off.], [IB10 run 1 (2026… | `IB10 run 1` R10; `IB10 run 1` R10; `Layer 2 on` R23; `Layer 2 on` R23; `Layer 2 off` R24 |
| 37 | prose | …Arm A resolved four of five episodes and Arm B non… | `Arm A` R20; `Arm B` R21; `Arm B` R21; `Arm B` R21; `Layer 1` R26; `m3_default` R29; `e01` R48 |
| 39 | prose | …The one unresolved Arm A episode, e09, began with an off-pattern answ… | `Arm A` R20; `e09` R48; `M3` R52 |
| 41 | prose | …fore supports the claim that the pipeline, a Layer 2 trigger plus M3 grounding and phased dispatc… | `Layer 2` R25; `Layer 1` R26; `vlm_verbatim` R28; `M3` R52 |
| 43 | heading | …== IB10: VLM vs Grounder Default (Arm C) <sec:res-ib… | `IB10` R18; `Arm C` R22 |
| 45 | prose | …The second IB10 run (2026-11-14) is separate and is never pooled… | `second IB10 run` R11; `Arm A` R20; `Arm C` R22; `Arm C` R22; `e02` R48; `M3` R52; `M3` R52 |
| 53 | table | …table.header([*Measure*], [*Arm A (ER-2)*], [*Arm C, before the re-run*], [*Ar… | `Arm A` R20; `Arm C` R22; `Arm C` R22 |
| 54 | table | …[Valid episodes], [5], [4 (e02 formed no jam)], [5 (e02 a2 counted)],… | `e02` R48; `e02` R48 |
| 55 | table | …[Resolved], [5/5 (4/4 without the smoke)], [4/4], [5/5],… | `smoke` R42 |
| 60 | table | …[Plan provenance], [`repaired` 4, `m3_default` 1], [`m3_default`], [`m3_default`],… | `m3_default` R29; `m3_default` R29; `m3_default` R29 |
| 62 | caption | …caption: flex-caption([IB10 run 2: live VLM against the grounder default.], [I… | `IB10 run 2` R11; `IB10 run 2` R11; `Arm A` R20; `Arm C` R22; `Arm C` R22; `e02` R48 |
| 65 | prose | …ed 4 of 4 valid episodes, against 5 of 5 for Arm A #ev("6.32"). Arm A is 5 of 5 counting the sm… | `Arm A` R20; `Arm A` R20; `Arm C` R22; `Arm C` R22; `smoke` R42; `smoke` R42; `e02` R48 |
| 67 | prose | …jam and resolved in 118.1 s on `m3_default`. Arm C became 5 of 5, mean 117.86 s #ev("6.34").… | `Arm C` R22; `m3_default` R29; `e02` R48 |
| 69 | prose | …*What the arms share.* Every Arm A first dispatch re-grounds to exactly the pla… | `Arm A` R20; `Arm A` R20; `Arm A` R20; `Arm C` R22; `Arm C` R22 |
| 71 | prose | …how that the model is useless either; in the two IB10 runs, run 1's e09 is the one case in which an off… | `two IB10 runs` R14; `Arm C` R22; `Arm C` R22; `Layer 2` R25; `e09` R48; `M3` R52 |
| 73 | heading | …== prereg-v3 Tranche 1 Pilot <sec:res-t1>… | `Tranche 1 Pilot` R02; `prereg-v3` R06 |
| 75 | prose | …Tranche 1 ran ten episodes on the five-robot S1b scene… | `Tranche 1` R03; `S1b` R19; `Arm A` R20; `Arm B` R21; `Layer 2 on` R23; `Layer 2 off` R24 |
| 83 | table | …table.header([*Measure*], [*Arm A*], [*Arm B*], [*Difference A − B, bootstrap… | `Arm A` R20; `Arm B` R21 |
| 90 | table | …)], [0 of 10 (no analyses)], [degenerate for Arm B],… | `Arm B` R21 |
| 91 | table | …F1], [0.778; 0.915], [n/a], [degenerate for Arm B],… | `Arm B` R21 |
| 96 | caption | …caption: flex-caption([prereg-v3 tranche 1, reported as a pilot.], [prereg-v3 tranche 1… | `prereg-v3 tranche 1` R01; `prereg-v3 tranche 1` R01; `S1b` R19; `M4` R52 |
| 99 | prose | …lay lower bound excludes zero by 0.6 s, with Arm A lower #ev("6.14"). With five pairs, every ru… | `Arm A` R20 |
| 101 | prose | …and not as a rescore of them, finds 1 of the tranche's 2 recorded `vlm_verbatim` plans dispatched… | `tranche` R05; `Arm A` R20; `Arm A` R20; `vlm_verbatim` R28; `M4` R52; `M4` R52 |
| 109 | prose | …r without changing any of them. The original tranche-1 outcome, 0 of 10 episodes complete, stands a… | `tranche-1` R03 |
| 117 | table | …table.header([*Primary cause*], [*Tranche 1, Arm A*], [*Tranche 1, Arm B*], [*Pilots, ho… | `Tranche 1` R03; `Tranche 1` R03; `Arm A` R20; `Arm B` R21 |
| 131 | prose | …changes (reported beside the primary coding; S1 not re-rated, see caption)*],… | `S1` R50 |
| 132 | table | …[S1, persistent-state chain rule], [not re-rated… | `S1` R50 |
| 133 | table | …[S2, start-inside straight-move check], [0], [0]… | `S2` R50 |
| 135 | caption | …auses of the failure units of the five-robot S1b episodes, by stratum. The strata are never p… | `S1b` R19; `Layer-2-off` R24; `batch` R41; `S1` R50; `S1` R50; `S1` R50 |
| 145 | table | …[Tranche 1 Arm A], [8], [0.875], [0.830], [0.875], [1],… | `Tranche 1` R03; `Arm A` R20 |
| 146 | table | …[Tranche 1 Arm B], [10], [1.000], [n/a], [1.000], [0],… | `Tranche 1` R03; `Arm B` R21 |
| 152 | caption | …is reported as n/a where it is undefined; in Arm B every unit falls in one code. Disagreements… | `Arm B` R21 |
| 155 | prose | …The ten registered tranche-1 episodes held 8 failure units in Arm A and 1… | `tranche-1` R03; `tranche 1` R03; `Arm A` R20; `Arm A` R20; `Arm A` R20; `Arm A` R20; `Arm B` R21 |
| 157 | prose | …e of what the robots did, so the two arms of tranche 1 are not compared on cause codes. In 2 pilot… | `tranche 1` R03; `Arm A` R20; `Arm B` R21; `Arm B` R21 |
| 159 | prose | …me, decides two units; if it were left open, Arm A would read 2 execution, 2 decision, 1 ground… | `Arm A` R20 |
| 161 | prose | …reproducible, and 13 units change code: 2 in Arm A, 5 and 4 in the horizon and stop-rule pilots… | `Arm A` R20; `Arm A` R20; `Arm B` R21; `S1` R50; `S1` R50; `S2` R50; `S3` R50; `S3` R50 |
| 163 | prose | …ed in 25 of the 28 Layer-2-on episodes: 3 in tranche 1 Arm A, 47 in the pilots and 7 in the Novembe… | `tranche 1` R03; `tranche 1` R03; `Arm A` R20; `Arm A` R20; `Arm A` R20; `Layer-2-on` R23; `Layer-2-on` R23; `S1` R50 |
| 165 | prose | …*Per leg.* In tranche 1 Arm A no mechanism acts on any of the 3 legs… | `tranche 1` R03; `Arm A` R20 |
| 174 | table | …hain rule*], [*Units with such a linked leg, S1*]),… | `S1` R50 |
| 185 | caption | …aption: flex-caption([Interception analysis, tranche 1, Arm A.], [Interception analysis, tranche 1,… | `tranche 1` R03; `tranche 1` R03; `Arm A` R20; `Arm A` R20; `Layer-2-off` R24; `S1` R50 |
| 194 | table | …hain rule*], [*Units with such a linked leg, S1*]),… | `S1` R50 |
| 205 | caption | …ry chain rule and under sensitivity analysis S1. The rows for the mechanisms overlap, so the… | `S1` R50 |
| 214 | table | …hain rule*], [*Units with such a linked leg, S1*]),… | `S1` R50 |
| 225 | caption | …ry chain rule and under sensitivity analysis S1. The rows for the mechanisms overlap, so the… | `S1` R50 |
| 234 | prose | …nd-stage label and the rebuilt task intents (S3), 2 #ev("6.63").… | `S3` R50 |
| 235 | prose | …is not linked to the command that pinned it; S1 finds one such unit. S1 relaxes this and is… | `S1` R50; `S1` R50 |
| 236 | prose | …them, a worked example. One episode and the Layer-2-off sheets could be identified from the method n… | `Layer-2-off` R24 |
| 241 | prose | …est is registered for it, and the registered tranche-1 episodes are never pooled with the explorato… | `tranche-1` R03 |
| 266 | prose | …exists for yields only; it was off in every IB10 run #ev("6.49").… | `IB10` R18; `M4` R52 |
| 268 | prose | …* An earlier recorded run on the same scene (ER2LIVE, 2026-09-30, older code) is the one recorded… | `ER2LIVE` R30; `stage-2` R36 |
| 298 | prose | …id the model's plan change the commands that M4 received? It classifies each analysis at thr… | `M4` R52 |
| 308 | table | …[2. Plan accepted unchanged (`vlm_verbatim`)], [2 (0 of 20 `junction_clear`)], [11], [1… | `vlm_verbatim` R28 |
| 316 | prose | …r, yielder and passer that ran all came from M3 #ev("6.49"). The 14 accepted plans came from… | `M3` R52 |
| 318 | prose | …0, plus three answers in two development-era smoke episodes #ev("6.49"). Where the effect can b… | `smoke` R42; `e09` R48; `e09` R48 |
| 326 | caption | …the decision (`junction_clear`, provenance `vlm_verbatim`) and the dispatch of `robot_3`'s back-out.… | `vlm_verbatim` R28; `M5` R52; `M4` R52 |
| 338 | table | …d, 3/4 arrived; takes 2 to 4 resolved by the M3 default plan; take 5 resolved 4/4, labelled… | `M3` R52 |
| 340 | table | …corridor with obstacle], [1], [resolved 2/2, M3-default resolution (grounder-corrected)],… | `M3-default resolution` R27 |
| 341 | table | …[Five robots, S1b seed position 21], [1], [unresolved, 1/5 arr… | `S1b` R19 |
| 354 | table | …alid response*], [*Accepted plan, recorded (`vlm_verbatim`)*], [*Accepted and dispatched as written, c… | `vlm_verbatim` R28 |
| 356 | table | …5 takes], [48 of 48], [3 (20 `repaired`, 25 `m3_default`)], [2 (takes 1 to 3: 2; takes 4 and 5: 0)],… | `m3_default` R29 |
| 358 | table | …ots, 1 take], [8 of 8], [2 (1 `repaired`, 5 `m3_default`)], [2], [not computed],… | `m3_default` R29 |
| 361 | caption | …ed.], [Demonstration campaign, per analysis (stage-2 retreat calls not counted): valid model resp… | `stage-2` R36; `M3` R52 |
| 366 | prose | …s unresolved: a one-frame identity glitch in M1 triggered the analysis on an approach snapsh… | `M1` R52; `M3` R52; `M3` R52 |
| 371 | caption | …ection scene declares no static obstacles to M3 (its rack blocks and walls are scene geometr… | `M3` R52 |
| 376 | prose | …A near-tie.* The two recede orders differ in M3’s recede cost by 0.010 m, against the verifi… | `M3` R52 |
| 377 | prose | …the release and the crossing order stayed on M3’s ranking, and the model's own `crossing_ord… | `M3` R52 |
| 396 | prose | …ames all four robots resolved the scene in a smoke run, which shows that the scene can be resol… | `smoke` R42 |
| 418 | caption | …acle, two robots, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead cam… | `M3-default resolution` R27 |
| 423 | caption | …or with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead cam… | `M3-default resolution` R27 |
| 428 | caption | …or with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead cam… | `M3-default resolution` R27 |
| 433 | prose | …The five-robot take ran the S1b pickup-and-delivery scene on seed position 2… | `S1b` R19; `S1b` R19; `M3` R52 |
| 439 | caption | …ff.], [Five-robot pickup-and-delivery scene (S1b, seed position 21, an exploratory seed outsi… | `S1b` R19 |
| 463 | table | …[IB10 run 1], [A 0.2633 m; B 0.2856 m], [0], [scene decl… | `IB10 run 1` R10 |
| 464 | table | …[IB10 run 2], [A 0.3008 m; C 0.2965 m], [0], [as run 1],… | `IB10 run 2` R11 |
| 465 | table | …[prereg-v3 tranche 1], [0.225–0.424 m over all ten episodes], [0]… | `prereg-v3 tranche 1` R01 |
| 469 | caption | …e distance from ground truth, floor stops in M4’s log, and the status of robot-obstacle cont… | `M4` R52 |
| 472 | prose | …#ev("6.37") #ev("6.41") #ev("6.17"). In most IB10 and campaign episodes the lowest pair distan… | `IB10` R18; `smoke` R42; `e09` R48 |
| 474 | prose | …m of a declared box under a `reverse`, which M3 does not sweep against declared boxes #ev("6… | `M3` R52 |
| 478 | prose | …xemptions are lost #ev("6.07"). It was on in IB10 run 2, where it never fired #ev("6.06"), and in th… | `IB10 run 2` R11; `M4` R52; `M4` R52 |
| 489 | table | …[Bystander waiver at command start (A19)], [unhonoured partner counts as own], [both… | `A19` R46 |
| 492 | caption | …and on. Unit tests and offline replay; on in IB10 run 2 (never fired) and in the demonstration takes… | `IB10 run 2` R11; `M4` R52 |
| 497 | prose | …- *Escort obstacle guard* (M3): refuses an escort whose straight segment c… | `M3` R52; `M4` R52 |
| 498 | prose | …- *Reverse obstacle guard* (M3): refuses a `reverse` whose leg crosses a de… | `M3` R52 |
| 499 | prose | …- *Stall abort* (M4): cancels a primitive whose commanded motion… | `M4` R52 |
| 500 | prose | …- *Queued-robot hold* (M3): used only in convoy takes 4 and 5, where i… | `M3` R52 |
| 504 | heading | …== v4 Offline Bench and Stage 1 Shadow <sec:res-bench>… | `Stage 1` R35; `v4` R38 |
| 506 | prose | …n level, text only, and is never pooled with prereg-v3 (@sec:ch5-bench) #ev("1.06") #ev("5.36"). It… | `prereg-v3` R06; `S1b` R19; `v4 bench` R37; `M3` R52 |
| 508 | prose | …The Stage 1 live shadow ran the per-cluster call beside… | `Stage 1` R35; `shadow` R44; `shadow` R44; `shadow` R44 |
| 512 | prose | …priors are confounded. This led v1 amendment A2 to randomise the order #ev("1.12"). The late… | `A2` R46 |

### Ch. 7 Discussion (`chapters/07-discussion.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 5 | prose | …ing is pooled across experiments, across the two IB10 runs, or with the demonstration takes.… | `two IB10 runs` R14 |
| 11 | prose | …jam in 4 of 5 episodes, against 0 of 5 with Layer 2 off, where the robots did not move again once th… | `Layer 2 off` R24; `Layer 2` R25; `smoke` R42; `M3` R52 |
| 19 | prose | …s arrived #ev("6.42"), and in the registered tranche-1 pilot no episode of either arm completed its task… | `tranche-1 pilot` R02; `second IB10 run` R11 |
| 27 | prose | …* is answered in part and at pilot scale. In tranche 1, Arm A detected 9 of 11 ground-truth conflic… | `tranche 1` R03; `Arm A` R20 |
| 28 | prose | …ed arm and the plan-influence trace, and the tranche-1 pilot has no completed episode in either arm (rung… | `tranche-1 pilot` R02; `Layer 1` R26 |
| 36 | prose | …ady been refused #ev("6.15"). The registered tranche shows the same pattern seed by seed: of Arm… | `tranche` R05; `S1b` R19; `Arm A` R20; `Stage 1` R35; `shadow` R44; `M3` R52; `M4` R52 |
| 40 | prose | …he campaign's 6 accepted plans become 5, and tranche 1's 2 become 1; both are recomputations beside… | `tranche 1` R03; `vlm_verbatim` R28; `M5` R52 |
| 44 | prose | …ot settle it. It names no dominant cause. In tranche 1 Arm A and in the pilot stratum as a whole th… | `tranche 1` R03; `Arm A` R20; `Layer-2-off` R24 |
| 59 | prose | …ion fix is not validated live.* It was on in IB10 run 2, where it never fired, and in the demonstrat… | `IB10 run 2` R11 |
| 68 | prose | …e would then have resolved. For 25 of the 45 Layer-2-on units (5 of 8, 19 of 33 and 1 of 4 by stratu… | `Layer-2-on` R23; `S3` R50; `S1` R50 |
| 72 | prose | …re not unseen, the samples are small and the IB10 episodes are near-repeats, each live result… | `IB10` R18; `S1b` R19; `Arm C` R22; `Layer-2-off` R24; `M3` R52 |
| 74 | prose | …shown because of its label, and the earlier ER2LIVE run was chosen because it qualifies #ev("5.5… | `ER2LIVE` R30 |
| 76 | prose | …The failure-cause rule was written after the tranche-1 results and after its authors had read earli… | `tranche-1` R03 |
| 80 | prose | …he source reports are not free of error. The tranche-1 report's dispatched column counted a refused… | `tranche-1` R03 |

### Ch. 8 Conclusion (`chapters/08-conclusion.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 9 | prose | …d an execution layer that reports back, with Layer 2 switchable off by one key on identical code… | `Layer 2` R25 |
| 11 | prose | …tion in 4 of 5 episodes, against 0 of 5 with Layer 2 off. In a separate run, the live-VLM arm cleared… | `Layer 2 off` R24; `Layer 2` R25; `smoke` R42 |
| 13 | prose | …ction scene, the pipeline cleared a jam that Layer 1 alone never cleared, and the grounder's defa… | `Layer 1` R26 |
| 22 | prose | …a candidate, but it has so far run only as a shadow that never dispatched #ev("6.47").… | `shadow` R44 |
| 25 | prose | …n the Layer-2-on and Layer-2-off arms on the tranche-1 seed positions with the fixes keyed on. If a… | `tranche-1` R03; `tranche 2` R04; `tranche` R05; `Layer-2-on` R23; `Layer-2-off` R24; `Layer-2-off` R24; `M3` R52; `M4` R52 |
| 26 | prose | …determined as written, a clock anchor in the Layer-2-off arm would make its 10 units codable, an orde… | `Layer-2-off` R24; `S1` R50 |

### Appendix B Traces and demos (`chapters/10-appendix-traces.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 16 | caption | …ection scene declares no static obstacles to M3 (its rack blocks and walls are scene geometr… | `M3` R52 |
| 34 | table | …d508d3440e51822fdcd3f0f0`], [head-on take 1, M3-default resolution (grounder-corrected)],… | `M3-default resolution` R27 |
| 45 | prose | …the demonstration takes, both IB10 runs and tranche 1 #ev("6.12"). For every ground-truth row the… | `tranche 1` R03; `both IB10 runs` R14 |
| 69 | table | …[IB10 live], [`ib10L_e01_armA_a1`], [3001], [clear… | `IB10` R18 |
| 70 | table | …[IB10 live], [`ib10L_e01_armA_a2`], [3001], [clear… | `IB10` R18 |
| 71 | table | …[IB10 live], [`ib10L_e02_armB_a1`], [3001], [clear… | `IB10` R18 |
| 72 | table | …[IB10 live], [`ib10L_e03_armA_a1`], [3001], [clear… | `IB10` R18 |
| 73 | table | …[IB10 live], [`ib10L_e04_armB_a1`], [3001], [clear… | `IB10` R18 |
| 74 | table | …[IB10 live], [`ib10L_e05_armA_a1`], [3001], [clear… | `IB10` R18 |
| 75 | table | …[IB10 live], [`ib10L_e06_armB_a1`], [3001], [clear… | `IB10` R18 |
| 76 | table | …[IB10 live], [`ib10L_e07_armA_a1`], [3001], [clear… | `IB10` R18 |
| 77 | table | …[IB10 live], [`ib10L_e08_armB_a1`], [3001], [clear… | `IB10` R18 |
| 78 | table | …[IB10 live], [`ib10L_e09_armA_a1`], [3001], [clear… | `IB10` R18 |
| 79 | table | …[IB10 live], [`ib10L_e10_armB_a1`], [3001], [clear… | `IB10` R18 |
| 80 | table | …[IB10 safety], [`ib10S_e01_armA_a1`], [3001], [cle… | `IB10` R18 |
| 81 | table | …[IB10 safety], [`ib10S_e02_armC_a1`], [3001], [cle… | `IB10` R18 |
| 82 | table | …[IB10 safety], [`ib10S_e02_armC_a2`], [3001], [cle… | `IB10` R18 |
| 83 | table | …[IB10 safety], [`ib10S_e03_armA_a1`], [3001], [cle… | `IB10` R18 |
| 84 | table | …[IB10 safety], [`ib10S_e04_armC_a1`], [3001], [cle… | `IB10` R18 |
| 85 | table | …[IB10 safety], [`ib10S_e05_armA_a1`], [3001], [cle… | `IB10` R18 |
| 86 | table | …[IB10 safety], [`ib10S_e06_armC_a1`], [3001], [cle… | `IB10` R18 |
| 87 | table | …[IB10 safety], [`ib10S_e07_armA_a1`], [3001], [cle… | `IB10` R18 |
| 88 | table | …[IB10 safety], [`ib10S_e08_armC_a1`], [3001], [cle… | `IB10` R18 |
| 89 | table | …[IB10 safety], [`ib10S_e09_armA_a1`], [3001], [cle… | `IB10` R18 |
| 90 | table | …[IB10 safety], [`ib10S_e10_armC_a1`], [3001], [cle… | `IB10` R18 |
| 91 | table | …[tranche 1], [`E27 A a1`], [6001], [clear], [34.8 (r1,… | `tranche 1` R03 |
| 92 | table | …[tranche 1], [`E27 B a1` (bring-up abort)], [670], [cle… | `tranche 1` R03 |
| 93 | table | …[tranche 1], [`E27 B a2`], [6001], [clear], [34.7 (r5,… | `tranche 1` R03 |
| 94 | table | …[tranche 1], [`E28 A a1`], [6001], [clear], [28.1 (r5,… | `tranche 1` R03 |
| 95 | table | …[tranche 1], [`E28 B a1`], [6001], [clear], [41.1 (r1,… | `tranche 1` R03 |
| 96 | table | …[tranche 1], [`E29 A a1`], [6001], [clear], [7.1 (r2, `… | `tranche 1` R03 |
| 97 | table | …[tranche 1], [`E29 B a1`], [6001], [clear], [14.0 (r1,… | `tranche 1` R03 |
| 98 | table | …[tranche 1], [*`E30 A a1`*], [6001], [*brief graze*], [… | `tranche 1` R03 |
| 99 | table | …[tranche 1], [`E30 B a1`], [6001], [clear], [10.0 (r2,… | `tranche 1` R03 |
| 100 | table | …[tranche 1], [`E31 A a1`], [6001], [clear], [19.3 (r2,… | `tranche 1` R03 |
| 101 | table | …[tranche 1], [`E31 B a1`], [6001], [clear], [8.7 (r2, `… | `tranche 1` R03 |

### Evidence index, ch. 1 rows (`evidence/ch1.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 4 | prose | …1.01", [Design targets: Layer 1 at 20–50 Hz, Layer 2 at 0.5–2 Hz.], [`68e67b5:docs/modules.md` (h… | `Layer 2` R25; `Layer 1` R26 |
| 8 | prose | …RQ5 (renamed from H1 to H5), frozen with the prereg-v1 research design; RQ1 scope note (post-trigge… | `prereg-v1` R08 |
| 10 | prose | …r live cells; floor latches exempt pairs. v3 A9: 0.20 m floor ruled a push-limiter backstop,… | `A9` R46; `A9` R46 |
| 12 | prose | …", [prereg-v1 tag on 2026-09-30 (= 569d95c); prereg-v3 design prepared 2026-10-06; append-only adde… | `prereg-v3` R06; `prereg-v1` R08 |
| 14 | prose | …31 live S1b episodes (E6-E26 pilots, E27-E31 tranche 1).], [`05a44eb:docs/reports/2026-10-22-v4-ben… | `tranche 1` R03; `S1b` R19; `E6` R47; `E26` R47; `E27` R47; `E31` R47 |
| 18 | prose | …#evidence("1.08", [Tranche 1: 5 seeds (positions 1 to 5) x 2 arms = 10 ep… | `Tranche 1` R03; `tranche 1` R03; `tranche 2` R04; `A32` R45 |
| 20 | prose | …m B Layer 2 off); exploratory, separate from prereg-v3.], [`68e67b5:isaac/config/scenarios/intersec… | `prereg-v3` R06; `IB10` R18; `Arm A` R20; `Arm B` R21; `Layer 2 on` R23; `Layer 2 off` R24; `intersection_bottleneck` R33 |
| 22 | prose | …ts; never pooled with the 2026-11-13 arms or prereg-v3.], [`e6a904e:docs/superpowers/specs/2026-11-… | `prereg-v3` R06; `Arm A` R20; `Arm C` R22; `Arm C` R22; `e02` R48; `e10` R48; `M3` R52 |
| 24 | prose | …#evidence("1.11", [Stage 1 live shadow of the per-cluster variant: 7 ep… | `Stage 1` R35; `shadow` R44; `shadow` R44 |
| 26 | prose | …#evidence("1.12", [v1 amendment A2: presentation order random, seeded, recorded… | `A2` R46; `A2` R46 |
| 28 | prose | …#evidence("1.13", [IB10 registration: in the earlier live pilot every IB10 plan w… | `IB10 registration` R16; `IB10` R18; `Arm A` R20; `M3` R52 |
| 30 | prose | …#evidence("1.14", [S1b: 5 robots, 5 task nodes, 5 tasks per robot (… | `S1b` R19; `mapd_5_s1b` R32 |
| 32 | prose | …fier order: every Arm A decision artifact of tranche 1 (28 artifacts, E27-E31) and of both IB10 run… | `tranche 1` R03; `both IB10 runs` R14; `IB10` R18; `Arm A` R20; `Arm A` R20; `Arm A` R20; `Arm C` R22; `E27` R47; `E31` R47 |

### Evidence index, ch. 3 rows (`evidence/ch3.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 6 | prose | …3.01", [Design targets: Layer 1 at 20–50 Hz, Layer 2 at 0.5–2 Hz; proposal safety values d\_min 0… | `Layer 2` R25; `Layer 1` R26; `M4` R52 |
| 14 | prose | …#evidence("3.05", [M5 timer period 0.5 s; detector runs on each sc… | `M5` R52; `M2` R52; `M3` R52 |
| 22 | prose | …s/specs/2026-10-06-prereg-v3-design.md` (A35 Arm B switch)])… | `Arm B` R21; `A35` R45; `M2` R52; `M3` R52 |
| 28 | prose | …#evidence("3.12", [Shipped M5 config: stall\_threshold\_sec 12.0, progress… | `M5` R52 |
| 38 | prose | …\_enabled False, refusal\_no\_action False); tranche-1 condition: `68e67b5:docs/reports/2026-10-21-… | `tranche-1` R03; `IB10 registration` R16; `S1b` R19; `mapd_5_s1b` R32; `M5` R52 |
| 40 | prose | …efuse, ties by robot order); junction\_clear chi ranking, release lead = rank 0, yielder re-e… | `chi` R40 |
| 50 | prose | …lines 13, 58–62); `68e67b5:docs/modules.md` (M4.4 d\_min 0.3 m); `68e67b5:reasoning/rag/comm… | `M4` R52 |
| 52 | prose | …admitted passers; shield holds not partners; A19 one-sided waivers; speed rule exempts cleari… | `A19` R46 |
| 54 | prose | …lue 0.20 m = footprint contact 0.18 m + ~2 × M1 median static error 0.011 m.], [`68e67b5:ros… | `M1` R52 |
| 56 | prose | …ecs/2026-10-06-prereg-v3-design.md` (A28(i), A32: "pre/post arm gates")])… | `A32` R45; `A28` R46; `M4` R52 |
| 60 | prose | …-scope, based on 68e67b5); later exploratory IB10 run with the key on: `cbe3dcf:docs/reports/2… | `IB10` R18; `IB10` R18; `smoke` R42 |
| 62 | prose | …#evidence("3.30", [Stage-1 call latency "ER-2 3.2-3.8 s" (and gpt-4o 2.… | `Stage-1` R35 |
| 64 | prose | …#evidence("3.31", [Tranche 1 ran at a real-time factor of about 0.18 (abo… | `Tranche 1` R03 |

### Evidence index, ch. 4 rows (`evidence/ch4.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 4 | prose | …#evidence("4.01", [Tranche 1 ran on runtime `1624db1`, whose code equals… | `Tranche 1` R03; `IB10` R18; `Arm A` R20; `batch` R41 |
| 6 | prose | …3-66; `68e67b5:docs/implementation_notes.md` M6, 2026-09-16 container rebuild entry])… | `M6` R52 |
| 18 | prose | …("4.08", [Grounding `mode: derived`; and the M5 reasoning pipeline and grounder derive the c… | `M5` R52 |
| 22 | prose | …#evidence("4.10", [M1 launch values: stopped 0.01 m/s, slow 0.05 m… | `M1` R52 |
| 24 | prose | …#evidence("4.11", [M5 shipped values: stall 12.0 s, progress 0.10… | `M5` R52 |
| 32 | prose | …lease, resolved, fallback); plan provenance `vlm_verbatim`, `repaired`, `m3_default` (`verify_and_repa… | `vlm_verbatim` R28; `m3_default` R29; `M5` R52 |
| 34 | prose | …n-command partners; floor file installed for tranche 1 and IB10.], [`68e67b5:ros2_ws/src/swarm_exec… | `tranche 1` R03; `tranche 1` R03; `IB10` R18; `IB10` R18 |
| 38 | prose | …#evidence("4.18", [M5 stall and cool-down on `time.monotonic()`; V… | `M5` R52; `M2` R52; `M5` R52; `M5` R52 |
| 40 | prose | …nce 2026-09-27 (`a1aa81d`); wall stamps made M1 speeds read about 0.38 x true; `stale_after_… | `M1` R52; `M6` R52; `M1` R52 |
| 42 | prose | …sts); `68e67b5:docs/implementation_notes.md` M6, 2026-09-16 "Ground-truth oracle fixed for p… | `M6` R52 |
| 44 | prose | …s.], [`68e67b5:docs/implementation_notes.md` M6, 2026-06-30 entry, and experiment section, 2… | `M6` R52 |
| 46 | prose | …vidence("4.22", [RTX lidar motion BVH: three kit arguments required together; one alone break… | `kit` R43; `M4` R52 |
| 48 | prose | …D cost about 10 debugging runs (2026-07-01). Tranche 1 build gate: every USD newer than its yaml, `… | `Tranche 1` R03; `M6` R52 |
| 52 | prose | …rs; the 60 failing or erroring ids equal the A27 reference list minus `tests/simulation`.], [… | `A27` R46 |
| 54 | prose | …gate (floor line `hard_contact_floor_m=0.2`; Arm B 0 decision artifacts); scorer `3c71503` and… | `Arm B` R21; `M1` R52 |
| 66 | prose | …abled: false` (prompt v2, no verify/repair); tranche 1 Arm A condition "backend: ER-2, plan channel… | `tranche 1` R03; `IB10` R18; `Arm A` R20; `Arm A` R20; `Arm A` R20 |
| 68 | prose | …250; `68e67b5:docs/implementation_notes.md` M6, 2026-06-21 and 2026-09-16 entries; `68e67b5… | `M6` R52 |
| 72 | prose | …#evidence("4.35", [IB10 artifacts record `reasoner_config_effective.… | `IB10` R18 |
| 74 | prose | …rded real-time factors: 0.396 on the new VM (smoke) vs 0.397 on the old VM, in a side-by-side c… | `smoke` R42; `E1` R47; `S1` R50; `S1` R50 |
| 76 | prose | …(grey-image sub-arm); Rev 5 Arm F found the M1 annotation overlay is not the trigger (raw f… | `M1` R52 |

### Evidence index, ch. 5 rows (`evidence/ch5.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 6 | prose | …#evidence("5.02", [prereg-v3 registers the Arm A minus Arm B comparison a… | `prereg-v3` R06; `Arm A` R20; `Arm B` R21; `A33` R45 |
| 8 | prose | …#evidence("5.03", [Tranche 1 adds no hypothesis and no threshold; 5 seeds… | `Tranche 1` R03; `E6` R47; `E26` R47 |
| 10 | prose | …13 to skip prereg-v3 tranche 2 and run IB10; tranche 1 reported as pilot.], [`ad67a18:docs/superpow… | `tranche 1` R03; `tranche-1` R03; `tranche 2` R04; `prereg-v3` R06; `IB10` R18; `A32` R45 |
| 12 | prose | …#evidence("5.05", [prereg-v1 tag on 2026-09-30, freezing the research des… | `prereg-v1` R08; `A1` R46; `A10` R46 |
| 14 | prose | …#evidence("5.06", [v1 Arm B = classical reasoner (per-type policy table,… | `Arm B` R21; `A2` R46; `A3` R46; `A4` R46; `A5` R46; `A2` R46; `A5` R46 |
| 16 | prose | …#evidence("5.07", [prereg-v2 design dated 2026-09-30, revisions 1 to 6: j… | `prereg-v2` R07 |
| 18 | prose | …#evidence("5.08", [prereg-v3 design prepared 2026-10-06; discipline: ever… | `prereg-v3` R06 |
| 20 | prose | …#evidence("5.09", [v3 A8/A9: IB10 release-lane remedy frozen, pull-off 0.33 m;… | `IB10` R18; `A8` R46; `A9` R46; `A8` R46; `A9` R46 |
| 22 | prose | …", [v3 A15(iii): latch-on-pass registered as S1b's conflict class; opposing robots latched at… | `S1b` R19; `A15` R46; `A15` R46 |
| 24 | prose | …ed), A36 (outcome, GPU wall-clock deviation, tranche-2 decision open).], [`ad67a18:docs/superpowers… | `tranche-2` R04; `Arm B` R21; `Layer-2-off` R24; `A32` R45; `A33` R45; `A34` R45; `A35` R45; `A36` R45; `A32` R45; `A36` R45 |
| 28 | prose | …#evidence("5.13", [S1b tracked band 5.0 x 3.6 m (\|x\| up to 2.5, \|y\|… | `S1b` R19; `mapd_5_s1b` R32 |
| 30 | prose | …#evidence("5.14", [S1b: 5 robots, 5 nodes, 5 tasks per robot (25),… | `S1b` R19; `mapd_5_s1b` R32; `S1` R50 |
| 32 | prose | …#evidence("5.16", [IB10: 4 robots, spawns 1.75 m from centre, goals… | `IB10` R18; `IB10` R18; `intersection_bottleneck` R33 |
| 34 | prose | …#evidence("5.17", [IB10 registration: question; runtime 68e67b5, no code deployed… | `IB10 registration` R16; `Arm A` R20; `Arm B` R21 |
| 38 | prose | …ate, task stream still run; one status line; Arm B overlay = base + one line.], [`ad67a18:docs/… | `Arm B` R21; `shadow` R44; `A35` R45 |
| 40 | prose | …gates; never pooled with 2026-11-13 arms or prereg-v3.], [`e6a904e:docs/superpowers/specs/2026-11-… | `prereg-v3` R06; `Arm C` R22; `Arm C` R22; `m3_default` R29; `m3_default` R29 |
| 42 | prose | …#evidence("5.21", [Runtimes: tranche 1 on 1624db1 (merged into 68e67b5); IB10 on 68… | `tranche 1` R03; `IB10` R18; `A36` R45 |
| 44 | prose | …#evidence("5.22", [Tranche-1 Arm A: ER-2, plan channel on, shield-escort… | `Tranche-1` R03; `Arm A` R20 |
| 46 | prose | …#evidence("5.23", [A33 measures: GT offset fit 0.00-1.00 s in 0.01… | `A33` R45; `A33` R45; `A34` R45 |
| 48 | prose | …#evidence("5.24", [A33(5)/(6): encounter below 0.45 m; merge_gap_s… | `A33` R45; `A33` R45; `A34` R45 |
| 50 | prose | …#evidence("5.25", [S1b free-flow table frozen from the 18 solo legs… | `S1b` R19; `A34` R45 |
| 52 | prose | …#evidence("5.26", [IB10 outcomes: resolved = criterion 1 AND criteri… | `IB10` R18; `Arm A` R20 |
| 54 | prose | …#evidence("5.27", [Tranche-1 order p1 A-B, p2 B-A, p3 A-B, p4 B-A, p5 A-B… | `Tranche-1` R03; `A33` R45 |
| 56 | prose | …#evidence("5.28", [Tranche-1 caps: 600 sim-s horizon; CAP_EP 0.25 USD gua… | `Tranche-1` R03; `Arm B` R21; `A34` R45 |
| 58 | prose | …#evidence("5.29", [IB10: 5 episodes per arm, order E01 A ... E10 B;… | `IB10` R18; `smoke` R42; `E01` R47; `E10` R47 |
| 60 | prose | …5 h cumulative, 1.00 USD total, 0.25 USD per Arm A episode.], [`e6a904e:docs/superpowers/specs/… | `Arm A` R20; `smoke` R42; `smoke` R42; `e01` R48; `e02` R48; `e03` R48; `e10` R48 |
| 62 | prose | …launch, no retry; invalid-jam counting rule; Arm C reported before and after.], [`e6a904e:docs/… | `Arm C` R22; `e02` R48 |
| 64 | prose | …#evidence("5.32", [Tranche-1 gates: contact gate 0.18 m all-pairs GT, 0 f… | `Tranche-1` R03 |
| 66 | prose | …#evidence("5.33", [IB10 safety: floor 0.20 m both arms, gated on sta… | `IB10` R18; `smoke` R42 |
| 68 | prose | …owers/specs/2026-10-06-prereg-v3-design.md` (A33(1)-(3), A33(7), A34 R11)])… | `A33` R45; `A33` R45; `A34` R45 |
| 70 | prose | …#evidence("5.35", [IB10: episodes not independent samples, no p-valu… | `IB10` R18; `Arm C` R22 |
| 72 | prose | …31 live S1b episodes (E6-E26 pilots, E27-E31 tranche 1); 149 valid, 137 positive; no frames, text-o… | `tranche 1` R03; `S1b` R19; `E6` R47; `E26` R47; `E27` R47; `E31` R47 |
| 74 | prose | …mate effects; exploratory; never pooled with A32-A36); modes recorded, classical, replay with… | `A32` R45; `A36` R45 |
| 76 | prose | …everse, reroute, temporary_wait with offline M3; keep executable options; numbered list plus… | `M3` R52 |
| 84 | prose | …#evidence("5.42", [Stage 1 live shadow: 7 episodes, seed positions 21-2… | `Stage 1` R35; `shadow` R44; `shadow` R44 |
| 88 | prose | …owers/specs/2026-10-06-prereg-v3-design.md` (A33(8))])… | `A33` R45; `E1` R47; `E5` R47; `E6` R47; `E20` R47 |
| 90 | prose | …#evidence("5.46", [Arm B meaning: v1 classical reasoner; v2 Layer-2-o… | `Arm B` R21; `Layer-2-off` R24; `Layer 2 off` R24; `A34` R45; `A35` R45; `A33` R45; `A34` R45; `A35` R45 |
| 92 | prose | …#evidence("5.47", [Tranche-1 and IB10 live cells listed robots in ascendi… | `Tranche-1` R03; `tranche 1` R03; `first IB10 run` R10; `IB10` R18; `IB10` R18; `Arm A` R20; `Arm A` R20; `Arm A` R20; `A2` R46; `A2` R46 |
| 94 | prose | …#evidence("5.48", [Auxiliary Layer 2 paths forced off by reasoning\_enabled false… | `Layer 2` R25; `shadow` R44; `shadow` R44 |
| 96 | prose | …rev-8 classical reasoner (module docstring "Arm B: the rev-8 classical congestion reasoner"):… | `Arm B` R21; `shadow` R44 |
| 98 | prose | …#evidence("5.50", [Tranche 1 chain 2026-10-21 14:07:06Z to 23:25:33Z, 9 h… | `Tranche 1` R03; `tranche 2` R04; `IB10 registration` R16; `A36` R45; `A36` R45; `A36` R45 |
| 100 | prose | …September head-on configuration, prompt v2; tranche-1 Arm A procedure); intersection-only delta: o… | `tranche-1` R03; `IB10` R18; `Arm A` R20; `Arm A` R20; `Layer 2 on` R23; `Layer-2-off` R24; `M3-default resolution` R27; `Stage 1` R35; `shadow` R44; `E21` R47; `M4` R52 |
| 102 | prose | …aml`; `68e67b5:isaac/config/scenarios/family/head_on_asymmetric_w0p2_eopen_bshort_o0.yaml` (and the other `family/head_on_asymmet… | `head_on_asymmetric_w0p2_eopen_bshort_o0` R31; `head_on_asymmetric_` R31; `convoy_counterflow_slip` R34 |

### Evidence index, ch. 6 rows (`evidence/ch6.typ`)

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 6 | prose | …obstacle 1, five robots 1), plus the earlier ER2LIVE run; outcomes, labels, three-way count (vali… | `ER2LIVE` R30 |
| 10 | prose | …plan-order switch; ER-2 80/80 valid; offline B3 rate 7/27 per first trigger; take 5 is const… | `B3` R39 |
| 14 | prose | …#evidence("6.05", [IB10 run 1 (2026-11-13), Layer 2 on vs off: Arm A 4/5 r… | `IB10 run 1` R10; `Arm A` R20; `Arm B` R21; `Layer 2 on` R23 |
| 16 | prose | …#evidence("6.06", [IB10 run 2 (2026-11-14), Arm A vs grounder-default Arm… | `IB10 run 2` R11; `Arm A` R20; `Arm A` R20; `Arm C` R22; `Arm C` R22; `e02` R48; `e02` R48 |
| 18 | prose | …\_clearing\_exemption (default off): P1, P3, A19 waiver inputs, direction check on third-robo… | `A19` R46 |
| 28 | prose | …mm); two brief grazes within noise (3.79 mm; tranche-1 E30 Arm A 0.97 mm); robot-robot footprint ga… | `tranche-1` R03; `Arm A` R20; `E30` R47 |
| 30 | prose | …he `junction_clear` recede and release legs; IB10 declares no boxes).], [`92158d3:docs/reports… | `IB10` R18; `E18` R47; `E18` R47; `M3` R52; `M4` R52 |
| 32 | prose | …#evidence("6.14", [prereg-v3 tranche 1: 10 episodes, 0/10 complete; tasks A 16/125,… | `prereg-v3 tranche 1` R01; `Arm A` R20 |
| 34 | prose | …#evidence("6.15", [S1b grounding bottleneck: 78 analyses gave 13 mo… | `S1b` R19; `M3` R52 |
| 38 | prose | …tatic approach 5.5 mm under a reverse, which M3 does not sweep against declared boxes.], [`a… | `M3` R52 |
| 48 | prose | …#evidence("6.30", [IB10 run 1 per episode: Arm A first dispatches `junctio… | `IB10 run 1` R10; `Arm A` R20; `Arm A` R20; `Arm B` R21; `Arm B` R21; `Arm B` R21; `m3_default` R29; `e09` R48; `e09` R48; `e01` R48 |
| 50 | prose | …#evidence("6.31", [IB10 run 1 e09: trigger 1 answered `yield` (M3 default… | `IB10 run 1` R10; `e09` R48; `e09` R48; `M3` R52; `M3` R52 |
| 52 | prose | …#evidence("6.32", [IB10 run 2 per episode: Arm A 114.3, 115.7, 116.2, 116.… | `IB10 run 2` R11; `Arm A` R20; `Arm A` R20; `Arm C` R22; `m3_default` R29; `smoke` R42; `smoke` R42; `e02` R48; `e02` R48 |
| 54 | prose | …#evidence("6.33", [IB10 run 2 dispatch delay: first dispatch minus onset,… | `IB10 run 2` R11; `Arm A` R20; `Arm C` R22 |
| 56 | prose | …#evidence("6.34", [IB10 run 2 after the post hoc e02 re-run: e02 a2 formed… | `IB10 run 2` R11; `Arm A` R20; `Arm C` R22; `Arm C` R22; `m3_default` R29; `e02` R48; `e02` R48; `e02` R48; `e02` R48 |
| 58 | prose | …#evidence("6.35", [Tranche 1 per arm: throughput at the common window A 0… | `Tranche 1` R03; `Arm A` R20; `Arm A` R20; `Arm B` R21 |
| 60 | prose | …of the two trivial baselines; misses in the M3 column come from runs with the gate off, bef… | `M3` R52 |
| 62 | prose | …`robot_1` 112.5 s, `robot_2` 136.1 s; label M3-default resolution (grounder-corrected); GT closest pair 0.2176… | `M3-default resolution` R27 |
| 64 | prose | …#evidence("6.38", [ER2LIVE (2026-09-30, code `3959d7f`, not part of the… | `ER2LIVE` R30; `stage-2` R36 |
| 66 | prose | …r a one-frame M1 identity glitch); takes 2-4 M3-default resolution (plans repaired or nulled; take 4's model or… | `M3-default resolution` R27; `vlm_verbatim` R28; `chi` R40; `chi` R40; `chi` R40; `M3` R52; `M1` R52 |
| 68 | prose | …ecame waits; provenance over 36 decisions 3 `vlm_verbatim`, 15 `repaired`, 18 `m3_default`; GT closest… | `vlm_verbatim` R28; `m3_default` R29; `smoke` R42 |
| 72 | prose | …es; 2 executed as named (decisions 1 and 2, `vlm_verbatim`); 6 withheld by grounding refusals (no feas… | `vlm_verbatim` R28 |
| 74 | prose | …("6.43", [Which stages use static obstacles: M3 escort length, heading, turn cap and park cl… | `M3` R52; `M3` R52 |
| 76 | prose | …(stage-2 calls not counted); accepted plan (`vlm_verbatim`) 6 of the 65 plan-channel analyses; changed… | `vlm_verbatim` R28; `m3_default` R29; `m3_default` R29; `stage-2` R36 |
| 80 | prose | …#evidence("6.46", [v4 bench, per-cluster choice on the 137 recorded posi… | `v4 bench` R37 |
| 82 | prose | …#evidence("6.47", [v4 Stage 1 live shadow: 50 analyses in 7 episodes; 50/5… | `Stage 1` R35; `v4` R38; `shadow` R44; `shadow` R44 |
| 88 | prose | …onoured; P3 a rejected leg is not a partner; A19 counts both as third robots; third-robot wai… | `A19` R46 |
| 90 | prose | …queued robots that dispatch never commanded; prereg-v3 tranche 1 2 recorded becomes 1 (a `reroute` rerouted a… | `prereg-v3 tranche 1` R01; `vlm_verbatim` R28; `chi` R40 |
| 96 | prose | …the rubric as written, sensitivity analyses S1 and S2, reconciliation, interception table d… | `S1` R50; `S2` R50 |
| 100 | prose | …, primary and contributing causes by column (tranche 1 Arm A and Arm B, pilots to horizon and cut b… | `tranche 1` R03; `Arm A` R20; `Arm B` R21; `Arm B` R21; `S1` R50; `S2` R50; `S3` R50; `S1` R50 |
| 102 | prose | …S3, sensitivity only), clock mapping for the Layer-2-off sheets that failed its pre-declared acceptan… | `Layer-2-off` R24; `stage-2` R36; `S3` R50 |
| 104 | prose | …decisions outside `junction_clear` recorded `vlm_verbatim` with a differing dispatch (4 more `junction… | `vlm_verbatim` R28 |

---

## 7. Change List Sections 10–11: Captions and Snippets With Shorthand

Source: `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v6d/docs/reports/2026-11-15-thesis-report-change-list.md` (branch `feat/v4-per-cluster-parity`, read at HEAD `f39bc8c`; a commit `a341d25` to the register only landed at 2026-11-15T13:57Z, the change list was not touched by it). Scanned: section 10.3 placement table and 10.4 Typst snippets (lines 418–578), 10.8–10.9 (607–664) and the 11.2 paste-ready drafts (709–924). `TBD-*` placeholder ids and the paper size "A4 preview" are not shorthand and were excluded. The change list was not edited.

### 7.1 Corrected Caption Texts

| Change-list line (anchor) | Figure label | Current text (shorthand part) | Corrected text |
|---|---|---|---|
| 424, 449 | `fig:ch5-ib10-frame` | "Four-robot intersection (`intersection_bottleneck`, the IB10 scene file, seed 42) … not from an IB10 experiment episode." | "Four-robot intersection (scene file `intersection_bottleneck`, seed 42) … not from an episode of intersection run 1 or 2." |
| 427, 476 | `fig:ch6-demo-panel` | "Right: the run's own M5 and M4 log lines replayed in sync, here the decision (`junction_clear`, provenance `vlm_verbatim`)" | "Right: the run's own orchestrator (M5) and execution-monitor (M4) log lines replayed in sync, here the decision (`junction_clear`, plan accepted unchanged, `vlm_verbatim`)" |
| 432–434, 521, 530, 539 | `fig:ch6-ho-yield`, `fig:ch6-ho-pass`, `fig:ch6-ho-arrived` | "demonstration take 1 of 1 (M3-default resolution, grounder-corrected)" | "demonstration take 1 of 1 (grounder-default resolution, grounder-corrected)" |
| 435, 548 | `fig:ch6-m5-start` | "Five-robot pickup-and-delivery scene (S1b, seed position 21, …)" | "Five-robot pickup-and-delivery scene (scene file `mapd_5_s1b`, seed position 21, …)" |
| 438 | `fig:ch6-er2live` (insert-at text) | "after the ER2LIVE paragraph" | "after the paragraph on the earlier recorded head-on run (30 Sep 2026)" |
| 793 | failure-cause table caption | "failure units of the five-robot S1b episodes … the Layer-2-off arm … batch stop rule" | "failure units of the five-robot episodes … the central-layer-off arm … the pilots' early-stop rule" |
| 837 | interception table caption | "Interception analysis, tranche 1, Arm A." | "Interception analysis, registered five-robot pilot, central layer on." |
| 858, 879 | interception captions (pilots, November takes) | "under sensitivity analysis S1" | "under the persistent-state link (sensitivity analysis)" |

Note: the convoy captions in section 10.3 still say "take 1 of 3" and "all three takes"; the campaign has five convoy takes (the demo package's `figures_for_report/README.md` flags this). This is a fact correction, not a naming one.

### 7.2 Table Headers and Snippet Lines

| Change-list line | Current | Replace with |
|---|---|---|
| 744 | "=== Strata, frozen outcomes and the Layer-2-off arm" | "=== Strata, frozen outcomes and the central-layer-off arm" |
| 746 | "the 10 episodes of registered prereg-v3 tranche 1 (five seed pairs, Arm A and Arm B), the 21 ER-2 pilot episodes … the bundles of the v4 shadow" | "the 10 episodes of the registered five-robot pilot (five seed pairs, central layer on and off), the 21 exploratory pilot episodes … the bundles of the live per-group shadow run" |
| 775 | `[*Tranche 1, Arm A*], [*Tranche 1, Arm B*], [*Pilots, horizon*] …` | `[*Registered pilot, on*], [*Registered pilot, off*], [*Exploratory pilots, horizon*] …` |
| 790, 791 | `[S1, persistent-state chain rule]`, `[S2, start-inside straight-move check]` | `[Persistent-state link (sensitivity)]`, `[Start-inside rule (sensitivity)]` |
| 804, 805 | `[Tranche 1 Arm A]`, `[Tranche 1 Arm B]` | `[Registered pilot, on]`, `[Registered pilot, off]` |
| 826, 847, 868 | `[*Units with such a linked leg, S1*]` | `[*Units with such a linked leg, persistent-state link*]` |
| 718, 734, 750, 761, 766, 814, 816, 887, 891, 910, 922 | "tranche-1", "Layer-2-on", "Layer-2-off", "Arm A/B", "S1"/"S2" in prose | per the legend: registered pilot; central layer on/off; persistent-state link / start-inside rule |

### 7.3 All Change-List Rows

| Line | Where | Anchor text (current, around the first hit) | Terms on the line and replacement key |
|---|---|---|---|
| 424 | prose | …(labelled VLM-driven execution), not from an IB10 experiment episode. \| `fig:ch5-ib10-frame` \| 75 % \|… | `IB10 experiment` R15; `IB10` R18; `IB10` R18; `IB10` R18; `intersection_bottleneck` R33 |
| 425 | prose | …scene yet \| New \| Convoy counterflow scene (`convoy_counterflow_slip`, seed 42), four robots, raw overhead camera… | `convoy_counterflow_slip` R34 |
| 426 | prose | …\| New \| Head-on corridor with an obstacle (`head_on_asymmetric_w0p2_eopen_bshort_o0`, seed 42), two robots, raw overhead camera… | `head_on_asymmetric_w0p2_eopen_bshort_o0` R31 |
| 427 | prose | …the decision (`junction_clear`, provenance `vlm_verbatim`) and the dispatch of `robot_3`'s back-out.… | `vlm_verbatim` R28; `M5` R52; `M4` R52 |
| 432 | prose | …acle, two robots, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead cam… | `M3-default resolution` R27 |
| 433 | prose | …or with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead cam… | `M3-default resolution` R27 |
| 434 | prose | …or with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead cam… | `M3-default resolution` R27 |
| 435 | prose | …New \| Five-robot pickup-and-delivery scene (S1b, seed position 21, an exploratory seed outsi… | `S1b` R19 |
| 438 | prose | …line 18 (section 3 items 4 and 8), after the ER2LIVE paragraph \| New \| Head-on corridor with obst… | `ER2LIVE` R30 |
| 449 | caption | …(labelled VLM-driven execution), not from an IB10 experiment episode.#fig-source("NEW-DC")]),… | `IB10 experiment` R15; `IB10` R18; `intersection_bottleneck` R33 |
| 458 | caption | …terflow scene.], [Convoy counterflow scene (`convoy_counterflow_slip`, seed 42), four robots, raw overhead camera… | `convoy_counterflow_slip` R34 |
| 467 | caption | …acle.], [Head-on corridor with an obstacle (`head_on_asymmetric_w0p2_eopen_bshort_o0`, seed 42), two robots, raw overhead camera… | `head_on_asymmetric_w0p2_eopen_bshort_o0` R31 |
| 476 | caption | …the decision (`junction_clear`, provenance `vlm_verbatim`) and the dispatch of `robot_3`'s back-out.… | `vlm_verbatim` R28; `M5` R52; `M4` R52 |
| 521 | caption | …acle, two robots, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead cam… | `M3-default resolution` R27 |
| 530 | caption | …or with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead cam… | `M3-default resolution` R27 |
| 539 | caption | …or with obstacle, demonstration take 1 of 1 (M3-default resolution, grounder-corrected), annotated overhead cam… | `M3-default resolution` R27 |
| 548 | caption | …ff.], [Five-robot pickup-and-delivery scene (S1b, seed position 21, an exploratory seed outsi… | `S1b` R19 |
| 627 | prose | …- The M4 startup line of take 5 shows `scoped_clearin… | `M4` R52 |
| 659 | prose | …against obstacles. The same table lists one M3 check that does use static boxes (the yielde… | `M3` R52 |
| 718 | prose | …tory and post hoc: it was designed after the tranche-1 results were known and after the pilot episo… | `tranche-1` R03; `S1b` R19; `Layer 2 on` R23; `Layer 2 off` R24 |
| 734 | prose | …D-R01: fidelity check passes as written, all Layer-2-on episodes, count]] of [[TBD-R02: recorded pos… | `Layer-2-on` R23; `stage-2` R36 |
| 744 | heading | …=== Strata, frozen outcomes and the Layer-2-off arm <sec:ch5-fc-strata>… | `Layer-2-off` R24 |
| 746 | prose | …never pooled: the 10 episodes of registered prereg-v3 tranche 1 (five seed pairs, Arm A and Arm B), the 21 E… | `prereg-v3 tranche 1` R01; `Arm A` R20; `Arm B` R21; `v4` R38; `batch` R41; `shadow` R44 |
| 750 | prose | …In the Layer-2-off arm no analysis is made and no command is di… | `Layer-2-off` R24; `Layer 2` R25; `Layer 2` R25 |
| 754 | prose | …stacle guard and a reverse obstacle guard in M3, which refuse a leg whose straight path, gro… | `M3` R52; `M4` R52 |
| 756 | prose | …oding and never in place of it #ev("6.61"). *S1* also links a command to a unit when the com… | `S1` R50; `S2` R50 |
| 761 | prose | …eption per stratum) and the caveat list. The Layer-2-off arm appears in Table 1 only: it dispatched n… | `Layer-2-off` R24; `S1` R50; `S2` R50 |
| 766 | prose | …s without changing any of them. The original tranche-1 outcome, 0 of 10 episodes complete, stands a… | `tranche-1` R03 |
| 775 | table | …table.header([*Primary cause*], [*Tranche 1, Arm A*], [*Tranche 1, Arm B*], [*Pilots, ho… | `Tranche 1` R03; `Tranche 1` R03; `Arm A` R20; `Arm B` R21 |
| 790 | table | …[S1, persistent-state chain rule], [[[TBD-T1-S1-… | `S1` R50 |
| 791 | table | …[S2, start-inside straight-move check], [[[TBD-T… | `S2` R50 |
| 793 | caption | …auses of the failure units of the five-robot S1b episodes, by stratum. The strata are never p… | `S1b` R19; `Layer-2-off` R24; `batch` R41 |
| 804 | table | …[Tranche 1 Arm A], [[[TBD-T2-A-U: units rated]]], [[[TB… | `Tranche 1` R03; `Arm A` R20 |
| 805 | table | …[Tranche 1 Arm B], [[[TBD-T2-B-U: units rated]]], [[[TB… | `Tranche 1` R03; `Arm B` R21 |
| 814 | prose | …The ten registered tranche-1 episodes held [[TBD-R04: failure units, tran… | `tranche-1` R03; `tranche 1` R03; `tranche 1` R03; `Arm A` R20; `Arm A` R20; `Arm B` R21; `Arm B` R21; `Layer-2-on` R23; `S1` R50; `S1` R50; `S2` R50; `S2` R50 |
| 816 | prose | …In the Layer-2-on strata, [[TBD-R15: units with a linked leg i… | `Layer-2-on` R23; `Layer-2-on` R23; `Layer-2-on` R23; `Layer-2-on` R23; `S1` R50; `S1` R50 |
| 826 | table | …hain rule*], [*Units with such a linked leg, S1*]),… | `S1` R50 |
| 837 | caption | …aption: flex-caption([Interception analysis, tranche 1, Arm A.], [Interception analysis, tranche 1,… | `tranche 1` R03; `tranche 1` R03; `Arm A` R20; `Arm A` R20; `Layer-2-off` R24; `S1` R50 |
| 847 | table | …hain rule*], [*Units with such a linked leg, S1*]),… | `S1` R50 |
| 858 | caption | …ry chain rule and under sensitivity analysis S1. The rows for the mechanisms overlap, so the… | `S1` R50 |
| 868 | table | …hain rule*], [*Units with such a linked leg, S1*]),… | `S1` R50 |
| 879 | caption | …ry chain rule and under sensitivity analysis S1. The rows for the mechanisms overlap, so the… | `S1` R50 |
| 887 | prose | …and that pinned it. The sensitivity analysis S1 relaxes this and is reported beside the prim… | `S1` R50 |
| 891 | prose | …est is registered for it, and the registered tranche-1 episodes are never pooled with the explorato… | `tranche-1` R03 |
| 910 | prose | …ayer-2-on arm and the Layer-2-off arm on the tranche-1 seed positions, and, if a scripted default-p… | `tranche-1` R03; `tranche` R05; `Layer-2-on` R23; `Layer-2-off` R24; `Layer-2-off` R24; `M3` R52; `M4` R52 |
| 922 | prose | …@sec:ch5-failure-cause was written after the tranche-1 results and after earlier diagnoses of some… | `tranche-1` R03 |

---

## 8. Evidence Register: Replacements for a Later Pass (Not Applied)

The register (`/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v6d/docs/reports/2026-11-13-thesis-evidence-register.md`) was **not edited**: a wrap-up commit (`a341d25`, "docs: add wrap-up rows and superseded counts to evidence register") landed at 2026-11-15T13:57Z, inside the 15-minute window. Line numbers below are at `a341d25`.

| Line | Place | Current | Replace with |
|---|---|---|---|
| 48 | claims ladder, rung a heading | "a. Pipeline clears IB10" | "a. Pipeline clears the four-robot intersection" |
| 48 | rung a claim | "A Layer 2 trigger plus M3 grounding clears the four-robot intersection jam that Layer 1 alone never clears" | "A central-layer trigger plus the grounder (M3) clears the four-robot intersection jam that local navigation alone never clears" |
| 50 | rung c claim | "M3's feasibility gate" | "the grounder's feasibility gate" |
| 52 | rung e claim | "handles congestion outside IB10" | "handles congestion outside the four-robot intersection" |
| 57 | recommended wording 1 | "the full Layer 2 pipeline … against 0 of 5 with Layer 2 off. In a separate run, …" | "the full central-layer pipeline … against 0 of 5 with the central layer off (intersection run 1, 13 November 2026). In a separate run (intersection run 2, 14 November 2026), …" |
| 58 | recommended wording 2 | "all 55 analyses … 6 of 53 plan-channel analyses" | fact, not naming: the campaign report's Rev 11 counts are 67 and 65 (as in the thesis abstract) |
| 62 | recommended wording 6 | "the October pilot runs (13 of 33)" | "the exploratory five-robot pilots of 10–17 October 2026 (13 of 33)"; the registered pilot also ran in October |
| 39 | short-name list | `IBL` = "IB10 live results", `IBS` = "IB10 safety and grounder-default arm" | `IBL` = intersection run 1 results; `IBS` = intersection run 2 results |
