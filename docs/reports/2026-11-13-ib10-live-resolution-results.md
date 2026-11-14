# IB10 Live Resolution Experiment - Results

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: results of the 10-episode, two-arm IB10 live resolution experiment run on 2026-11-13 under the registration in `docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md`.

---

## Purpose

The experiment asks whether the full Layer 2 pipeline (M5 trigger, live M2, M3 `junction_clear` grounding, phased M4 dispatch) physically clears the four-way `intersection_bottleneck` (IB10) jam that stays frozen when Layer 2 is off. It is exploratory and is never pooled with the preregistered v3 experiment. All definitions below are the frozen ones: criteria from `docs/reports/2026-10-03-step7b-oracle-freeze.md` ("IB10 scoring frozen"), censoring from spec section 4, attribution from spec section 6 and the exemption caveat from spec section 7.

The claim this report supports is narrow: **the VLM + grounding pipeline clears the four-way jam that the Layer-1-only system never clears**. It does not support "the VLM's plan clears the jam" (see Limitations).

---

## Design

- Scene: `isaac/config/scenarios/intersection_bottleneck.yaml` (md5 prefix `042802d6`), 4 robots, one per arm, 300 sim-s horizon, seed label 42, no pose jitter.
- Runtime: git `68e67b5` as deployed on the VM; no code was deployed. The kit adds only the IB10 USD, the 0.20 m floor `safety.yaml` (`c41913f0`) and a per-episode overlay, and restores the v3 pin after each invocation.
- Arm A: Layer 2 on, live `gemini-robotics-er-2-preview` (ER-2). Arm B: Layer 2 off (`reasoning_enabled: false`).
- 5 counted episodes per arm, interleaved e01 A, e02 B, ... e10 B. e01 ran as a smoke episode first.
- Success: frozen `resolved` (criterion 1 jam valid and criterion 6 all four arrived), zero floor stops, GT minimum pairwise distance after t0 of at least 0.18 m.

All times are sim-seconds unless a clock time is given. "Onset" is `formed_jam.onset_sec`; "time to resolution" is the last arrival minus onset; unresolved episodes are censored at 300 s minus onset.

---

## Results

### Per-episode table

Episodes e01 to e10 in registered order. e01 appears twice because attempt a1 was excluded (see below). Every bundle had a valid formed jam (criterion 1) and 0 floor stops and 0 GT contact frames.

| Slot | Arm | Attempt | t0 / onset | First dispatch (strategy, provenance) | Arrivals | Resolved | Time from onset | GT min pair (m, pair, t) | Est. USD |
|---|---|---|---|---|---|---|---|---|---|
| e01 | A | a1 (EXCLUDED) | 18.0 / 28.1 | 30.7 `junction_clear`, `m3_default` | 4/4 | yes | 116.9 | 0.3160 r1+r3 @28.2 | 0.0057 |
| e01 | A | a2 | 17.7 / 27.6 | 30.5 `junction_clear`, `repaired` | 4/4 | yes | 116.5 | 0.3109 r2+r3 @27.7 | 0.0106 |
| e02 | B | a1 | 17.4 / 27.6 | none | 0/4 | no | censored (272.4) | 0.3120 r1+r4 @27.6 | 0 |
| e03 | A | a1 | 16.3 / 26.9 | 29.3 `junction_clear`, `repaired` | 4/4 | yes | 112.9 | 0.3079 r2+r4 @26.5 | 0.0109 |
| e04 | B | a1 | 17.5 / 27.6 | none | 0/4 | no | censored (272.4) | 0.2856 r2+r3 @27.7 | 0 |
| e05 | A | a1 | 18.4 / 28.5 | 31.4 `junction_clear`, `repaired` | 4/4 | yes | 116.6 | 0.3007 r1+r4 @28.6 | 0.0060 |
| e06 | B | a1 | 17.1 / 27.4 | none | 0/4 | no | censored (272.6) | 0.3136 r2+r3 @27.4 | 0 |
| e07 | A | a1 | 18.0 / 28.1 | 30.6 `junction_clear`, `repaired` | 4/4 | yes | 115.5 | 0.3382 r2+r3 @28.1 | 0.0060 |
| e08 | B | a1 | 17.1 / 27.3 | none | 0/4 | no | censored (272.7) | 0.3258 r1+r4 @27.3 | 0 |
| e09 | A | a1 | 17.6 / 28.5 | 31.3 `yield`, `m3_default` (then 108.0 and 244.6 `junction_clear`, `m3_default`) | 0/4 | no | censored (271.5) | 0.2633 r1+r2 @295.5 | 0.0294 |
| e10 | B | a1 | 17.4 / 27.4 | none | 0/4 | no | censored (272.6) | 0.3247 r2+r3 @27.4 | 0 |

