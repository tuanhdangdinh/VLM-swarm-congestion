# Layer-2-Off Pilot: Does the Reactive Layer Alone Resolve Our Congestion Cells?

**Prepared:** 2026-10-06

**Revision history:**

- Initial draft: the four registered no-intervention episodes (head-on, B1, B3, IB10; seed 42, mock no-congestion decision layer) on the v2 tree `b5cafe4`, per-episode measurements, the comparison against each cell's best-known intervened episode, and the recommendation under the registered decision branches.
- Rev 2: review corrections. The analysis cadence is in wall time, not sim time. B3's intervened references are scripted-oracle (no live B3 episode exists), and the two v2-lineage battery-v2 harvest runs are added. The censored-over-censored B1 ratio is removed. The motion and mechanism claims are narrowed. Pairing and independence caveats are added to the run counts.

---

## Summary

This is the registered layer-2-off pilot. Its contract is the "Layer-2-off pilot (registered 2026-10-06, PILOT — excluded from confirmatory counts)" block of `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` in the main checkout. It is a PILOT, so every episode is excluded from every confirmatory count.

- **Matrix:** all four episodes ran as registered, once each: head-on `head_on_asymmetric_w0p2_eopen_bshort_o0`, B1 `bottleneck_merge`, B3 `convoy_counterflow_slip` and IB10 `intersection_bottleneck`. Seed 42, `RECORD=0`, zero API calls. The VM ran the v2 branch tip `b5cafe4`, not the parked v3 costmap fix. No run was repeated or discarded.
- **Silencing held in every episode.** M2 answered `congestion_detected=false` on every one of 230 analyses (50 / 39 / 65 / 76). There were 0 dispatches in M5's log, 0 `command received` lines in M4's log, and 0 decision artifacts with a grounded command. The analyses did fire: the first came 2.4–5.0 sim-s after the conflict onset, then once per 15 s M5 cooldown until the horizon. The cooldown runs on M5's wall clock, which is ≈ 3.5–5.6 sim-s by artifact stamps.
- **Every cell latched and stayed clogged at the registered horizon.** Each cell's robots came inside M4's 0.45 m latch 0.4–0.9 s before the GT conflict onset, at 0.27–0.39 m. No robot moved again once latched. Late releases (B1 robot_3, B3 robot_3/robot_4) moved only until they latched onto the queue. 0 of 13 robots arrived, `conflict_dissolution` is censored in all four, and the 0.45 m separation never recovered. All four classify `clogged`.
- **Deliverable sentence:** *Without the decision layer, 4 of 4 cells never resolve at the registered horizon (0/13 robots arrive; every cell is frozen in the M4 latch within 1 s of the conflict onset). With it, 3 of 4 resolve: head-on and IB10 under live ER-2 decisions, and B3 under a scripted oracle decision (no live B3 episode exists yet). B1 is the exception: its intervened episodes are themselves clogged by the registered stage-2 rank-0 defect. The censored delay lower bounds are ≥ 531 s against 150 s (head-on), ≥ 799 s against 238 s (B3) and ≥ 1026 s against 457–503 s (IB10). Each lower bound is 2.0–3.5× the intervened delay and is still growing at the horizon.*
- **Decision branch:** the result matches the registered expectation (latch/clog everywhere). No cell self-resolved, so there is no design finding to send to the owner. **Recommendation: register the full no-intervention arm into collection** (run counts below).
- **VM:** pristine after the pilot. Configs are back to `1f656533…` / `e18c723c…`, the installed tree is byte-identical to the pre-pilot snapshot, `pgrep` is empty and the GPU is at 0 % / 171 MiB. The VM is left RUNNING at `b5cafe4`, as found. VM time: 08:11–10:01 UTC.

---

## Apparatus

### Silencing mechanism

- **Mechanism:** `BACKEND_ID=mock` with `MOCK_DECISION_FILE` and `MOCK_RETREAT_CHOICE_FILE` both empty. In that case `build_backend("mock")` returns a bare `MockBackend()` (`reasoning/vlm/backend_factory.py`). Its built-in `_DEFAULT_RESPONSE` is `congestion_detected: false`, `strategy: none` on every call (`reasoning/vlm/mock_backend.py`).
- **Why no mock file:** `config/mock_decisions/` has no none-forever script. The built-in default is a constant, so no file was added and nothing new is committed.
- **Trap 3 does not apply.** That livelock needs a repeated *congestion* verdict. A no-congestion answer never dispatches.
- **M5 ran normally.** Stall and close/slow triggers fired, and each analysis returned `no dispatch stage=vlm reason=congestion_detected=false`. The 15 s cooldown (wall clock) then re-armed the trigger, ≈ 3.5–5.6 sim-s apart by artifact stamps. Stage 2 was never reached.

