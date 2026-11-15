<!-- Second independent review of the thesis, 2026-11-15. Reviewed docs/thesis working tree from 653e86f to 336ba30. Copied unchanged from the review job output. -->

# Second Independent Review of the Project Report (Examiner's Reading)

**Prepared:** 2026-11-15, read-only. Nothing in any repository was edited, staged or committed. No VM, API or test runs.

## 0. What Was Reviewed

**Thesis tree.** `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-thesis/thesis/`, branch `docs/thesis`.

- At the start, HEAD was `653e86f` ("docs: tighten chapter 4", 23:19 +0700). `git status --short` showed `05-methodology.typ` and `06-results.typ` modified.
  - The brief expected uncommitted edits in chapters 4 and 6 and in two appendices. In fact Chapter 4 was already committed, and the dirty files were Chapters 5 and 6.
- During the review the other session committed them: `4539708` (Chapter 6, 23:21:16) and `336ba30` (Chapter 5, 23:21:38).
- At the end, HEAD was `336ba30` and the working tree was clean.

**The PDF is a snapshot of the working tree at 653e86f plus those uncommitted edits.**

- Chapter 6 in the PDF is byte-identical to `4539708`.
- Chapter 5 in the PDF predates `336ba30`. The difference is about ten wording edits and one deleted sentence ("The scripted arm is grounder default by construction"); no number or claim changed. Every Chapter 5 quote below was re-checked against the committed file.
- The findings that sat in text uncommitted at the start are tagged **[uc]** below: they are in Chapter 5 and 6 text, now committed.

**Compile.**

- Method: copied to the scratch directory and compiled with tinymist 0.15.12. Both allowed compiles were used, one for `main.typ` and one for `supplement.typ`. Both succeeded with no error output.
- `main.pdf` has 104 pages: front matter i–x, body 1–71, references 72–76, appendices A–D 77–94. The supplement has 40 pages.
- Kept: `/private/tmp/claude-501/-Users-tuanhdangdinh-Documents-vgu-vlm-swarm/f764a230-50c3-421e-83e5-9de28f4c653c/scratchpad/thesis_review2/out.pdf` (the report) and `/private/tmp/claude-501/-Users-tuanhdangdinh-Documents-vgu-vlm-swarm/f764a230-50c3-421e-83e5-9de28f4c653c/scratchpad/thesis_review2/supp.pdf` (the supplement). The scratch source copy is deleted.

**Reading.**

- All 104 pages were read as extracted text (`pdftotext`).
- About 60 pages were also viewed as rendered images, PDF pages 10, 12–13, 20–21, 24–26, 28–33, 37–51, 60–76, 89–90 and 94–96. These include every large table except Table 3, every main-text figure and Appendix C's first page.
- The layout of the remaining pages (front matter 1–9, Chapter 1–2 text pages, Appendix B stills 91–93, Appendix C/D raw blocks 97–104) was judged from text only.

**Word count.**

- Body (PDF pages 11–81, Chapter 1 to the end of Chapter 8, including tables, captions and figure labels): 29,523 whitespace tokens and 27,159 alphabetic words.
- Front matter and the lists (pages 1–10) add 9.5 k tokens, mostly dot leaders. Appendices add about 6.0 k and references 1.75 k.
- The body is within the 25,000–30,000 target. No cut is required.

**Evidence tags.** 190 tags are cited in the chapters and 190 rows are defined: none missing, none unused. No `#todo` or `[VERIFY]` remains.

## 1. Overall Assessment

The report is close to ready, and its central honesty is its strength. It shows that the coordination layer clears one staged jam, that a scripted default plan does just as well, and that the VLM's own contribution was not demonstrated. It keeps every caveat the owner required, and it never says "collision-free" or "uses the image". The numbers I traced match their primary sources, apart from the items in section 5.

What most affects grade and credibility now:

1. **Visible typesetting defects in the PDF.**
   - Table 4 runs off page 18 through the footer.
   - Table 20's header columns overprint each other.
   - Figure 14's caption overprints the footer.
   - About four near-empty pages sit in Chapter 5.
   - Four sentences lost their semicolon after an evidence tag, including the scope-change disclosure and the RQ2 answer.
2. **The physical-testbed claim in the abstract.** "The model always chose a bounded back-out" holds only after excluding earlier attempts in which it chose `priority_override` and `reroute`. Chapter 8 Future Work says these strategies are "untested on hardware", although they were tried and failed. Both statements contradict the hardware README the report cites.
3. **The Discussion is thin and disconnected from the literature.**
   - Chapters 7 and 8 contain no citation. The negative result is never set against Garg et al., Valmeekam / Kambhampati or Zheng et al., although Chapter 2 set these up.
   - RQ2 is labelled "negative for the model", though at the intersection the model's chosen strategy, once grounded, did clear the jam. The finding is "no added value shown", which is not the same as "negative".
4. **Process voice and disclosure.**
   - "The owner" rules, decides and accepts in eight places, and is never defined.
   - There is no statement on AI assistance, and the declaration of authorship was dropped.
   - The report's ~720 bracketed evidence tags resolve only in a separate 40-page supplement.
   - Together these make the report read in places like a lab record. An examiner will ask who did what.

## 2. Argument and Structure

**Story.** The chain problem → RQ1–RQ3 → design → method → results → answers is coherent. Chapter 2 ends each section with a gap, Chapter 2.7 derives the three RQs, Chapter 6 reports per study and Chapter 8 answers per RQ. Design and implementation are cleanly separated: Chapter 3 is the design, Chapter 4 the build, and §4.9 holds the later, non-evaluated mechanisms. Results (Chapter 6) are mostly separated from interpretation (Chapter 7).

