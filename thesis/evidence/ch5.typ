// Evidence rows for chapter 5: one evidence call per number, id = chapter.NN.
#import "../lib.typ": *

#evidence("5.01", [Five research questions RQ1 to RQ5, renamed from H1 to H5; RQ1 scope note (post-trigger classification only).], [`569d95c:docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` ("Research questions (RQ1-RQ5, thesis skeleton)")])

#evidence("5.02", [prereg-v3 registers the Arm A minus Arm B comparison as CI estimation of the delta per regime; Goldilocks expectation recorded as interpretation, not a directional hypothesis.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (R3.6a item 4; A33(7))])

#evidence("5.03", [Tranche 1 adds no hypothesis and no threshold; 5 seeds (positions 1 to 5) x 2 arms = 10 episodes; pilots E6 to E26 excluded.], [`75a499c:docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` (sections 1.1, 1.3, 1.5)])

#evidence("5.04", [Registered confirmatory n is R = 20 per arm from the first 20 seeds; owner decided on 2026-11-13 to skip prereg-v3 tranche 2 and run IB10; tranche 1 reported as pilot.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A32, quoting the v3 scene design line 155); `50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (section 1); `cbe3dcf:docs/reports/2026-11-13-thesis-evidence-register.md` (Five Robots, tranche-1 row)])

#evidence("5.05", [prereg-v1 tag on 2026-09-30, freezing the research design (rev 9.5) and amendments A1 to A10.], [tag `prereg-v1` = `569d95c`; `569d95c:docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md` (Rev 25)])

#evidence("5.06", [v1 Arm B = classical reasoner (per-type policy table, FCFS + commitment tiebreak); v1 amendments A2 (random seeded presentation order), A3 (swap gate, pre-gate RQ3 scoring), A4 (position-verified arrival, 0.35 m tolerance), A5 (distance channels, 0.45 m).], [`569d95c:docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md` (A2-A5); `569d95c:docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` (Experimental arms)])

#evidence("5.07", [prereg-v2 design dated 2026-09-30, revisions 1 to 6: junction_clear composite, proposed_plan propose-verify channel, provenance, statistics block (McNemar, Wilson, KM + RMST, bootstrap).], [`4e285a0:docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (revision history; "What v2 measures that v1 cannot")])

#evidence("5.08", [prereg-v3 design prepared 2026-10-06; discipline: every scored criterion registered before collection, pilots excluded; fixed stack is ground truth, outcomes not assumed to transfer.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (header; Discipline items 2-3)])

#evidence("5.09", [v3 A8/A9: IB10 release-lane remedy frozen, pull-off 0.33 m; 0.20 m floor ruled a push-limiter backstop, not a contact preventer.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A8, A9)])

#evidence("5.10", [v3 A15(iii): latch-on-pass registered as S1b's conflict class; opposing robots latched at the 0.45 m latch.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A15)])

#evidence("5.11", [v3 A32 (config freeze), A33 (measures, REGISTERED vs PROPOSAL), A34 (R6-R11, all proposals ruled at default, Arm B = Layer-2-off), A35 (reasoning_enabled), A36 (outcome, GPU wall-clock deviation, tranche-2 decision open).], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A32-A36, revision history)])

#evidence("5.12", [No confirmatory v1 or v2 data reported; "No confirmatory-grade evidence remains". Reason for the v1/v2 collection status not confirmed from a committed source [VERIFY].], [`cbe3dcf:docs/reports/2026-11-13-thesis-evidence-register.md` (Gaps)])

#evidence("5.13", [S1b tracked band 5.0 x 3.6 m (|x| up to 2.5, |y| up to 1.8); two islands 0.55 x 1.60 x 0.30 m; coverage 9.78 %; every gap at least 0.90 m.], [`68e67b5:isaac/config/scenarios/mapd_5_s1b.yaml` (header comments)])