In the four resolved counted Arm A episodes the closest approach is the jam pose at formation, before the first dispatch (0.30 to 0.34 m); the manoeuvre opened distance. e09 is the only episode in which a manoeuvre produced the minimum.

### Pooled per arm

| | Arm A (VLM on, ER-2) | Arm B (Layer 2 off) |
|---|---|---|
| Counted episodes | 5 | 5 |
| Resolved (frozen) | 4/5 | 0/5 |
| Success (also 0 floor stops, no GT contact) | 4/5 | 0/5 |
| Arrivals | 16/20 | 0/20 |
| Time from onset (s) | 112.9, 115.5, 116.5, 116.6; e09 censored (271.5) | all five censored (272.4 to 272.7) |
| Lowest GT pairwise distance | 0.2633 m (e09) | 0.2856 m (e04) |
| Floor stops / GT contacts | 0 / 0 | 0 / 0 |
| Attribution | `repaired` 4, `m3_default` 1 (e09), `vlm_verbatim` 0 | `none` 5 |
| Est. spend, counted | $0.0629 | $0 |

Including the excluded a1 attempt, Arm A resolved in 5 of 6 attempts. That figure is descriptive only and is not the counted result.

### The excluded attempt

`ib10L_e01_armA_a1` is excluded by the registered harness-failure rule (spec section 5) with outcome `harness_fail:condition`. The kit's condition gate (`cond_ib.py`) checked the model id against `diagnostics.backend_id` (value `gemini`) instead of `diagnostics.served_model` (value `gemini-robotics-er-2-preview`), so the gate failed a correct episode. The chain stopped at 16:17:30 UTC and the VM was restored and terminated.

- Facts (verified from `vm/attempts.tsv`, the driver logs and the bundle): the episode itself resolved (4/4, 116.9 s from onset, rank (1, 4, 4)), 0 floor stops, GT min 0.3160 m, one `junction_clear` dispatch with provenance `m3_default`, est. $0.0057.
- Fix: two lines in `cond_ib.py` (`backend_id` replaced by `served_model` in the model-id set and its docstring). Kit file-list md5 changed from `5548cb600539bd5b6b1c8ccdafae1631` (smoke driver, a1) to `8c7641cebd601aba203646b4809d5625` (smoke driver a2 and the follow-up driver). The owner accepted the smoke result after a2 (`SMOKE_ACCEPTED`).
- a2 re-ran the same slot under a new attempt label as spec section 5 allows. The a1 result was not selected or hidden: it also resolved, and it is the only Arm A episode in which M3's default plan, rather than an edited model plan, was dispatched and resolved the jam.

### Arm B proof of condition

