> Copied 2026-11-15 from the planning session's scratch directory so it is not lost. It reviewed the `docs/thesis` working tree at `88d8cfe` (with `thesis/chapters/00-front.typ` uncommitted) through commit `231baac`; the text below is unchanged. Later thesis commits (to `e1bbce6`) address its three MUST FIX items, and its section 4.3 is stale (the scripted safety tests and the convoy rerun have since reported); see `docs/reports/2026-11-15-session-wrap-up.md` section 10.

# Independent Review of the Thesis Against the Project State

**Prepared:** 2026-11-15 (read-only review; nothing in any repo was edited)

## 0. What Was Reviewed, and How

- **Thesis.** `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-thesis/thesis/`, branch `docs/thesis`.
  - HEAD at start: `88d8cfe` (2026-11-15 21:49, "docs: add hardware sentence and keywords to abstract"), with `chapters/00-front.typ` uncommitted. The chapters were read from the **working tree** at that point.
  - HEAD at end: `231baac` (22:07, "docs: restore abstract hardware clause and fix review follow-ups"), via `6658c48` and `7316233`. `git diff --stat 88d8cfe..7316233`: 14 files, +123/−131. `231baac` changed 6 more files.
  - Every MUST FIX item below, and the key SHOULD FIX items, were re-grepped in the working tree at `231baac`. Items fixed in between are dropped (they are listed in 0.1).
  - At `231baac` the abstract hardware clause reads "the model chose a bounded back-out each time and the robots reported it complete". It is still contradicted by scenario E (MUST FIX 1).
- **Yardstick.** I read these in full or in the relevant sections:
  - wrap-up index (v7j);
  - evidence register sections "VLM Contribution", "Hardware", "Claims Supports / Does Not" (v6d);
  - change list sections 1–6, 8, 9, 11.5–11.6 (v6d);
  - naming glossary term tables (v7j);
  - failure-cause reconciliation sections 1, 2, 4.1 (v7q);
  - convoy non-arrival report, Summary (v7t);
  - rubric and robot5 report, Part A §1 (v7j);
  - demo-campaign report: three-way table and the Rev 13 diff (v7j `2cafbf7`).
- **Code checked (verified).** All at v7c `8933863`, the pin plus the safety fix:
  - `reasoning/vlm/prompt_builder.py`: v3.4 header comment and template; `CURRENT_PROMPT_VERSION = 2` in `models.py`;
  - `prompt_v1.py` and `prompt_v2.py`: both end with the `<think>…</think>` block;
  - `orchestrator_node.py:1161`: v3 only when the plan channel is on;
  - `command_grounder.py`: legacy and derived modes, the `chi` / `model_when_verified` order source, the `verify_and_repair_plan` location;
  - `config/rag.yaml`: `mode: derived`; the orchestrator config notes that the convoy needs `legacy`;
  - `isaac/vgu_sim/acceptance_logging.py:99-100`: contact lists hard-coded `[]`;
  - `safety.py`: `min_distance_m`, `hard_contact_floor_m` default 0.0;
  - `gemini_backend.py:58`: `image_position="after_text"`.
- **Prompt records verified byte for byte.**
  - `assets/prompts/demo-ib-take5-user.txt` and `-answer.txt` equal `prompt.user_prompt` and `raw_text` of `ibD_t05_a1/decisions/df397030….json`: 7,363 characters, SHA-256 `cbc947c4…` stored, recomputed and file all equal.
  - `ib10-run1-e03-user.txt` and `-answer.txt` equal v7a `ib10L_e03_armA_a1/decisions/6c5406d8….json`: 6,738 characters, SHA `cde5e273…`.
  - The stage-2 asset was **not** compared (not verified).
- **Mechanical checks (verified).**
  - 185 Evidence Index rows are defined and 185 are cited: none missing, none unused, no duplicates.
  - Every `@fig/@tab/@sec/@eq` reference resolves. Every `image(...)` path exists.
  - Body word count (chapters 00–08) is about 30,060, at the top of the 25–30 k target.
- **Number checks.** Headline numbers (4/5, 16/20, 115.96/117.80/117.86, 79/79 and 37, 0 of 39, 67 of 67, 6 of the 65, +0.032 [−0.008, +0.080], 0/10) were grepped in the **primary** reports (v7a, v7d, the head-on re-score, v7i, v7j DC, the tranche-1 report). The failure-cause tables were compared cell by cell with v7q 4.1 and 2. Everything else is **index-checked** (wrap-up or register), not checked against the primary.
- **Not done.** No PDF compile. Chapter 2 literature claims were not checked.

### 0.1 Fixed Between 88d8cfe and 7316233 (Not Reported Below)

- Ch. 1 Summary now cites both scripted-arm figures (4 of 4; 5 of 5 after the re-run).
- `@sec:impl-later` now lists the plan-dispatch mismatch record.

---

## 1. Research Questions

The thesis frames its question in three ways, which do not match one another:

- the **abstract**: can a VLM "supply that decision" (who yields);
- the **problem statement** (`01-introduction.typ`, Problem Statement): can the pipeline clear congestion, "and what does each part contribute?";
- **RQ1–RQ5** (Ch. 1 Research Questions; restated in `05-methodology.typ` "Research Questions and Hypotheses").

`tab:intro-rq-map` adds two "Informs" entries that are not RQs: "Model's share in executed commands" (plan-influence trace) and "Which stage limits the pipeline" (failure-cause classification).

A fourth framing appears at `231baac` in `02-background.typ` Research Gap: "…and, because every decision is grounded deterministically, what the grounder contributes".