#evidence("5.14", [S1b: 5 robots, 5 nodes, 5 tasks per robot (25), dwell 5 sim-s, release stagger 2.5 sim-s, H = 600 sim-s; seed list of 100 with 20 confirmatory; structure from a published MAPD study at harsher density (documented deviation).], [`68e67b5:isaac/config/scenarios/mapd_5_s1b.yaml`; `68e67b5:config/s1_seeds.yaml` (100 seeds, confirmatory_count 20); `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (scene design attached, S1 density framing)])

#evidence("5.16", [IB10: 4 robots, spawns 1.75 m from centre, goals on the opposite arm; duration 300 sim-s; seed 42; jam gate onset window [8, 40] s, min duration 2.0 s, 4 robots within 1.0 m; oracle junction_clear.], [`68e67b5:isaac/config/scenarios/intersection_bottleneck.yaml`; `1ee23d2:docs/reports/2026-10-03-step7b-oracle-freeze.md` ("IB10 scoring frozen", criterion 1)])

#evidence("5.17", [IB10 registration: question; runtime 68e67b5, no code deployed; overlay with pull-off 0.33 m, plan channel on; Arm B = Arm A overlay + reasoning_enabled false; seed 42 a label only, near-deterministic; parallel bring-up; earlier live pilot plans all repaired or replaced; B vs A is pipeline on vs off.], [`50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (sections 1-3, 6)])

#evidence("5.18", [OrchestratorConfig.reasoning_enabled: bool = True at the pinned runtime.], [`68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` (line 544)])

#evidence("5.19", [reasoning_enabled false: detector skipped, backend never constructed, shadow/probes/contradiction forced off, no artifact or dispatch; scene log, registry, arrival gate, task stream still run; one status line; Arm B overlay = base + one line.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A35); `68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` (lines 537-544, 1013-1050)])

#evidence("5.20", [Arm C addendum: questions; Arm C = scripted MockBackend, three entries (none, junction_clear x4 no plan, none), m3_default; 15 s cooldown re-trigger; isolates plan content only, cannot re-plan; condition gates; never pooled with 2026-11-13 arms or prereg-v3.], [`e6a904e:docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md` (sections 1, 3, 5, 6, 9); `68e67b5:config/mock_decisions/intersection_junction_clear_m3_default_once.json`])

#evidence("5.21", [Runtimes: tranche 1 on 1624db1 (merged into 68e67b5); IB10 on 68e67b5; grounder-default run on 68e67b5 + safety.py and safety_monitor_node.py + scoped_clearing_exemption key, floor 0.20 m.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A36(1)); `50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (section 2); `e6a904e:docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md` (section 2)])

#evidence("5.22", [Tranche-1 Arm A: ER-2, plan channel on, shield-escort grounding, churn bound off, sequential bring-up 180 s per stack, floor 0.20 m, MAX_ANALYSES 0.], [`75a499c:docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` (section 1.2)])

#evidence("5.23", [A33 measures: GT offset fit 0.00-1.00 s in 0.01 s steps; t0 = robot_1 release; H 600 sim-s gives about 570 rel-s; censoring reasons; completeness out of 25; makespan = time to full resolution; throughput grid 1.0 s; delay departure speed above 0.03 m/s, arrival within 0.35 m staying within 0.5 m; arrival window ends at the segment dwell_complete, else T_end.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A33(0)-(4); A34 R11)])

#evidence("5.24", [A33(5)/(6): encounter below 0.45 m; merge_gap_s 2.0; min_duration_s 0.0; pre_s 0.0; post_s 5.0; min_overlap 1; accepted types {deadlock}; F1 = 2|D n I|/(|D|+|I|); an analysis matches at most one conflict; tie-break largest overlap, latest onset not after t_a, earliest onset; unmatched positive = false positive; undetected latency censored at min(end + post_s, T_end) - onset; per-conflict delta on conflicts with onset at or before tau_i; degenerate_arm_b.], [`68e67b5:benchmarks/s1_scoring/conflicts.py` (ENCOUNTER_M, ConflictParams); `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A33(5)-(7), A34 R10-R11)])