**Contribution statements side by side.**

| Place | Statement |
|---|---|
| Abstract | No explicit contribution sentence. It states the question, the system and results, and ends on limits ("All quantitative results come from simulation, small samples and one VLM in the live comparisons.") |
| Ch. 1.4 | Six artefact contributions: closed loop; grounder with per-dispatch plan-audit labels ("what the closest published systems do not report … is the per-dispatch audit label as an experimental quantity"); safety layer independent of the model; registered designs; offline benchmark; physical demonstration ("not an evaluation") |
| Ch. 2.6–2.7 | Gap: "none reports, per dispatch, how a model's plan fared in the check and whether it changed what was executed" |
| Ch. 7 | No contribution paragraph; a "ladder" of supported and unsupported claims |
| Ch. 8.1 | "The lasting contribution is a way to measure the model's share: per-dispatch plan-audit labels, re-grounding without the plan, and a scripted default-plan arm on identical code." |

The four are consistent in substance.

- **Gaps.** The abstract lacks the take-home contribution sentence. Chapter 8's "way to measure the model's share" omits that the report's own Chapter 7.2 shows the label over-states agreement ("The plan-audit label over-states agreement"), so the method works only together with the dispatch-match correction. Say so in Chapter 8.
- **Negative result as a finding.** This is mostly well done (Chapter 7 rung e, Chapter 8 "narrow"). What is missing is the "so what": no paragraph on what a practitioner learns. Examples: grounding carries the work; the audit labels need a dispatch check; prompts that list feasible actions turn the model into a constrained selector; the stall trigger plus a scripted strategy is a strong baseline. Nor does anything relate this to the success claims of Garg et al. (2024/2026).

**Chapter jobs.**

- Chapter 2 is used later only by pointer. Chapters 6–8 contain no citations (Chapter 6: 0, Chapter 7: 0, Chapter 8: 0; Chapter 2: 88). Zheng et al. (option-identifier bias) is the obvious frame for the "first-slot / robot_1 prior" finding (§6.10), and Valmeekam / Kambhampati for the "grounder did the work" finding. Neither is invoked in Chapter 7.
- Chapter 7 (about 1,900 words) is short against Chapter 5 (about 6,400) and Chapter 6 (about 6,700).

**Lab-log residue.**

- "the owner" appears 8 times: Ch. 5.1 "on 13 November 2026 the owner chose to run the intersection experiment instead…", "values ruled by the owner", Table 14 "after the owner accepted it", Table 15, §5.11 "one owner-requested convoy rerun take", §5.12.2 "an owner ruling", Ch. 6.2 "rather than by the owner" [uc], App. B.3 "on the owner's machine".
- Ch. 4.6: "a stale stage cost about ten debugging runs in July 2026".
- Table 10 keeps internal ids such as "(prereg-v3 tranche 1)", "(IB10 run 1)", "(v4 bench)" and "(Stage 1)". These are allowed once in parentheses by the glossary, but "Stage 1" and "v4 bench" mean nothing to a reader.
- Ch. 5.2 cites "(A33)" and "v3 addendum A33".

**Density.** About one evidence tag every 38 words; for example, §6.8 "Obstacles" carries 9 tags in 8 lines. This is defensible for traceability but heavy for an examiner. Consider moving tags in prose to the end of the paragraph.

**Signposting.** Good: §1.7, chapter openers, Table 10 as the single register of grades. One confusing spot: Table 1 and Table 10 both map studies to RQs with slightly different entries. The Table 1 failure-cause row says "RQ2 (where unfinished episodes stopped)"; Table 10 says RQ2. Fine, but redundant.

## 3. Research Questions

| RQ (stated) | Answered where | Answer in one sentence (Ch. 8) | Evidence and grade | Ch. 8 vs Ch. 6–7 and abstract | Limits stated? |
|---|---|---|---|---|---|
| RQ1 classification (Ch. 1.3; restated in Ch. 2.7, Ch. 5.1 by reference) | Ch. 8.1 item 1; Ch. 7.1.1 pointer | "answered in part": recall 9/11, 0 FP in 26, type accuracy 0.778, F1 0.915 on five seed pairs | Registered pilot (registered as confirmatory, reported as pilot) [6.35] [6.14]; numbers verified in the tranche-1 report lines 243, 362, 372–378 | Consistent with Table 18 and the abstract ("classification was scored only after the stall trigger") | Yes: trigger+VLM together, single accepted label, blocker kind not evaluated. Not used: the offline benchmark (Table 1 says it informs RQ1) and the campaign "no congestion" answers |
| RQ2 strategy competence | Ch. 8.1 item 2 | "negative for the model": layer 4/5 vs 0/5; scripted arm 4/4 (5/5); nothing cleared elsewhere | Exploratory pilots plus illustrative demos | Consistent with Ch. 7 rungs a and e and the abstract. But "negative" over-reads: the RQ asks whether the model's strategies clear congestion, and at the intersection the chosen `junction_clear`, grounded, did clear it. What was not shown is added value over a scripted strategy. Suggested wording: "Answered: the chosen strategy cleared the intersection once grounded, but no added value over a scripted strategy was shown, and nothing cleared reliably elsewhere." | Yes (comparator never ran; exploratory) |
| RQ3 yielder and order | Ch. 8.1 item 3 | "negative at the decision level": the gate made the yielder correct 79/79 (37 overturned); no model chose from the scene; crossing order never executed; one near-tie back-out order | Post hoc re-score (decision level) + pre-registered offline replays + one illustrative take | Consistent with Ch. 6.5, 6.7.1, Ch. 7 rung c and the abstract. 79/79 and 37 verified in the head-on re-score lines 222 and 437 | Yes |