RQ answers exist only in `07-discussion.typ` §"Answers to the Research Questions". In Ch. 8 the Conclusion section answers the problem statement but answers no RQ by number; RQ4 and RQ5 appear only in Future Work ("RQ4 and RQ5 need their own experiments").

**Per-study questions** (Ch. 5 "Research Questions and Hypotheses"):

| Study | Question as worded | Answer in Ch. 6 | Verdict |
|---|---|---|---|
| Registered pilot | Effect on completion, throughput, delay and per-conflict quality, as intervals with no direction | 0/10 complete; +0.032 [−0.008, +0.080]; delay −31.5 s [−71.6, −0.6]; recall 0.818 | Answered as registered. Reported as a pilot and not pooled with exploratory runs in any outcome. The one exception is "27 of 55", which pools its failure units with the exploratory and November ones (SHOULD 1) |
| Intersection run 1 | Does the pipeline physically clear a jam that stays frozen with the layer off? | 4/5 against 0/5 | Answered |
| Intersection run 2 (a) | Does the runtime run cleanly with the safety fix on and the floor armed? | Fix on, never fired; 0 floor stops; 0.3008 / 0.2965 m | Answered ("clean"; the fix itself is not exercised) |
| Intersection run 2 (b) | Does the jam clear the same way with no VLM call and the default plan? | Yes, 4/4 (5/5), with the same plan | Answered |
| Offline benchmark | Rank variants; no effect estimate | Per-cluster format gain; models match the first option | Answered |

**RQ2/RQ3 wording differs between chapters.**

- Ch. 5 states RQ2 "compared with a per-type policy table" and RQ3 "compared with a first-come-first-served rule with a commitment tiebreak".
- Ch. 1 states the questions without comparators, then says those comparators were not used.
- This is consistent, but the Ch. 7 answers use neither comparator, so RQ2 and RQ3 as registered are unanswered. As reworded in Ch. 1 they are answered.
- The head-on re-score does use a first-come-first-served (manifest) rule, at decision level only. Ch. 7 could say so.

| Question (where stated) | Where answered | One-sentence answer as written | Evidence rows | Verdict |
|---|---|---|---|---|
| **RQ1** classification: type, blocker kind, congestion vs normal flow (Ch. 1, Ch. 5) | Ch. 7 §disc-rq; Ch. 6 §res-t1 | "answered in part, at pilot scale": recall 9/11, 0 FP in 26, type accuracy 0.778, involved-set F1 0.915 | 6.35, 6.14 | **Partly answered.** (a) Blocker kind is never reported, though `blocker_kind` is in the schema (Ch. 3). (b) Detection recall is a property of the stall trigger plus the VLM, not of the VLM alone. (c) Type accuracy is against a ruled accepted set {deadlock} (Ch. 5 tab:ch5-a33), so it tests little. (d) The map table says the offline benchmark informs RQ1, but §disc-rq does not use it. (e) Intersection evidence is not used: the 4 "no congestion" answers in the demo, and take 1's analysis of a pre-jam snapshot. |
| **RQ2** strategy competence (Ch. 1) | Ch. 7 §disc-rq | "answered for the pipeline, not the model (rungs a, d, e)" | via rungs | **Answered, but only by pointer.** The negative content is not stated as an answer: the model's strategies, once grounded, cleared the intersection, but a scripted `junction_clear` did the same, and nothing cleared the convoy (5 takes) or the five-robot scene (0/10 complete). The registered comparator (a per-type policy table) never ran (stated in Ch. 1). |
| **RQ3** yielder and crossing order effective (Ch. 1) | Ch. 7 §disc-rq; Ch. 6 §res-headon, §res-demo-ib | "informed only at decision level; the gate made the yielder correct, the model's choice followed labels or listing order where testable, and its one executed back-out order was a near-tie" | 6.08–6.11, 6.39 | **Answered (negative), decision level only.** This is accurate. Missing: the model's `crossing_order` was never used in execution (take 5, ev 6.39), which is the direct answer to the crossing-order half. |
| **RQ4** semantic advantage | Ch. 1 Research Questions; Ch. 7 | "not tested" | — | **Not answered; stated explicitly.** Fine. The improved-annotation lead (55/67) and the zero `blocker_kind` evidence could be named as what exists. |
| **RQ5** closed-loop adaptation | Ch. 1; Ch. 7 | "not tested" | — | **Not answered, stated.** But live prompts carried a failure-context and plan-state block (Ch. 3 step 5; Ch. 4 Prompt), and ev 6.80 shows that block was wrong after overrides ("wait (done)"). That is evidence bearing on RQ5's premise and should be mentioned. |
| **Problem statement** "can the pipeline clear congestion… and what does each part contribute?" (Ch. 1 Problem Statement) | Ch. 8 Conclusion ¶3 | "narrow": the pipeline clears one staged scene; the deterministic layer carries it | 6.05, 6.06, 6.02 | **Answered.** One sentence is arguable (SHOULD 0). |
| **Contributions 1–6** (Ch. 1 Contributions) | Chs. 3–6 | — | 1.04–1.07 | **Supported** as worded, including the safety caveat. Contribution 2 claims the per-dispatch audit label as novel; the thesis itself shows the label over-counts (Ch. 7 "Plan versus dispatch"). It is qualified by "together with a re-grounding", which is acceptable. |
| "Model's share" (map row, not an RQ) | Ch. 6 §res-plan; Ch. 7 | 0 of 39; once, a near-tie | 6.02, 6.39 | Answered, but not as an RQ. |
| "Which stage limits the pipeline" (map row) | Ch. 6 §res-failure-causes; Ch. 7 | no dominant cause; large undetermined share | 6.63 | **Answered (null)**, and stated as a null. Good. |