- Verified from each Arm B `ARM_CHECK.txt`: `arm=B False False False 0.33 -1 config/rag.yaml True`, overlay md5 prefix `14c19b7b` (the Arm A overlay plus `reasoning_enabled: false`).
- Verified from the `COND` line of each Arm B episode in the driver log: `artifacts=0 analyses=0 dispatched=0 backends=none models=none l2off_status=1`, `scene_lines` 973 to 999, `floor_armed=True handoff_guard=True m5_session=True`. There is no cost log and no probe for any Arm B episode.
- Verified from GT: after t = 32.6 s the maximum robot speed is 0.0006 to 0.0008 m/s in all five episodes, final distance to goal is 1.97 to 2.07 m, and 0 of 20 robots arrived. Robots stop at jam formation (onset 27.3 to 27.6), about 10 s after t0, and never move again.
- Verified for e02 by direct count: M4 logged `safety stop ... reason=min_distance_violation` 55,415 to 55,427 times per robot, from jam formation to the last M4 line. Counts for the other Arm B episodes (about 56,100 to 56,300 per robot) are copied from the run agent's extraction. That Layer 1 has no release for this latch without Layer 2 is a property of the M4 design stated in the task brief; this report does not re-verify it in code.

### e09 failure narrative

Facts, each verified from the e09 bundle (`decisions/*.json`, `m5.log`, `gt/ground_truth.jsonl`, `cost.log`) unless marked:

1. Trigger 1, sim 31.3 s. ER-2 answered `yield` (robot_1 yields to robot_2), unlike the four resolved episodes where the first answer was `junction_clear`. M3 rejected the plan (`rejection_reason`: "repair distance exceeds bound 4") and dispatched its default plan, a 2-robot `yield`. This decision carries a `stage2` retreat-choice block.
2. Trigger 2, sim 108.0 s. ER-2 answered `junction_clear` naming only robot_2 and robot_4; its `crossing_order` was a non-permutation (degradation `crossing_order=default:non_permutation`) and M3 again rejected the plan ("repair distance exceeds bound 4"). M3's default plan was a 2-robot `junction_clear` (degradation `junction_clear=recede`): a recede phase for robot_4, then a "cross" phase holding robot_2 in `temporary_wait` for 8 s ("yield refused: no other involved robot to pass") and robot_4 for 120 s. No leg commands any robot to cross.
3. GT: all four robots had speed at most 0.02 m/s for one continuous interval of 120.1 s, from 120.1 s to 240.2 s. `m5.log` logs the cross phase as `completed=True phase_reached=resolved done=True`, with zero arrivals.
4. Trigger 3, sim 244.6 s. ER-2 answered `junction_clear` with `proposed_plan: null` (degradation `proposed_plan=default:invalid_structure`); M3 reports "plan absent" and dispatched its default 4-robot `junction_clear` (recede robot_4, recede robot_3, release phase). The same phase structure produced the 4/4 arrivals in the resolved episodes.
5. At 300 s robot_2 was 0.37 m from its goal, moving at 0.091 m/s; robots 1, 3, 4 were 2.74, 2.76 and 2.94 m from their goals and still. The 0.2633 m minimum (robot_1 and robot_2, 295.5 s) occurred while `robot_1+robot_2` was the active exempt pair; M4's last `exempt pairs changed` line is `robot_1+robot_2` and was never followed by `-`.

Inference, not verified:

- The failure is not explained by provenance alone, because the excluded a1 also ran on `m3_default` and resolved.
- A plausible cause is the off-pattern first answer (`yield`) followed by a degenerate 2-robot `junction_clear` that held the scene idle for about 120 sim-s, leaving too little horizon for the third dispatch to finish. The 120 s idle interval matches the 120 s `temporary_wait` in the phase, which supports (but does not prove) that the wait timer, not a failure, ended the phase.
- robot_2 would likely have arrived within seconds; the release phase for the other three robots would not have finished within the horizon. Not tested.

### Episode similarity