**Scope-change disclosure** (owner rules):

| Location | Says "not tested" | Says moved to Future Work after the experiments | "Part of no registered design / changes no result" | Exploratory runs mentioned, not reported as evidence | "not preregistered" absent? |
|---|---|---|---|---|---|
| Ch. 1.3 "Scope change" | yes | yes | yes | yes [1.16] | yes |
| Ch. 5.1 [uc-adjacent] | yes | yes | yes | yes | yes |
| Ch. 8.1 | "were not tested and are future work" | — | — | — | yes |
| Ch. 8.2 | "moved from the research questions" | — | — | — | yes |

- No leftover RQ4/RQ5 appears in the chapters, Table 1, Table 10 or the abbreviations list. The only mentions are Evidence Index rows 1.03 and 5.01 (supplement), which describe the first design; that is correct.
- The only "not pre-registered" is the Table 24 caption, which is correct for the head-on re-score.
- Defect: in Ch. 1.3 the disclosure sentence lost its semicolon: "…on a blocked head-on scene [1.16] they are not reported as evidence here." See MUST FIX 1.

## 4. Technical Correctness and Currency

Verified against code at v7c `8933863` or against run artifacts.

- **Orchestrator values.** `orchestrator.yaml`: stall 12.0 s, goal-reached 0.15 m, arrival 0.35 m, proximity speed 0.05 m/s, cool-down 15.0 s, command timeout 20.0 s, failure-context window 60.0 s, stage-2 2 × 8.0 s. These match Table 8 and §3.4.
- **Safety values.** `safety.yaml`: 0.45 m latch, 0.6 m stale band, `hard_contact_floor_m: 0.0` shipped. These match Table 5 and §4.4.
- **Head-on demonstration take.** Decisions `4de32642` (`reverse`) and `f40c0537` (`yield`, `yield_robot` robot_1): `prompt_version` 2, `prompt_robot_order_mode` random, plan absent. The v2 prompt ends with the `<think>` instruction. The gate line in the M4/M5 log reads "yield re-grounded request=f40c0537… from=robot_1 to=robot_2 reason=… 0.70 m retreat room < 1.08 m required". This matches Table 12 (head-on row), Ch. 4.5 (v1/v2 `<think>` ending) and the Figure 14 bottom strip verbatim.
- **Convoy rerun.** Decisions `cfaabdc5` and `9ea3e3c2`: `prompt_version` 3, `id_asc`, `strategy` yield, `yield_robot` robot_2, `involved_robots` [robot_1, robot_2], `plan.provenance` repaired; second analysis "none". This matches §6.7.2 and the rerun rows of Table 28. Table 12 has no row for the rerun take (stale, NICE).
- **Take 5 trace (Figure 14).** Latency 7,728 ms, 1 attempt, `order_equivalent: true`, `dispatch_order_source` model. Verified in `df397030…json`.
- **Appendix C.2 (stage-2 prompt), verified byte-for-byte; new.**
  - Source: `v7a …/ib10L_e09_armA_a1/decisions/e26783998f584d0996175cf42c4501a4.json`.
  - User prompt 1,092 characters, equal to `assets/prompts/ib10-run1-e09-stage2-user.txt`. SHA-256 `b8e68562…` recomputed and equal to the stored value.
  - Raw answer 107 characters, byte-equal.
  - Letter assignment: B = candidate A (rank 1), A = candidate B (rank 0). `grounded_label` A, system prompt "You are a helpful assistant." The appendix statement is accurate.
  - Appendix C holds only three records. C.1 (run 1 e03) and C.3 (`df397030`) were verified by the previous review, so C.2 was the only new byte check possible. The head-on and rerun artifact reads above are the second and third record checks (against Table 12 and Figures 14 and 23, not byte-for-byte).
- **Grounder, plan audit, legacy vs derived, feasibility gate, "audit, not dispatch".** The descriptions in §3.6 match what the previous review verified in code. Legacy is now defined (§3.6: "Legacy mode, used by the convoy scene, clamps distances … and has no bands, ranked candidates or degradation list; the queued-robot hold works only in it").
- **Prompt ending.** §4.5 now explains the JSON-only line replacing the `<think>` block. Its "made Sonnet 5.5 refuse 91 of 96 attempts" comes from the v3.4 re-pin report and the code comment [4.17]. §6.10 gives "30 of 48" for the swapped-ID replay. These are two different studies; name the study behind 91/96 so the reader does not see two conflicting refusal rates.
- **Runtime per study.** Table 11 and Ch. 1.6 ("one pinned runtime, plus the safety fix in intersection run 2") are correct. The demonstration runtime is described as "a later prompt and … the plan-order switch, so not the evaluated runtime" but is not pinned by commit in the main text.
- **Inaccurate design claim, Ch. 3.7.** "The grounder sizes escort and pass legs with the same radius, so a grounded manoeuvre does not trip the latch." In convoy takes 4–5 a grounded escort latched at 0.418 m and 0.419 m against a held bystander (§6.7.2). Reword as a design intent that holds for command partners only.
- **Hardware code.** No commit in any branch of the main repository contains Zenoh code, the runbook `docs/guides/notion_end_to_end_vlm_zenoh_runbook.md` named in the README, or `gemini-3.1-flash-lite` outside documentation (`git log --all -S`). This confirms "the code that ran is not in the repository's history".

## 5. Numbers

**Checked in primary sources: match.**