**Wording no longer answerable (suggestions only):**

- RQ2 presumes the VLM's strategy is the active ingredient. Reword it as: "Does the pipeline, with the VLM's strategy choice, clear congestion that local control leaves, and how much of that is due to the VLM's choice as opposed to grounding?"
- RQ3 presumes the yielder/order can be judged "effective". Reword it as: "Does the VLM's choice of yielder and order reflect the scene rather than labels or listing order, and does it reach execution?"
- The "Which stage limits" row presumes a limiting stage. Keep it as asked, but say in Ch. 1 that the answer is a null.

---

## 2. Pipeline and Architecture Coverage

V = verified against code; R = checked against reports only.

| Element (code) | Described where | Accurate? |
|---|---|---|
| Perception M1 (ArUco, homography, status, STALE) | Ch. 3 Modules; Ch. 4 Perception | Yes (R) |
| Trigger (12 s wall-clock stall, proximity rule, cool-down 15 s) | Ch. 3 Decide/Detect; Ch. 4 tab:impl-m5 | Yes (R) |
| Prompt building v1/v2/v3.4; default v2, v3 only with the plan channel | Ch. 4 Prompt; Ch. 5 tab:ch5-prompts | Yes (V: `CURRENT_PROMPT_VERSION=2`, `orchestrator_node.py:1161`). Gap: the `<think>` ending of v1/v2 and why v3.4 dropped it are not in the prose (§3 below) |
| Backends; models live vs offline | Ch. 4 Backends, tab:impl-stack | Yes (R; V for the Gemini image after text). The abstract's "one live VLM" is wrong (SHOULD 6) |
| Parser (consistency, plan names each robot once) | Ch. 3 Strategy Vocabulary | Yes (R) |
| Plan channel and plan audit (`verify_and_repair_plan`, ≤4 edits, labels) | Ch. 3 "Plan audit", "Audit, not dispatch" | Yes. It states that phases are grounded from the decision fields and that the flag is not a strict match (R: PT D) |
| Order channel (`plan_dispatch_order_source`, default `chi`, `model_when_verified` only in the demo intersection) | Ch. 3 tab:grounding-config; Ch. 4 Later Extensions; Ch. 5 demo | Yes (V: `command_grounder.py:88-95`) |
| Grounder reads the plan? | Ch. 3; Ch. 6 §res-demo; Ch. 7 | Yes: "for `reverse` and `reroute` the grounder acts on the involved-robots list and never reads the plan". Ch. 1 Problem Statement is also correct |
| Grounding modes legacy / derived | Ch. 3 tab:grounding-config mentions **derived only** | **Incomplete.** Legacy mode is never defined. Per the `command_grounder.py` docstring, legacy distances are clamped rather than feasibility-banded. The park point, sidestep and escort clearance come from the declared geometry when it is supplied. There are no ranked, swept-path-validated retreat candidates and no degradation list. Legacy is the code path when params are None; `config/rag.yaml` sets derived; the convoy scene requires legacy. Ch. 5 and Ch. 6 rely on it all the same: yet Ch. 5 §demo ("registered legacy convoy grounding") and Ch. 6 convoy ("the legacy grounding has no template") rely on it. The queued-robot hold works only in legacy (wrap-up §3). Also missing: the five-robot validation reverse fell through to the legacy reverse template (rubric Part A §1) (V for the mode switch) |
| Yield feasibility gate (`off`/`swap`/`refuse`) | Ch. 3 "Yield feasibility gate" | Yes (V). Missing: in the convoy the gate never fires, because the scene declares no static obstacles (v7t Summary: 0 of 49 first-trigger yields change). This explains why takes 4–5 kept the infeasible-side yielder robot_1 |
| Stage-2 retreat selection | Ch. 3 Decide; Ch. 4; App. C stage-2 prompt | Yes (R) |
| Dispatch and `junction_clear` phases | Ch. 3 Act; Ch. 4 phase queue | Yes (R) |
| Execution primitives (raw cmd_vel backup, pull-off, escort `drive_heading`) | Ch. 4 Execution | Yes. "This straight segment does not check static obstacles." |
| Safety monitor: latch 0.45 m centre distance, speed, STALE band, floor 0.20 m centre distance (0 in the shipped file), exemptions | Ch. 3 tab:safety, Clearing exemption; Ch. 4 Safety monitor | Yes (V: floor default 0.0). Pair-only scope is stated in Ch. 1, Ch. 3 and Ch. 6 |
| Safety-exemption scope fix | Ch. 3 "Exemption scope"; Ch. 4 Later; App. B tab:res-sx | Yes: on in run 2, never fired; firings not counted in the demo. "The first three were fixed" is close to the source, where P2 is "moot" |
| Ground truth and scoring; contact stub | Ch. 3 M6; Ch. 4 lessons; Ch. 5 measures; Ch. 6 Safety | Yes (V: `acceptance_logging.py:99-100`) |
| Later mechanisms (escort and reverse guards, stall abort, contact logging, queued hold, mismatch record) | Ch. 4 §impl-later | Yes as of `7316233`. The counterflow yielder swap (v7t, now on DC Rev 13) is absent (§4.3) |
| Runtime per experiment | Ch. 3 opening; Ch. 4 opening; Ch. 5 tab:ch5-arms; Ch. 6 §res-demo "not the evaluated runtime" | Mostly yes. The demonstration runtime is not identified by commit (`demo/campaign-kits` delta; v7k runtime-delta spec), and neither is the validation take's (v7n `a412949`). Ch. 1 Scope "one pinned runtime" ignores that run 2 = pin + fix |
| Demo recording and rendering | App. B "Format of the demonstration videos", tab:app-videos | Partly. The presentation cut and its md5s are not listed; the renderer branch is not named. Acceptable |

