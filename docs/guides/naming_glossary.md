# Naming Glossary for Reader-Facing Text

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: canonical reader-facing names for scenes, experiments, arms, system parts, outcome labels, distances, analysis terms and safety mechanisms; identifier scheme; replace list; exceptions; how-to-read notes for the three most-cited reports.
- Rev 2: thesis snapshot updated to HEAD `9b71aa3`; facts softened to the sources (pilot dates, MC context, TurtleBot3 model, earlier intersection pilots, demonstration dates in UTC and UTC+7); provenance row added to the replace list; "preregistration" removed from it.
- Rev 3 (2026-11-15): reader-facing name for Layer 2 changed from "central layer" to "coordination layer" (owner decision of 2026-11-15, relayed by the report-writer session); added the distinction from M4's "coordination command" and "coordination exemption"; all derived forms updated.

---

## Purpose and Scope

The owner's request (2026-11-15): "also standardize experiments name, scenarios, the readers wont understand what is prereg-v3 or IB10".

This glossary sets the names used in **reader-facing text**: the thesis report, slides, video cards, the demo package and any summary written for someone who has not seen the repository. It does not rename anything in the repository. Repo documents (specs, reports, implementation notes) keep the module IDs of `docs/standards/doc_style.md` and may keep internal ids; when one of them is quoted to a reader, translate it with this file.

Sources the names were checked against:

- The thesis working tree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-thesis/thesis/` (branch `docs/thesis`, read at HEADs `7e589d8` to `9b71aa3` between 13:50Z and 14:05Z on 2026-11-15, while another session was editing it; read only). Where the thesis already had a clear name, this glossary adopts it.
- The reports listed under "Where the canonical evidence is" in each table, plus the demo package READMEs and the on-screen captions in v7g `config/demo_presentation/*.json`.

The full list of thesis lines that still use internal shorthand, with replacements, is `docs/guides/naming_glossary_thesis_replacements.md`.

---

## 1. Rules of Use

1. **Reader-facing name everywhere** in prose, headings, figure and table captions, table headers and slide titles.
2. **Internal id once**, in parentheses at first use in each chapter, or in a "repo id" column of a table. Example: "the four-robot intersection (scene file `intersection_bottleneck`)".
3. **Scenes: robot count first.** "Four-robot intersection", never "the intersection" alone at first use in a chapter.
4. **Dates in full**: "13 November 2026" in prose, "13 Nov 2026" in tables. Dates are UTC, as in the run reports; say so when a series crosses midnight (the demonstration campaign is 14–15 Nov UTC, all 15 Nov in local time UTC+7).
5. **Never bare** in reader text: "tranche", "tranche 1", "prereg", "prereg-v3", "IB10", "S1b", "Arm A/B/C", "batch N", "ER2LIVE", "T1/T2", "S1/S2/S3", "A33" and module codes M1–M6 without their role.
6. **Kept as defined abbreviations** (in the thesis abbreviation list, then usable): ER-2, VLM, Nav2, GT (ground truth), Layer 1 and Layer 2 (defined in Chapter 1 and Chapter 3; use "coordination layer" in headings, captions and table headers), M1–M6 (always with the role at first use in a chapter, and in every heading and caption).
7. **Stays as written**: branch names, file paths, commit hashes, config keys, scene file names, bundle and take labels, on-screen log lines. These are verbatim records; section 5 lists them and gives their meaning.
8. **Registered vs confirmatory.** Almost every study here was registered (written down before it ran): both intersection runs, the demonstration campaign and the offline replays included. Only the five-robot pilot of 21 October 2026 was registered **as confirmatory**. Write "registered as confirmatory" when that is what is meant, and "registered before it ran" for the rest.

---

## 2. Tables

### 2.1 Scenes

| Reader-facing name | Internal ids and aliases (repo id) | One-line plain definition | Canonical evidence |
|---|---|---|---|
| **Four-robot intersection** | scene file `intersection_bottleneck` (`isaac/config/scenarios/intersection_bottleneck.yaml`); IB10; `ib`, `ib10L_*`, `ib10S_*`, `ibD_*` bundle labels | Four robots start 1.75 m from the centre of a cross aisle, one per arm, each bound for the opposite arm; they reach the centre together and jam. Staged, seed 42, 300 sim-s, nothing randomised. | Thesis Chapter 5, scene section; v7a `docs/reports/2026-11-13-ib10-live-resolution-results.md` |
| **Four-robot convoy counterflow scene** | scene file `convoy_counterflow_slip` (`isaac/config/scenarios/convoy_counterflow_slip.yaml`); `cv`, `cvD_*`, `cvH_*` | One robot drives into a 0.55 m wide, 1.0 m long gap and meets a counter-flow robot nose to nose; two more robots queue behind the first, held at their start for 120 s and then released. Seed 42, 260 sim-s. | Thesis Chapter 5; v7j `docs/reports/2026-11-15-demo-campaign-results.md` sections 5 and 12 |
| **Two-robot head-on corridor with obstacle** | scene file `head_on_asymmetric_w0p2_eopen_bshort_o0` (`isaac/config/scenarios/family/`); head-on asymmetric; `ho`, `hoD_*` | Two robots meet nose to nose in a 0.55 m wide, 2.0 m long corridor; a box behind `robot_1` leaves it 0.70 m of retreat room against 1.08 m needed, so only `robot_2` can yield. Seed 42, 300 sim-s. | Thesis Chapter 5; demo campaign report section 6 |
| **Head-on scene family** | head-on asymmetric family, `family/head_on_asymmetric_*` | The two-robot head-on corridors that differ in which side the blocking box stands on; the mirrored scenes make `robot_1` the correct yielder. Used by the head-on decision analyses. | Thesis Chapter 5, offline analyses |
| **Five-robot pickup-and-delivery scene** (task-stream scene) | scene file `mapd_5_s1b` (`isaac/config/scenarios/mapd_5_s1b.yaml`); S1b; "S1 family"; `m5`, `m5D_*`, `m5V_*`; `mapd_5_s1b_seed21` | Five robots each serve five pickup-and-delivery tasks (25 in all) in a 5.0 m by 3.6 m tracked band with two rack islands; congestion is not scripted, it emerges from the task stream. 600 sim-s. | Thesis Chapter 5; v7j `docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` section 1 |
| **Seed position** | `seed position k`, seeds 1–100, `s1`…`s5` | Index into the registered list of 100 seeds; a seed fixes the start assignment and task sequence of the five-robot scene. Positions 1–20 were the planned confirmatory seeds. | Tranche-1 report section 1.3 |

### 2.2 Experiments and Run Series

Listed in the order a reader meets them in the thesis. "Episode" = one simulated run of one arm.

| Reader-facing name | Internal ids and aliases | One-line plain definition | Canonical evidence |
|---|---|---|---|
| **Registered five-robot pilot** (21 Oct 2026; 5 seed pairs, 10 episodes) | prereg-v3 tranche 1; tranche 1; "confirmatory tranche"; `batch6`, `p10` kit; `confirmatory=1`, `tag=confirmatory_t1`; seed pairs E27–E31, each with an Arm A and an Arm B episode | Coordination layer on against coordination layer off on seed positions 1–5 of the five-robot scene, registered **as confirmatory**: its analysis plan was fixed before it ran. Reported as a pilot because only 5 of the 20 planned seed pairs ran (the owner decided on 13 Nov 2026 not to run the rest). Never pooled with any later or earlier run. 0 of 10 episodes completed their tasks. | v7j `docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` sections 2–9 |
| **Exploratory five-robot pilots** (October 2026, series reports dated 10–17 Oct; 21 episodes) | ER-2 pilots; pilots E6–E26; series `churn_wave` (E6), `live_batch` (E7, E8, E10), `resume` (E9, E11), `batch2` (E12–E17), `batch3` (E18–E20), `batch4` (E21–E23), `batch5` (E24–E26); kits p3–p9; "A22 live batch", "A27/A30 mini-batch" | Coordination layer on only, with the live VLM, on the five-robot scene, while the v3 design was being tuned. Exploratory; six (E10, E17, E23–E26) were cut short by the pilots' early-stop rule. E5 (scripted echo model) is excluded everywhere. | v7j `docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md` section 5.2 |
| **Intersection run 1: coordination layer on vs off** (13 Nov 2026; 5 + 5 counted episodes) | IB10 live resolution; IB10 run 1; first IB10 run; `IBL`; `ib10_live`; slots e01–e10 (E01–E10), labels `ib10L_eNN_armX_aN`; Arm A vs Arm B | Full pipeline against the coordination layer switched off, on the four-robot intersection, registered before it ran, exploratory. Resolved 4 of 5 with the coordination layer on, 0 of 5 off. One excluded attempt (e01 a1). | v7a `docs/reports/2026-11-13-ib10-live-resolution-results.md` |
| **Intersection run 2: live VLM vs scripted default plan** (14 Nov 2026; 5 + 5 slots, plus one post hoc re-run) | IB10 safety default arm; IB10 grounder-default arm/run; IB10 run 2; second IB10 run; `IBS`; `ib10_safety`; labels `ib10S_eNN_armX_aN`; Arm A vs Arm C; re-run "e02 a2" | Live-VLM arm against a scripted arm that skips the VLM call and runs the grounder's default plan, with the safety-exemption fix on and the hard-contact floor armed. Exploratory. Live VLM 5 of 5 (including the first check episode); scripted 4 of 4 valid, 5 of 5 after the post hoc re-run of slot e02. Never pooled with run 1. | v7d `docs/reports/2026-11-14-ib10-safety-default-arm-results.md` |
| **Earlier intersection pilots** (reports of 2 and 8 Oct 2026) | IB10 composite smoke, lead-flip diagnosis, remedy validation, closure | Development and validation runs of the intersection remedy before the two runs above; the thesis cites them only as "the earlier live pilot". Not part of any reported comparison. | v7a `docs/reports/2026-10-0{2,8}-ib10-*.md` |
| **Demonstration campaign** (14–15 Nov 2026 UTC, all on 15 Nov in local time UTC+7; 12 valid takes in four scenes) | demo campaign; `DC`; `demo_campaign/`; takes `ibD_t0N_aN`, `cvD_*`, `cvH_*`, `hoD_*`, `m5D_*` | Live takes of the full pipeline, to show what it does, not how well. Caps 12 machine-hours and $10. Write "demonstration take N of M" per scene (intersection 5, convoy 5, head-on 1, five robots 1). Illustrative only; no rates. | v7j `docs/reports/2026-11-15-demo-campaign-results.md`, Final Summary |
| **Five-robot validation take** (15 Nov 2026) | `m5V_t01_a1`; "validation take"; `demo/validation-guard-contacts` | One live take of the five-robot scene run to check the escort obstacle guard and the geometric contact logging live. The guard was armed but never triggered (no escort was grounded); the contact lists stayed empty. | Thesis Chapter 4, later extensions; v7j `docs/implementation_notes.md` (2026-11-15 entries) |
| **Scripted safety tests** | `sft` kit (`data/logs/vm_runs/demo_campaign/sft/`, scripts `gen_revguard_grounding_sft.sh`, `gen_stall_safety_sft.sh`); branch `test/safety-mechanisms-scripted` (v7s) | Scripted live tests of the reverse obstacle guard and the stall abort, one mechanism per take, scripted decision, no model call. Both passed once (15 Nov 2026); the escort obstacle guard had no take. Results: `docs/reports/2026-11-15-safety-mechanism-scripted-tests-results.md` on the v7s branch (updated 2026-11-15; an earlier version of this row said no results report existed). | v7s branch `test/safety-mechanisms-scripted` (`74dd45c`) |
| **Earlier recorded head-on run** (30 Sep 2026) | ER2LIVE; `ER2LIVE_20260930_152222`; "05_head_on_earlier_run_ER2LIVE" | One live run of the two-robot head-on corridor on older code (`3959d7f`), in which the model's yielder was kept by the feasibility gate and executed. Selected because it qualifies; not part of the campaign. | Demo campaign report section 11 |
| **Head-on re-score of recorded decisions** | `RS`; head-on VLM-vs-rule re-score | Re-reads every recorded live head-on decision and scores the first named yielder against the scene's correct yielder and three trivial references. Post hoc, counts only. | main checkout branch `docs/head-on-vlm-vs-rule`, `docs/reports/2026-11-14-head-on-vlm-vs-rule-rescore.md` |
| **Swapped-ID replay** (robot labels swapped) | `SW`; swapped-id replay | Offline replay that swaps the two robots' labels (plus grey-image and no-obstacle-text arms, both listing orders) to tell a scene-driven choice from a label- or slot-driven one. Registered before its first call. | branch `exp/head-on-swapped-id-replay`, `docs/reports/2026-11-14-head-on-swapped-id-replay-results.md` |
| **JSON-only replay** (answer format changed to JSON only) | `JO` | Offline replay that replaces the prompt's answer-format block with one JSON-only line, for every model. | branch `exp/head-on-json-only-replay`, `docs/reports/2026-11-14-head-on-json-only-replay-results.md` |
| **Improved-annotation replay** (clearer image labels) | `IA` | Offline replay with legible robot labels and no obstacle text, with and without one sentence saying a backing robot needs free floor behind it. | branch `exp/head-on-swapped-id-replay`, `docs/reports/2026-11-14-improved-annotation-replay-results.md` |
| **Plan-influence trace** | `PT` | Re-grounds every recorded live four-robot analysis with and without the model's plan (and with the scripted decision) to show which executed commands depended on the plan. | branch `docs/vlm-plan-influence-trace` (v7i), `docs/reports/2026-11-15-vlm-plan-influence-trace.md` |
| **Plan-order prompt check** (offline) | `PC`; order-channel plan check; "plan check cycles"; kit/prompt condition B3 | Offline check of the prompt condition that lists the plan actions the verifier accepts, used with the plan-order switch at the intersection. | v7j `docs/reports/2026-11-15-vlm-order-channel-plan-check.md` |
| **Offline Sonnet check (intersection)** | "Sonnet 5.5 arm", "Sonnet check" | Offline pre-registered check of Claude Sonnet 5.5 on the intersection prompt, built as a possible live arm for intersection takes 4–5. | Demo campaign report sections 3.1–3.5 |
| **Convoy held-robot prompt check** (offline) | `CH`; held-robot prompt condition | Offline check whether stating the queued robots' held state in the prompt makes the model include them; result no-go (0 of 22 per condition). | v7j `docs/reports/2026-11-15-convoy-held-robot-prompt-check.md` |
| **Offline contact recompute** | `GC` (recompute part); footprint-gap recompute | Places each robot's collision footprint at its logged pose (10 Hz) and measures the gap to every declared box and robot; 5 mm counts as contact, 1 s of contact as sustained. Pending live validation. | branch `feat/gt-contact-logging` (v7m), `docs/reports/2026-11-15-gt-contact-logging.md` |
| **Offline decision benchmark** (v4 bench) | v4 bench; v4 offline bench | Replays 187 recorded five-robot analyses (31 episodes) through prompt variants and the production grounder; text only (no frames were kept). Ranks candidates, does not estimate effects. | Thesis Chapter 5, bench section |
| **Live per-group shadow run** | Stage 1 shadow; v4 shadow; `per_cluster_shadow` | Seven five-robot episodes (seed positions 21–27) in which a second, per-group model question was asked, grounded and logged after each analysis but never dispatched. | `docs/reports/2026-11-13-v4-stage1-shadow-results.md` |
| **Failure-cause classification** | failure-cause rubric; FU coding; rounds 1–2 | Post hoc assignment of a primary cause class to every failure unit of the 33 five-robot episodes (10 registered, 21 exploratory pilots, 2 November takes), by two blind raters, with reconciliation. | v7j rubric report Part B; v7q `docs/reports/2026-11-15-failure-cause-reconciliation.md` |
| **Interception analysis** | interception table | Offline: for each dispatched leg linked to a failure unit, would the escort obstacle guard, the reverse obstacle guard or the stall abort have refused or aborted it. | Reconciliation report section 7 |
| **Physical TurtleBot3 demonstration** (12 Nov 2026) | hardware run | The pipeline run on physical TurtleBot3 robots with an overhead RealSense camera and `gemini-3.1-flash-lite` as the model; not part of any experiment. | Thesis Chapter 4, physical demonstration |

### 2.3 Registered Designs and Their Numbered Changes

| Reader-facing name | Internal ids | Plain definition | Canonical evidence |
|---|---|---|---|
| **First registered design (v1)** (tag 30 Sep 2026) | prereg-v1; tag `prereg-v1` = `569d95c`; amendments A1–A10 | Two-robot battery with a classical-reasoner control. No confirmatory data reported. | `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md` at `569d95c` |
| **Second registered design (v2)** (from 30 Sep 2026) | prereg-v2 | Recovery from a formed jam: composite `junction_clear` command, plan channel and plan-audit labels, statistics block. No confirmatory data reported. | Thesis Chapter 5, preregistration history |
| **Third registered design (v3)** (6 Oct 2026) | prereg-v3; addenda A1–A36 | Fixed navigation stack, emergent congestion (five-robot scene); its registered confirmatory collection produced only the registered five-robot pilot. | `docs/superpowers/specs/2026-10-06-prereg-v3-design.md` at `ad67a18` |

Numbered items (the letter A is shared by v1 amendments and v3 addenda; never cite a bare "A33" to a reader):

| Id | Reader-facing description |
|---|---|
| v1 amendment A2 | random, seeded, recorded robot listing order in the prompt |
| v1 amendment A3 | adoption of the yield feasibility gate (`swap`), scored before the gate |
| v1 amendment A4 | position-verified arrival as primary outcome |
| v1 amendment A5 | distance channels instead of simulator contact flags (0.45 m) |
| v3 addenda A8, A9 | intersection release-lane remedy (0.33 m pull-off) and the ruling that the 0.20 m floor is a push limiter |
| v3 addendum A15 | "latch-on-pass" registered as the five-robot conflict class |
| v3 addendum A32 | freeze of the five-robot scene configuration |
| v3 addendum A33 | the registered measure definitions (scoring rules for every five-robot measure) |
| v3 addendum A34 | owner rulings R6–R11 on A33's proposals; redefined the control as coordination layer off |
| v3 addendum A35 | the coordination-layer-off switch (`reasoning_enabled: false`) |
| v3 addendum A36 | outcome record of the registered pilot and one deviation; tranche 2 left to the owner |

### 2.4 Arms (Conditions)

| Reader-facing name | Internal ids | Plain definition | Where used |
|---|---|---|---|
| **Coordination layer on (live VLM)** | Arm A; Layer 2 on; "live-VLM arm"; `armA` | Full pipeline: stall trigger, VLM call (Gemini Robotics-ER 2), grounding, phased dispatch. | Registered pilot; both intersection runs; every demonstration take |
| **Coordination layer off** | Arm B; Layer 2 off; Layer-2-off; `reasoning_enabled: false`; `armB` | The orchestrator returns before the congestion detector; no analysis, no model call, no dispatch; local navigation and the task stream still run. | Registered pilot; intersection run 1 |
| **Scripted default-plan arm (no VLM call)** | Arm C; grounder-default arm; scripted mock; `armC` | A scripted backend answers "no congestion", then `junction_clear` for all four robots with no plan, then "no congestion"; the grounder builds and labels its own default plan. Handed strategy and robot set, so it isolates plan content only. | Intersection run 2 only |

**Warnings.** "Arm A" means coordination layer on in every experiment, but its comparison arm differs (coordination layer off in the registered pilot and intersection run 1; scripted default plan in intersection run 2). "Arm B" had two earlier meanings (v1: classical reasoner; v2: "no congestion" mock); only "coordination layer off" applies to reported data.

### 2.5 System Parts and Models

| Reader-facing name | Internal ids | Plain definition |
|---|---|---|
| **Local navigation (Layer 1)** | Layer 1; Nav2 stack | Each robot's own navigation stack, 20–50 Hz target. |
| **Coordination layer (Layer 2)** | Layer 2; L2; "central layer" (the glossary's first choice, replaced) | The slow centralised loop (0.5–2 Hz target): stall trigger, VLM call, grounding, dispatch. Reader-facing name set by the owner on 2026-11-15 (an earlier draft chose "central layer" to avoid a clash). "Coordination layer" names this slow reasoning layer only; "coordination command" and "coordination exemption" remain M4's execution-level terms and are not renamed. |
| **Perception and robot tracking (M1)** | M1; `swarm_perception` | Overhead camera, ArUco tracking, scene state and annotated frame. |
| **VLM reasoning (M2)** | M2; backend | Builds the request, calls the model, validates the decision. |
| **The grounder (M3)** (grounding and plan verification) | M3; RAG grounding; "plan verifier", "verify-and-repair" | Deterministic, geometry-driven: turns a decision into commands, audits and repairs or replaces the model's plan, refuses infeasible manoeuvres. |
| **Execution and safety monitor (M4)** | M4; `swarm_execution` | Dispatches commands, runs the motion primitives, enforces the proximity latch and the hard-contact floor. |
| **Orchestrator (M5)** | M5; `swarm_orchestrator` | State machine and task registry; owns the stall detector and the pipeline trigger. |
| **Simulation (M6)** | M6; `isaac/vgu_sim` | Isaac Sim scenes, ground-truth logging. |
| **The VLM** = Gemini Robotics-ER 2 | ER-2; ER2; `gemini-robotics-er-2-preview` | The hosted model in every live comparison and demonstration take. |
| **Claude Sonnet 5.5** | Sonnet; Sonnet 5.5 | Second model in the offline benchmark, replays and the offline Sonnet check. |
| **GPT-4o** | gpt-4o | Model of earlier head-on runs and replays. |
| **Gemini 3.1 Flash-Lite** | `gemini-3.1-flash-lite` | Model of the physical TurtleBot3 demonstration only. |
| **Scripted mock backend** | mock, echo model (E5), `config/mock_decisions/*.json` | A backend that returns fixed decisions; never a model. |
| **Ground truth** (GT) | GT; `gt/` logs | Simulator poses, independent of perception. |

### 2.6 Outcome Labels, Plan-Audit Labels and Distances

| Reader-facing name | Internal ids | Plain definition | Canonical evidence |
|---|---|---|---|
| **Resolved** / **success** (intersection) | `resolved`, `success` | Resolved: valid jam and all four robots arrive (within 0.35 m, never beyond 0.5 m after). Success: resolved, no floor stop, no robot pair below 0.18 m. | Thesis Chapter 5, intersection measures |
| **Invalid (no jam formed)** | invalid jam; validity gate failed | The run did not form a jam inside the registered window; excluded, not failed. | same |
| **Complete / failed / censored** (five-robot) | completeness | Complete: all 25 tasks done; failed: not, and ran to the horizon; censored: cut short. | Tranche-1 report section 5 |
| **Unresolved failure** (demonstration label) | Unresolved failure | Not every robot reached its goal. | Demo campaign report, Final Summary |
| **VLM-driven execution** (demonstration label, intersection only) | VLM-driven execution | A resolved intersection take whose verified plan, including its back-out order, was dispatched as written and whose order differs from the grounder's default for the same snapshot. Says the model's order was executed, not that it improved anything. | same |
| **Grounder-default resolution** (demonstration label) | M3-default resolution | Every other resolved take, including one whose yielder the feasibility gate swapped or in which a fallback command ran. Qualifier **"grounder-corrected"** when the gate replaced the model's yielder (head-on take). | same |
| **VLM decision accepted and executed** (earlier head-on run only) | ER2LIVE label; also "VLM-driven execution" in the campaign's final-summary table | The 30 Sep 2026 run in which the model's yielder was kept and executed. Use this wording: the thesis rule reserves "VLM-driven execution" for the intersection. | Demo campaign report section 11; package README |
| **Plan-audit label** (provenance) | `plan.provenance`; provenance | Records how the dispatched plan relates to the model's proposed plan. The dispatched command always comes from the grounder. | Thesis Chapter 5, attribution |
| ↳ **accepted unchanged** | `vlm_verbatim` | The model's plan passed the audit with no edit. | same |
| ↳ **repaired** | `repaired` | Passed after the grounder's edits. | same |
| ↳ **grounder default** | `m3_default` | Plan absent, rejected or not repairable; the grounder's own default plan is the reference. | same |
| **Plan-dispatch match** | `dispatch_matches_plan` | Whether the dispatched command matches the audited plan. | same |
| **Back-out order** | recede order; `junction_clear` recede phases | The order in which the intersection's cross-axis robots back out along their own arms. | Thesis Chapter 3 |
| **Grounder's default order** | chi; chi cost; `dispatch_order_source=chi` | The grounder's own cost-based order for the back-outs, used unless the plan-order switch lets a verified model plan set it (`dispatch_order_source=model`). | Thesis Chapter 3, grounding settings table |
| **Yield feasibility gate** | `grounding_yield_feasibility` in `swap` mode; "the gate" | Replaces a named yielder that has no room to back up with one that has. On in the head-on scenes, off at the intersection. | Thesis Chapter 3 |
| **Second-stage question** | stage 2; stage-2 retreat call | A follow-up model call that picks the retreat side for the grounded yielder. | Thesis Chapter 3 |
| **Proximity latch, 0.45 m** | latch; "safety distance" | M4 stops a robot pair whose centres come within 0.45 m; also the conflict definition of the five-robot measures. | Thesis Chapter 5, safety gates |
| **Hard-contact floor, 0.20 m (centre distance)** | hard floor; `hard_contact_floor_m` | M4 stops a pair below 0.20 m centre distance; a push limiter that fires at or after contact, not a contact preventer. | same |
| **Ground-truth contact threshold, 0.18 m** | `gt_contact` | Centre distance below which ground truth counts a robot pair as in contact. | same |
| **Contact (offline recompute), 5 mm** | contact entry | Footprint gap of at most 5 mm; sustained when it lasts 1 s. | Offline contact recompute |

### 2.7 Analysis Terms

| Reader-facing name | Internal ids | Plain definition | Canonical evidence |
|---|---|---|---|
| **Failure unit** | FU, `FUn` (e.g. "E26 FU1") | A conflict still open at the last ground-truth sample, or a lone stall (a robot that moved under 0.05 m in the last 60 s, not at a task node). | Thesis Chapter 5, failure units |
| **Decision cause** | V, V1–V6 | The model's answer was missing, missed the conflict, left out a robot, named an infeasible role or contradicted itself. | Rubric report section 7.2 |
| **Grounding and verification cause** | G, G1–G7 | The grounder refused, replaced or altered a sound decision, or let an unsafe manoeuvre through. | same |
| **Execution cause** | X, X1–X6 | A command was dispatched as intended and the robots did not carry it out. | same |
| **Environment geometry cause** | EG, EG1–EG2 | The scene left no way out, or an undeclared obstacle met a robot. (Not the register's short name `EG` for the escort guard report.) | same |
| **Undetermined** | U, `U:<what is missing>` | Evidence to apply the rule is missing. | same |
| **Decision-substitution test** | T1; its fidelity check (`U:T1_fidelity` when it fails) | Grounds every hypothetical decision of a fixed set on the snapshot of an analysis and asks whether any would move a robot of the unit. Never "T1" for the registered pilot. | Rubric report section 7.4 |
| **Straight-move test** | T2 | Whether any robot of the unit has a straight move in one of eight headings that clears its neighbours without passing within 0.14 m of a box or robot. | same |
| **Execution check** | T3 | Per dispatched leg: M4's terminal status, ground-truth displacement against the commanded distance (under 50 % counts as not executed), recomputed minimum gap, latch lines. | same |
| **Live oracle test** (not run) | T4 | A live re-run with a scripted decision; never required for coding, named only when it would decide. | same |
| **Persistent-state link (sensitivity analysis)** | S1 | Also links a command to a unit when the robot stayed pinned against the same box or robot from the end of the command to the onset. | Reconciliation report section 5.2 |
| **Start-inside rule (sensitivity analysis)** | S2 | Recomputes the straight-move test with the guards' rule for a robot that starts inside the required clearance. | Reconciliation report section 5.3 |
| **Extra recorded inputs for the substitution test (sensitivity analysis)** | S3 | Reruns the substitution test with the stored second-stage label and rebuilt task intents. | Reconciliation report section 5.1 |
| **Registered measure definitions** | A33 | The scoring rules of the five-robot measures (clock, completeness, makespan, throughput, delay, conflict episodes, per-conflict scoring), fixed before the registered pilot. | Thesis Chapter 5, measures |
| **Strata** | registered / pilots horizon / pilots stop rule / November takes | The groups the failure-cause tables keep apart; never pooled. | Reconciliation report section 1 |
| **First check episode** | smoke, smoke episode | The first episode of a run, inspected before the rest ran; counted only if it passed its gates. | Thesis Chapter 5, procedure |
| **Run kit** | kit, `kit/` | The deploy, launch, gate and restore scripts of one run, pinned by md5. | same |
| **Shadow** | classical shadow, live shadow | Computed and logged beside the live decision, never dispatched. | Thesis Chapter 5, arms |

### 2.8 Safety Mechanisms (By Function)

All were written after the evaluated runtime and are off by default unless stated.

| Reader-facing name | Config key | Plain definition | Validation state (2026-11-15) |
|---|---|---|---|
| **Safety-exemption scope fix** | `scoped_clearing_exemption` | Narrows which robots inside one coordination command are exempt from M4's proximity check. | On in intersection run 2 (never fired) and in the demonstration takes; unit tests and replay |
| **Escort obstacle guard** | `escort_obstacle_guard` | The grounder refuses an escort whose straight segment crosses a declared obstacle. | Offline replay; armed in the validation take, never triggered |
| **Reverse obstacle guard** | `reverse_obstacle_guard` | The same check for `reverse` legs; refuses the whole reverse. | Unit tests and offline replay of 17 commands; not run live |
| **Stall abort** (execution side) | `safety.stall_abort.enabled` | M4 cancels a primitive whose commanded motion produces no measured movement. | Unit and node tests, offline replay of 221 primitives; not run live |
| **Geometric contact logging** | none (always on) | Ground truth records footprint gaps to boxes and robots on every row. | Fields present in the validation take; lists stayed empty; partially validated |
| **Queued-robot hold** (convoy) | `grounding_hold_queued_crossers` | The grounder holds unnamed robots outside the corridor whose goals lie past its far end. | Used in convoy takes 4–5, both unresolved |
| **Plan-dispatch mismatch record** | `plan_dispatch_mismatch_visibility` | Writes a companion record when the dispatched command contradicts the audited plan; never changes the plan-audit label. | Built (v7r), logging only |
| **Plan-order switch** | `plan_dispatch_order_source: model_when_verified` | Lets a verified model plan set the intersection's back-out order. | Demonstration campaign only |
| **Coordination-layer-off switch** | `reasoning_enabled: false` | Turns the coordination layer off (control arm). | Registered pilot, intersection run 1 |

---

## 3. Compact Labels for Tables

The thesis already numbers the intersection runs ("IB10 run 1", "IB10 run 2") and the demonstration takes ("take 5 of 5"). Keep that numbering and drop only the internal prefix; do not add scene letters or "Exp. N".

| Use in tables | Stands for |
|---|---|
| Intersection run 1 (13 Nov) | Intersection run 1: coordination layer on vs off |
| Intersection run 2 (14 Nov) | Intersection run 2: live VLM vs scripted default plan |
| Registered pilot (21 Oct) | Registered five-robot pilot |
| Exploratory pilots (10–17 Oct) | Exploratory five-robot pilots, E6–E26 |
| Demo take N of M | Demonstration take N of M of one scene |
| On / Off / Scripted | Coordination layer on / coordination layer off / scripted default-plan arm, as column headers when the table caption names the run |

Episode ids stay as ids, defined once: "pilot episodes E6–E26", "seed pairs E27–E31 of the registered pilot (each one coordination-layer-on and one coordination-layer-off episode)", "intersection slots e01–e10".

---

## 4. Replace List

For search-and-replace by a human. Always read the sentence; several terms are ambiguous.

| Internal term | Replace with | Warning |
|---|---|---|
| prereg-v3 tranche 1, tranche 1, tranche-1, Tranche 1 | the registered five-robot pilot | "tranche-1 X" becomes "the registered pilot's X" |
| tranche 2 | the remaining 15 registered seed pairs (not run) | |
| tranche (bare) | the registered pilot | |
| prereg-v1 / prereg-v2 / prereg-v3 | the first / second / third registered design (v1 / v2 / v3) | when it means data, it is the registered pilot |
| prereg (as a word) | registration; the registered design | "preregistration" and "pre-registered" are ordinary words and stay |
| IB10 live resolution, IB10 run 1, first IB10 run | intersection run 1 | |
| IB10 grounder-default arm/run, IB10 safety default arm, IB10 run 2, second IB10 run | intersection run 2 | |
| both/two IB10 runs | both intersection runs | |
| IB10 (scene) | the four-robot intersection | AMBIGUOUS: scene vs runs; "IB10 measures" are the intersection measures of both runs |
| S1b | the five-robot pickup-and-delivery scene | keep `mapd_5_s1b` once as the file name |
| S1 family, S1 scene | the five-robot scene family | |
| S1, S2, S3 (failure-cause text) | the persistent-state link / start-inside rule / extra-inputs sensitivity analysis | AMBIGUOUS with the S1 scene family |
| Arm A | coordination layer on (live VLM) | the comparison arm differs between runs |
| Arm B | coordination layer off | v1 and v2 meanings are history only |
| Arm C | scripted default-plan arm (no VLM call) | intersection run 2 only |
| Layer 2 on / off, Layer-2-on / -off | coordination layer on / off | mandatory in headings, captions and table headers |
| Layer 2 | the coordination layer (Layer 2) | defined term; prose may keep it after Chapter 1 |
| M3-default resolution | grounder-default resolution | on-screen video text keeps the old label |
| `vlm_verbatim` / `repaired` / `m3_default` | accepted unchanged / repaired / grounder default | keep the code in monospace once |
| provenance | plan-audit label (provenance) | define at first use; may stay where it names the recorded field |
| chi, chi cost | the grounder's default (cost) order | |
| recede, recede order | back out, back-out order | |
| ER2LIVE | the earlier recorded head-on run (30 Sep 2026) | file and video names keep `ER2LIVE_*` |
| batch, batch2–batch6 | pilot series; the registered pilot (batch6) | "batch stop rule" → "the pilots' early-stop rule" |
| E6–E26, E27–E31, e01–e10 | keep as ids, defined once | E27–E31 are seed pairs (two episodes each); e01–e10 are intersection slots |
| A33 (and other An) | the registered measure definitions (v3 addendum A33); see section 2.3 | never confuse with "Arm A"; v1 amendments and v3 addenda share the letter |
| T1 / T2 | decision-substitution test / straight-move test | never "T1" for the registered pilot |
| Stage 1 (shadow) | the live per-group shadow run | |
| v4 bench | the offline decision benchmark | |
| B3 (kit, prompt) | the plan-order prompt condition | |
| smoke | the first check episode | |
| stage 2, stage-2 | the second-stage (retreat-side) question | |
| M1–M6 alone | role name with the code: perception (M1), VLM reasoning (M2), grounder (M3), execution and safety monitor (M4), orchestrator (M5), simulation (M6) | |
| ER-2, ER2 | Gemini Robotics-ER 2 (ER-2) | keep ER-2 as a listed abbreviation |
| DC, PT, PC, CH, IBL, IBS, RS, SW, IA, JO, GC, EG, FC, PD | the report by its reader-facing name (section 2.2) | register short names only; `EG` clashes with the cause class |
| head-on asymmetric family | the head-on scene family | |
| safety distance (0.45 m) | proximity latch (0.45 m) | |
| hard floor | hard-contact floor (0.20 m centre distance) | |

---

## 5. Known Exceptions (Stay Internal Because They Are Verbatim Records)

| Item | Example | Meaning |
|---|---|---|
| Take and bundle labels | `ibD_t05_a1`, `cvH_t04_a2`, `m5V_t01_a1`, `ib10L_e09_armA_a1`, `ib10S_e02_armC_a1` | scene code (`ib` intersection, `cv` convoy, `ho` head-on, `m5` five robots), then `D` demonstration, `H` convoy with queued-robot hold, `V` validation, `L` intersection run 1, `S` intersection run 2; `tNN` take, `eNN` slot, `armX` arm, `aN` attempt |
| Video and image file names | `ER2LIVE_20260930_presentation.mp4`, `fig_intersection_jam_t30p10_clean.png` | `tXXpYY` in a figure name is the simulated time XX.YY s |
| On-screen video text | outro "Outcome: M3-default resolution (grounder-corrected)"; legend "`dispatch_order_source=chi` = the system's own ordering"; "provenance: `vlm_verbatim` = plan accepted unchanged, `repaired` = edited by the verifier, `m3_default` = replaced by the grounding module's default plan" | burned into the rendered videos (v7g `config/demo_presentation/*.json`); the legend already translates them. Read "M3-default resolution" as grounder-default resolution |
| On-screen log lines | `provenance=vlm_verbatim reason=... dispatch_order_source=model`, `yield re-grounded`, `refusal withheld` | real M5 and M4 log lines replayed in sync |
| Folder names of the demo package | `05_head_on_earlier_run_ER2LIVE/` | kept so that paths in other documents stay valid |
| Config keys, scene file names, branch names, commits | `reasoning_enabled: false`, `mapd_5_s1b`, `demo/campaign-kits` | as written |
| Evidence-index source column of the thesis | `75a499c:docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` | paths and commits; the claim column is reader text and follows this glossary |

---

## 6. How to Read the Three Most-Cited Reports

Counted from the thesis evidence index: the registered-pilot report (17 citations), the demonstration campaign report (10) and the thesis evidence register (7). None of them is rewritten; read them with these notes.

### 6.1 `docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` (v7j; the registered five-robot pilot)

- "S1b Confirmatory Tranche 1", "tranche", "the tranche" = the registered five-robot pilot of 21 Oct 2026. "Confirmatory" was its registered status; the thesis reports it as a pilot.
- "E27"–"E31" = seed pairs for seed positions 1–5 ("s1"–"s5"); each has an "A" (coordination layer on) and a "B" (coordination layer off) episode; "a1"/"a2" are attempts.
- "A32"–"A36" = v3 addenda (section 2.3); "R6"–"R11" = owner rulings recorded in A34; "A33(7)" = paragraph 7 of the measure definitions.
- "RECORD = 0" = a dataset tag passed to the launcher, nothing more (A34 R6); "`batch6`", "p10" = the run-kit folders.
- "MC context" (section 1.9) = an offline pre-run check that grounded each seed's first conflict with a scripted echo decision; the report calls it an upper bound, not a prediction.
- "COND line", "silence gate" = the per-arm condition gates; "`degenerate_arm_b`" = per-conflict measures are undefined for coordination layer off by construction.
- "r1"–"r5" = `robot_1`–`robot_5`; "T_end" = end of observation; "GT closest pair" = minimum ground-truth centre distance.

### 6.2 `docs/reports/2026-11-15-demo-campaign-results.md` (v7j; the demonstration campaign)

- "`ib`", "`cv`", "`ho`", "`m5`", "`m5v`", "`cvh`" = the four-robot intersection, the convoy counterflow scene, the head-on corridor, the five-robot scene, the five-robot validation take, the convoy takes with the hold. Take labels: section 5.
- "B3" = the intersection run kit with the plan-order prompt condition; "Part A"/"Part B" = the section's two questions (why the model gave no plan; the Sonnet arm).
- "chi", "recede" = the grounder's default (cost) order; back-out.
- "M3-default resolution" = grounder-default resolution; "VLM-driven" = VLM-driven execution (intersection only, except the ER2LIVE row of the final-summary table, which the thesis words as "VLM decision accepted and executed").
- "legacy grounding" = the grounding vocabulary of the registered convoy configuration, which has no post-gate recovery.
- "fix cycles" = the fix attempts the campaign registration allowed per scene (section 2.5); "Rev N" = the report's revision that added the section.
- Counts: the final-summary three-way table is per analysis; 67 of 67 valid, 6 accepted unchanged of 65 plan-channel analyses after Rev 11. Older figures (55 of 55, 6 of 53) are the Rev 5 state.

### 6.3 `docs/reports/2026-11-13-thesis-evidence-register.md` (v6d; the thesis evidence register)

- Short names: `DC` demonstration campaign report; `PT` plan-influence trace; `PC` plan-order prompt check; `CH` convoy held-robot prompt check; `IBL` intersection run 1; `IBS` intersection run 2; `RS` head-on re-score; `SW` swapped-ID replay; `IA` improved-annotation replay; `JO` JSON-only replay; `GC` contact logging and offline recompute; `EG` escort obstacle guard (not the cause class EG); `FC` failure-cause reconciliation and interception table; `PD` plan-dispatch mismatch record.
- "Rung a"–"f" = the claims ladder; rung a's "IB10" = the four-robot intersection.
- "v7a", "v7j" and similar = local worktree folders, not versions.
- The "VLM Contribution" section quotes the campaign at Rev 5 (55 of 55 valid; 6 of 53 accepted); the thesis abstract uses the later 67 and 65.
- "The October pilot runs" (recommended wording 6) = the exploratory five-robot pilots of 10–17 Oct 2026, not the registered pilot of 21 Oct 2026.

### 6.4 The Two Intersection Reports (v7a, v7d)

- "IB10" = the four-robot intersection; "e01"–"e10" = slots; "Arm A/B/C" = section 2.4; "smoke" = the first check episode; "key on" = the safety-exemption scope fix switched on; "floor" = hard-contact floor; "e02 a2" = the post hoc re-run of slot e02 in intersection run 2.