- Intersection run 1 (v7a): 4/5, 16/20, 112.9 / 115.5 / 116.5 / 116.6 s, 0.2633 m, 0.2856 m.
- Intersection run 2 (v7d): 115.96, 117.80, 117.86, 114.3, 118.1 s, 0.3008 m, 0.2965 m, 3.4 s.
- Registered pilot (tranche-1 report): 0/10; 16/125 and 12/125; +0.032 [−0.008, +0.080]; −31.5 s [−71.6, −0.6]; 0.818, 0.778, 0.915; 0 FP in 26; 17.6 s; 0.225–0.424 m.
- Head-on re-score: 5/23, 10/12, 12/30, 11/13, the always-robot_1 and first-come-first-served columns, 79/79 and 37.
- Demo campaign (`DC`): totals 69/69; 6 of 65; convoy 50 of 50 with 3 / 20 / 25 and the rerun's 1 repaired plus 1 "none"; 0.2176, 0.276, 0.370, 0.374–0.379, 0.497 and 0.418 / 0.419 m; 72 of 76; 3.79 mm; 82.1 mm; 0.981 / 0.971 m costs; latencies 6.7–11.5 s and 7.0–13.0 s.
- Plan-dispatch report (v7r §6.3): 6 → 5, with motion-only 6 and raw 3.
- Scripted safety tests (`SFT`): 40.83 s, 0.293, 46.30 s, 2.21 s, 24 rows, 1017 and 1313 rows.
- Failure-cause reconciliation (v7q): agreement row 0.964 / 0.909 / 0.948, 139 of 154 and 151, 233 snapshots, 9.1 and 20.9 s, the 45-unit denominator (8, 33, 4), 57 legs.
- Plan-influence trace (v7i): 0 of 20 `junction_clear`; the 2 / 11 / 1 accepted.

**Campaign totals after the rerun: confirmed.**

- 13 valid takes: intersection 5, convoy 6, head-on 1, five-robot 1.
- 69 of 69 valid responses: 9 + 50 + 2 + 8.
- 6 of 65 accepted unchanged among the first twelve takes. The 65 is plan-channel only: 67 minus the 2 head-on analyses.
- Corrected count 5 of 61. The 61 is stated in the Table 28 caption and the abstract as the 65 minus the four intersection "no congestion" answers.
- Convoy: 6 takes, 5 unresolved, 1 resolved.

**Index-checked only** (against the evidence rows or the wrap-up, not the primary report): Table 25 replay counts, §6.9 benchmark coverage figures, Table 26 per-column values beyond those listed above, §6.4 sensitivity numbers ("4 of 233", "13 change code"), Table 18 per-seed dispatch counts ("corrected against the command log").

**Mismatches and population problems.**

| # | Location | Text | Source / problem | Fix |
|---|---|---|---|---|
| N1 | Ch. 1.2 ¶2 | "true of live ER-2 plans (0 of 20 accepted unchanged)" | The 0 of 20 is ER-2 **`junction_clear`** plans only. Table 26 shows 2 ER-2 intersection plans accepted unchanged (both `reverse`) (v7i lines 39, 137) | "true of the 20 live ER-2 `junction_clear` plans (none accepted unchanged), not of …" |
| N2 | Ch. 7.3.1 | "for 25 of 45 coordination-layer-on units no mechanism applies" | Tables 21–23 label as "No mechanism applies" the parent row 8 + 24 + 3 = 35; 25 is its "no linked leg" sub-row (5 + 19 + 1), as Ch. 6.4 correctly says. The figure also pools three strata | "for 25 of 45 units (5 of 8, 19 of 33, 1 of 4) no escort or reverse leg is linked" |
| N3 | Ch. 6.8 "Obstacles" | "fires … on none of 191 completed ones" | The source counts 191 **contact-free** completed primitives; 2 completed primitives in contact would end FAILED (wrap-up R21; v7p 6.2–6.4) | "none of 191 contact-free completed ones" |
| N4 | Ch. 4.8 and Ch. 6.11 vs README | "Unparsable replies and earlier wait-only or timed-out attempts are excluded" | README §6: "Earlier `priority_override`, `reroute`, and odometry-loss attempts are also not counted … when they only produced waiting or timed-out backup commands". The outcome is paraphrased; the model's choice is dropped | Name the strategies (see MUST FIX 2) |
| N5 | Supplement row 6.63 | "27 of 55 undetermined (15 …, 10 …)" | Pools strata; the chapters were fixed, the row was not | Per stratum, as in Ch. 6.4 |
| N6 | Supplement rows 6.13 and 6.18 | "not run live" / "no live run" | Stale since the scripted tests (6.86); the chapters say "validated live once" | Append "; validated live once in a scripted safety test (6.86)" |
| N7 | Ch. 5.8.4 vs Ch. 6.4 | Method: "full-code agreement as raw agreement"; results give "full code for 50 of 55 (kappa 0.895)" | Inconsistent reporting rule (minor) | Either drop the kappa or add it to the method |

**Units and rounding.** Consistent. The 0.2643 / 0.186 m errata are not used. The 3.79 mm vs 0.97 mm grazes are consistent with the `DC` report.

## 6. The Newest Material

### 6a. Physical Testbed (Ch. 4.8, Ch. 6.11, App. D, Abstract, Ch. 8.2)

**Attribution.**