---

## 3. Prompt Coverage

- **Versions per experiment.** Ch. 5 `tab:ch5-prompts` with ev 6.82/6.83 gives v3.4 for the registered pilot and both intersection runs, v3.4 plus additions for the demo intersection, v3.4 for the convoy and five-robot takes, v2 for the demo head-on, and v1 for the offline replays. Good; ev 6.82 was built from every artifact.
- **JSON-only ending and why.** Ch. 4 says v3.4 ends with "a closing instruction to write only JSON" but not why. The code comment (`prompt_builder.py:54-60`) gives the reason: the `<think>` block contradicted the registered spatial-CoT prohibition, and "Anthropic's documented `reasoning_extraction` trigger made Sonnet 5.5 refuse 91/96 attempts". Ch. 6 "Refusals" speaks of the "original ending" without saying that it is the `<think>` block of v1/v2. The word "think" appears nowhere in the chapters, only in ev 6.82/6.83. **SHOULD FIX.**
- **Plan grammar, release rule, options block.** App. C `demo-ib-take5` prints the block "Plan actions the system's verifier accepts…" and the ordering sentences verbatim (verified). The prose says "three plan-ordering sentences". The artifact's `prompt_conditions` records two separate conditions, `plan_grammar_rules` and `plan_grammar_release_rule`. Naming the release rule as one of the three would make prose and record match. NICE.
- **Held-robot state note.** It is default off and was used offline only (Ch. 4 Later; Ch. 6 convoy, 0 of 22). No live run had it on (consistent with wrap-up R8). Good.
- **Image input; presentation order; stage-2 prompt.** Image after text: stated and verified. Ascending order is stated as a limit in Chs. 1, 5, 6 and 7. The stage-2 prompt is in App. C. Good.
- **Verbatim records.** Two of three verified byte-exact against their artifacts; the stage-2 record was not checked. Attribution is correct (e03 of run 1, take 5).
- **Prompt findings present.** Presentation-order bias; no evidence of scene/image use; constrained selection by the options block; wrong plan state shown back (Ch. 7 "Plan versus dispatch"; Ch. 7 Limitations).
- **Prompt findings missing.**
  - (a) The prompt contract invites the reverse mismatch: `involved_robots` is undefined, the grammar puts no constraint on a `reverse` plan, and the prompt tells the model the plan is verified "before anything is dispatched", which is untrue for `reverse`/`reroute`. Under a strict reading the model's reverse answers are self-inconsistent (rubric Part A §1, "contract ambiguity", "self-inconsistent model answer"). The thesis says only that "the verifier constrains no `reverse` plan". **SHOULD FIX.**
  - (b) Plans were nulled for "copied option text" as well as for repeated robots (change list §5; DC 2.5). The thesis says only "invalid structure". NICE.

---

## 4. Experiments and Findings Coverage

### 4.1 Wrap-Up Rows R1–R26

| Row | In thesis | Numbers | Grade and caveat | Status |
|---|---|---|---|---|
| R1 intersection run 1 | Ch. 6 §res-ib10-ab | match | exploratory; near-repeats | OK |
| R2 intersection run 2 | Ch. 6 §res-ib10-c | match (both scripted figures) | OK | OK |
| R3 safety-exemption fix | Ch. 6 Safety; App. B | match (64, 68, 6 lost) | "not validated live" | OK |
| R4 head-on re-score | Ch. 6 tab:res-headon | match | post hoc; gate column from artifact fields | OK |
| R5 plan-influence trace | Ch. 6 tab:res-plan | match | OK | OK |
| R6 plan-order prompt check | Ch. 6 take 5 (7 of 27 only) | partial: A/B/A3/B3 accepted-unchanged counts (2/40, 2/40, 6/40, 14/29) absent; inferred ascending-id bias absent | — | thin |
| R7 offline Sonnet check (B3) | **absent** | — | — | **MISSING** (glossary has a reader name for it: "Offline Sonnet check (intersection)") |
| R8 convoy held-robot check | Ch. 6 convoy | match | OK | OK |
| R9 three offline replays | Ch. 6 tab:res-replay | match | OK | OK |
| R10 intersection takes | Ch. 6 tab:res-demo, take 5 | match | near-tie, chosen for label | OK |
| R11 convoy takes 1–5 | Ch. 6 convoy | match | OK | OK; **will go stale** (§4.3) |
| R12 head-on take | Ch. 6 | match | OK | OK |
| R13 five-robot take | Ch. 6 | match | OK | OK |
| R14 ER2LIVE | Ch. 6 §res-headon; App. B | match | selected; older code | OK |
| R15 three-way count | Ch. 6 tab:res-threeway; abstract; Chs. 1, 7, 8 | match | Missing caveat: the 65 counts 4 intersection "no congestion" answers, while the corrected 5 comes from v7r's 61 plan-block decisions, so "6 of 65 → 5" mixes denominators (register "Where Sources Disagree", Rev 8) | SHOULD |
| R16 plan-dispatch mismatch | Ch. 6 §res-demo; Ch. 7 | match (10 of 33; 3 of 3; 15 → 9) | "not a rate" added at 7316233 | OK |
| R17 contact recompute | Ch. 6 Safety; App. B tab:app-contacts | match; −0.16 vs −0.2 mm explained | "pending validation" | OK |
| R18 validation take | Ch. 6 Safety; Ch. 4 Later | match ("partially validated", "armed and harmless") | OK | OK. 2/5 arrived is not stated (NICE) |
| R19 escort guard | Ch. 6 Safety; Ch. 4 Later | match | OK | OK |
| R20 reverse guard replay | Ch. 4 Later ("17 recorded reverse commands"); Ch. 6 Safety | **headline missing**: 14 of 17 refused, 10 justified (8 contact, 2 graze), 3 untested, 1 FP; in October 10 of the 14 had a leg FAILED live, 7 pinned to the 195 s deadline. Ch. 6 "October `reverse` legs pinned robots against box faces" cites only **#ev("6.18")** (stall abort). The "7 pinned" figure is in **6.13** (guard report §8.5–8.6), so 6.13 should be cited too. (Inferred: I did not open the stall-abort report, which may also cover contact stalls.) | — | **SHOULD** (thin; add a citation) |
| R21 stall-abort replay | Ch. 4 Later ("221 recorded primitives") | **headline missing**: fires on 10/10 contact stalls 2.3–3.0 sim-s after contact; 0 of 191 false fires; 19 of 21 silent live failures were latch-held. The reconciliation's narrower scope (100 primitives) is not distinguished | — | **SHOULD** |
| R22 failure-cause classification | Ch. 6 §res-failure-causes | tables match v7q 4.1 and 2 cell for cell (verified) | "27 of 55" pools strata (SHOULD 1) | OK, except pooling |
| R23 interception | Ch. 6 three tables | match (0/8; 9/33; 1/4, 2/4; 29 = 9/15/5) | "not resolution" | OK |
| R24 queued hold replay | ev 6.19 only (47 answers, 46 yields; consistent with the v7o report) | prose omits the 46/46 and the "about 2/3 per take" caveat | — | NICE |
| R25 errata | not needed | — | — | OK |
| R26 unverified audit count | not cited | — | — | OK (correctly excluded) |