### Per-run gates (`_vm_driver/l2_run.sh` + `l2_chain.sh`; every gate passed in all four runs)

| Gate | Head-on | B1 | B3 | IB10 |
|---|---|---|---|---|
| `pgrep -f run_simulation` empty before launch | 0 s | 0 s | 0 s | 0 s |
| `GATE OK` (`logs saved to`) | ✓ | ✓ | ✓ | ✓ |
| M5 started (session line) | ✓ | ✓ | ✓ | ✓ |
| Installed `reasoning_backend_id` at 150 s (sidecar) | `mock` | `mock` | `mock` | `mock` |
| Analyses started = no-dispatch `congestion_detected=false` lines = artifacts | 50 | 39 | 65 | 76 |
| M5 `dispatch request=` lines / M4 `command received` lines | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Artifacts with `congestion_detected: true` / `grounded_command_present` / non-mock `backend_id` | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Provider-name mentions in m5.log (gemini/openai) | 0 | 0 | 0 | 0 |
| GT `completed: true`, last `sim_time_sec` = `duration_sec` | 300.0 | 200.0 | 260.0 | 300.0 |
| `RESTORE OK` (orchestrator src + installed `1f656533…`, rag `e18c723c…`) | ✓ | ✓ | ✓ | ✓ |

- **Horizon:** `REC_SEC` covered each scene (1300 / 1000 / 1600 / 1600 s). Isaac therefore finished `duration_sec` on its own every time. A truncated run would have aborted the chain as invalid; none was.
- **No PID kills:** the settle step found the process table clear after 10 s every time.

### Deploy and restore

