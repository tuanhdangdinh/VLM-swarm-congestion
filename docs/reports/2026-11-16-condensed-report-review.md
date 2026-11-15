<!-- Independent review of the condensed report, 2026-11-16. Reviewed docs/thesis a7d03a7, b62346d and 326a732. Copied unchanged from the review job output. -->

# Third Independent Review: Condensed Project Report vs Extended Report and Primary Evidence

Reviewer: independent read-only agent. Date: 2026-11-16 (local). Nothing in any repository was edited, staged or committed; no VM, API calls or test suites.

## 0. What was reviewed, at which HEAD

The thesis branch `docs/thesis` moved twice during the review. Each finding is tagged with the HEAD it was checked at.

| HEAD | Time (+0700) | Change | PDF reviewed | How seen |
|---|---|---|---|---|
| `a7d03a7` | 15 Nov 23:52 | condensed report (30 pp) + extended | the brief's `project-report-condensed.pdf` (timestamp 23:52, matched this HEAD) | all 30 pages viewed as images; text extracted |
| `b62346d` | 16 Nov 00:04 | "expand condensed report to 37 pages": strategy table, safety-invariant table, prompt listing, scene layouts and frames, interception table, replay table, safety-by-study table, bench + shadow + exploratory sections, three demo stills, physical frames, two new references, new abstract | recompiled scratch copy `src_b62346d/cond_b62346d.pdf` (37 pp) | pages 4–37 viewed as images (pp. 1–3 title, copyright, acknowledgements unchanged in the diff and viewed at `a7d03a7`) |
| `326a732` | 16 Nov 01:14 | "hide evidence tags in both reports": `ev()` now prints nothing (a weak space); fig-source lines removed; Appendix A and contribution 4 reworded | recompiled `cond_326a732.pdf` (37 pp) and `ext_326a732.pdf` (141 pp) | text extracted and checked; page structure compared by per-page density with `b62346d` (identical page breaks); not re-viewed image by image |

**Final HEAD at hand-back: `326a732`** (working tree had uncommitted edits in `chapters/04-implementation.typ`, `chapters/05-methodology.typ`, `lib.typ` at the time of the second check, i.e. another session is still editing). Unless marked, page numbers below are the printed page numbers of `b62346d`/`326a732` (identical layout); `a7d03a7` numbers are marked "(a7d)".

The brief's PDF (`a7d03a7`) is **stale**: it is not what would be handed in now.

## 1. Verdict

Not ready to hand in as is, but close. The substance is sound and honest: every headline number I checked against the primary reports matches, the owner's caveats are almost all present at full strength, RQ1–RQ3 are answered by number, the scope change is disclosed in the right words, and the related-work comparison now exists in the Discussion. Four things must change first: (1) the latest commit (`326a732`) that hides the evidence tags **fuses words together** wherever a tag sat mid-sentence ("modelsarticulated", "exemptionan escort", "obstaclesOctober", "endingand", "(Table 11)and"), on top of the old swallowed semicolons — this is visible on pages 8, 9, 23, 24/25 and must be fixed in `lib.typ` or the sources; (2) the new abstract's hardware clause ("the chain ran end to end in four staged arrangements") drops the `robot_3 FAILED` outcome and weakens the selection disclosure, reversing an earlier MUST fix; (3) the "79 of 79" head-on figure is stated next to a table whose runs sum to 78, without saying it counts gate-on runs of all models; (4) the RQ2 answer lost its "exploratory five-episode pilots" limit (owner rule: evidence and limits in the answer itself). The rest are SHOULD items: undefined terms, three compressed sentences, one ambiguous figure caption, layout gaps and figure order.

## 2. Number audit

Method: every number in the condensed text at `b62346d`/`326a732` was extracted (abstract, prose, all 15 tables, 10 figures, listing, RQ answers) and compared with the Extended Report (`a7d03a7` PDF; `326a732` text) and, for all headline, abstract, RQ-answer and results-table numbers, with the primary report (or, where noted, its Evidence Index row only). About 330 numeric values checked. "OK" = same value in condensed, extended and primary.

### 2.1 Mismatches and population problems