**Counts.**

- Of 26 rows: 20 covered adequately (R1–R5, R8–R14, R16–R19, R22, R23, R25, R26).
- Thin: 4 (R6, R20, R21, R24).
- Missing caveat: 1 (R15).
- Missing entirely: 1 (R7).
- Stale: 0 at the HEAD reviewed, but R11 / R15 / the campaign totals go stale with DC Rev 13 (§4.3).

### 4.2 Number Mismatches

None found in the numbers checked. Every numeric claim I compared matched its source, including the failure-cause tables cell by cell and the kappas (round 1 class 35/0.507, code 32/0.551; final 53/0.948 and 50/0.895).

Apparent conflicts that are not mismatches:

- 46 vs 47: 47 first-trigger answers, 46 yields.
- 146.7 vs 146.9 s: the robot entered the island at 146.7 s and stopped at 146.9 s.
- −0.16 vs −0.2 mm: rounding, explained in App. B.

Two citation issues:

- Only ev 6.18 is cited for the October reverse pins; 6.13 should be added (inferred).
- ev 6.16 cites the register at `586e881`, which predates its Rev 8 content (rung e/f additions, wording 6). The register is now at `2582f45`. NICE.

### 4.3 New Since the Brief (Not a Thesis Error; Integrate With Caveats)

- **Convoy rerun landed after the reviewed HEAD.** It is recorded in v7j `2cafbf7` (21:57, DC Rev 13, §14).
  - Kit `cvy`: queued-robot hold plus counterflow yielder correction, one demonstration take `cvY_t01_a2`, resolved 4/4.
  - The model itself named the feasible yielder robot_2. The correction was armed but **did not fire**. The hold added robot_3 and robot_4.
  - Label: "Resolved — grounder held the queued robots; model chose strategy and yielder"; n = 1, illustrative.
  - The closest non-exempt pair was 0.497 m (0.047 m above the latch). robot_2 passed 0.0185 m from `aisle_barrier/south` on its return (recompute verdict: clear). The passer–passer pairs were never exempt.
  - The report's latest commit `3866ec1` (after `2cafbf7`) states that **the correction was not exercised live**: "with this answer the queued-robot hold alone gives the same command, so this take is no live test of the correction". Its effect is shown offline only.
  - Campaign totals become 13 valid takes and 69 of 69 valid analyses; the rerun adds 0 accepted unchanged. The ledger reads 27,223 s and $2.8784.
  - The source of the fix is v7t `docs/reports/2026-11-15-convoy-non-arrival-and-yielder-feasibility.md`. It also shows the existing gate never fires in the convoy (0 of 49).
- **Thesis sentences this touches:**
  - abstract (67 analyses);
  - Ch. 1 Summary of Findings (67);
  - Ch. 5 tab:ch5-studies ("12 valid takes") and §ch5-demo;
  - Ch. 6 tab:res-demo, tab:res-threeway (convoy 48 → 50; total 67 → 69) and §res-demo-convoy, plus its caveat "a resolving take would have been a grounding result, not a VLM one", which should stay;
  - Ch. 7 rung e ("all five convoy takes … ended unresolved") and Limitations ("Nothing recovers a latched convoy cluster; the queued-robot hold did not resolve the scene in its two takes");
  - Ch. 8 Conclusion ("the convoy and five-robot demonstration takes stayed unresolved") and Future Work ("Recover latched clusters").
  - Wording to keep: "shows the corrected pipeline can execute the resolving sequence live, not that the VLM resolves convoy congestion" (DC Rev 13). Also note the yielder choice was the model's this time, with n = 1.
