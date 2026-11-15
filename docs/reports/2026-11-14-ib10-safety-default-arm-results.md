# IB10 Safety Smoke and Grounder-Default Arm - Results

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: results of the 10-slot IB10 run of 2026-11-14 (key-on safety smoke, Arm A live ER-2, Arm C grounder default only), registered in `docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md`.
- Rev 2 (2026-11-14): added the section "Re-run of slot e02 (2026-11-14)". The original sections are not rewritten. Where they say e02 was not re-run, that section supersedes them.
- Rev 3 (2026-11-15): added the erratum "2026-11-15 Erratum — Contact Wording" and scoped every contact statement to the robot-pair distance; no number or verdict changed.

---

## 2026-11-15 Erratum — Contact Wording

Ground truth's two contact lists, `robot_static_contacts` and `robot_robot_contacts`, are hard-coded to `[]` in `isaac/vgu_sim/acceptance_logging.py:99-100`. No contact detector exists, so "the GT contact lists are empty" shows nothing. The sound channel is the logged minimum pairwise distance (`min_pairwise_distance_m` and the GT positions), a centre-to-centre robot-robot distance. Nothing in GT logs contact with static obstacles. The same caveat is in `docs/reports/2026-09-25-overnight-findings.md` (Metric correction 2 and its Rev 11 note) and `docs/reports/2026-10-08-s1-pilot.md`; the full account is section 8.7 of `docs/reports/2026-11-15-demo-campaign-results.md` (branch `demo/campaign-kits`).

- **What the statements rested on.** The scorer (`data/logs/vm_runs/ib10_safety/kit/score_ibs.py`, lines 16, 49 and 188) defines `gt_contact` as GT minimum pairwise centre distance < 0.18 m, "never the GT contacts field". This report's own recompute is the same distance count. In this report, "contact frames" means GT frames with a robot pair closer than 0.18 m. Those statements stand.
- **Affected statements.** The parenthesis "the GT contact lists are also empty in all 10" (Per-episode table notes), "0 GT contact entries" (Re-run section, Safety), the "GT contacts" label in the two pooled tables, and the unqualified "0 contacts" (e02 chain, step 5) and "no contact" (Interpretation). Each is now scoped in place and marked "(corrected 2026-11-15, see erratum)".
- **What remains supported.** Robot-robot only, by distance: 0 GT frames with a pair closer than 0.18 m in all 10 episodes and in e02 a2. The lowest pair is 0.3008 m in Arm A (e01), 0.2965 m in Arm C (e10) and 0.3060 m in e02 a2; e02 a1 never came below 2.0136 m. 0 floor stops. Every verdict and number is unchanged.
- **Static obstacles.** IB10 declares no static obstacles (`intersection_bottleneck.yaml` has no `static_obstacles`; "No obstacles"), so the gap is not material in the way it is for the S1b rack-island scenes. Contact with the warehouse rack blocks and walls that bound the aisles is not logged either and was not checked (inferred to be absent from the aisle-centreline lanes, not measured).

---

## Purpose

The run asks two questions, both from the addendum (section 1).

1. With the exemption-scope fix on (`scoped_clearing_exemption: true`) and the 0.20 m hard-contact floor armed, does the four-way `intersection_bottleneck` (IB10) Layer 2 pipeline still run cleanly?
2. Under that same runtime, does the jam clear the same way when no VLM is called (Arm C: scripted strategy and robot set, M3's default plan) as when the live VLM is called (Arm A)?

It is exploratory. It is never pooled with prereg-v3 and never pooled with the 2026-11-13 run (`docs/reports/2026-11-13-ib10-live-resolution-results.md` on branch `feat/ib10-live-resolution`).

The claim this report supports is narrow: **in this scene, a Layer 2 trigger plus M3's default `junction_clear` plan clears the jam, with or without a VLM choosing the strategy and robot set.** It does not show that the VLM is needed, and it does not show that it is useless (see Interpretation).

Evidence grading used below: **verified** means re-derived by this report's author from the raw bundle files (`gt/ground_truth.jsonl`, `m4.log`, `m5.log`, `decisions/*.json`, `nav2_r*.log`, `summary/episodes.jsonl`, `vm/attempts.tsv`); **copied** means taken from a run agent's report or from the scorer's output without re-derivation.

---

## Design

- Scene `isaac/config/scenarios/intersection_bottleneck.yaml` (md5 `042802d6b3980ce6591b0f5b343c85cd`), 4 robots, one per arm, 300 sim-s horizon, seed label 42, no pose jitter. Verified identical in all 10 bundles (`scenario_md5.txt`), as is the IB10 USD (`1d185bb0f4d56618b7ee6af92742c365`).
- Runtime: git `68e67b5` plus three safety files from `fix/safety-exemption-scope` (branch tip `8933863`): `safety.py`, `safety_monitor_node.py` and a merged `safety.yaml` (0.20 m floor file plus `scoped_clearing_exemption: true`, `waiver_closing_tolerance_m: 0.05`, `waiver_closing_readings: 3`). Both arms ran this runtime. Verified: all 10 `m4.log` files carry the startup line ending in `hard_contact_floor_m=0.2 exempt_actions=reverse,yield scoped_clearing_exemption=True waiver_closing_tolerance_m=0.05 waiver_closing_readings=3`.
- Arm A: Layer 2 on, live `gemini-robotics-er-2-preview`. Arm C ("grounder default only"): Layer 2 trigger, M3 grounding and phased M4 dispatch on, M5's backend the scripted `MockBackend` replaying `config/mock_decisions/intersection_junction_clear_m3_default_once.json`: first answer `none`, second `junction_clear` (all four robots, no `proposed_plan`), then `none` held. No VLM call.
- One overlay for both arms (`ib10s_l2on.yaml`, md5 `0196f1e8db0ffb9553c166707441362d`).
- Fixed order: e01 A (the smoke), then e02 C, e03 A, e04 C, e05 A, e06 C, e07 A, e08 C, e09 A, e10 C.
- Success: frozen `resolved` (criterion 1 jam valid and criterion 6 all four arrived), zero floor stops, GT minimum pairwise distance at least 0.18 m. All times are sim-seconds unless a clock time is given; "time from onset" is the last arrival minus `formed_jam.onset_sec`.

### Counting rules applied

- **Smoke.** The smoke (e01) counts as Arm A episode 1 only if `attempts.tsv` records it `ran` and `SMOKE_ACCEPTED` exists (addendum section 3). `attempts.tsv` records `ran`. `SMOKE_ACCEPTED` exists, but it was not written by the owner directly: its text reads "accepted 2026-11-14 by session lead under the owner's standing conditional instruction ('If it passes, run the Grounder-default-only arm')", and the follow run agent created the file at the session lead's direction (copied from the run agent's report). The addendum says only the owner writes it, so this is a deviation from the registered procedure. Arm A is therefore shown both ways below: 5/5 with the smoke, 4/4 on the follow-up episodes only.
- **Invalid jam.** The addendum (section 1) inherits "exclusions and attempt rules" from the 2026-11-13 spec (`docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md`, section 5). That table says: "Invalid jam (criterion 1 fails): Excluded from the primary denominator and reported (`resolved: None`)." The rule is applied manually in this report, see below.