- Generally good. Ch. 4.8 says the details "come from the team's testbed notes, outside the repository [4.41]". Ch. 4.8 and Ch. 6.11 say "code … not in the repository's history". Results are kept apart: "never pooled with simulation results"; "not an evaluation".
- Row 4.41's source is "Team testbed notes (owner-supplied draft of 15 Nov 2026; not committed to the repository)". The examiner cannot check it.
- Repository content available: the evidence register's hardware table (v6d lines 241–262) and the README (`~/Downloads/verified_scenarios_12-11-2026/README.md`, md5 `26718adb…`, which matches row 1.07). The folder listing: `README.md` (8 KB), `decision_artifacts/`, `logs/`, `verified_scenarios_images_2026-11-12/`.
- Outcomes A 4/4, C 3/3, D 4/4 and E 3 completed with robot 3 failed match the README summary table and the register.

**Problems.**

1. **Selection hidden in the abstract (MUST).** "On physical TurtleBot3 robots in four staged arrangements, the model always chose a bounded back-out." The README excludes from its success set earlier attempts in which the model chose `priority_override` and `reroute` (these produced waits or timed-out backups), plus two parse failures. "Always" is true only of the kept run per arrangement.
2. **Future Work contradicts the source (MUST).** Ch. 8.2: "yielding, phased junction clearing, priority-based coordination and re-routing are untested on hardware, which ran only bounded reverse". Priority override and reroute were tried on hardware and did not succeed.
3. **Unhedged statements about code that is not in the repository (SHOULD).**
   - Ch. 4.8: "The model sends no velocities: its decision passes grounding, which checks identifiers and bounds the commands, and the safety monitor before anything reaches a robot."
   - Ch. 6.11: "Each outcome belongs to the whole chain: the model sends no velocities …".
   - Both rest on team notes only. Prefix them with "According to the team's notes".
   - The stop conditions are already hedged ("A robot was to be stopped …"), which is good.
4. **Appendix D dating (SHOULD).** "The values are those used on 12 November 2026", but the source is a draft dated 15 November that is not in the repository. Either say "as recorded in the team's notes of 15 November" or commit the notes.
5. **Proportion (NICE).** §4.8 (about 1 page, Table 9, Figure 3) plus Appendix D (2 pages of configuration) is generous for an illustrative demonstration with n = 1 per arrangement and no goals. This is acceptable given the reproducibility aim. The abstract keywords "TurtleBot3, … Zenoh" foreground it more than the evidence warrants.
6. **Consistency.** The abstract's "completed by all but one robot" (14 of 15 commanded) matches Ch. 6.11. "Bounded back-out" vs Ch. 6.11's `reverse` is acceptable. The safety boundary of 0.50 m (README line 122) and the speed 0.08 m/s (team notes) are attributed correctly.

### 6b. Scripted Safety Tests and the Convoy Rerun

**Scripted safety tests.** Integrated correctly and consistently with the owner wording "validated live once in a scripted safety test":

- in §4.9 (reverse guard, stall abort, contact logging);
- in §6.4 caveats, §6.8, §7.3 and §8.1;
- in Table 10 ("Scripted safety test", n = 1 per mechanism, registered: Yes);
- the escort guard is "offline only" everywhere.

The numbers match `SFT`. The supplement rows 6.13 and 6.18 are stale (N6).

**Convoy rerun.** Integrated with the required caveats:

- §6.7.2: "the resolution depended on the grounder's hold, and the correction did not fire, so it is untested live";
- Figure 23 caption: "not evidence that the VLM resolves convoy congestion";
- Table 27 label, Table 28, §7.3, §8.1 RQ2, §8.2.

One nuance: §6.7.2 says "After dispatch only exempted pairs came under 0.45 m". `DC` line 1205 records the last 22 latch lines of the standoff pair within 0.26 s after dispatch, before the exemption registered. This is negligible (NICE). Table 12 lacks a rerun row (NICE).

### 6c. Appendix B and Appendix C

**Appendix B.**

- Accurate and attributed.
- The intro is stale: "and the offline contact recompute that Section 6.8 summarises". The recompute table moved to the supplement in `8429569`.
- Figure 15's log pane is illegible at print size, though the caption carries the content.
- Figure 14 (page 80) appears after Figure 15 (page 79), and its caption runs into the footer rule.
- Table 32's caption reads "Source: [6.01]. Source: [6.84]."

**Appendix C.**

- Accurate: C.2 is verified above. The SHA values are given.
- Not excessive (about 7 pages). The full prompt is a legitimate examiner need.
- Cross-references render as "Section C" and "Section D" in Ch. 4.5, Ch. 4.8 and Ch. 5.4. Use "Appendix C".

## 7. Claims Discipline

Grep over chapters 00–08 for safe, guarantee, ensures, robust, successfully, significant, "demonstrates that", collision-free, validated and contact, judged in context.

| Hit | Verdict |
|---|---|
| Abstract: "the model always chose a bounded back-out" | **Over-claim** (section 6a). MUST |
| Ch. 8.2: "priority-based coordination and re-routing are untested on hardware" | **Wrong** (section 6a). MUST |
| Ch. 1.1: "The design question is therefore also how its decision becomes safe commands" | Residual of the earlier "safe commands"; motivation voice, but contradicts §3.6. Use "commands that pass the safety checks" (SHOULD) |
| Ch. 3.7: "a grounded manoeuvre does not trip the latch" | Over-claim (section 4). SHOULD |
| Abstract and Ch. 8.1: "Safety evidence is robot-pair distance only"; Ch. 7 f "robot-pair centre distance only" | The owner wording is "robot-pair centre distance plus an offline geometric recompute". The text then cites a contact the recompute found, so "only" contradicts itself. SHOULD |
| Ch. 8.1 RQ2 "negative for the model" | Arguable (section 3). SHOULD |
| §4.9: yielder correction "49 of 49 recorded first-trigger yields resolving" | Reads as resolution. Should be "grounding into the resolving sequence" (offline). SHOULD |
| "validated" | Otherwise correct ("validated live once in a scripted safety test", "not validated live", "offline only") |
| "collision-free", "0 contacts", "uses the image", "generalises", "significant", "guarantees", "ensures", "robust" | No over-claiming hits. "Robust" appears only in the Zheng et al. reference title |
| Demonstration rates | None; "nothing is a rate" is stated repeatedly |
| The intersection take with the model's back-out order | Correctly framed: Figure 9 says "An end-to-end execution example, not controlled evidence of improved performance" |
| Registered pilot 0 of 10 | Stands, never pooled: "The registered pilot's 0 of 10 stands" (§6.4, §7.3.1) |
| Failure causes | "names no dominant cause"; strata are kept apart in the chapters (except N2) |