- **Scripted safety tests.** Still registered only: v7s `b000103`, 21:19, "register scripted safety-mechanism tests", with no results report. The thesis is silent on both jobs. It does not pre-empt them, which is good, but it does not mark them as in progress either.
  - The register's Rev 8 wording 5 adds: "the obstacle guards and the stall abort … are validated offline only, and their live validation is in progress".
  - The thesis says "not run live" (true). Add "live scripted tests registered, results pending" in Ch. 6 Safety and Ch. 8 Future Work "Validate the safeguards live".

### 4.4 Statements With No Source in the Reports

- Abstract hardware sentence: "the robots reported complete each time". Contradicted by ev 6.48 and register Hardware (scenario E: 3 completed, robot 3 FAILED).
- Ch. 8: "whose value over a scripted choice was not tested" (see SHOULD 0; arguable rather than unsourced).
- "27 of 55" undetermined, and its reasons as a pooled split (15/10/2). This figure appears in no source report; v7q gives per-stratum figures only. It is arithmetically correct.

---

## 5. Claims Discipline

| Hit (file, quote) | Verdict |
|---|---|
| `00-front.typ` abstract: "the model choosing a bounded back-out that the robots reported complete each time" (at `231baac`: "…each time and the robots reported it complete") | **Wrong** (scenario E had a FAILED robot; ev 6.48). MUST FIX |
| abstract: "All quantitative results come from simulation, small samples and one live VLM." | **Inaccurate.** gpt-4o ran live in the September head-on runs (35 of the re-scored runs) and the vp10 pilot (13 of the 41 traced analyses), and the hardware used `gemini-3.1-flash-lite`. Ch. 8 has the correct form: "one VLM in the live comparisons". SHOULD |
| abstract: "Safety evidence is robot-pair distance only; one sustained robot-obstacle contact was confirmed." | Acceptable, but it omits register Rev 8 wording 5 ("reverse manoeuvres driving robots into declared obstacles in October runs; guards and stall abort validated offline only"). SHOULD |
| `01-introduction.typ` Problem Statement: "a deterministic grounder turns its decision into safe commands" | Over-claims (escort/reverse legs are not obstacle-checked, as the next paragraph admits). Suggest "into commands that pass robot-pair safety checks". SHOULD |
| Ch. 1 Contributions 1: "the VLM decides, the grounder produces commands" | Borderline; elsewhere the thesis says "the model proposes". NICE |
| Ch. 1, Ch. 7, Ch. 8: "names no dominant cause" | Correct use (a null) |
| "bottleneck" | Only as the congestion type; Ch. 7 avoids "grounding is the bottleneck" ("they do not attribute failures to grounding"). Good |
| "validated" | Used correctly ("not validated live", "partially validated") |
| "collision-free", "0 contacts", "uses the image", "generalises" | **No hits** (grepped). Ch. 1 Scope says "no result is generalised beyond its scene, model and runtime". Good |
| Demo rates (`%`, "rate", "per cent" grepped in chapters 06–08 and 10, and in `evidence/ch6.typ`) | **No rate from demo takes.** The only hits are "nothing is a rate", "no rate for the live takes", "not a rate", the bootstrap "percentile", and the future-work "success rate". Good |
| Ch. 8 Conclusion ¶3: "whose value over a scripted choice was not tested" | Arguable; see SHOULD 0 |
| Ch. 3 Requirements item 4: "A model failure leads to no action, never to an unchecked motion" | Misleadingly broad (SHOULD 8) |
| Ch. 8 ¶1: "The live comparisons and the demonstration campaign were registered before their data" | True per Ch. 5 tab:ch5-studies |

Totals:

- 1 wrong: the abstract hardware clause.
- 4 imprecise or over-broad: "one live VLM"; "into safe commands"; Ch. 3 item 4; the Ch. 8 scripted-choice sentence.
- 1 borderline: "the VLM decides".
- 1 acceptable but incomplete: the abstract safety sentence.

The abstract and conclusion otherwise stay within Chapter 6. In particular they give both scripted figures, the 6 → 5 correction, "the only scene computed", and "selected for its label".

---

## 6. Internal Consistency and Completeness

- **Pooling rule vs "27 of 55".** Ch. 5 opening says "strata within a study are never pooled", and Ch. 6 says "strata never pooled". Yet the pooled count appears in Ch. 1 Summary ("27 of 55 failure units stay undetermined"), Ch. 6 "Undetermined units", Ch. 7 §disc-grounding and §disc-failure-cause context, and Ch. 8 Future Work. Use the register's wording 6: registered pilot 12 of 18 (on 2/8, off 10/10, no clock anchor); exploratory pilots 13 of 33; November 2 of 4.
- **Leftover placeholders.** Two `#todo[[VERIFY]…]` boxes remain in `05-methodology.typ`:
  - "Registered Designs": owner to confirm why no v1/v2 confirmatory data exist;
  - "Procedure": "owner to define what the pre-arm and post-arm gates check".
  - ev 5.12 also carries "[V…ERIFY]" text.
- **Unreferenced.** `tab:ch5-procedure` is defined and never referenced (NICE).
- **Shorthand.**
  - Chapters are essentially clean. Remaining terms are defined ones or in parentheses: `IB10 run 1/2` twice in tab:ch5-studies (deliberate), `vlm_verbatim`/`m3_default` 4 (defined), "Layer 2" 4 (defined), `chi` 3, `ER2LIVE_…mp4` 1 (a file name).
  - Evidence Index rows still use Arm A/B/C 32×, prereg 38×, tranche 31×, IB10 25×, `vlm_verbatim`/`m3_default` 16×, S1b 6×.
  - This is acceptable for a traceability appendix, but it is inconsistent with the glossary. The worst is ev 6.06: "grounder-default scripted default-plan arm".