Verified by recomputation from GT (position RMS over the four robots, aligned on each episode's first-motion t0, 0.1 s sampling). The run agent's own extraction gave slightly different values because of its alignment (both listed).

- Arm B: pairwise RMS over [60 s, end) is 0.028 to 0.061 m for all 10 pairs (agent: 0.028 to 0.061 m over the same window). The five episodes are repeats of one frozen state.
- Arm A branches, defined by which robot M3 recedes first (verified from `m5.log` command ids and the dispatched release pull-off):
  - robot_4 first, pull-off +0.33 m: e01 (a1 and a2) and e07. RMS e01 a2 vs e07: 0.194 m (agent 0.200).
  - robot_3 first, pull-off -0.33 m: e03 and e05. RMS 0.247 m (agent 0.295).
  - Between these two branches: 0.424 to 0.476 m (agent 0.411 to 0.475), with equal resolution time (112.9 to 116.6 s).
  - e09 differs from all of them (RMS 2.05 to 2.10 m; agent 1.97 to 2.03 m): first answer `yield`, then a degenerate plan.
- So Arm A is about three distinct trajectories, two of them represented by two near-duplicate episodes each, and one by e09. Before dispatch all ten episodes look alike (t0 16.3 to 18.4 s, onset 26.9 to 28.5 s, first dispatch 29.3 to 31.4 s).
- What picks the recede order is not identified: `dispatch_order_source` is `chi` in all of them (open item).

### Cost

- Counted Arm A est. $0.0629 (0.0106 + 0.0109 + 0.0060 + 0.0060 + 0.0294, re-derived from `episodes.jsonl`); excluded a1 est. $0.0057; total est. $0.0686 of the $3.00 cap. Arm B made no model calls.
- These are `cost_watch.py` estimates from token usage, not invoices. The pre-episode Gemini probe call is not included in them. Every Arm A probe (6 episodes) returned `http=200 verdict=OK` (verified in the chain and driver logs; no 429 or 402).
- e09's `cost.log` records `billed_calls=4` for 3 artifacts. The call count steps by 2 at the first artifact, then by 1 at each of the next two. The first decision is the only one with a `stage2` retreat-choice block, so the extra billed call is probably that second-stage call. This is an inference from the step pattern and the decision file, not from a provider log.

### Timeline

Times are UTC on 2026-11-13, from `driver_*.log`, `vm/chain_ib.log` and `vm/attempts.tsv` (verified).

| Event | Time |
|---|---|
| Smoke driver 1 starts; VM started | 15:49:34; 15:54:03 |
| e01 a1 ends (condition gate failed), VM terminated | 16:17:30; 16:19:36 |
| Smoke driver 2 starts; VM started | 16:21:54; 16:24:13 |
| e01 a2 ends, VM terminated | 16:47:54; 16:50:07 |
| `SMOKE_ACCEPTED` written | about 16:56 |
| Follow-up driver starts; VM started | 16:56:27; 16:56:40 |
| e02 to e10 end (per `attempts.tsv`) | 17:23:48, 17:42:47, 18:05:39, 18:24:40, 18:47:36, 19:06:38, 19:29:34, 19:51:31, 20:14:27 |
| `CHAIN_IB DONE` | 20:14:28 |
| `RESTORE_IB OK`; VM `TERMINATED` (verified by the driver) | 20:15:27; 20:17:14 |

The follow-up VM was up 3 h 20 m 34 s against a 6 h cap. Each Arm B episode took about 22.5 min and each Arm A episode about 18.5 min (e09 about 21.5 min); these wall-clock figures are copied from the run agent's extraction and agree with the `attempts.tsv` end times to within a minute.

---

## Verification status

| Item | Status |
|---|---|
| Outcome, arrivals, times, GT min, cost, attribution counts | Verified: `summary/summary.json` and `summary/episodes.jsonl`; arrival-time arithmetic and GT minima recomputed from `gt/ground_truth.jsonl` |
| 0 floor stops, 0 GT contact frames | Verified: zero stop lines in `m4.log` (startup line `hard_contact_floor_m=0.2` present in every bundle); zero contact frames in every GT file |
| e09 sequence, plans, provenance, 120.1 s idle window | Verified from bundle |
| Arm B speeds, final distances | Verified from GT |
| Arm B latch line counts | e02 verified; other Arm B counts copied |
| Similarity RMS | Recomputed; differs slightly from the agent (both given) |
| Per-episode wall clock | Copied (cross-checked against `attempts.tsv`) |
| Reasons for the e09 failure, the e09 4th billed call | Inference, labelled as such |

One value in the run agent's report differed from the re-derived one: it put the all-robots-still interval in e09 at about 130 to 244 sim-s (about 115 s); the recomputation with a 0.02 m/s threshold gives 120.1 to 240.2 s (120.1 s). Its `ib10L_e09` figure of "the 4th billed call unidentified" is narrowed above but still unconfirmed.

---

## Reproducibility

| Item | Value |
|---|---|
| Runtime commit | `68e67b5` (`feat/v3-integration`); the VM matched it on the IB10-path files (`vm/pins_run_last.log` all `ok`) |
| Registration | `docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` at `50704c2` |
| Model | `gemini-robotics-er-2-preview`, verified from `diagnostics.served_model` in every Arm A artifact; recorded `reasoner_config_effective.temperature` is 0.6 (not verified whether the provider honours it) |
| Scene yaml md5 | `042802d6b3980ce6591b0f5b343c85cd` (all 11 bundles) |
| IB10 USD md5 | `1d185bb0f4d56618b7ee6af92742c365` (all 11 bundles) |
| `orchestrator.yaml` / `rag.yaml` md5 | `1f656533a30a35882d57d0d64a57bd0d` / `e18c723cff9cada3f320d564c2ecee5a` (installed equals pristine in every `RESTORE.txt`) |
| Floor `safety.yaml` md5 prefix | `c41913f0` (`config/safety/safety_floor020.yaml`); original `safety.yaml` restored to `598396622ca50baddc3e19b4608fa3e3` |
| Overlay Arm A / Arm B md5 | `0196f1e8db0ffb9553c166707441362d` / `14c19b7b64161a00d67064d05016ca64` |
| Source overlay | `kit/src/ib10_remedy_orchestrator_0d0cfbfa.yaml`, md5 `0d0cfbfa67c4b3f56257b9c3b763d5fe` |
| Kit file list `kit_md5_ib.txt` md5 | `8c7641cebd601aba203646b4809d5625` (final; `5548cb600539bd5b6b1c8ccdafae1631` during a1) |
| Kit file md5s | listed in `kit/kit_md5_ib.txt` and in `MANIFEST.md5` (every file under `kit/`, `summary/`, `vm/`, the driver logs, one line per run bundle) |
| `MANIFEST.md5` md5 | `578f75294cdfb349ea5fdf37ea27760b` |
| Archive | `data/logs/vm_runs/ib10_live_archive_20261113.tar.gz`, md5 `4d0b2c547bb3daa2d46136d4d5e9cc54`, 26,706,038 bytes, 421 files |

The archive holds `kit/`, `summary/`, `vm/`, `runs/`, the three driver logs, `SMOKE_ACCEPTED` and `MANIFEST.md5`; it omits only `known_hosts_ib`. No evidence file was modified; `summary/score_ib.diff` was added.

Secret check on the archived tree (counts only, nothing printed): 0 files match Google API key, `sk-`, GitHub token, bearer token, private-key block, `key=` URL parameter or `*_KEY=value` patterns. Two files (`kit/gemini_probe_ib.py`, `kit/gemini_probe_ib.sh`) mention the header name `x-goog-api-key` or `API_KEY` as code and contain no key value.

The mid-run scorer change is preserved as `summary/score_ib.diff` (md5 in `MANIFEST.md5`). It adds counting by `vm/attempts.tsv`: per slot only the attempt recorded `ran` is counted, every other attempt is scored and listed as excluded with its outcome, and a slot with zero or several `ran` attempts raises a `SLOT_FLAG`. The summary gains `counted`, `excluded`, `excluded_attempts` and `excluded_est_usd`; cost reading tolerates a missing value; a new `--attempts` option defaults to `<runs>/../vm/attempts.tsv`. The change affects counting and presentation only, not the frozen scoring functions. It was made after the smoke episode and before the follow-up; `summary/summary.json` and `episodes.jsonl` come from the final scorer.

---

## Limitations

- **n and independence.** n = 5 per arm, one scene, one seed family, no pose jitter. Arm B is five repeats of one frozen state (pairwise RMS below 0.07 m). Arm A is about three distinct trajectories. The episodes are not independent samples, so no p-value is given. No interval is given either.
- **What the claim covers.** The supported claim is "the VLM + grounding pipeline clears the four-way jam that the Layer-1-only system never clears". It is not "the VLM's plan clears it": no plan was executed verbatim (`vlm_verbatim` = 0; 4 repaired by M3, 1 replaced by M3's default), and the excluded a1 resolved on M3's default plan. The experiment cannot separate whether a trigger with M3's default alone, with no VLM, would do equally well. That ablation was not run.
- **Arm B is a deterministic baseline.** Its outcome follows from the min-distance latch having no release without Layer 2, not from a competing method. The B to A contrast is pipeline on versus pipeline off, not a comparison with a classical coordinator.
- **Open safety-exemption caveat (spec section 7).** One command exempts every pair of robots inside it from M4's proximity check. e09's closest approach (0.2633 m) occurred inside a still-exempt pair that was never cleared. It stayed above the 0.18 m contact criterion and the 0.20 m floor, but the proximity latch did not cover that pair. A fix exists on branch `fix/safety-exemption-scope` (default off, tip `f2a578d`); it was not used in this run. Trace: `docs/reports/2026-11-13-safety-exemption-trace.md` on branch `feat/v4-per-cluster-parity`.
- **Simulation, exploratory, kit changes.** Isaac Sim only, sim-seconds, no hardware. The kit had a bug (the condition gate, above) fixed once between smoke attempts, and the scorer gained attempt-aware counting before the follow-up. The Arm A model output is not deterministic (recorded temperature 0.6), so the Arm A branch structure may differ on a rerun.

---

## Open Items

- **e09 degenerate plan.** A 2-robot `junction_clear` with no cross leg was marked `phase_reached=resolved done=True` with zero arrivals after its 120 s wait. This looks like an M3/M5 grounding and phase-completion gap and has not been investigated.
- **Recede-order branching.** The recede order and pull-off sign differ between otherwise near-identical Arm A runs; what drives it is not identified.
- **e09's fourth billed call.** Probably the `stage2` retreat-choice call on the first decision; unconfirmed (no provider-side log).
- **Exemption scope.** Unresolved on this branch; see Limitations.
- **No-VLM ablation.** An M3-default-only arm was not run.

---

## Artifacts

All under `data/logs/vm_runs/` (gitignored); `ib10_live/` below means `data/logs/vm_runs/ib10_live/`.

- `ib10_live/summary/summary.json`, `ib10_live/summary/episodes.jsonl`, `ib10_live/summary/score_ib.diff`
- `ib10_live/vm/attempts.tsv`, `ib10_live/vm/chain_ib.log`, `ib10_live/vm/pins_run_last.log`, `ib10_live/vm/deploy/`
- `ib10_live/driver_smoke_20261113T154933Z.log`, `ib10_live/driver_smoke_20261113T162154Z.log`, `ib10_live/driver_follow_20261113T165627Z.log`, `ib10_live/SMOKE_ACCEPTED`
- `ib10_live/runs/ib10L_e01_armA_a1` ... `ib10L_e10_armB_a1` (11 bundles), each with `decisions/`, `gt/ground_truth.jsonl`, `m4.log`, `m5.log`, `ARM_CHECK.txt`, `CONDITION.txt`, `RESTORE.txt`, `cost.log`
- `ib10_live/kit/` (scripts, overlays, `kit_md5_ib.txt`), `ib10_live/MANIFEST.md5`
- `data/logs/vm_runs/ib10_live_archive_20261113.tar.gz`
- Registration: `docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md`