#evidence("5.25", [S1b free-flow table frozen from the 18 solo legs of the 2026-10-10 harvest; cross-VM caveat kept as a limitation.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A34 R8); `68e67b5:benchmarks/s1_scoring/data/free_flow_s1b_2026-10-10.json`])

#evidence("5.26", [IB10 outcomes: resolved = criterion 1 AND criterion 6 (within 0.35 m, never beyond 0.5 m after); success = resolved, 0 floor stops, GT min pair at least 0.18 m; time to full resolution from onset; outcome rank; attribution per dispatched decision: strategy, `plan.provenance` and `dispatch_matches_plan`.], [`50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (section 4, "Attribution (Arm A)", line 72); `1ee23d2:docs/reports/2026-10-03-step7b-oracle-freeze.md` (criteria 1, 6, 11)])

#evidence("5.27", [Tranche-1 order p1 A-B, p2 B-A, p3 A-B, p4 B-A, p5 A-B; arm read from CONDITION.txt; up to 3 bring-up attempts, ON_SEED_FAIL=stop; pin gate before every episode.], [`75a499c:docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` (sections 1.3, 1.6, 1.7); `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A33(9))])

#evidence("5.28", [Tranche-1 caps: 600 sim-s horizon; CAP_EP 0.25 USD guard; CAP_TOTAL 1.30 USD; MIN_REMAINING 0.25 USD; Arm B no budget gate; pin stop rule 300 sim-s.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A34 R7); `75a499c:docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` (section 1.7)])

#evidence("5.29", [IB10: 5 episodes per arm, order E01 A ... E10 B; smoke rule; exclusion table; caps 6 h per invocation, 0.50 USD per episode, 3.00 USD total, no analysis cap.], [`50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (sections 3, 5, 8)])

#evidence("5.30", [Grounder-default run: e01 A smoke, then e02 C, e03 A ... e10 C; 5 C + 4 A + smoke; one shared overlay; caps 5 h cumulative, 1.00 USD total, 0.25 USD per Arm A episode.], [`e6a904e:docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md` (sections 3, 10)])

#evidence("5.31", [Post hoc e02 re-run amendment: written after results, committed before the re-run; one launch, no retry; invalid-jam counting rule; Arm C reported before and after.], [`e6a904e:docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md` (section 13)])

#evidence("5.32", [Tranche-1 gates: contact gate 0.18 m all-pairs GT, 0 floor stops; floor gate on startup line 0.2; condition gate per arm; escort/park vs 0.45 m; pin gate; breach reported, episode not dropped.], [`75a499c:docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` (section 1.6)])

#evidence("5.33", [IB10 safety: floor 0.20 m both arms, gated on startup line; floor stops are outcomes; cross-cluster exemption caveat; grounder-default smoke pass criteria (0.18 m GT, 0 floor stops, no key-on stall) and added descriptive counts.], [`50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (section 7); `e6a904e:docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md` (sections 4, 7)])

#evidence("5.34", [Paired percentile bootstrap over seed pairs, B = 10000, seed 20261021, 95 %; common window tau_i; Wilson 95 % CI for completeness; KM + RMST for makespan; throughput mean with n at risk.], [`68e67b5:benchmarks/s1_scoring/arm_delta.py` (DEFAULT_REPS, DEFAULT_BOOT_SEED); `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A33(1)-(3), A33(7), A34 R11)])

#evidence("5.35", [IB10: episodes not independent samples, no p-values, no confidence claims beyond counts; Arm C addendum: no p-values, no intervals, A vs C times not directly comparable.], [`50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (section 6); `e6a904e:docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md` (sections 8, 9(c), 9(e), 13.5)])

#evidence("5.36", [Bench corpus: 187 items from 31 live S1b episodes (E6-E26 pilots, E27-E31 tranche 1); 149 valid, 137 positive; no frames, text-only.], [`05a44eb:docs/reports/2026-10-22-v4-bench-baseline.md` (Inventory)])