| # | Page | Condensed | Extended | Primary | Problem |
|---|---|---|---|---|---|
| N1 | 17–18, 27 (RQ3), abstract implied | "grounded yielder was correct in 79 of 79 runs, and in 37 the gate overturned the model's pick"; Table 11 rows 23+12+30+13 = **78** runs | same (Table 24) | re-score report: 92 units incl. "8 other models, west, 14"; "with the swap gate on, the grounded yielder was correct in 79/79 runs, and 37 of those 79 were M2 picks the gate overturned" | **Denominator mixes populations.** 79 = gate-on runs over all models including the 14 "other model" runs not in Table 11; the table shows only gpt-4o and ER-2. A reader summing the table gets 78 and cannot reconcile. Value correct, qualifier missing. |
| N2 | 23 | "one sustained robot-obstacle contact (the five-robot take), one brief graze and 42 bundles clear" | "one bundle with a sustained contact (which also contains a 3.79 mm brief graze), one bundle with a brief graze, and 42 bundles clear" | gt-contact report / row 6.12: two brief grazes (3.79 mm; E30 0.97 mm) | Bundle-level count is right, but "one brief graze" undercounts grazes (two). Qualifier "bundle" lost. |
| N3 | 21 Fig. 6 vs caption | figure box 3: "commanded back-out distances (0.781 m, 0.971 m)"; caption: "back-out costs 0.981 m (`robot_3`) and 0.971 m (`robot_4`) ... (commanded distances; the reason was not established)" | Appendix B caption: "the distances in the back-out phases are commanded distances, and the reason for the difference was not established" | demo report 7.2 check 7: chi robot_4 0.971, robot_3 0.981 (cost = recede distance); GT robot_3 backed ~0.79 m | Compression made the caption say 0.981/0.971 **are** commanded distances, contradicting the 0.781 in the figure above it. |
| N4 | 7 | "nose to nose two chassis touch at about 0.076 m [3.25]" | cites [6.01] | row 3.25 has no 0.076 (it is the 0.20 m floor derivation); 0.076 m is in the demo report (lines 80, 886) | Wrong tag (now hidden, but `check.sh` traceability is wrong). Also the 0.18 m gate (p. 12, Table 15) is never explained as "footprint contact separation", so 0.076 vs 0.18 looks contradictory to a reader. |
| N5 | 8 | "gpt-4o-2024-08-06 ran in earlier head-on runs and offline replays" | same | row 6.49: "October gpt-4o intersection pilot 13" analyses, live | Omits the live October gpt-4o intersection pilot that supplies a column of Table 12 ("October gpt-4o pilot (13)"). The threats bullet "other models ran only offline or earlier" is consistent; the implementation sentence is not. |
| N6 | 18 | "18 dispatches in four episodes; where the effect can be judged, neither episode resolved" | "in e09 and the gpt-4o pilot, neither resolved" | row 6.49 | "neither" has no two-item antecedent after "four episodes". |
| N7 | 14 | "The unresolved episode began with an off-pattern model choice that left all four robots standing for 120.1 s" | — | IB10 run-1 report: trigger 1 `yield` (m3_default); trigger 2 two-robot `junction_clear`, after which all four stood still 120.1 s (120.1–240.2 s) | Value OK; "began with" is wrong — the standstill followed the second trigger. |
| N8 | 2, 26 (contribution 4) | "every scored criterion was fixed before its data" | "Every scored criterion was fixed before its data were collected, and post hoc analyses are labelled as such" | row 1.05 "pilots excluded" | Qualifier cut; contradicted by Table 4 rows "No (post hoc)" and "Specification only". |
| N9 | iv (abstract) | "the chain ran end to end in four staged arrangements" | `a7d03a7` abstract: "the kept run of each of four staged arrangements ended in a bounded back-out, completed by all but one robot" | README §7: E "3 completed, robot 3 failed — Partial execution success" | Outcome cut; "ran end to end" overstates scenario E (see caveat audit). |

No other mismatch found. No number appears in the condensed report that is absent from both the Extended Report and the primary sources, except the new Table 15 values 0.3101 m (validation take) and 0.374 m (convoy rerun), which I verified directly in the primaries (validation report line 82/152; demo report line 1207, "exempt").

### 2.2 Verified OK (headline groups)