- **Limitations coverage**, against the brief's list:
  - small n: yes;
  - exploratory status: yes;
  - single live VLM: yes;
  - simulator-only: yes, Ch. 5 external validity, carried by Ch. 7 "all stand";
  - selected demo takes: yes, Ch. 7 Threats;
  - LLM raters with no human check, non-clean blinding: yes, Ch. 5 and Ch. 7;
  - reconstructed command streams: yes;
  - unvalidated mechanisms: yes;
  - contact evidence as an offline recompute: yes.
  - **Missing:** reproducibility and data availability (see below).
- **Reproducibility.**
  - The front matter links `github.com/tuanhdangdinh/VLM-swarm-congestion`.
  - Every 2026-11 source branch is local and unpushed (register "Citable Artifacts"). Run bundles and videos are git-ignored, on one Mac, with no off-machine copy (wrap-up §5). The hardware source is `~/Downloads/verified_scenarios_12-11-2026/README.md` (ev 6.48).
  - Only Ch. 7 Threats mentions "unpushed, unreviewed branches".
  - Add a short data-availability statement saying what is in the public repo and what is not.
- **Future work.** It reflects the real open items: plan grammar, plan-driven reverse/reroute, plan feedback, obstacle checks on every straight manoeuvre, the E18 margin, live safeguard validation, a post-fix comparison, the clock anchor.
  - Missing: the convoy yielder-feasibility fix, now run once (§4.3); reverse shortening (owner-approved, not built); the stall-abort follow-ups.
- **Word-count cut.** The body is about 30.06 k words (at the limit). The change-list caveats checked are present:
  - pair-only safety;
  - contact stub;
  - audit not dispatch;
  - constrained selection;
  - near-tie;
  - chosen for label;
  - both scripted figures;
  - "valid is not usable";
  - the T1 dispatch correction.
  - **One caveat was lost or never applied:** change-list row 48. Ch. 3 Requirements item 3 ("A deterministic grounder checks each manoeuvre against the declared geometry … or refuses to move robots") has no escort/reverse caveat. The gap is stated later in §design-grounding.
  - Ch. 3 item 4 ("Safety independent of reasoning … A model failure leads to no action, never to an unchecked motion") is contradicted by the five-robot escort, which was an unchecked motion caused by a model decision. **SHOULD.**

---

## 7. Verdict and Prioritised Fix List

### 7.1 Answers to the Owner's Three Questions

**Up-to-date pipeline, code, prompt?** Largely yes.

- The architecture, grounding, plan audit, order channel, safety monitor and contact stub are described accurately against the code. The text correctly says the grounder never reads the plan for `reverse`/`reroute` and that the order switch is default-off and intersection-only.
- Two recorded prompts are verified verbatim, and the per-experiment prompt table is built from every artifact.
- Gaps:
  - legacy grounding mode is never defined, though the convoy results depend on it;
  - the `<think>` → JSON-only change and its reason (Sonnet refusals) are not explained;
  - the prompt-contract ambiguity behind the reverse mismatches is missing;
  - the demonstration and validation runtimes are not pinned by commit.

**New experiments and findings?** Yes, up to the reviewed HEAD, with good number fidelity. No mismatch was found in the numbers checked.

- Thin: the reverse-guard and stall-abort replay headlines, the per-variant counts of the plan-order check, and the denominator caveat on "6 of 65 → 5".
- Missing: the offline Sonnet intersection check (R7).
- New since the brief: the convoy rerun (DC Rev 13, 4/4, n = 1) landed after the reviewed HEAD. It makes the convoy sentences and campaign totals stale once adopted.
- The scripted safety tests have no result yet. The thesis neither pre-empts them nor marks them as pending.

**Answers all research questions?** No, but honestly.

- RQ4 and RQ5 are explicitly untested.
- RQ1 is partly answered: blocker kind is never reported, and detection is trigger-plus-VLM.
- RQ2 and RQ3 are answered in the negative, at pilot and decision level, but RQ2's answer is only a pointer to rungs.
- Ch. 8 never answers the RQs by number.
- The abstract poses a third version of the question.
- Negative and null answers are stated, not hidden.

### 7.2 MUST FIX

1. **Abstract, `00-front.typ` Abstract ¶2:** "the model choosing a bounded back-out that the robots reported complete each time". At `231baac` it reads "the model chose a bounded back-out each time and the robots reported it complete".
   - Problem: scenario E had 3 completed and robot 3 FAILED (ev 6.48; register Hardware; Ch. 6 §res-physical says so).
   - Fix: "… the model chose a bounded back-out each time, and 14 of 15 commanded robots reported the back-out complete (one run per arrangement, no goals, illustrative)", or simply "in three of four arrangements every robot reported it complete".
2. **RQ answers.** Ch. 8 must answer RQ1–5 explicitly, one line each, consistent with Ch. 7 §disc-rq.
   - RQ2 should be written out as a negative answer, not "(rungs a, d, e)".
   - RQ1 must say blocker kind was not evaluated and that detection is trigger-plus-VLM.
   - Align the abstract's question with the problem statement.
3. **Remove the two `#todo[VERIFY]` boxes** in `05-methodology.typ` ("Registered Designs" and "Procedure") and the VERIFY text in ev 5.12. Either get the owner's sentence or delete the claim (the pre/post-arm gate sentence can be cut).

### 7.3 SHOULD FIX