#evidence("5.37", [Bench purpose (ranks candidates, does not estimate effects; exploratory; never pooled with A32-A36); modes recorded, classical, replay with prompt-hash check; metric definitions.], [`fe44eca:docs/specs/v4_vlm_bench.md` (Purpose, Scoring Metrics, Modes)])

#evidence("5.38", [Grounding-first v1: probe pairwise yield, reverse, reroute, temporary_wait with offline M3; keep executable options; numbered list plus none of the above.], [`1639470:docs/reports/2026-10-23-v4-grounding-first-candidates.md` (Design)])

#evidence("5.39", [Replays with ER-2 and Claude Sonnet 5.5; baseline and grounding-first variants; shuffle seed 20261023; temperature 0.0 could not be sent (ER-2 Interactions API has no temperature field; Sonnet 5.5 returns HTTP 400 on non-default sampling), recorded per call as unsupported_sampling.], [`fd567f3:docs/reports/2026-10-23-v4-replay-er2.md` (Runs, Rev 2)])

#evidence("5.40", [Cluster candidates (gf-candidates-v2): grouping from scene state, threshold r_conflict_m = 1.5 m; seed and attach rules set after a GT-agreement sweep on the same 187 items.], [`7850f5a:docs/reports/2026-10-24-v4-gf-cluster-candidates.md` (Design, Observed Grouping)])

#evidence("5.41", [Per-cluster choice: one slot per observed group, none_feasible per slot, pydantic per-item contract, re-ask; each chosen option grounded alone; first-option chooser is the default-ordered first option (Rev 3).], [`055c269:docs/reports/2026-11-12-v4-per-cluster-choice.md` (Design; Rev 3 correction)])

#evidence("5.42", [Stage 1 live shadow: 7 episodes, seed positions 21-27, runtime fdf333d, ordinary loop dispatched, shadow never dispatched.], [`0eb8ce5:docs/reports/2026-11-13-v4-stage1-shadow-results.md` (Scope, Runtime)])

#evidence("5.43", [Pinned safety config: min_distance_m 0.45, hard_contact_floor_m 0.0; floor file sets 0.20.], [`68e67b5:ros2_ws/src/swarm_execution/config/safety.yaml`; `68e67b5:config/safety/safety_floor020.yaml`])

#evidence("5.44", [All 20 registered confirmatory seeds already ran as pilots (E1-E5 echo, E6-E20 live); recorded as a limitation.], [`ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A33(8))])

#evidence("5.46", [Arm B meaning: v1 classical reasoner; v2 Layer-2-off = no-congestion mock; from v3 A34 R9 / A35 Layer 2 off via reasoning_enabled false.], [`4e285a0:docs/superpowers/specs/2026-09-30-prereg-v2-design.md`; `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A33(10) D4, A34 R9, A35)])

#evidence("5.47", [Tranche-1 and IB10 live cells listed robots in ascending identifier order: every decision artifact records `robot_presentation_order: id_asc` (tranche 1: 28 Arm A artifacts; first IB10 run: 10 Arm A artifacts; grounder-default run: 25 artifacts); IB10 Arm A overlay `prompt_robot_order: id_asc` (md5 0196f1e8db0ffb9553c166707441362d). v1 amendment A2 had made the order random.], [Gitignored run bundles, read 2026-11-14: `feat/v3-integration` worktree `data/logs/vm_runs/batch6/s1b_E*_armA_er2_confT1_a1/decisions/*.json`; `feat/ib10-live-resolution` worktree `data/logs/vm_runs/ib10_live/runs/*/decisions/*.json`, `kit/overlays/ib10_armA.yaml`; `feat/ib10-safety-default-arm` worktree `data/logs/vm_runs/ib10_safety/runs/*/decisions/*.json`; `569d95c:docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md` (A2)])