- **Intersection run 1** (Table 5; abstract; 1.4; RQ2): 4/5 vs 0/5; 16/20 vs 0/20; 112.9, 115.5, 116.5, 116.6 s, e09 censored; off all censored; min 0.2633 (e09) / 0.2856 m; 0 floor stops; repaired 4, grounder default 1, accepted 0; 120.1 s. Primary: v7a `2026-11-13-ib10-live-resolution-results.md` lines 19, 65–87, 115. OK.
- **Intersection run 2** (Table 6; RQ2): live 5/5 (4/4 without first check episode), 20/20, 114.3–116.9 s mean 115.96; scripted 4/4 valid, 16/16, mean 117.80; after re-run 5/5, 20/20, 115.5, 118.1, 118.5, 118.6, 118.6 mean 117.86; 0.3008 / 0.2965 m; 0 floor stops. Primary v7d `2026-11-14-ib10-safety-default-arm-results.md` lines 20, 80–101, 359, 387–394. OK.
- **Registered pilot** (Table 7; RQ1; abstract): 0/10; 16/125 vs 12/125; 0.128 / 0.096, +0.032 [−0.008, +0.080]; 323.4 / 354.9 s, −31.5 [−71.6, −0.6]; recall 0.818 (9 of 11); 0 FP in 26; type 0.778; F1 0.915; off 0 of 10 conflicts; dispatched/withheld 5/4, 2/2, 2/3, 1/4, 2/1 (= erratum 5/2/2/1/2 and 4/2/3/4/1); GT min 0.225–0.424 m; "excludes zero by 0.6 s". Primary v7j `2026-10-21-s1b-confirmatory-tranche1.md` lines 25, 239–243, 349–378. OK. (Table 7 "PASS 5/5" per arm = primary "PASS 10/10".)
- **Failure-cause** (Table 8; text p. 16): every cell of Table 8 equals reconciliation §4.1; undetermined 12/18 (2/8, 10/10), 13/33, 2/4; class agreement 53/55 final, 35/55 round 1; 3 of 5 final disagreements by one reader. Primary v7q `2026-11-15-failure-cause-reconciliation.md` §2, §4.1. OK.
- **Interception** (Table 9, new at `b62346d`): legs 3/47/7 (=57); reverse 29 (9 J, 15 F, 5 UT); stall 7; escort 1/1; any 31 (10/15/6) and 3 (all J); no linked leg 5/8, 19/33, 1/4; 15 of 29 false positives. Primary §7.2, §7.3. OK. ("no mechanism applies" = the report's "no linked leg" column, correct.)
- **Head-on re-score** (Table 11): all 16 cells equal re-score table rows; 37 overturned. OK apart from N1.
- **Replays** (Table 10): 85/96; 129/144; 30/48; 146/146, 46/96, 76/96; 50/96. Evidence rows 6.09, 6.11 (primaries not opened; index-checked only).
- **Plan influence** (Table 12): 41/39; 24/13/4; accepted 2 (0 of 20 junction_clear)/11/1 = 14; dispatched as written 2/6/0 = 8; 0 of 22/13/4 = 39; decision fields 5/13 = 18 in 4 episodes; 10 of 33 reverse legs; 6→5, 2→1. Rows 6.02, 6.49, 6.51 (plan-dispatch report v7r not opened beyond the index; 10/33 and 6→5 consistent across rows 6.51 and 6.80).
- **Demonstration campaign** (Tables 13, 14; abstract; 7.1): 13 valid takes (5/6/1/1); 3 bring-up aborts; 69 of 69 valid (9/50/2/8; demo report "Rev 13: 69 of 69", wrap-up R15); 6 of 65 recorded (1/3/2) with "first twelve takes"; 5 of 61 corrected (1/2/2); convoy 20 repaired, 25 grounder default; five-robot 1 repaired, 5 grounder default; changed behaviour 1 (intersection only); take 5 0.010 m margin vs 0.15; 32.9 s, 41.9 s, 95.1–146.4 s; convoy 33 later proposals as 8 s waits; head-on 0.70 vs 1.08 m; five-robot 1 of 5, 6 refused, 4526 of 4534. Demo report + rows 6.37–6.45, 6.84. OK. The 69 (with rerun) vs 65/61 (first twelve takes) populations are kept apart in Table 14 and the abstract no longer quotes them.
- **Safety** (6.6, Table 15): 44 bundles, 82.1 mm, 2.21 s, 0.2176 m, 0.276/0.370 m, 0.374 m (exempt), 0.3101 m, 6001 rows. OK apart from N2.
- **Bench / shadow** (6.7, new): 137 positives, 0.496→0.832, 0.620→0.934, 168/168, 181/181, 0.949; 7 episodes, 50 blocks, 12 analyses, 14/33/3. Rows 6.46, 6.47. OK.
- **Hardware** (6.9): A 4/4, C 3/3 (robot 4 excluded), D 4/4, E 3 COMPLETED + robot_3 FAILED; two parse failures; priority_override/reroute attempts excluded; 0.50 m, 0.08 m/s (row 4.41, team notes not seen). README md5 26718adb… lines 22–208 read. OK.
- **System constants**: 0.45 m, 0.2 m/s, 0.6 m, 0.20 m floor, 0.18 m gate, 12 s / 0.10 m, ≤ 4 edits, 20–50 Hz, 0.5–2 Hz, eight strategies, v3.4 prompt. Rows 1.02, 1.04, 3.01, 3.12, 3.20, 3.22. OK.

## 3. Caveat audit (owner decisions), at `326a732`

| Owner decision | Present? | Where | Strength |
|---|---|---|---|
| ~35 pages | yes | 37 PDF pages (5 front + 32) | full |
| RQ1–RQ3 answered by number with evidence and limits | yes | 7.4, p. 27 | RQ1, RQ3 full; **RQ2 weakened**: "both are exploratory five-episode pilots" (present in Extended 8.1) cut from the answer; RQ3 answer lacks the ascending-listing limit (stated p. 2, p. 13) |
| Two further questions untested → Future Work; narrowing after the experiments, part of no registered design, changes no result; never "not preregistered" | yes | 1.2 "Scope change", p. 1; 7.5 p. 27 | full, wording matches |
| Exploratory runs touching them mentioned, not evidence | yes | p. 1 | full |
| "coordination layer", "the authors" | yes | throughout; "the authors decided" p. 10 | full ("separate owners" p. 5 refers to modules, harmless) |
| No "collision-free" | yes | only as "this report never claims collision-free operation" p. 23 | full |
| Safety evidence = robot-pair centre distance + offline geometric recompute | yes | abstract, 6.6, 7.1 | full in condensed. **Extended still says "robot-pair centre distance only"** (contribution 3, Ch. 7, Fig. 14 caption) |
| Intersection VLM-order take = execution example, not improved performance | yes | p. 20, Fig. 6 caption | full |
| Demonstration takes illustrative, no rates | yes | 6.5, Tables 13–14 | full |
| Registered five-robot pilot 0 of 10 stands, never pooled | yes | abstract, 6.2, p. 16 "The registered pilot's 0 of 10 stands" | full |
| Failure-cause: no dominant cause, strata never pooled | yes | p. 16, Tables 8–9 | full |
| RQ2 "no added value over a scripted strategy was shown", not softened | yes | 1.4, 7.4 | full; 7.2 "the deterministic layer alone accounts for the clearing" is stronger than "credited to the trigger and the grounder" (see §4) |
| Convoy: five unresolved, one resolved with the queued-robot hold = grounder result; yielder correction did not fire, untested live | yes | p. 21, Table 13, RQ2 | full |
| Reverse guard + stall abort "validated live once in a scripted safety test"; escort guard offline only; none part of an evaluated run | yes | p. 9, p. 23, 7.3 | full (abstract no longer mentions them — fine) |
| Hardware: team notes outside repo; code not in history; never pooled; selection disclosed (priority_override/reroute → waits/timed-out backups; two unparsable replies) | body yes (p. 9, p. 25) | **abstract weakened**: "ran end to end in four staged arrangements (illustrative; earlier attempts with other strategies excluded)" — drops robot_3 FAILED, drops what the excluded attempts produced, drops the parse failures |
| LLM-agent raters, no human check | yes | 5.3 p. 12, 7.3 | full |
| No AI-use statement | yes (none) | — | as ruled |

Positive sentences vs their Extended caveat:
- Abstract "In head-on scenes the grounder's feasibility gate, not the model, made the yielder correct" — Extended adds "two-robot" and "decision-level analyses, the first post hoc". Lost in the abstract (kept in 6.3 and 7.4).
- Abstract "its plan was rarely accepted unchanged" — fine; but the "first twelve takes" population and "illustrative" are now carried only by "illustrative demonstration takes": OK.
- 1.4 "0 of 39 traced live four-robot analyses" — Extended: "that pass its fidelity gate"; "post hoc, partly inferred" lost here (kept in 6.4).
- 7.1 "ER-2 answered validly in all 69 campaign analyses" — "second-stage calls not counted" lost (kept in Table 14 caption).
- 7.2 Garg comparison — "deterministic layer alone accounts for the clearing" without "in five near-repeat episodes, given `junction_clear` for all four robots".
- Conclusion — caveats present in the same paragraph. OK.

## 4. Compression errors (quote, page, fix)

1. p. 8–9 (all HEADs; worse at `326a732`): "a scope fix for the safety exemption[6.07] an escort obstacle guard … obstacle[6.13] an execution-side stall abort … movement[6.18] geometric contact logging[6.12] a queued-robot hold … scene[6.19] and a convoy yielder correction" → at `326a732` renders "safety exemptionan escort … obstaclean execution-side … movementgeometric contact logginga queued-robot hold … sceneand a convoy". Source `short/s04-implementation.typ:52` uses `#ev("…");` (semicolon swallowed by Typst).
2. p. 23: "the safety monitor ignores obstacles [6.43] October reverses" → at `326a732` "ignores obstaclesOctober reverses" (`s06-results.typ:237`).
3. p. 8: "TurtleBot3 Burger modelsarticulated by Isaac Sim's Newton backend" (`326a732` only; `s04:5`).
4. p. 24–25: "the `robot_1` preference (Table 11)and take 5's order"; "version 1's `<think>` endingand none of 146" (`326a732` only; `s06:264, 266`).
5. Abstract hardware clause (N9) — outcome and selection detail cut.
6. Abstract "In head-on scenes …" — "two-robot", "decision-level, post hoc" cut.
7. p. 2 contribution 4 (N8) — "post hoc analyses are labelled as such" cut; now reads as if no analysis were post hoc.
8. p. 18 (N6) "neither episode resolved" — antecedent lost.
9. p. 21 Fig. 6 caption (N3) — "(commanded distances; the reason was not established)".
10. p. 14 (N7) "began with an off-pattern model choice".
11. p. 27 RQ2 — "both are exploratory five-episode pilots" cut from the answer; "The registered comparator, a per-type policy table, never ran" became "The registered comparator never ran" (the comparator is named only on p. 2).
12. p. 26 7.2 "which shows that at the intersection the deterministic layer alone accounts for the clearing" — stronger than the evidence (trigger + grounder, with the strategy handed to the scripted arm; five near-repeat episodes).
13. p. 8 (N5) gpt-4o "earlier head-on runs and offline replays" omits the October live intersection pilot.
14. p. 23 (N2) "one brief graze" — bundle level, two grazes.
No case found of "validated" without "once, scripted", of a default-off mechanism described as evaluated, or of a replay described as live.

## 5. Self-containedness

**Evidence tags.** At `a7d03a7`/`b62346d` the bracketed ids were first used on p. 1 ([1.02]) but explained only in Appendix A (p. 25/32) and in passing in contribution 4. All 87 (a7d) / 95 (b623) distinct ids used in the condensed sources resolve to rows of `evidence/*.typ`, i.e. to Extended Report Appendix E (verified by `comm`). At `326a732` tags are hidden: the condensed report now says "Every number in this report is traced to a source" (p. 2, p. 32) but gives the reader **no way to find the row** for a claim (the Extended Report's text no longer prints ids either; Appendix E is an id-keyed list). Figure "Source:" lines are gone too. If the owner wants hidden tags, the sentence should say the index is organised by chapter and claim, or the tags should be printed in the Extended Report at least.

**Pointers** (checked against the extended PDF as compiled at `a7d03a7` and `326a732`): Extended Report Chapter 2 (related work) ✓; Chapter 5 (methods) ✓; Chapter 6 (results, contributing causes, sensitivity) ✓; Chapters 7–8 ✓; Appendix A sources ✓, B trace/stills/videos ✓, C prompts ✓, D testbed ✓, E Evidence Index ✓, F two detail tables ✓. Internal: Sections 1.2, 4, 5.4, 6.4, 7.4, 7.5, A ✓. "Evidence Index (Section A)" in the Outline (p. 2) is ambiguous — the index is in the Extended Report's Appendix E; Section A only describes it.

**Undefined or late-defined terms** (page of first use, `b62346d` numbering):
- escort / escort segment (p. 7; Table 2 lists "optional escort" but never says what it is) — central to the only confirmed contact.
- plan channel (p. 7), proposed_plan grammar.
- fidelity gate (Table 4 p. 10; p. 18).
- first check episode (p. 14, Table 6).
- take labels "grounder-default resolution", "grounder-corrected", "VLM-driven execution", "limitation demonstration" (Table 13 p. 19, Fig. 6) — rule never stated.
- seed pair, seed position (Table 4, Table 13), horizon (p. 12, Table 5/7: value not given), censored.
- throughput at the common window, mean delay lower bound, detection recall, type accuracy, involved-set F1 (Table 7).
- GT (Tables 5–7, 15; "ground-truth" is spelled out on p. 12 but the abbreviation is never introduced).
- context code N0, "parked robots excluded, not units" (Table 8).
- bundle (p. 23, Table 4).
- second-stage calls (Table 14).
- "third design" (p. 2) — only the first registered design is introduced.
- "plan-order switch" (p. 19) — described on p. 1 as "one opt-in exception" but not named.
- Table 12 columns "October gpt-4o pilot (13)" and "Two head-on pairs, ER-2 (4)" — neither study appears in Table 4.
- latch (p. 21 "the four latched") — defined implicitly as the 0.45 m hold (Table 3) — acceptable.
- ArUco, Zenoh, OpenCR (keywords, p. 9) — acceptable for a CS report but an abbreviation list would help.

**Studies introduced without a result.** At `b62346d` the bench, shadow run and replays gained results (6.7, Table 10). Still without a result in the condensed report: "Earlier recorded head-on run, 30 Sep 2026" (Table 4) and "Plan-order and convoy held-robot prompt checks" (Table 4: "22 answers per convoy condition", result 0 of 22 never given).

## 6. Research questions (`326a732`)

| RQ | Stated | Answered by number | Matches results / abstract | Evidence + limits in answer |
|---|---|---|---|---|
| RQ1 | 1.2 p. 1 (post-trigger scope note) | 7.4 p. 27: 9 of 11, 0 FP in 26, 0.778, 0.915 | = Table 7; abstract gives no RQ1 numbers (says only nothing; the `a7d03a7` abstract had "classification was scored only after the stall trigger", now cut) | yes: one scene, five seed pairs, stall trigger + VLM, single label, blocker kind not evaluated |
| RQ2 | p. 1 | 4 of 5 vs 0 of 5; 4/4, 5/5; 0 of 10; convoy 5 + 1 | = 6.1, Tables 5–6, 13; = abstract and 1.4 | partly: "registered comparator never ran" present; **"exploratory five-episode pilots" missing** |
| RQ3 | p. 1 | 79 of 79, 37 overturned; replays; one near-tie order | = 6.3, Table 11 (see N1), Fig. 6 | "negative at the decision level" ✓; listing-order limit not in the answer |

Scope-change disclosure: p. 1, full substance of the owner wording; no trace of RQ4/RQ5 as main questions (grep: none).

## 7. Structure and balance (`326a732`, printed pages)

Front matter 5 (title, copyright, acknowledgements, abstract, contents); Ch. 1 pp. 1–2 (2); Ch. 2 pp. 3–4 (2); Ch. 3 pp. 5–7 (3); Ch. 4 pp. 8–9 (1.5); Ch. 5 pp. 10–13 (4); Ch. 6 pp. 14–25 (12); Ch. 7 pp. 26–28 (2.2); References pp. 29–31 (2.1); Appendix A p. 32 (0.5). 37 PDF pages, within "about 35".

Present: problem statement, RQs, contributions, related work with a comparison table and a Discussion subsection (7.2), method outline (now with scene layouts, strategy table, prompt excerpt), threats, limitations, future work, data availability. Missing or thin: (a) any cost/latency figure for the model (the obvious "is the VLM worth it" question; spend $0.2127 pilot, $0.056 run 2, ER-2 latency ~7.7 s exist in the sources); (b) measure definitions (§5); (c) an abbreviation list.

7.2 check against Extended Ch. 2: Valmeekam (planner repairs → much of final plan is the planner's, by edit distance) ✓; Kambhampati LLM-Modulo ✓; Garg 2024/2026 (VLM on a stall, top-view image, safe low-level controller) ✓; Zheng option-ID bias ✓. Not discussed although Table 1 places them closest to the claimed gap: Physical Agentic AI (per-dispatch enforcement gate; Extended Ch. 2 says it "reports how many faulted steps the gate stops") and Dwedar et al. (reachability gate). The Gap paragraph ("none reports, per dispatch, how the model's plan fared …") needs one sentence distinguishing gate stop counts from a per-dispatch audit label plus a no-plan re-grounding; the Extended Ch. 2 gap also qualified the plan-checking work as "symbolic single-robot tasks", which the condensed gap dropped (and which does not fit Physical Agentic AI's robot crew anyway).

Contribution statement: abstract and conclusion both name the measurement method (plan-audit labels checked against dispatch, re-grounding without the plan, scripted default-plan arm); the introduction lists five contributions with this as no. 2. Consistent.

Not worth its space: Copyright page boilerplate (if not required by the template); near-empty p. 28 and p. 31.

## 8. Presentation as seen

Viewed at `a7d03a7` (all 30 pp.) and `b62346d` (pp. 4–37):
- **Fused words / lost semicolons** (§4 items 1–4) — p. 8, 9, 23, 24, 25. MUST.
- **Figure order** (`b62346d`): Figure 5 (camera frames) prints on p. 11 before Figures 3 and 4 (pp. 12–13); the text cites "Figure 3 and Figure 4 … and Figure 5". `placement: auto` floats reordered them.
- **Figure 5** three panels at one-third width: robot labels and ArUco ids unreadable at print size; caption carries the identification.
- **Table 8** header: "ExploratoryExploratory" — the two column heads touch with no gap (same in the extended Table 19).
- **Fig. 6**: grey footnote line inside the figure in ~6 pt type; legible on screen, marginal in print.
- Large empty areas: p. 9 (~55 % blank, end of Ch. 4), p. 15 (~40 %), p. 20 (~40 %), p. 25 (~35 %), p. 28 (~85 %, three bullets), p. 31 (~95 %, one reference). The `a7d03a7` 2-line p. 7 problem is fixed.
- Tables 1, 4 break across pages with repeated headers ✓; no column one word wide (Table 12 "Two head-on pairs, ER-2 (4)" is narrow, 4 lines, acceptable). No overprinting seen in the condensed report.
- Page numbering i–v, 1–32 ✓; title "Project Report" ✓; abstract ~250 words, one page ✓; contents ✓; no list of figures/tables (acceptable).
- **References**: 33 entries at `b62346d` (31 + Dresner & Stone 2008, Okumura et al. 2022; both bibliographic data correct as far as I know). Earlier ambiguous pairs resolved (one Yang, one Zhang, one Chen 2023; Liu 2024/2026 and Garg 2024/2026 and Macenski 2020/2022 differ by year). Every in-text citation resolves (APA style only prints cited entries). Minor: "Berg, J. van den" with in-text "Berg et al." (APA: van den Berg); Valmeekam title "Models : A" (space before colon); Garg 2026 is a project web page with no venue or arXiv id; arXiv ids 2608.22657, 2609.19315, 2609.27816 and Google 2026 not verifiable offline.
- Language: otherwise clean; Table 4 caption "Studies in this report, "Registered" means …" comma splice.

## 9. Extended Report sanity

- Compiles: 142 pp. at `a7d03a7` (the brief's PDF), 141 pp. at `326a732` (scratch compile).
- Appendices A sources (+ intro), B trace/stills/videos, C prompts (C.1–C.3), D testbed (D.1–D.3), E Evidence Index, F detail tables (F.1–F.2) exist as described.
- Not applied, as the writer said: no related-work subsection in the Discussion (Ch. 7 = 7.1–7.4) — confirmed. Figure 14 (Appendix B, p. 79) caption overprints the footer rule and "Page 79" — confirmed still present. Table 20 header: no overprint seen at `a7d03a7` (p. 50–51, "Disagree-ments" hyphenated) — appears already fine. Runtimes by commit: no such table found.
- Same defects as the condensed: lost semicolon "[6.48] earlier attempts" (`chapters/06-results.typ:414`) → at `326a732` "reverseearlier attempts"; at `326a732` ~18 further fused spots, e.g. "no navigation goals(Section 4.8)", "temporary_wait(Table 3)", "under the latch(Figure 4)", "deterministic scene(Figure 5, Figure 6)", "260 sim-s(Figure 7)", "300 sim-s(Figure 8)", "confirmatory episode(Table 13)", "VLM plus grounding(Section 1.2)", "arrived(Figure 9; …)".
- **Contradictions with the condensed report** (facts/wording rules, not style): Extended contribution 3, Ch. 7 ("Safety evidence is narrow … centre distance only") and Fig. 14 caption say safety evidence is "robot-pair (centre) distance only", the condensed says "plus an offline geometric recompute" (owner wording). The 79-of-79 population issue (N1) is shared. No numeric contradiction found.

## 10. Prioritised fix list (for `326a732`)

### MUST FIX before submission
1. **Fused words from hidden tags** (pp. 8, 9, 23, 24, 25; Extended ~20 places). Cause: `ev()` returns `h(0pt, weak: true)`, which eats the spaces on both sides, and `#ev("…");` eats the semicolon. Fix one of: (a) make hidden `ev` return `none` and write tags glued to the preceding word (`models#ev("4.05") articulated`, `exemption#ev("6.07")\; an`), or (b) keep the weak space but replace every mid-sentence `word #ev(…) word` with `word#ev(…) word` and every `#ev(…);` with `#ev(…)\;`. Then grep the compiled text for `[a-z](an|a|and|the|October|earlier|articulated|geometric) ` and `[a-z]\((Table|Figure|Section)`. Condensed spots: `s04:5`, `s04:52` (×5), `s06:237`, `s06:264`, `s06:266`.
2. **Abstract hardware clause** (p. iv): replace with "On physical TurtleBot3 robots, in the kept run of each of four staged arrangements the model chose a bounded back-out, completed by all robots but one; earlier attempts in which it chose `priority_override` or `reroute`, which gave only waits or timed-out backups, and two unparsable replies were not kept (illustrative, no navigation goals)."
3. **79 of 79** (p. 17–18, p. 27; Extended 6.5, 8.1): "the grounded yielder was correct in all 79 runs with the gate on (gpt-4o, ER-2 and eight other models; Table 11 shows only gpt-4o and ER-2), and in 37 of them the gate overturned the model's pick." Or add the "8 other models, west, 14" row to Table 11.
4. **RQ2 answer** (p. 27): after "…re-grounds to that plan" add "; both are exploratory five-episode pilots on one scene". Optionally "The registered comparator, a per-type policy table, never ran."

### SHOULD FIX
5. Contribution 4 (p. 2): "every scored criterion of the registered studies was fixed before its data, and post hoc analyses are labelled as such (Table 4)".
6. Abstract head-on sentence: "In two-robot head-on scenes the grounder's feasibility gate, not the model, made the yielder correct (post hoc, decision-level)."
7. Fig. 6 caption (p. 21): "back-out costs 0.981 m (`robot_3`) and 0.971 m (`robot_4`) differ by 0.010 m, within the verifier's 0.15 m tolerance; the commanded back-out distances in box 3 (0.781 m, 0.971 m) differ from these costs for `robot_3`, for a reason not established."
8. p. 18: "…in 18 dispatches in four episodes; where the effect can be judged (intersection run 1's e09 and the October gpt-4o pilot), neither resolved."
9. p. 14: "In the unresolved episode (e09) the model's second answer, a two-robot `junction_clear`, left all four robots standing for 120.1 s."
10. 7.2 (p. 26): "…shows that at the intersection, given `junction_clear` for all four robots, the trigger and the grounder's default plan account for the clearing in five near-repeat episodes…". Add one sentence on Physical Agentic AI and Dwedar et al.: they gate each step and count stops; neither reports a per-dispatch label of the model's plan together with a re-grounding without it.
11. Evidence traceability with hidden tags (p. 2, p. 32): either print tags in the Extended Report, or say how a reader finds the row (by chapter and claim). Fix the wrong tag for 0.076 m (`s03`: [3.25] → [6.01]) and explain 0.18 m as the footprint contact separation used as the gate (p. 7 or p. 12).
12. Define, in one short paragraph in 5.2 or a glossary box: escort, plan channel, fidelity gate, first check episode, the four take labels, seed pair/position, horizon and censoring, throughput at the common window, mean delay lower bound, detection recall, type accuracy, involved-set F1, GT, N0, bundle, second-stage call; name the plan-order switch on p. 1; introduce the third design on p. 2.
13. p. 8: "gpt-4o-2024-08-06 ran in earlier head-on runs, an October intersection pilot (Table 12) and offline replays"; add the October gpt-4o intersection pilot and the four-robot two-head-on-pairs scene to Table 4 or footnote Table 12.
14. Figure order: make Figures 3–5 non-floating or cite Figure 5 first; enlarge Figure 5 to two rows or drop to two panels.
15. Table 8 header: shorten to "Pilots, horizon" / "Pilots, early stop" (the column group already says exploratory) or allow hyphenation.
16. p. 23: "one other bundle with a brief graze (two grazes in all, both within noise)".
17. Add one sentence on model cost and latency (e.g. registered pilot spend $0.21; run 2 live arm $0.056; ER-2 latency about 7.7 s per call in take 5).
18. Extended: replace "robot-pair (centre) distance only" in contribution 3, Ch. 7 and Fig. 14 caption with the owner wording; fix the Fig. 14 caption/footer overprint.

### NICE TO HAVE
- Report the 30 Sep head-on run and the convoy held-robot check (0 of 22) in one line each, or drop them from Table 4.
- Fill or tighten pp. 9, 15, 20, 25, 28, 31 (e.g. `placement: auto` on Tables 7, 13; move the last three Future Work bullets up).
- Table 4 caption comma splice; "Berg" → "van den Berg"; "Models : A" spacing; Garg 2026 venue.
- Abstract: one RQ1 number (9 of 11 conflicts detected, post-trigger).
- Outline "Evidence Index (Section A)" → "(Appendix A describes it; the index is Appendix E of the Extended Report)".
- "Six modules with separate owners" → "with separate responsibilities".
- Table 11 caption "not pre-registered" → "post hoc" (consistent with Table 4; avoids the phrase the owner dislikes).

### Likely examiner questions

| # | Question | Answered in condensed? |
|---|---|---|
| 1 | If the scripted default plan clears the intersection, what does the VLM add, and at what cost and latency? | Partly: 6.1, 7.1, 7.4 (no added value shown); cost/latency not given |
| 2 | How do you compare with Garg et al.? | Yes, 7.2 p. 26 |
| 3 | Why no classical coordinator live? | States it (7.3, p. 2), not why |
| 4 | Why list robots in ascending order when the slot bias was known? | States it (p. 2, 5.4, 6.8), not why |
| 5 | Does the VLM use the image at all? | Yes, negatively: 6.7 ("the gain is the format's, without vision"), 6.8, 7.1 |
| 6 | Why did the five-robot pilot complete nothing even with the layer off? | Partly: failure causes p. 16, Table 8; no density argument |
| 7 | 79 of 79 — where is the 79th run in Table 11? | No (N1) |
| 8 | What exactly ran on the robots, and why a different model (flash-lite)? | Code not in history (p. 9); why flash-lite not answered |
| 9 | Can I reproduce this? | Appendix A: not publicly; answered negatively |
| 10 | Who rated the failure causes, and was any human check done? | Yes, p. 12 and 7.3 |

## 11. Could not check
- Primary reports for the swapped-ID/JSON-only/improved-annotation replays, plan-influence trace, plan-dispatch recomputation (v7r), scripted safety tests (v7s), convoy yielder report (v7t), bench and shadow run: checked against the Evidence Index rows only (inferred consistent).
- Team testbed notes (row 4.41) — outside any repository.
- Strategy table (Table 2) against `command_grounder.py`; intersection geometry (1.2 m aisle) against the scene file.
- `326a732` layout was not re-viewed image by image; page breaks inferred identical to `b62346d` from per-page text density.
- Web verification of references (arXiv ids dated 2026).
- Whether the uncommitted working-tree edits seen at the final check change any of the above.