**Undersold.**

- The stall trigger plus grounder clearing a jam that is otherwise permanent (4/5 vs 0/5) is a real, positive system result. It is stated, but immediately submerged.
- The per-dispatch audit plus re-grounding is a reusable measurement method. Chapter 8 says so in one sentence.
- The gate's 79/79 is a positive finding for the deterministic layer. It could be framed as a design lesson ("let geometry pick the yielder").

## 8. Presentation (Seen in the PDF)

**Length.** 104 pages. The body is 27.2 k words, within target, so no cut is needed. If a cut were wanted without losing caveats, these move cleanly to an appendix:

- §4.6 Engineering Lessons;
- Table 14's "Caps" row;
- §5.9 variant details;
- the three interception tables (Tables 21–23): keep one combined table and put the others in the supplement.

**Defects (verified in the rendered images).**

- **Table 4 (body page 18).**
  - The "Effect" column is about one word wide.
  - `junction_clear` overflows the right margin.
  - The last row runs through the footer ("Page 18" overprinted) and is cut off.
  - The table does not break to page 19. MUST.
- **Table 20 (pages 51–52).** "Disagreements" and "Disagreements left undetermined" overprint each other in the header. SHOULD.
- **Tables 21–23.** The "persistent-state" header touches the right rule. NICE.
- **Figure 14 (page 80).** The caption overprints the footer rule and "Page 80". SHOULD.
- **White space.**
  - Pages 35–38 are each between one-third and two-thirds empty, because full-width figures (Figures 5–8, Table 11) are placed in flow.
  - Pages 21, 30, 57 and 58–62 also end half empty.
  - Use `placement: auto` floats or reduce the image heights. SHOULD.
- **Figure 8 caption.** The long monospace scene name forces "Figure 8: Two-robot head-on corridor with obstacle" into word-spread justification. NICE.
- **Apostrophes after digits render as primes.** For example "M1′s", "Nav2′s", "run 1′s", "Chapter 6′s", "robot_1′s", "version 1′s" (pages 19–20, 26, 52, 56, 65 and others). NICE, but frequent.
- **Missing semicolons after evidence tags** (the source has `#ev("…");`, and Typst consumes the `;`):
  - Ch. 1.3 Scope change: "[1.16] they are not reported";
  - Ch. 4.6: "[3.31] every threshold in this report";
  - Table 28 caption [uc]: "recorded labels unchanged [6.51] the 65 include";
  - Ch. 8.1 RQ2: "(0 of 10) [6.14] the convoy stayed".
  - Fix: `#ev("…")\;` as used elsewhere. MUST, because two of these are the scope disclosure and the RQ2 answer.
- **Table 10 caption.** "Studies in this report, "Registered" means …" is a comma splice. NICE.
- **§6.8.** "over 44 recorded bundles, found" has a stray comma. NICE.

**Figures and tables.**

- Legible at print size except Figure 15's log pane and the scene-label text of Figures 4–5 (small but readable).
- Every figure and table is referenced in the text.
- Captions are self-contained and carry the grade, for example "Illustrative take, n = 1".

**Front matter.**

- The title page says "Project Report".
- The abstract is 260 words, within a typical limit.
- Acknowledgements are present.
- The lists of figures, tables and abbreviations are complete for the main text. Missing abbreviations: N0 (Table 19), TCP, IP and Wi-Fi (App. D), UTC.
- No declaration of authorship (dropped earlier per wrap-up 10.2) and no AI-use statement. Presence or absence only; check the institution's template.

**References.**

- 78 bibliography entries; Typst prints only the cited ones.
- I compared cited keys loosely and dropped my uncited list, because my regex missed `#cite(<…>)` forms. Not fully checked.
- **Visible problem.** Two pairs collapse to identical author-year labels, and the printed entries lose their author lists:
  - "Yang et al. (2023)": Set-of-Mark and Safety Chip;
  - "Zhang et al. (2024)": LaMMA-P and Guidance Graph;
  - "Chen et al., 2024": SpatialVLM and Chen, Y. "Scalable … Centralized or Decentralized" in the text.
  - In-text citations are therefore ambiguous. APA needs 2023a/2023b suffixes or initials. SHOULD.
- **Plausibility spot-check** (internal consistency only, no web access):
  - Coffman 1971 (ACM CSUR 3(2) 67–78): plausible.
  - Dresner & Stone 2008 (JAIR 31): plausible.
  - Kaplan & Meier 1958 (JASA 53(282)): plausible.
  - Garg et al. 2026: only a project-page URL; the bib says "arXiv preprint: 2404.06413", the same id as Garg 2024. Flag as weakly identified.
  - Tang et al. 2026 "Late Autumn" (arXiv 2611.02391), an id from November 2026, and Dwedar 2026 (2609.27816), GAVEL (2609.19315) and Physical Agentic AI (2608.22657): plausible by date pattern but unverifiable here.
  - Nothing looks fabricated on internal grounds. The examiner may query the very recent arXiv ids.