#evidence("5.48", [Auxiliary Layer 2 paths forced off by reasoning\_enabled false: shadow\_classical (classical answer computed and logged beside every VLM analysis, never dispatched), t0\_probe\_mode (off-trigger stage-1 analyses, log-only, never grounded or dispatched), contradiction\_trigger (re-triggers analysis when a dispatched leg reports FAILED or the robot departs from its leg, skipping the cooldown).], [`68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` (ContradictionTriggerConfig lines 93-107; shadow\_classical lines 419-422; t0\_probe\_mode lines 439-447; REASONING\_OFF\_STATUS\_LINE lines 1012-1015)])

#evidence("5.49", [Bench classical chooser = `resolve_classical` of the rev-8 classical reasoner (module docstring "Arm B: the rev-8 classical congestion reasoner"): FCFS passing order with commitment tiebreak, last arrival yields; re-run in `classical` mode, compared with the live shadow record.], [`fe44eca:docs/specs/v4_vlm_bench.md` (Scoring Metrics item 4, Modes); `68e67b5:reasoning/baselines/classical_reasoner.py` (docstring)])

#evidence("5.50", [Tranche 1 chain 2026-10-21 14:07:06Z to 23:25:33Z, 9 h 18 min; real-time factor about 0.18; about 55 min per full-horizon episode; no wall-clock cap registered. v3 A36(5)-(6): tranche 2 (30 episodes) about 28 GPU-h at 55 min per episode, ER-2 spend "extra and small". IB10 registration: n = 5 per arm with no stated rationale; per-episode wall clock estimated 28-35 min. No power analysis in either.], [`75a499c:docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` (section 4, line 288; section 8, "Wall-clock time"); `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A36(5), A36(6)); `50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (sections 3 and 9)])

#evidence("5.51", [Demonstration campaign registration, written before any machine time: four scenes (intersection, convoy counterflow, head-on with obstacle, five robots at seed position 21, an extension seed already used by pilot E21 and the Stage 1 shadow); caps 12 VM-h and \$10; Layer 2 on with live ER-2 in every take, no Layer-2-off or scripted arm; scoped\_clearing\_exemption and 0.20 m floor asserted on the M4 start-up line; per-scene settings (2026-11-14 IB10 Arm A; registered convoy legacy grounding, robot\_3 and robot\_4 held by a 120 s start delay in the convoy overlay; September head-on configuration, prompt v2; tranche-1 Arm A procedure); intersection-only delta: options block and plan\_dispatch\_order\_source model\_when\_verified, intersection overlay keeps grounding\_yield\_feasibility off; amendments: wall-share reallocation (10.7), closing note on take-plan deviations (10.8), convoy takes 4-5 with grounding\_hold\_queued\_crossers on (12); one take per invocation, operator stop at the first take meeting the demo goal, up to 5 valid takes and 3 bring-up aborts per scene; labels Unresolved failure, VLM-driven execution (intersection classifier rule), M3-default resolution; unchosen takes listed, selection disclosed; recording changes the real-time factor.], [`1584fd8:docs/superpowers/specs/2026-11-15-demo-campaign.md` (sections 1-4, 6, 7, 10.3, 10.4, 10.7, 10.8, 12)])

#evidence("5.52", [Scene files: convoy\_counterflow\_slip (4 robots, aisle\_barrier 0.55 m x 1.0 m, robot\_1 and robot\_2 face each other, robot\_3 and robot\_4 queued behind robot\_1 with goals past the gap, 260 s, seed 42, oracle correct\_yielder robot\_2, correct\_order robot\_1, robot\_3, robot\_4, strategy convoy, rationale on the latch); head\_on\_asymmetric\_w0p2\_eopen\_bshort\_o0 (2 robots, aisle\_barrier 0.55 m x 2.0 m, blocker\_west at x -1.85, 0.70 m from the mouth against 1.08 m required, oracle correct\_yielder robot\_2, 300 s, seed 42) and its family of mirrored variants.], [`68e67b5:isaac/config/scenarios/convoy_counterflow_slip.yaml`; `68e67b5:isaac/config/scenarios/family/head_on_asymmetric_w0p2_eopen_bshort_o0.yaml` (and the other `family/head_on_asymmetric_*` files)])