- **Pre-deploy state:** the VM source tree was at `a8fc1bc` (the verbatim pilot's tree). Against a local `b5cafe4` manifest of 739 tracked non-doc files, exactly the expected six files differed:
  - `reasoning/rag/plan_metrics.py` and `reasoning/vlm/prompt_builder.py`, which are live-mounted at `/ws`;
  - four unit-test files.
- **The orchestrator.yaml exception:** the VM-pristine `orchestrator.yaml` (`1f656533…`, the prereg-v1 tag version) differs from the tip's (`11fb304a…`). This is the standing convention: every driver installs a full overlay over it, and restores it afterwards.
- **Deploy:** those six files were shipped by tar with fresh mtimes (`_vm_driver/l2_deploy.sh`). The post-deploy manifest differs from `b5cafe4` only at that orchestrator.yaml. No `ros2_ws/` source changed between `a8fc1bc` and `b5cafe4`, so no package was rebuilt.
- **Installed-vs-source check:** run read-only (`l2_instcheck.sh`) both before and after the pilot. Both times, 126/126 installed runtime files matched source and the full installed tree had 519 files. The post-run full-tree md5 manifest is byte-identical to the pre-run one, so no trap-19 launch-`.pyc` drift remained.
- **Container:** sees the deployed `prompt_builder.py` / `plan_metrics.py` md5s at `/ws/reasoning`.
- **Leftovers:** none of the four scenarios left a ground-truth directory under `data/logs/simulation/`.

### Cell configurations (`_vm_driver/gen_l2_overlays.py`; every key asserted by `yaml.safe_load`)

| Cell | Overlay (md5) | Configuration |
|---|---|---|
| Head-on | `ho_orchestrator.yaml` (`b571636a…`) | The verbatim pilot's head-on overlay, verbatim: the 2026-09-28 calibration apparatus. Goals are (2.6, 0) / (−1.5, 0), obstacles ON (`MODALITY=on`), and the arrival check is on. Gate, order and plan-channel settings have no effect under the mock. |
| B1 | `b1_orchestrator.yaml` (`7e4ba315…`) | The verbatim pilot's B1 overlay, verbatim: the registered goal row. robot_3 has `start_delay_sec` 80, the junction box has `half_length_m` 1.1 with arms, and the x band is [−0.46, 0.46]. |
| B3 | `b3_orchestrator.yaml` (`a6473853…`) + `b3_rag.yaml` (`63f50f91…`) | `scripts/vm/v2_overlay.py convoy_slip` applied to copies of the pristine files. This is the registered B3 goal row: four-robot `initial_tasks` with robot_3/robot_4 `start_delay_sec` 120, corridor `half_length_m` 0.5, and rag `grounding.mode: legacy`. |
| IB10 | `ib10_orchestrator.yaml` (`d1e11073…`) | The step-6 / plan-grammar calibration overlay, verbatim. It carries the junction fields (`junction_recede_offset_m` 1.2, `junction_backup_clearance_m` 1.1, `junction_recede_stagger_m` 0.2, `tracked_extent_m` 1.75). The gate does not matter because nothing dispatches. |

`start_delay_sec` runs on M5's wall clock. The actual releases are therefore read from GT own-departure: B1 robot_3 at sim 39.8; B3 robot_3/robot_4 at sim 50.8.

### Measurement

- **Committed scorers, branch tip:** `coverage_scene_scores.py` (`flow` for head-on, `b1`, `b3`, `ib10`) with `free_flow_v1`. The definition of `outcome_class` is unchanged: zero dispatches with every robot arrived would have classed `resolved`.
- **Session-local extras:** `_analysis/l2_analyze.py` computes the following, all from GT sim time:
  - latch evidence: per-row minimum pairwise distance, first time below 0.45 m, spells, and whether separation ever recovered for ≥ 1 s;
  - per-robot departure, last motion, path and final pose;
  - STALE streaks, via the scorer's `stale_streaks`;
  - M4 safety-stop line counts, as corroboration only (their stamps are not sim time);
  - analysis times.
- **Analysis times and the GT clock (trap 18):** analysis times were mapped to GT with a **per-run fitted** clock offset. The fit minimizes the median M1-vs-GT position error over fresh MOVING rows. The fitted offsets were 0.45 / 0.60 / 0.55 / 0.55 s, with median residuals 3.6–5.1 mm. No conclusion depends on the offset.

---

## Per-Episode Tables

All times are sim-s. "Latch" is the first GT instant at which some pair is below M4's 0.45 m `min_distance_m`.

### Outcome

| Cell | Class | Arrived | Conflict onset | Latch | Pair distance at latch hold | Separation ever recovers? | Frozen from → horizon | Analyses (first, last) | Dissolution / full resolution |
|---|---|---|---|---|---|---|---|---|---|
| Head-on | `clogged` | 0/2 | 22.1 | 21.7 | 0.343 m (r1–r2) | no (278.4 s below 0.45 m) | 22.0 → 300 | 50 (25.7, 297.7) | censored / censored |
| B1 | `clogged` | 0/3 | 27.9 (merge `perpendicular_latch`) | 27.0 | 0.394 m (r1–r2) | no (173.1 s) | 27.8 → 200 (r3 joins at 75.5) | 39 (30.9, 197.2) | censored / censored |
| B3 | `clogged` | 0/4 | 29.1 | 28.5 | 0.281 m (r1–r2); queue r3–r4 0.433 m | no (231.6 s) | 29.0 → 260 (r3/r4 stop at 54.9) | 65 (34.1, 257.3) | censored / censored |
| IB10 | `clogged` (formed-jam gate valid, onset 32.9 in [8, 40], 4 in radius) | 0/4 | 32.9 | 32.1 | 0.273 m (closest pair) | no (268.0 s) | 32.8 → 300 | 76 (35.3, 299.0) | censored / censored |

### Delay against free flow (`free_flow_v1`; every robot censored, so these are lower bounds charged to the horizon)

| Cell | Per-robot delay lower bound (s) | Sum lower bound (s) |
|---|---|---|
| Head-on | r1 ≥ 261.8, r2 ≥ 269.3 | **≥ 531.1** |
| B1 | r1 ≥ 162.5, r2 ≥ 164.3, r3 ≥ 129.7 | **≥ 456.5** |
| B3 | r1 ≥ 215.5, r2 ≥ 219.1, r3 ≥ 181.6, r4 ≥ 183.0 | **≥ 799.2** |
| IB10 | r1 ≥ 256.5, r2 ≥ 256.5, r3 ≥ 256.6, r4 ≥ 256.4 | **≥ 1026.0** |

### Trajectory evidence (GT)

| Cell | Robot | Departs | Last motion > 0.03 m/s | Final (x, y) | Distance to goal | Path (m) |
|---|---|---|---|---|---|---|
| Head-on | robot_1 | 13.2 | 22.0 | (−0.17, 0.00) | 2.77 | 1.34 |
| Head-on | robot_2 | 13.2 | 22.0 | (0.18, 0.00) | 1.68 | 1.34 |
| B1 | robot_1 | 16.8 | 27.8 | (0.69, −0.05) | 1.78 | 1.72 |
| B1 | robot_2 | 17.6 | 27.8 | (0.40, 0.22) | 1.52 | 1.60 |
| B1 | robot_3 | 39.8 | 75.5 | (0.06, −0.01) | 2.41 | 2.51 |
| B3 | robot_1 | 22.1 | 29.0 | (−0.14, −0.01) | 2.61 | 1.07 |
| B3 | robot_2 | 22.1 | 29.0 | (0.14, 0.00) | 2.14 | 1.06 |
| B3 | robot_3 | 50.8 | 54.1 | (−1.47, 0.05) | 3.93 | 0.45 |
| B3 | robot_4 | 50.8 | 54.9 | (−1.88, 0.18) | 3.73 | 0.62 |
| IB10 | robot_1 | 22.6 | 32.8 | (−0.19, 0.01) | 1.94 | 1.56 |
| IB10 | robot_2 | 22.6 | 32.8 | (0.21, 0.03) | 1.96 | 1.56 |
| IB10 | robot_3 | 22.7 | 32.9 | (0.03, −0.19) | 1.94 | 1.56 |
| IB10 | robot_4 | 22.7 | 32.8 | (0.02, 0.22) | 1.97 | 1.53 |

Notes on the tables:

- **The pattern is the same in every cell.** Nav2 drives each pair nose-to-nose into the aperture or junction. GT puts every pair inside M4's 0.45 m min-distance stop, and M4's continuous `min_distance_violation` lines show the stop holding. With no coordination command, no pair is ever exempted. The latch times above are a GT-distance proxy, not M4's own timestamps. That the stop is the proximate cause is the natural reading, but it is untested without M4: no run switched M4 off, so whether Nav2 alone would also deadlock in these apertures is not measured. From 1.5 s after the latch to the horizon, GT speeds stay ≤ 0.003 m/s (≤ 0.001 m/s outside B3) in all four cells; that is physics jitter, not motion. The r1–r2 distance in B3 drifts by 1 mm over 231 s.
- **The same latch also captures late joiners.** In B1, robot_3 is released at 39.8 and closes to 0.417 m from robot_2, then stops at 75.5. In B3, robot_3/robot_4 are released at 50.8; robot_4 closes the queue gap from 0.57 to 0.433 m within 4 s and both stop, still 1.33 m behind robot_1.
- **Corroboration (M4):** the `safety stop … reason=min_distance_violation` lines run continuously for every robot until the end: 59 k (head-on), 35–44 k (B1), 64–70 k (B3) and 70 k (IB10) per robot. There were 0 GT robot-robot contact rows in any episode.
- **STALE:** no episode is confounded. The longest streak is 3.9 s (B3 robot_1, 45 rows out of 874); every other robot is ≤ 0.33 s. The phantom `robot_17` seen in earlier B1 runs did not appear.
- **Aperture throughput (B1):** 0 of 3 exits. The aperture clogged within the horizon.
- **B3 `first_slipper` is not meaningful here.** The scorer reports `robot_4` at 51.1 s. That is the wall-clock hold-back release, not a slip through a cleared gate: robot_2 never clears it. The field is reported, not interpreted.
- **Arm B (classical shadow) is logging only, never dispatched.** Its strategy across the analyses was:
  - head-on: `yield` robot_2, the registered `correct_yielder`, in all 50 analyses;
  - B1: `reroute` in all 39;
  - B3: a mix of `yield` robot_1 / robot_2 and `reroute`;
  - IB10: `yield` robot_2 or robot_4.

  So the scene was decidable from the logged state, and only the decision layer was absent.

---

## Comparison Table: Layer-2-Off vs Best-Known Intervened Episode

Every intervened reference was re-scored with the same scorer and the same `free_flow_v1` table (`_analysis/score_refs.sh`, outputs under `_analysis/refs/`).

| Cell | Layer-2-off (this pilot, `b5cafe4`, s42) | Best-known intervened episode | Intervened outcome | Intervened delay (sum, s) | Intervened dissolution / full resolution (s) | Delay contrast |
|---|---|---|---|---|---|---|
| Head-on | `clogged`, 0/2, delay ≥ 531.1 | Verbatim pilot ep 1 `vp01` (ER-2, s42, same overlay md5 `b571636a…`, tree `a8fc1bc`, one `yield` dispatch). Pilot eps 2/3/5 agree, and gpt-4o ep 4 is `intermittent` 2/2. | `resolved`, 2/2 | 149.8 (eps 1–5: 147.4–153.3) | 69.1 / 107.8 | ≥ 3.5× |
| B1 | `clogged`, 0/3, delay ≥ 456.5 | The registered decision-scored smokes: verbatim pilot eps 6/7 (`vp06`/`vp07`, ER-2, same overlay `7e4ba315…`). Context: the 2026-09-30 older-tree mock-yield smokes (`b1_fix` B1FIX/SWFIX) | `clogged` 0/3 (`vp06`, `vp07`; stage-2 rank-0 defect, Rev 20/22 exclusion). Older smokes: `clogged` 2/3 (r1 and r2 arrive, r3 censored) | ≥ 456.3 / ≥ 457.4. Older: ≥ 242–256 | censored. Older: 93–100 / censored | none on v2 (both clog). Against the older 2/3 smokes: not comparable (both censored) |
| B3 | `clogged`, 0/4, delay ≥ 799.2 | **Scripted oracle decision only; no live B3 episode exists.** `B3DEMO_20260930_134023`: the demo 4-arrival run, mock `convoy_counterflow_oracle_order_once`, older tree, run under the v1 name `convoy_counterflow` with the same goal row (r3/r4 delay 120, corridor 0.5, rag legacy). Its GT is scored against the slip yaml, whose geometry is pinned byte-identical to v1 by `test_convoy_counterflow_slip_scenario.py`. Corroborated on v2 lineage by the 2026-10-04 battery-v2 harvest runs `b2_convoy_off` / `b2_convoy_on`, which use the same mock and the `convoy_slip` overlay. | `resolved`, 4/4 (harvest runs: `resolved` 4/4 ×2) | 237.7 (harvest: 233.9 / 239.6) | 137.8 / 178.8 (harvest: 138.1 / 173.9 and 138.4 / 179.7) | ≥ 3.4× |
| IB10 | `clogged`, 0/4, delay ≥ 1026.0 | Step-7b rerun 2 (mock, the deciding 4/4) and v2 demo ep 2 (live ER-2). Also verbatim pilot eps 8/9 (ER-2 v3.2) | `resolved`, 4/4 in all four | 503.3 / 490.5 (eps 8/9: 457.0 / 478.0) | 158.4 / 192.8 (demo ep 2: 155.3 / 190.3) | ≥ 2.0× |

Notes on the comparison:

- **Head-on and IB10:** the lower bounds are horizon-censored, and the layer-2-off robots are frozen. The true contrast is "never" against roughly 2 minutes, not a finite ratio. The ratios above are floors.
- **B1:** the v2 intervened reference is no better than layer-2-off. `vp06` (≥ 456.3 s) and this pilot (≥ 456.5 s) are indistinguishable, because the registered stage-2 rank-0 2× lateral defect sends the yielder into an infeasible retreat. Under the Rev 22 rule those episodes are decision-scored only and excluded from flow metrics. The B1 flow contrast therefore cannot be read until that defect is fixed. Even the older-tree mock smokes never delivered robot_3 inside the 200 s horizon.
- **B3 provenance:** every B3 reference is a scripted mock that replays the oracle order. It shows that the decision layer's execution path resolves B3 when it is handed the right answer. It does not show a model resolving B3. A search of `data/logs/vm_runs/` found no gemini or openai `convoy_counterflow*` episode. The demo is the older tree under the v1 name. The harvest runs are v2 lineage (2026-10-04) but not `b5cafe4` itself. All three agree within 6 s of total delay.
- **Reference GT clocks:** every comparison number is GT-derived, so no clock join is involved.

### Deliverable sentence

> Without the decision layer, **4 of 4** cells never resolve at the registered horizon: 0 of 13 robots arrive, and every cell freezes in M4's 0.45 m latch within 1 s of its conflict onset and never separates again. With it, **3 of 4** resolve: head-on 2/2 and IB10 4/4 under live ER-2 decisions, and B3 4/4 under a scripted oracle decision (no live B3 episode exists yet). B1's intervened episodes are themselves clogged by the registered stage-2 defect. Where both arms are scorable, total delay against free flow is ≥ 531 s vs 150 s (head-on), ≥ 799 s vs 238 s (B3) and ≥ 1026 s vs 457–503 s (IB10). The layer-2-off figures are censored lower bounds.

---

## Decision Branch and Recommendation

The registration fixes two branches:

1. latch/clog everywhere → register the full no-intervention arm into collection;
2. any self-resolving cell → stop and report that cell to the owner as an oracle design finding.

**Branch taken: (1).** Self-resolution was defined before reading the data as every involved robot position-verified as arrived inside the horizon. No cell met it, and no cell reached even a partial arrival. Every cell shows the identical latch mechanism within 1 s of onset, so there is no design finding for the oracle.

**Recommendation: register the full no-intervention arm into collection**, on the same (scenario, seed) keys as the intervened arm, so the registered paired McNemar and KM/RMST analyses apply directly. One no-intervention episode per (scenario, seed) can pair against both backend arms (ER-2 and gpt-4o), because nothing in it depends on the backend.

| Cell | Suggested no-intervention runs | Rationale |
|---|---|---|
| Head-on `_bshort` | 10 (the intervened arm's first 10 seeds) | IF all 10 intervened pairs resolve, ten discordant pairs give an exact McNemar p ≈ 0.002 per cell. The discordant count depends on the backend arm paired against: gpt-4o's IB10 pilot episode clogged 0/4. A 0/10 resolve rate has a Wilson 95 % upper bound of 28 %. That bound assumes independent trials, and the head-on seeds 42–44 varied by only about 1–2 s, so near-deterministic replicates make it nominal. |
| B3 `convoy_counterflow_slip` | 10 (same rule) | Same as head-on. |
| IB10 `intersection_bottleneck` | 10 (same rule) | Same as head-on. |
| B1 `bottleneck_merge` | 5 | Both arms clog on v2 until the stage-2 defect is fixed, so pairs are concordant and uninformative. Five seeds document the reactive-only baseline (Wilson upper bound 43 %), with an option to top up to 10 once B1's intervened arm is flow-scorable. |
| **Total** | **35 episodes** | About 13 VM-hours at the observed 18–29 wall-min per episode. Zero API spend. `RECORD=0`. |

Rules to carry into the registration:

- **Mechanism:** the silencing mechanism is this pilot's. Use mock with no decision file and the per-run silence gate (0 dispatches, all artifacts `congestion_detected: false`, sidecar `mock`).
- **Horizon:** the full registered horizon, enforced by the GT-completed horizon gate.
- **Scoring:** the same scorers and `free_flow_v1`.
- **Censoring:** censored delays enter KM/RMST as censored at the horizon, never as finite times.
- **Scope note for the paper:** in this system the reactive layer is Nav2 plus M4's pairwise min-distance stop. Together they never self-resolve these cells. The observed clog is that stop holding symmetric pairs indefinitely (proximate cause; untested without M4), which is the reactive-deadlock pattern of Marcolino-2017 / Garg. The arm quantifies that our reactive layer cannot self-resolve. It does not claim that every reactive controller would fail.

---

## Artifacts

- **Runs:** `data/logs/vm_runs/layer2off_pilot/runs/l2_0{1..4}_*` in the main checkout (gitignored). Each holds GT, every node log, all decision artifacts, `m5_scene.jsonl`, the overlays as installed, the 150 s sidecar and `CONDITION` / `GATE` / `M5_STARTED` / `SILENCE` / `RESTORE` files.
- **Analysis:** `_analysis/l2_0*_score.json` (committed scorers) and `_analysis/l2_0*_extras.json` (latch, trajectory, offset and shadow). Also `_analysis/summary.json` and `_analysis/refs/` (the intervened references re-scored).
- **Driver:** `_vm_driver/` holds `l2_deploy.sh`, `l2_instcheck.sh`, `gen_l2_overlays.py`, `l2_run.sh`, `l2_chain.sh` and `specs.txt`, plus the pre/post installed manifests and the post-deploy source manifest. Also `chain.log` and the per-run `.nohup` logs.
- **Suite:** docs-only change. 63 failed / 5149 passed / 153 skipped / 3 errors (collection) at `b5cafe4`, and the same after this commit. The failures are pre-existing local environment failures. The diff touches no code or tests.