**Evidence Index usability.**

- The main PDF's Appendix A now lists only the documents (Tables 30–31) plus a data-availability paragraph. All 190 rows are in the separate supplement.
- An examiner reading only `main.pdf` sees about 720 tags with no resolution. Make sure the supplement is submitted with the report and named on the title page or in §1.7.
- In the supplement, internal ids remain in source columns (prereg 35×, tranche 20×, IB10 5×, `vlm_verbatim` 10×, run labels 16×). This is acceptable as traceability.

**Language.**

- Mostly British spelling ("colour", "recognise", "behaviour") under `region: "us"`. Mixed "artefact" and "artifact": "artefact fields" §6.5, "registered artefacts" §6.7, "decision artifact" §4.3 and App. C. NICE.
- Sentences are long and dense. Some are hard to parse: §5.8.6 and the Table 14 "Caps" cell ("$1.30 total, on episodes start only with $0.25 left").
- Tense is consistent (past for runs, present for design).

## 9. Reproducibility and Integrity

- **Data availability.**
  - Present, in Appendix A: unpushed branches, bundles and videos on one machine, and the hardware README outside the repository.
  - The public repository link is in the front matter.
  - Placement is late: an examiner meets it only in the appendix. A one-line pointer in §4.7 "Testing and Reproducibility" would help.
- **Language-model raters.** The disclosure is accurate and visible in §5.8.4 ("both language-model agents with no recorded human check") and §7.3.1.
- **AI assistance in building, analysing or writing.** No statement. Combined with "the owner ruled …" and the agent-produced analyses, an examiner is likely to ask. Note the absence; follow the institution's rules.
- **Ethics and safety.** Only simulation and a small indoor robot demonstration. No statement is needed beyond the safety caveats present.

## 10. Status of the Previous Review's Items

| Item | Status | Location checked |
|---|---|---|
| MUST 1 abstract hardware clause (scenario E FAILED) | **Fixed** ("completed by all but one robot"), but a **new** issue: "always chose" hides excluded strategies (section 6a) | Abstract |
| MUST 2 Ch. 8 answers RQs by number | **Fixed** | Ch. 8.1 items 1–3 |
| MUST 3 remove `#todo[VERIFY]` | **Fixed** (none in chapters or evidence) | grep |
| SF0 Ch. 8 "value over a scripted choice was not tested" | **Fixed** ("whether the model's strategy choice helps where no scripted choice is known was not tested") | Ch. 8.1 last ¶ |
| SF1 "27 of 55" pooled | **Fixed in the chapters** (Ch. 1.5, 6.4, 7.2, 8.2 per stratum); **not** in supplement row 6.63 | grep |
| SF2 legacy grounding undefined | **Fixed** | §3.6 |
| SF3 `<think>` → JSON-only and why | **Fixed** (§4.5, §6.10, Ch. 7 b); the 91/96 vs 30/48 sources are not named (SHOULD) | §4.5 |
| SF4 prompt contract and the reverse mismatch | **Fixed** ("The prompt invites this: …") | §7.2 |
| SF5 reverse-guard and stall-abort headlines, ev 6.13 | **Fixed** (14 of 17, 10/3/1, 7 pinned; 10/10, 191, 19 of 21; cites 6.18 and 6.13); "contact-free" nuance (N3) | §6.8 |
| SF6 "one live VLM" | **Fixed** ("one VLM in the live comparisons") | Abstract, §8.1 |
| SF7 safety sentence (reverses into obstacles; guards) | **Fixed** | Abstract, §8.1 |
| SF8 Ch. 3 Requirements items 3–4 | **Fixed** | §3.1 items 3–4 |
| SF9 problem statement "safe commands" | **Fixed in §1.2**; residual "safe commands" in §1.1 | §1.1 last ¶ |
| SF10 denominator caveat 65 vs 61 | **Fixed** | Table 28 caption, abstract, §1.5, §7 d |
| SF11 offline Sonnet intersection check (R7) | **Partly**: "for Sonnet 5.5, never run live, in 1 of 15" is present; 16/16 valid and 11 accepted are absent | §6.7.1 |
| SF12 integrate the convoy rerun | **Fixed** | §6.7.2, Tables 27–28, Fig. 23, §7, §8 |
| SF13 data availability | **Fixed** (Appendix A), placed late | App. A |
| SF14 runtime pinning | **Partly**: Ch. 1.6 fixed; demonstration and validation runtimes are still not identified by commit in the text | §5.11, §6.7 |

Counts: MUST 3 of 3 fixed. SHOULD 12 of 15 fixed, 3 partly (SF11, SF14, and SF9 residual). SF1 and SF3 are fixed in the chapters with small residuals (row 6.63; naming the 91/96 study).

Previous NICE items: the RQ3 `crossing_order` point (done), the RQ5 feedback point (done, Future Work), the release rule (the prompt record shows it), the per-variant A/B/A3/B3 counts (absent), the 46/46 hold (absent; the "49 of 49 … 27 with the hold alone" correction figure is present), and the presentation cut listed in App. B (done).

## 11. Prioritised Fix List

### MUST FIX Before Submission