---

## Results

### Per-episode table

All 10 slots, in registered order. "Onset" is the formed-jam onset (copied from the scorer's frozen gate). "First dispatch" is the sim time of the single `junction_clear` dispatch and its provenance. Arrivals, GT minimum, floor stops and contact frames were re-derived from `gt/ground_truth.jsonl` and `m4.log` (verified; arrival rule: within 0.35 m of goal and never beyond 0.5 m afterwards; t0 = first sample with any robot faster than 0.03 m/s). Cost is the `cost_watch.py` estimate (copied).

| Slot | Arm | t0 / onset | First dispatch (provenance) | Arrivals | Resolved | Time from onset | GT min pair (m, pair, t) | Est. USD |
|---|---|---|---|---|---|---|---|---|
| e01 (smoke) | A | 18.7 / 29.0 | 31.7 (`repaired`) | 4/4 | yes | 114.3 | 0.3008 r3+r4 @109.6 | 0.0118 |
| e02 | C | 41.0 / none | 25.8 (`m3_default`) | 0/4 | no jam (`invalid_jam`) | not scored | 2.0136 r2+r3 @59.9 | 0 |
| e03 | A | 17.2 / 27.3 | 30.0 (`m3_default`) | 4/4 | yes | 115.7 | 0.3210 r2+r4 @27.3 | 0.0125 |
| e04 | C | 16.9 / 27.0 | 33.3 (`m3_default`) | 4/4 | yes | 118.5 | 0.3151 r2+r3 @27.0 | 0 |
| e05 | A | 18.0 / 28.1 | 31.0 (`repaired`) | 4/4 | yes | 116.9 | 0.3194 r2+r3 @28.1 | 0.0118 |
| e06 | C | 17.1 / 27.2 | 33.6 (`m3_default`) | 4/4 | yes | 118.6 | 0.3250 r2+r3 @27.3 | 0 |
| e07 | A | 15.9 / 26.0 | 28.8 (`repaired`) | 4/4 | yes | 116.2 | 0.3082 r2+r3 @26.1 | 0.0125 |
| e08 | C | 18.5 / 29.0 | 34.8 (`m3_default`) | 4/4 | yes | 115.5 | 0.3671 r2+r4 @28.6 | 0 |
| e09 | A | 18.7 / 29.3 | 32.2 (`repaired`) | 4/4 | yes | 116.7 | 0.3365 r1+r3 @29.4 | 0.0074 |
| e10 | C | 17.7 / 27.9 | 34.1 (`m3_default`) | 4/4 | yes | 118.6 | 0.2965 r2+r3 @27.9 | 0 |

Every valid episode had 0 floor stops and 0 GT frames with any robot pair closer than 0.18 m (verified over all frames and all six pairs; robot-robot only. The GT contact lists are hard-coded empty and are not evidence; IB10 declares no static obstacles. Corrected 2026-11-15, see erratum). In nine of ten episodes the closest approach is the jam pose at formation, before any dispatch. In e01 the minimum (0.3008 m, r3+r4 at 109.6 s) occurs during the manoeuvre, after the first dispatch. Time from onset equals last arrival minus onset (verified from the arrivals and the onset).

### Pooled per arm

| | Arm A (live ER-2) | Arm C (grounder default only) |
|---|---|---|
| Slots run | 5 (smoke + 4) | 5 |
| Valid jam | 5 | 4 (e02 invalid) |
| Resolved, registered rule (invalid jam out of the denominator) | 5/5 (follow-up only: 4/4) | 4/4 valid; 4/5 slots |
| Arrivals | 20/20 | 16/16 valid (e02: 0/4, no jam) |
| Time from onset (s) | 114.3, 115.7, 116.2, 116.7, 116.9 (mean 115.96) | 115.5, 118.5, 118.6, 118.6 (mean 117.80) |
| Lowest GT pair (m) | 0.3008 (e01) | 0.2965 (e10) |
| Floor stops / GT pair frames < 0.18 m (corrected 2026-11-15, see erratum) | 0 / 0 | 0 / 0 |
| Attribution | `repaired` 4 (e01, e05, e07, e09), `m3_default` 1 (e03) | `m3_default` 4 (e02 as well, by construction) |
| Est. spend | $0.056 (smoke $0.0118, follow-up $0.0442) | $0 |

Spend is copied from the scorer and `vm/attempts.tsv` (the arithmetic 0.0118 + 0.0125 + 0.0118 + 0.0125 + 0.0074 = 0.0560 was re-checked). It excludes the one-token Gemini probes.

### e02 and the scorer's "counted" column

The scorer's summary shows Arm C as `bundles 5, counted 5, scored 4, status_counts {invalid_jam: 1, scored: 4}` and its table prints e02 as "counted". Both views, so the discrepancy is traceable:

- **Scorer view (copied from `summary/summary.json`, mechanism verified in `kit/score_ibs.py`).** `counted` means only that `vm/attempts.tsv` records the slot `ran` (`apply_attempts`, line 218); it is independent of the jam gate. The aggregates then split: `bundles`, `counted` and `est_usd` use all counted rows (5), while `scored`, `success`, `resolved_frozen`, `floor_stop_episodes`, `deadline_ended_episodes`, `third_robot_waivers` and `min_gt_pairwise_m` are computed over `status == "scored"` rows only (4). So `deadline_ended_episodes: 0` for Arm C does not include e02, although e02's own record carries five `m5_failed` deadline-ended entries on the `junction-cross` command (verified in `episodes.jsonl`).
- **Registered-rule view (applied here).** e02 fails criterion 1, so under the 2026-11-13 spec section 5 it is excluded from the primary denominator and reported: Arm C is 4 resolved of 4 valid, and 4 of 5 slots. The slot was not re-run.

### e02: facts, then inference

Facts, each verified from the e02 bundle (`ib10S_e02_armC_a1`) unless marked:

1. The Nav2 stacks reported ready. The launcher printed `Nav2 lifecycle active: 4/4 stacks after 2s` and `gate passed in 33s` (e03 to e10: 30 to 32 s). `GATE OK` and `RESTORE OK` were recorded.
2. In the robot_1 Nav2 stack, which hosts the shared `map_server`, `lifecycle_manager_map_server` logged `Starting managed nodes bringup` and `Configuring map_server` at wall 1794637168.0, and then nothing: no `Activating map_server`, no bond, no `Managed nodes are active`. `map_server` read the map (240 x 160 at 0.05 m/cell) and logged `failed to send response to /map_server/change_state (timeout): client will not receive response` at 1794637168.2. In e04 the same stack logged `Activating map_server` 0.23 s after `Configuring` and `Managed nodes are active` 0.12 s later.
3. As a result no costmap received a map. From the first plan request (wall 1794637214, 06:20:14 UTC) to the end of the episode (06:36:02), all four stacks logged `Can't update static costmap layer, no map received` (2,078 lines in total) and `GridBased plugin failed to plan ... "Costmap timed out waiting for update"` (361 lines: 152, 131, 70 and 8 in robots 1 to 4). The costmaps also logged `Sensor origin ... out of map bounds` (18,200 lines across the stacks).
4. The robots therefore never got a plan. GT: three robots moved 0.31 to 0.32 m from their start points and robot_4 moved 0.00 m; the minimum pair distance never fell below 2.01 m. No jam formed (`jam_valid: false`).
5. M5's first analysis (wall 1794637222.6, sim 21.2) fired on "3 robot(s) stalled >= 12.0s" at distance to goal 3.51 m. The mock answered `none`. A second stall analysis 15.0 wall-s later (sim 25.8) got `junction_clear`, and M3 dispatched its default plan against a scene that was not jammed. The recede phases ran, the `junction-cross` command resolved `failed` five times, and the fallback `reroute` was dispatched. 0 key-on lines, 0 floor stops, 0 robot-robot contact frames (minimum pair 2.0136 m; corrected 2026-11-15, see erratum).
6. Other episodes: `Costmap timed out waiting for update`, `no map received` and the `map_server` response timeout appear in no other bundle of 2026-11-14 (0 lines in e01 and e03 to e10), and in none of the 11 bundles of 2026-11-13 (checked in `vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/runs/`). `Timed out waiting for transform` lines (4 to 14 per episode, 5 in e02) appear in every episode during start-up and are not specific to e02. e10 has one unrelated `Failed to create plan with tolerance of: 0.500000` line mid-episode.

Inference, not verified:

- The map never reached the costmaps because `map_server` was never activated, and it was never activated because the lifecycle manager's configure call did not complete (the service response was dropped). Why the response was dropped is not known; a start-up ordering race in this launch is a candidate (in e02 the lifecycle manager's `Starting managed nodes bringup` preceded `map_server`'s own `Creating`, in e04 it followed it), but the logs do not prove it.
- "First episode after the rebuild" is circumstance, not cause: e01 (first after the smoke deploy) started cleanly.
- The M5 stall trigger does not distinguish a jam from stuck robots, so it fired Layer 2 on a non-jam.

The kit's gates (`GATE OK`, the `4/4 stacks active` check) do not detect this failure, because the lifecycle manager for the navigation stacks is a different node from the one that failed.

### Arm C proof of condition

An independent check from the Arm C artifacts, not the kit's gate. Verified over all 14 Arm C decision artifacts (e02: 2, e04, e06, e08, e10: 3 each):

- `diagnostics.backend_id` and `diagnostics.reasoner_config_effective.backend_id` are `mock` in 14/14; `served_model` is `None` in 14/14; `reasoner_config_effective.model_id` is `None`; `token_usage` is `None` and `attempt_token_usage` is `[None]`; `latency_ms` is 0.
- The decisions are, per episode in stamp order: `none`, `junction_clear`, and (e04 to e10) `none`. The `junction_clear` decision names all four robots and has `proposed_plan: null`; its `raw_text` is the script's text ("Scripted mock decision ...").
- All five dispatched plans have provenance `m3_default` and rejection reason `plan absent`.
- No `.cost.log` exists for any Arm C episode, and there is no Gemini probe line before any Arm C episode (`vm/probe.log`: five probes, all before Arm A episodes, `http=200 verdict=OK`, 4.07 to 4.37 s). For contrast every Arm A artifact (9 of 9) has `backend_id` `gemini`, `served_model` `gemini-robotics-er-2-preview` and a token usage block (for example prompt tokens 2,931 to 3,030).
- The only `gemini`, `openai` or `api_key` hits in the Arm C logs are fc_launch's own `reasoning_backend_id: openai -> mock (restored on exit)` lines.
- `CONDITION.txt`: `backend=mock mock_echo=0`, script md5 `6c670a6e1fd0ea1cb1704075f64e2816` (all five).

This is artifact-level evidence. There is no network-level evidence (no packet capture or provider log). Also, `fc_launch.sh` still sources `/ws/.env` in Arm C, so the key was present in M5's environment; the mock path returns before any provider branch is built (addendum section 5).

### Safety-key evidence

- The key and the 0.20 m floor were on in all 10 episodes (startup line, above).
- Key-on-only lines in `m4.log`, counted directly: `plan continue partners not honoured` 0, `rejected leg not a member` 0, `latch waiver armed` 0, `latch waiver revoked` 0, in all 10 episodes (verified; the scorer's `keyon` counters are 0 in all 10 as well). Third-robot waivers 0, revocations 0, key-on stalls 0. The key was on and never fired.
- Hard-contact floor stops (`hard_contact_floor_m=0.2 pairs=`): 0 in all 10.
- Other M4 stops, tabulated because they are not floor stops. Ordinary `min_distance_violation` latch lines (min distance 0.45 m) occur in every episode in which the robots jam, which is expected: 9,487 to 13,834 lines per jammed episode, 0 in e02. `stale_pose_unsafe` stops: e04 4 lines, e10 2 lines, 0 elsewhere. No other stop reason appears. The stale-pose stops did not affect either episode's outcome (both resolved); their cause was not examined.

### Dispatch-delay comparison

Verified from the artifacts' scene stamps and the scorer's t0 and onset:

| | Arm A (5) | Arm C (4 valid) | C minus A |
|---|---|---|---|
| First dispatch, sim-s | 28.8 to 32.2 (mean 30.73) | 33.3 to 34.8 (mean 33.96) | +3.23 |
| First dispatch minus onset | 2.7 to 2.9 (mean 2.79) | 5.8 to 6.4 (mean 6.18) | +3.39 |
| First dispatch minus t0 | 12.8 to 13.5 (mean 13.03) | 16.3 to 16.5 (mean 16.41) | +3.38 |
| Time from onset to last arrival | 114.3 to 116.9 (mean 115.96) | 115.5 to 118.6 (mean 117.80) | +1.84 |
| Dispatch to last arrival | 111.6 to 114.0 (mean 113.17) | 109.7 to 112.4 (mean 111.62) | -1.55 |

The delay is the scripted `none`. Arm C's first analysis (answered `none`, stamps 29.7 to 31.3) is followed by the dispatching analysis 3.5 to 3.7 sim-s later (verified: 3.57, 3.70, 3.53, 3.47), and in e02 the M5 log shows the two analyses 15.0 wall-s apart, matching the 15 s `cooldown_sec`. The completion times point the same way as the delay but do not match it: Arm C finishes 1.8 s later from onset, less than the 3.4 s dispatch delay, so after its dispatch Arm C was on average 1.6 s faster. Why is not explained; with 5 and 4 valid episodes it may be within spread. The times are not strictly comparable because of the delay (caveat (c)).

### Similarity and branching

Verified. Which robot M3 recedes first is read from the order of `junction-recede-robot_N` commands in each `m5.log` (and equals the `junction_phases` order in the artifact):

| Branch | Arm A | Arm C |
|---|---|---|
| r4 recedes first | e03, e05, e07, e09 | e04, e06 |
| r3 recedes first | e01 | e08, e10 (e02, invalid, also r3 first) |

- The executed dispatch order equals the chi order the scorer recomputes from each artifact's own snapshot (`rank_recede_candidates`) in 10 of 10 episodes, and `dispatch_order_source` is `chi` in every artifact. So the recede order is M3's chi ranking of the trigger snapshot (verified). What in the snapshot tips chi between r3 and r4 from one near-identical episode to the next was not analysed (open); the chi-versus-snapshot link is therefore only established as far as "M3 ranks, the snapshot differs".
- The scorer's field `chi_pair.executed_recede` is misleading for `repaired` plans and was not used. It reads the order of `plan.legs`, which for a repaired plan is the model's leg order after edits (for e05: `reverse r3, reverse r4, yield r1, cross r2`, after two `swap` and one `substitute` edit), not the dispatch order. It reports e01, e05 and e07 as `executed_order_correct: False` although the dispatched order equalled chi in all three. The run agent's report took this field as the executed order and so lists e01 as r4-first and e05 and e07 as r3-first, the reverse of the dispatch log; its branch tallies (A r4-first 3, r3-first 2) are wrong and the table above replaces them. The frozen scoring (resolved, arrivals, times) does not use that field.
- A second difference between episodes is the cross-phase retreat side: `retreat_choice` A with pull-off +0.36 m in e01 and e09 (both Arm A), B with -0.36 m in all other episodes with a jam. It is not a model choice: no artifact carries a `stage2` block and every cross phase has the degradation `retreat=default:no_choice`. Offline re-grounding of the e01 and e09 snapshots reproduces the +0.36 m phases, so it comes from the snapshot.
- Position RMS over the four robots, aligned on each episode's t0, window 60 to 170 s after t0 (verified):

| Pairs | Count | RMS range (m) |
|---|---|---|
| r4-first, retreat B, either arm (e03, e04, e05, e06, e07) | 10 | 0.04 to 0.16 |
| r3-first, retreat B (e08, e10) | 1 | 0.12 |
| e09 (r4-first, retreat A) against r4-first retreat B episodes | 5 | 0.27 to 0.29 |
| e01 (r3-first, retreat A) against e08, e10 | 2 | 0.29, 0.34 |
| r3-first against r4-first | 18 | 0.60 to 0.67 |

So there are about four trajectories: r4-first with retreat B (five episodes, both arms, mutually within 0.16 m), r3-first with retreat B (e08, e10), r4-first with retreat A (e09) and r3-first with retreat A (e01). Before dispatch all ten episodes look alike. Resolution time does not separate the branches beyond the 1.8 s mean difference above. Arm C episodes appear in both main branches, with no VLM involved; Arm A is not a different set of trajectories from Arm C except for the two retreat-A episodes.

### Plan equality: Arm A first dispatch against M3's default

The kit-prep finding (offline, on 2026-11-13 snapshots) was that the commands Arm A dispatched first equal M3's default plan. Checked here on today's bundles in two ways (verified):

- Re-grounding with the repo's own `ground_junction_clear_phases` (via `kit/reground_c.py`, which needs no VM). On each of the five Arm A first-dispatch snapshots (e01, e03, e05, e07, e09), the scripted Arm C decision re-grounds to exactly the recorded executed `junction_phases` (all four phases: two recedes, cross, release; actions and parameters, apart from free-text `reason`). The only difference is one degradation tag, `order=discarded_yield_axis`, present on the cross phase and fallback of the recorded Arm A plans and absent in the script's, because the script gives no `crossing_order`. The same check on the e04 Arm C snapshot gives the same answer, as a control. This includes the four `repaired` plans: M3 repaired the model's plan back to its own default, so the executed commands were M3's.
- Comparing executed `junction_phases` of Arm A and Arm C episodes in the same branch (127 fields each, reason and ids excluded): e05 against e04 (both r4-first, retreat B) has no structural difference in actions, robots, phase order or holds beyond the three degradation-tag lines above, and numeric differences of at most 0.021 m (retreat y) with backup distances differing by up to 0.008 m. e07 against e04: at most 0.029 m. e03 against e06 (e03 is the `m3_default` Arm A episode): at most 0.090 m, and e03 against e05 shows no structural difference and at most 0.081 m. These small numeric differences come from slightly different trigger snapshots. e01 and e09 differ from the Arm C episodes in the retreat side (A against B, 0.72 m in pull-off), as above, for the same snapshot reason.

What differs between arms, then: the dispatch time, the degradation tag, the snapshot-dependent numbers, and in two Arm A episodes the retreat side. It does not show a difference that comes from the VLM's answer. What the VLM did contribute is not visible in the executed commands: its `proposed_plan` was wrong in every one of the four episodes with a proposal (the scorer's `proposed_pair_correct` is False for e01, e05, e07 and e09) and M3 discarded or repaired it; in e03 the VLM gave a strategy token only.

### Cost

Arm A est. $0.0560 in total ($0.0118 smoke plus $0.0442 follow-up); Arm C $0 (no calls). The estimates come from `cost_watch.py` token counts, not provider invoices, and exclude the five one-token probes. Per-episode Gemini requests record `temperature`, `top_p`, `top_k` and `presence_penalty` as dropped from the request: `m5.log` states "Gemini Interactions API has no ('temperature', 'top_p', 'top_k', 'presence_penalty') fields; ReasonerConfig values are dropped from the request" (verified, once per Arm A episode). The recorded 0.6 temperature was therefore not sent, and the Arm A answers are not under temperature control.

### Timeline

UTC, 2026-11-14. Starts and ends from `driver_*.log`, `vm/attempts.tsv`, `wallclock_ledger.tsv` (verified).

| Event | Time |
|---|---|
| Smoke driver starts; VM started | 05:45:36; 05:45:49 |
| e01 starts; ends (`attempts.tsv`) | 05:50:15; 06:09:22 |
| `RESTORE_IBS OK`; VM `TERMINATED` (verified by the driver) | 06:09:52; 06:11:20 |
| Follow driver starts; VM started | 06:13:49; 06:14:00 |
| e02 starts | 06:18:24 |
| Episode ends e02 to e10 | 06:37:31, 06:56:52, 07:16:09, 07:35:20, 07:54:32, 08:13:54, 08:33:03, 08:52:26, 09:11:28 |
| `CHAIN_IBS DONE`; `RESTORE_IBS OK` | 09:11:28; 09:12:09 |
| VM `TERMINATED` (verified by the driver) | 09:13:53 |

Wall clock: smoke 1,531 s and follow 10,793 s, 12,324 s of the 18,000 s (5 h) cap. Each episode took about 19 min (ends minus the previous end, verified). `vm/STOP_CHAIN` is an empty file touched by `restore_ibs.sh` (line 31) to stop a chain from restarting during the restore. It is not the wall-clock watchdog and no episode was stopped early.

---

## Interpretation

- **Within this run the VLM arm and the scripted default-plan arm are indistinguishable in outcome.** All valid episodes resolve (Arm A 5/5, Arm C 4/4 valid), times are within a few seconds of each other (means 115.96 s and 117.80 s from onset), the executed commands are M3's default plan in both arms, and the dispatch delay of Arm C (about 3.4 s) is of the same order as the 1.8 s mean difference in completion time. Combined with yesterday's VLM-off arm (0/5, a separate run with the key off, not pooled), the supported claim is: **a Layer 2 trigger plus M3's default `junction_clear` plan clears this jam; the VLM's contribution in this scene is limited to selecting the strategy and the robot set, which the scripted arm was given.**
- This run does **not** show that the VLM is needed, and it does not show that it is useless in general. Arm C was handed the correct strategy and robot set. Yesterday's e09 shows that the VLM can also choose off-pattern (a `yield`, then a degenerate two-robot plan) and fail; today's Arm A did not, in 5 of 5 episodes. Arm C cannot show that, because it cannot re-plan after a failure: every analysis after the first dispatch is answered `none`.
- **n and independence.** n = 5 (Arm A) and 4 valid (Arm C), one scene, no pose jitter, near-repeat episodes in about four trajectories. These are not independent samples. No p-value and no confidence interval is given.
- **The safety fix was active but never exercised.** All key-on counters are 0 in all 10 episodes (no unhonoured partner, no rejected leg, no waiver, no revocation). The run shows that the key does not disturb the normal recede-and-release manoeuvre in nine valid episodes (no floor stop, no robot pair closer than 0.18 m, no key-on stall; corrected 2026-11-15, see erratum). It is not a live validation of the fix, as caveat (a) of the addendum already said.
- **Further limits.** Arm C cannot re-plan after a failure. Times are not strictly comparable between arms because of the dispatch delay. Simulation only. Exploratory. Never pooled with prereg-v3 or with yesterday's arms.

---

## Verification Status

| Item | Status |
|---|---|
| Outcome, arrivals, GT minimum and pair, floor stops, contact frames, t0 | Verified: recomputed from `gt/ground_truth.jsonl` and `m4.log` (arrival rule and t0 rule stated in the table intro); agree with the scorer in all 10 episodes |
| Formed-jam onset and validity, `outcome_rank`, attribution, per-episode cost | Copied from `summary/episodes.jsonl` (onset and time from onset cross-checked against last arrival) |
| e02 chain (map_server, costmaps, M5 sequence) | Verified from the e02 `nav2_r*.log`, `m5.log` and GT; the reason the service response was dropped is not known |
| Costmap and map_server lines in other bundles | Verified by grep over all 10 bundles of today and all 11 bundles of 2026-11-13 |
| Arm C no-VLM | Verified at artifact level (14/14); no network-level evidence |
| Recede order, branches | Verified from `m5.log` and artifacts; the run agent's order (e01, e05, e07) differs and is wrong; what tips chi is open |
| Plan equality | Verified offline by re-grounding and by field comparison |
| Dispatch delay | Verified from artifact scene stamps and scorer t0 and onset |
| Archive and MANIFEST | Built here; see Reproducibility |
| Run agents' wall-clock narrative, SMOKE_ACCEPTED authorship | Copied |

Values in the run agents' reports that differ from the verified ones (both given):

- Executed recede order, e01: agent r4 then r3; verified r3 then r4. e05: agent r3 then r4; verified r4 then r3. e07: agent r3 then r4; verified r4 then r3. Branch tallies: agent r4-first A e01, e03, e09 and r3-first A e05, e07; verified r4-first A e03, e05, e07, e09 and r3-first A e01.
- Arm C against Arm A: agent "C is about 2 s slower, consistent with the dispatch delay of about 3.4 s"; verified 1.84 s slower from onset against a 3.39 s delay (not matching), and 1.55 s faster from dispatch.
- e02 GT: agent "robots 1 to 3 moved inward only to about +-1.43 m"; verified: three robots moved 0.31 to 0.32 m, robot_4 0.00 m.
- e02 cause: agent "Nav2 was not ready ... I did not check why the costmap lagged"; verified: the `map_server` never activated (above).
- `summary.json` Arm C `deadline_ended_episodes: 0`: computed over scored rows only; e02 has five deadline-ended entries.

---

## Reproducibility

| Item | Value |
|---|---|
| Runtime | git `68e67b5` plus the three files below; the VM matched the pin list on every episode (`vm/pins_run_last.log` all `ok`, `PINS_V3 OK` at each restore) |
| Registration | `docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md` (commit `ed8b203` on `feat/ib10-safety-default-arm`), inheriting `docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (`50704c2`) |
| Deployed `safety.py` | `3011d9a735e790f56f6c46d98c76f1d9` (68e67b5: `c6c9cbaeb9cb816dd2ba759c2464afb4`); equals `fix/safety-exemption-scope` at `8933863` (verified with `git show`) |
| Deployed `safety_monitor_node.py` | `c2cad302be27cf1b638fbeebf295ae7d` (68e67b5: `7b45075fcb940e3e3b57154b3b727958`); equals the fix branch (verified) |
| Deployed `safety.yaml` (merged) | `65fb84a396c3d61a4e4179cd2360897b` (68e67b5: `598396622ca50baddc3e19b4608fa3e3`); floor file `c41913f02cf4e988162c30a44a5dda04` plus fragment `08c06b51491e9273c77d4c2e96b4c1ba` |
| Installed copies | The deploy log shows installed equals source for all three (copied from the driver logs); restore returned the 68e67b5 bytes (`restore_ibs.sh` lines in the smoke driver log) |
| Model | `gemini-robotics-er-2-preview`, `diagnostics.served_model` in all 9 Arm A artifacts (verified). Sampling parameters are dropped by the Interactions API, see Cost |
| Scene yaml / USD md5 | `042802d6b3980ce6591b0f5b343c85cd` / `1d185bb0f4d56618b7ee6af92742c365` (all 10 bundles) |
| Orchestrator overlay | `0196f1e8db0ffb9553c166707441362d` = `kit/overlays/ib10s_l2on.yaml` (all 10 `orchestrator.overlaid.yaml`, verified); source `kit/src/ib10_remedy_orchestrator_0d0cfbfa.yaml` (`0d0cfbfa67c4b3f56257b9c3b763d5fe`) |
| `rag.yaml` / `orchestrator.yaml` | `e18c723cff9cada3f320d564c2ecee5a` / `1f656533a30a35882d57d0d64a57bd0d` (all 10 `RESTORE.txt`: installed equals pristine) |
| Arm C script | `config/mock_decisions/intersection_junction_clear_m3_default_once.json`, `6c670a6e1fd0ea1cb1704075f64e2816`; `reasoning/vlm/mock_backend.py` `c27742a08ee0808aa9f3e52f63c307a1` (matched the precondition) |
| Kit list md5s | `kit/kit_md5_ibs.txt` `72358e80fb040861fc8fdac27ca5a67b` (28 VM files); `kit/kit_md5_all_ibs.txt` `0db47b478920d42da89ea1418c79964f` (40 files). `mac_kit_md5_ibs.sh --check` prints `KIT_MD5 OK` against the current kit (verified); the drivers logged the same two md5s for both invocations |
| `MANIFEST.md5` | `data/logs/vm_runs/ib10_safety/MANIFEST.md5`, md5 `da6f3283bd6fba9e6b5d4ec431732916`: every file under `kit/`, `summary/`, `vm/`, the two driver logs, `SMOKE_ACCEPTED`, `SMOKE_CHECK.txt`, `wallclock_ledger.tsv` and the top-level files of `runs/`, one line each, plus one `BUNDLE` line per directory in `runs/` (md5 of the sorted per-file listing; 20 directories) |
| Archive | `data/logs/vm_runs/ib10_safety_archive_20261114.tar.gz`, md5 `9cc5c5da3476924d110d4e0f3e0d640d`, 22,970,137 bytes, 427 files (426 evidence files plus `MANIFEST.md5`) |

The archive holds `ib10_safety/` without `known_hosts_ibs` (confirmed absent; no `._*` files, built with `COPYFILE_DISABLE=1`). No evidence file was modified: the md5 listing of every file in `ib10_safety/` (excluding `known_hosts_ibs`, 426 files) was identical before and after the checks and the archive build; only `MANIFEST.md5` was added.

Secret check on the tree before archiving (counts of matching files only, nothing printed): Google API key `AIza...` 0, `sk-` 0, GitHub token 0, bearer token 0, private-key block 0, `key=` URL parameter 0, `*_KEY`, `_TOKEN` or `_SECRET` assignments with a value 0, `x-goog-api-key:` header with a value 0. Binary frames were not scanned.

---

## Limitations

- **n and independence.** n = 5 (A) and 4 valid (C), one scene, one seed label, no pose jitter. About four distinct trajectories, mostly near-duplicates. No p-value, no interval.
- **What Arm C is.** Arm C was handed the strategy (`junction_clear`) and the robot set (all four). It isolates the plan content and the live loop around it. It cannot re-plan after a failure and cannot show that the VLM adds nothing.
- **Smoke acceptance.** `SMOKE_ACCEPTED` was written under the owner's conditional instruction by the session lead's run agent, not by the owner. Arm A is given with and without the smoke.
- **e02.** A harness start-up fault, not a result about the method. It was not re-run (owner decision pending); Arm C has 4 valid episodes, not 5.
- **Timing.** Arm C dispatches about 3.4 s after Arm A because of the scripted `none`. Completion times are not strictly comparable.
- **Safety.** The fix was active and never fired. No claim about the fix is made.
- **Model sampling.** Arm A answers are not under temperature control (sampling fields dropped by the API); a re-run may branch differently.
- **Simulation and scope.** Isaac Sim only. Exploratory. Never pooled with prereg-v3 or with the 2026-11-13 arms (different code delta and key setting).

---

## Open Items

- e02 is not re-run; the owner has not decided.
- `GATE OK` and the `4/4 stacks active` check do not detect a `map_server` that never activates (or a Nav2 start-up stall in general). A check that the costmaps received the map, or that `Activating map_server` was logged, would catch it.
- Why the `map_server` configure response was dropped in e02 is unknown.
- What tips M3's chi ranking between r3-first and r4-first, and what sets the retreat side (A against B), between near-identical snapshots is not analysed.
- The scorer's `chi_pair.executed_recede` reads `plan.legs`, not the dispatched order, and is misleading for `repaired` plans.
- The summary's per-arm aggregates exclude `invalid_jam` rows only for some fields (`scored`, `deadline_ended_episodes`) and not for `counted` and `est_usd`; the exclusion rule is not applied automatically.
- Exemption-scope fix: still not exercised live.

---

## Re-run of Slot e02 (2026-11-14)

**This re-run is post hoc.** The owner ordered it on 2026-11-14 ("re-run the invalid default-only episode") after seeing every result above. It is registered in the addendum's section 13 (commit `e6a904e`), which was committed before the run. The counting rule is the one already registered: an invalid jam is excluded from the denominator and reported. There is no third attempt.

The sections above are left as written. Their statements that e02 "was not re-run" (Limitations, Open Items, and the e02 counting paragraph) are superseded by this section.

### Run

| Item | Value |
|---|---|
| Bundle | `ib10S_e02_armC_a2`, stamp `20261114_105811`. One invocation (`run_ibs.sh rerun`), one launch, no bring-up retry. |
| Settings | Same as every Arm C episode. `CONDITION.txt`: `tag=ib10_safety record=0 confirmatory=0 arm=C backend=mock mock_echo=0`, script md5 `6c670a6e1fd0ea1cb1704075f64e2816`, overlay md5 `0196f1e8db0ffb9553c166707441362d`, seed 42. `ep_run_ibs.sh`, `cond_ibs.py`, `ibs_env.sh`, deploy, restore and overlay are byte-identical to the original run. |
| Timeline (UTC) | Driver start 10:53:36. VM start 10:53:48. Snapshot, build, deploy and ov OK by 10:58:05. Episode end 11:17:12. `RESTORE_IBS OK` 11:17:53. VM `TERMINATED` (verified by the driver) 11:19:27. |
| Gates | Chain: `COND arm=C artifacts=2 dispatched=1 analyses=2 ... backends=['mock'] models=['None'] provenance=[('m3_default','plan absent')] tokens=0`, `GATE OK`, `RESTORE OK`, `outcome=ran`, `CHAIN_IBS DONE`, driver `result=ok`. Restore: `installed packages == snapshot (72 files)`, `PINS_V3 OK`, `RESTORE_IBS OK`. No `RESTORE_FAILED_*` or `VM_NOT_STOPPED_*` marker. |
| Wall clock | 1,539 s booked in `wallclock_ledger_rerun.tsv`. Total 13,863 s of the 18,000 s cap. |
| Spend | $0. No cost log, no probe line for the label, no Gemini call. |

### a2 Facts

Each fact below was verified from the raw bundle unless it is marked "scorer".

- **Map start-up was clean** (`startup_check_ibs.py`):
  - robot_1's stack (the `map_server` host) logged `Activating map_server` once and the map lifecycle manager logged `Managed nodes are active` once.
  - There was no `change_state` response timeout.
  - All four stacks logged 0 `no map received` and 0 `Costmap timed out waiting for update` lines.
  - The e02 a1 failure did not repeat.
- **Jam valid** (scorer): `jam_valid: true`, onset 27.5 s, t0 17.0 s.
  - Our own t0 rule (the first GT frame with any robot faster than 0.03 m/s, from frame differences) gives 17.1 s.
- **Analyses and decisions.** Two analyses, both answered by the mock, in the order the script defines:
  1. Sim 30.4: a single-robot stall trigger (`robot_2`), answered `none`; the log shows `no dispatch stage=vlm`.
  2. 15.0 wall-s later, sim 34.1: a four-robot trigger, answered `junction_clear` naming `robot_1` to `robot_4`, with `proposed_plan: null`.
  - There was no third analysis. e04 to e10 each had a third, single-robot analysis after the release.
- **No VLM**, in both artifacts:
  - `diagnostics.backend_id` and `reasoner_config_effective.backend_id` are both `mock`;
  - `served_model` and `model_id` are None, and `mock_mode` is None;
  - `token_usage` is None and `attempt_token_usage` is `[None]`;
  - `latency_ms` is 0.
- **Dispatch.** One dispatch, at sim 34.13 s. That is 6.63 s after onset (the four valid Arm C episodes: 5.8 to 6.4 s) and 17.13 s after t0. Its provenance is `m3_default`, with rejection reason `plan absent`, and `dispatch_matches_plan` is true.
- **Executed recede order.** robot_3 receded first, then robot_4. This comes from the order of the first `junction-recede-robot_N` command lines in `m5.log`.
  - All `junction-recede-robot_3`, `junction-recede-robot_4`, `junction-cross` and `junction-release` status lines resolved `completed`.
  - 0 commands resolved `timed_out` or `failed`.
- **Retreat side.** `retreat_choice` A, cross pull-off +0.36 m, release pull-off -0.33 m.
  - That is the same branch as e01 (Arm A): robot_3 recedes first, retreat A.
  - It is the first Arm C episode on retreat A.
  - There is no `stage2` block, so the side came from the snapshot, not from a choice.
- **Arrivals: 4/4.** Times after t0: robot_2 77.8 s, robot_3 98.2 s, robot_4 114.4 s, robot_1 128.6 s.
  - We recomputed them with the report's rule: within 0.35 m of the goal, and never beyond 0.5 m afterwards.
  - They match the scorer.
- **Resolved:** yes, frozen rank (1, 4, 4) (scorer).
  - Time from onset 118.1 s. Check: 17.0 + 128.6 - 27.5 = 118.1.
  - Episode success: true (scorer).
- **Safety.**
  - GT minimum pair distance 0.3060 m, robot_1 and robot_4 at 27.5 s, the jam pose. This is over all 3,001 frames.
  - 0 GT frames with any pair closer than 0.18 m (robot-robot only). The GT contact lists are hard-coded empty and are not evidence (corrected 2026-11-15, see erratum).
  - 0 floor stops (`hard_contact_floor_m=0.2 pairs=`).
  - 0 `stale_pose_unsafe` lines. 14,446 ordinary `min_distance_violation` latch lines, which is in the range expected for a jammed episode.
- **Key-on lines.** All zero in `m4.log`:
  - `plan continue partners not honoured` 0, `rejected leg not a member` 0, `latch waiver armed` 0, `latch waiver revoked` 0.
  - The scorer's `keyon` counters are all 0, with no deadline-ended commands and no key-on stalls.
- **M4 startup line.** It appears once and ends in `hard_contact_floor_m=0.2 exempt_actions=reverse,yield scoped_clearing_exemption=True waiver_closing_tolerance_m=0.05 waiver_closing_readings=3`.

### Counting

The scorer applies the invalid-jam rule (`score_ibs.py`, amendment) and writes `summary_rerun/`:

- e02 a1 is listed as `EXCLUDED:invalid_jam` (`RERUN_RULE e02: ib10S_e02_armC_a1 recorded ran, status invalid_jam -> EXCLUDED:invalid_jam`).
- a2 is the slot's counted attempt (`RERUN_RULE e02: counted attempt ib10S_e02_armC_a2`).
- `attempts.tsv` is not edited. `vm_rerun/attempts.tsv` still records the a1 row as `ran`; its first 11 lines are byte-identical to `vm/attempts.tsv`. It adds one row: a2, `ran`.

### Pooled Arm C, Before and After the Re-run

| | Before (original report) | After the re-run |
|---|---|---|
| Slots run / attempts | 5 slots, 5 attempts | 5 slots, 6 attempts (e02 a1 excluded as `invalid_jam`) |
| Valid jams, counted | 4 | 5 |
| Resolved | 4/4 valid (4 of 5 slots) | 5/5 |
| Arrivals | 16/16 valid | 20/20 counted |
| Time from onset (s) | 115.5, 118.5, 118.6, 118.6 (mean 117.80) | 115.5, 118.1, 118.5, 118.6, 118.6 (mean 117.86) |
| Lowest GT pair (m) | 0.2965 (e10) | 0.2965 (e10); a2 0.3060 |
| Floor stops / GT pair frames < 0.18 m (corrected 2026-11-15, see erratum) | 0 / 0 | 0 / 0 |
| Attribution | `m3_default` 4 | `m3_default` 5 |
| Recede first | robot_4: e04, e06; robot_3: e08, e10 | robot_4: e04, e06; robot_3: e08, e10, e02 a2 |
| Spend | $0 | $0 |

Arm A is unchanged: 5/5 (follow-up only, 4/4), mean 115.96 s.

The interpretation above does not change. Both arms resolve every valid episode, and the times are within a few seconds of each other. This holds with the same caveats: n = 5 per arm, near-repeat episodes in about four trajectories, Arm C given the strategy and robot set, and the re-run decided after the results were seen. No p-values and no intervals.

### Re-run Kit Change and Evidence Integrity

- **Kit change.** Addendum section 13.4 gives the file list and the old and new md5s. The change has four parts:
  - a `rerun` mode in `chain_ibs.sh` and `run_ibs.sh`;
  - the invalid-jam rule in `score_ibs.py`;
  - the new reporting-only `startup_check_ibs.py`;
  - a dry test extended to the new path, which ended `TEST_DRY_IBS OK` before and after the amendment commit.
- **Diff.** `summary_rerun/kit_change_rerun_20261114.diff`, md5 `1add02a432024c983117783d1209c096`. The previous md5 lists are beside it: `kit_md5_ibs.txt` `72358e80fb040861fc8fdac27ca5a67b` and `kit_md5_all_ibs.txt` `0db47b478920d42da89ea1418c79964f`.
- **Original evidence.** The re-run did not write any original evidence file:
  - The VM tree was pulled into `vm_rerun/`.
  - `runs/` was pulled with `--ignore-existing`.
  - The ledger and summary went to new files.
- **Original manifest check.** `MANIFEST.md5` (md5 `da6f3283bd6fba9e6b5d4ec431732916`, unchanged) was re-checked after the run. It covers 426 evidence files in 95 file lines and 20 bundle lines.
  - 107 of its 115 lines match.
  - The 8 that differ are exactly the changed kit files: `kit/README.md`, `kit/chain_ibs.sh`, `kit/kit_md5_all_ibs.txt`, `kit/kit_md5_ibs.txt`, `kit/mac_kit_md5_ibs.sh`, `kit/run_ibs.sh`, `kit/score_ibs.py`, `kit/test_dry_ibs.sh`.
  - All 20 bundle lines match, including e02 a1.
  - The original archive is unchanged (md5 `9cc5c5da3476924d110d4e0f3e0d640d`).
- **Supplementary manifest.** `data/logs/vm_runs/ib10_safety/MANIFEST_rerun_20261114.md5`, md5 `094488566cea5ee4c454fa305a337565`. It has 84 file lines and covers:
  - the a2 bundle, its `_backup_` directory and `.outer.log`;
  - `vm_rerun/` and `summary_rerun/`;
  - `driver_rerun_20261114T105336Z.log`, `wallclock_ledger_rerun.tsv` and `RERUN_STARTED_20261114T105336Z`;
  - the 9 changed or added kit files.
- **Supplementary archive.** `data/logs/vm_runs/ib10_safety_rerun_archive_20261114.tar.gz`, md5 `09d761d17edf01d9eb51ee8e58897baa`, 2,219,545 bytes, 85 files (the 84 above plus the manifest). It contains no `known_hosts` file and no `._*` files.
- **Secret check.** The same count-only scan as the original was run over the new files, and every pattern was 0.
- **Summary files.** `summary_rerun/summary.json` md5 `8a4350379c3134ea93ccb82c6b993215`; `summary_rerun/episodes.jsonl` md5 `ff1e4453cdb4cf6ed0f34c0ec040a158`.

### Verified and Copied in This Section

**Verified from the raw a2 bundle:**

- map start-up;
- the decision artifacts: backend, model, tokens and provenance;
- the `m5.log` analysis and dispatch order and the command resolutions;
- arrivals, GT minimum and frames under 0.18 m;
- floor stops, key-on lines and the M4 startup line;
- `CONDITION.txt` and `RESTORE.txt`;
- the restore lines in the driver log;
- the VM `TERMINATED` status, read separately with `gcloud ... describe` after the driver exited.

**Copied from the scorer:** onset, `jam_valid`, frozen `resolved`, rank and success. Onset and time from onset were cross-checked against our arrival times.

### Open Items After the Re-run

- Why the e02 a1 `map_server` configure response was dropped is still unknown. One clean re-run does not show it cannot recur.
- `startup_check_ibs.py` reports the fault but is not a gate. Making it a gate for future runs would need a new registration.

---

## Artifacts

All under `data/logs/vm_runs/` (gitignored); `ib10_safety/` below means `data/logs/vm_runs/ib10_safety/`.

- `ib10_safety/summary/summary.json`, `ib10_safety/summary/episodes.jsonl`
- `ib10_safety/vm/attempts.tsv`, `ib10_safety/vm/chain_ibs.log`, `ib10_safety/vm/chain_ibs.20261114T061821Z.log`, `ib10_safety/vm/probe.log`, `ib10_safety/vm/pins_run_last.log`, `ib10_safety/vm/deploy/`, `ib10_safety/wallclock_ledger.tsv`
- `ib10_safety/driver_smoke_20261114T054535Z.log`, `ib10_safety/driver_follow_20261114T061349Z.log`, `ib10_safety/SMOKE_CHECK.txt`, `ib10_safety/SMOKE_ACCEPTED`
- `ib10_safety/runs/ib10S_e01_armA_a1` ... `ib10S_e10_armC_a1` (10 bundles, each with `decisions/`, `gt/ground_truth.jsonl`, `m4.log`, `m5.log`, `nav2_r1.log` to `nav2_r4.log`, `launcher.log`, `ARM_CHECK.txt`, `CONDITION.txt`, `RESTORE.txt`); `runs/ib10S_e02_armC_a1` is the invalid-jam bundle
- `ib10_safety/kit/` (scripts, overlays, `kit_md5_ibs.txt`, `kit_md5_all_ibs.txt`), `ib10_safety/MANIFEST.md5`
- `ib10_safety_archive_20261114.tar.gz` (same directory level as `ib10_safety/`)
- Registration: `docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md`
- 2026-11-13 reference, branch `feat/ib10-live-resolution`: `docs/reports/2026-11-13-ib10-live-resolution-results.md`
- Re-run (2026-11-14): `ib10_safety/runs/ib10S_e02_armC_a2`, `ib10_safety/vm_rerun/`, `ib10_safety/summary_rerun/`, `ib10_safety/driver_rerun_20261114T105336Z.log`, `ib10_safety/wallclock_ledger_rerun.tsv`, `ib10_safety/MANIFEST_rerun_20261114.md5`, `ib10_safety_rerun_archive_20261114.tar.gz`