0. **Ch. 8 Conclusion ¶3** (downgraded from MUST; arguable): "the model supplied a valid strategy and robot set, whose value over a scripted choice was not tested".
   - This matches the registered scope: Ch. 5 says the scripted arm "isolates plan content only", and both arms ran the same strategy.
   - But a reader will take it as "untested", while run 2's arms were indistinguishable with the scripted arm handed the oracle strategy.
   - Clarify: "…which matched a scripted arm handed the same strategy in intersection run 2; whether the model's choice helps where no scripted choice is known was not tested."
1. **"27 of 55" pooled across strata** (Ch. 1 Summary; Ch. 6 "Undetermined units"; Ch. 7 §disc-grounding; Ch. 8 Future Work). Give it per stratum (register wording 6).
2. **Legacy grounding undefined** (Ch. 3 tab:grounding-config, Ch. 4 "Grounding interface").
   - Add one sentence: legacy = clamped distances (from declared geometry when supplied), with no feasibility bands, no ranked swept-path retreat candidates and no degradation list. It is used by the convoy scene, where the gate never fires because no obstacles are declared (v7t Summary).
   - Add that the queued hold is legacy-only.
3. **Prompt ending** (Ch. 4 Prompt; Ch. 6 Refusals). Explain that v1/v2 end in a `<think>` block, v3.4 replaced it with the JSON-only line, and why (`prompt_builder.py:54-60`: spatial-CoT prohibition; Sonnet 91/96 refusals). Make "original ending" in Ch. 6 say "the `<think>` ending of v1".
4. **Prompt contract and the reverse mismatch** (Ch. 7 "Plan versus dispatch"). Add the rubric Part A finding:
   - `involved_robots` is undefined, the grammar does not constrain `reverse`, and the prompt promises verification "before anything is dispatched";
   - the model's reverse answers are self-inconsistent under a strict reading.
5. **Reverse-guard and stall-abort headlines** (Ch. 6 Safety, "Obstacles"). Add R20 (14 of 17 refused, 10 justified, 1 false positive; 10 of the 14 FAILED live in October, 7 pinned) and R21 (10/10 contact stalls, 0/191 false fires; 19 of 21 silent failures latch-held). Add #ev("6.13") to "October `reverse` legs pinned robots", which cites only #ev("6.18") (inferred).
6. **"One live VLM"** (abstract, last sentence). Replace with "one VLM in the live comparisons", or name gpt-4o's earlier live head-on runs and the hardware model.
7. **Safety sentence in the abstract and Ch. 8.** Add the register's Rev 8 wording-5 clause: reverses drove robots into declared obstacles in October runs; the guards and the stall abort are validated offline only, with live tests registered and pending.
8. **Ch. 3 Requirements items 3–4.** Add the escort/reverse caveat (change-list row 48). Item 4's "A model failure leads to no action, never to an unchecked motion" is about model failures, and the five-robot escort came from a valid decision. The sentence is not contradicted, but it is misleadingly broad: add "valid decisions can still produce motion that is unchecked against static obstacles".
9. **Problem statement** (Ch. 1): "turns its decision into safe commands" → "into commands checked against robot-pair safety limits".
10. **Denominator caveat on "6 of 65 → 5"** (Ch. 6 tab:res-threeway caption, abstract). The 65 includes 4 intersection "no congestion" answers; v7r's base is 61 plan-block decisions (register "Where Sources Disagree", Rev 8).
11. **Offline Sonnet intersection check (R7) missing.** Add one sentence in Ch. 6 take 5: 16/16 valid, 11 accepted, 1 of 15 first triggers would qualify; no live Sonnet take (DC 3.4–3.5; order-check report §11).
12. **Integrate the convoy rerun** (§4.3) once the owner accepts it, at every location listed there, with the "grounding result, not a VLM one" caveat, and with the 3866ec1 point that the yielder correction was not exercised live. Until then, add a one-line "in progress" note in Ch. 6 convoy and Ch. 8, and a "registered, results pending" note for the scripted safety tests.
13. **Data availability.** Add a statement (front matter or the Ch. 4 Testing and Reproducibility section): branches unpushed, bundles and videos git-ignored on one machine, hardware README outside the repo.
14. **Runtime pinning.** Name the demonstration-campaign runtime (branch and commit of `demo/campaign-kits`, delta spec in v7k) and the validation take's (`a412949`) in Ch. 5 §ch5-demo. Change Ch. 1 Scope "one pinned runtime" to "the pinned runtime, plus the safety fix in run 2".

### 7.4 NICE TO HAVE

- Plan-order check per-variant counts (A/B/A3/B3) and the inferred ascending-id bias (R6).
- Queued-hold replay 46/46 in the prose (R24).
- Validation take 2/5 arrived (R18).
- RQ3: state that the model's `crossing_order` was never used in execution.
- RQ5: note that the failure and plan-state feedback in live prompts was partly wrong (ev 6.80).
- Name the release rule among the "three plan-ordering sentences".
- "copied option text" as a second reason plans were nulled.
- Update ev 6.16 to the register's current commit, and ev 6.01/6.44 if DC Rev 13 is adopted.
- Reference `tab:ch5-procedure`.
- Ch. 1 Contributions "the VLM decides" → "proposes".
- List the presentation cut in App. B.

---

## 8. Could Not Check

- **PDF render.** No compile was run; layout, overfull tables and figure placement were not checked.
- **Stage-2 prompt asset.** Not compared with its artifact.
- **Primary reports not opened.** Numbers in the swapped-ID / JSON-only / improved-annotation, contact, guard, stall-abort, validation, plan-order and held-robot reports were checked against the wrap-up and register only ("index-checked").
- **Chapter 2 literature claims.** Not checked.
- **Words lost by the cut.** I could not diff for meaning lost before `88d8cfe`. I checked only that the required caveats are present at `7316233`.