1. **Lost semicolons** (four places): Ch. 1.3 Scope change "[1.16] they"; Ch. 4.6 "[3.31] every"; Table 28 caption "[6.51] the 65"; Ch. 8.1 RQ2 "[6.14] the convoy". In the source write `#ev("…")\;`.
2. **Hardware selection.**
   - Abstract: replace "the model always chose a bounded back-out" with "in the one kept run per arrangement the model chose a bounded back-out (earlier attempts with `priority_override` and `reroute`, which produced only waits or timed-out backups, and two unparsable replies were not kept)", or shorten to "in the kept run of each arrangement".
   - Ch. 4.8 and Ch. 6.11: name the excluded strategies as the README does (§6 "Runs excluded").
   - Ch. 8.2: replace "priority-based coordination and re-routing are untested on hardware" with "were tried on hardware only in attempts that produced waits or timed-out backups".
3. **Table 4 overflow** (body page 18): give "Effect" a wider column (for example `columns: (auto, auto, auto, 1fr)`, or shorten the setting names), and allow the table to break.

### SHOULD FIX

4. **RQ2 label.** Ch. 8.1 and Ch. 1.5 "negative for the model": reword as in section 3.
5. **Discussion.**
   - Add one subsection relating the findings to Chapter 2: Garg et al.'s VLM deadlock resolution vs "the grounder did the work"; Valmeekam and Kambhampati on LLM plans needing verifiers; Zheng et al. on option-id bias vs the robot_1 / first-slot prior; Physical Agentic AI's gate counts vs the audit labels.
   - Add a short "lessons" paragraph and a contribution sentence in the abstract.
6. **Define or remove "the owner"** (8 places, listed in section 2). Use "we", "the authors" or "the project lead". Consider an AI-use statement.
7. **Ch. 7.3.1 "25 of 45 … no mechanism applies"**: fix the label and give per-stratum counts (N2).
8. **Ch. 1.2 "0 of 20"** is `junction_clear` only (N1).
9. **Safety-evidence wording.** In the abstract, Ch. 7 f and Ch. 8.1, write "robot-pair centre distance plus an offline geometric recompute" (owner wording) instead of "distance only".
10. **Ch. 3.7** "a grounded manoeuvre does not trip the latch": limit to command partners; cite convoy takes 4–5.
11. **Hardware hedging.** Prefix the "the model sends no velocities …" sentences (Ch. 4.8, Ch. 6.11) with "According to the team's notes". Re-date Appendix D or commit the notes.
12. **Table 20 header and the Figure 14 caption** overprinting; **white space** on pages 35–38 and others.
13. **Ambiguous references**: Yang 2023 ×2, Zhang 2024 ×2, Chen 2024 ×2. Add a/b suffixes or initials.
14. **Stale text after the supplement move.** The Appendix B intro ("offline contact recompute"), "Section C/D" → "Appendix C/D", supplement rows 6.13, 6.18 and 6.63 (N5, N6), and Table 32's double "Source".
15. **§6.8** "none of 191 completed ones" → "contact-free" (N3). **§4.9** "49 of 49 … resolving" → "grounding into the resolving sequence".
16. **§1.1** "safe commands" residual. **§4.5** name the study behind "91 of 96".
17. **Make sure the supplement is submitted** with the report and referenced from the title page or §1.7. Otherwise the ~720 tags are unresolvable.

### NICE TO HAVE

- Digit-apostrophe primes ("M1′s"); artefact/artifact consistency; the Table 10 caption comma splice; the §6.8 stray comma; the Figure 8 caption spacing.
- Table 12 rerun row; R6 per-variant counts; 16/16 and 11 for the Sonnet check; the "after dispatch" nuance in §6.7.2; abbreviations N0, TCP, IP, UTC.
- Pin the demonstration runtime commit in §5.11.
- Reduce tag density (move tags to the ends of sentences or paragraphs).
- Clarify Figure 9 / Figure 14: costs 0.981 / 0.971 m vs the commanded 0.781 / 0.971 m. Say explicitly that the recede cost and the commanded distance differ for robot_3 and why that is unknown.

### Likely Examiner Questions

| # | Question | Where the report answers |
|---|---|---|
| 1 | If the default plan clears the jam, what does the VLM add, and is it worth its latency and cost? | Partly: Ch. 6.2, Ch. 7 a/e, Ch. 8 "narrow". No cost or latency trade-off discussion |
| 2 | How do your results compare with Garg et al., who report VLM deadlock resolution? | **Not answered** (no citations in Chapters 7–8) |
| 3 | Why no classical coordinator live? | Ch. 5.12.2 (machine time, the ruling), Ch. 7.3 |
| 4 | Why list robots in ascending order when slot bias was known? | States the fact (Ch. 1.3, 5.6, 6.10), **not why** |
| 5 | Did the VLM use the image at all? | Ch. 6.5 and 6.10, Ch. 7 e: no evidence |
| 6 | Who is "the owner", who did the work, and were AI tools used for code, analysis and writing? | Only the LLM raters are disclosed (§5.8.4); **otherwise not answered** |
| 7 | Why did the five-robot pilot complete nothing even with the layer off: is the scene too dense? | Partly: §5.3.1 "much harsher density"; the failure-cause null |
| 8 | Can I reproduce this? | Appendix A data availability: not publicly. Answered, but negatively |
| 9 | What exactly ran on the robots, and why a different model? | Code not in the repository (§4.8). **Why** flash-lite is **not answered** |
| 10 | n = 5 near-deterministic repeats: what can they show? | §5.7, §5.12.2: counts only, large differences only |

## 12. Could Not Check

- The rendered layout of about 44 pages was judged from text only (section 0).
- The full bibliography against the rendered list: the uncited-entry check was abandoned (regex limits). No web verification of references.
- The Chapter 2 literature claims.
- Primary sources for Table 25, §6.9 and parts of §6.4 (index-checked only).
- The team testbed notes (not in any repository) behind row 4.41 and Appendix D.
- Whether the institution requires a declaration of authorship or an AI-use statement.
