# IB10 Live Resolution Experiment (Exploratory)

**Prepared:** 2026-11-13

**Revision history:**

- Initial draft: registration of a 10-episode, two-arm IB10 run on the prereg-v3 tranche-1 runtime, written before any episode ran.

---

## 1. Question

Does the full Layer 2 pipeline physically clear the four-way `intersection_bottleneck` (IB10) jam, which stays frozen when Layer 2 is off? The pipeline is M5 trigger → live M2 → M3 `junction_clear` grounding → phased M4 dispatch.

This is a new exploratory experiment. It is separate from prereg-v3 and is never pooled with any prereg-v3 cell, tranche or pilot. The owner decided on 2026-11-13 to run it and to skip prereg-v3 tranche 2.

---

## 2. Runtime and Scene

| Item | Value |
|---|---|
| Code | The prereg-v3 tranche-1 runtime as deployed on the VM: git `68e67b5` (`feat/v3-integration`, which contains `1624db1`). No code is deployed. |
| VM changes | The kit adds only the IB10 USD and the 0.20 m floor `safety.yaml` swap, and swaps in the per-episode overlay. All of them are removed and md5-verified back to the v3 pin when each invocation ends. M5's own run outputs stay in the VM repo's `data/logs/` (`m5_decisions`, `m5_scene`, `m5_frames`), as in every earlier run; they are copied into each bundle. |
| Scene | `isaac/config/scenarios/intersection_bottleneck.yaml` (`042802d6`), unedited: 4 robots, one per arm, `duration_sec: 300` (this governs Isaac; `SIM_SEC` is inert), `seed: 42`. |
| Seed | 42 for every episode. The seed is a label only: the scene is near-deterministic, so the episodes are repeated runs of one scene, not draws of different scenes. |
| Nav2 bring-up | Parallel (`fc_launch.sh`'s default), as in every IB10 record. Isaac's clock runs during bring-up, and the frozen jam gate's onset window [8, 40] s is absolute sim time. Parallel bring-ups gave t0 22–24 s and onset 32–34 s. The S1b sequential mode put first motion at 29–32 s on this VM, which would move the onset to the 40 s edge. |
| Overlay, Arm A | `ib10_remedy_orchestrator.yaml` (`0d0cfbfa`, the overlay of the IB10 closure wave) with `keep_debug_frames: true`. It carries the release-lane remedy (`scenario_geometry.junction_release_pull_off_m: 0.33`, `junction_release_pull_off_side: -1`), `plan_channel_enabled: true` and `grounding_params_path: config/rag.yaml`. |
| Overlay, Arm B | The Arm A overlay plus `reasoning_enabled: false`. |
| Remedy pieces | Pull-off: `306a0d2`, config-gated (off unless the overlay sets it). Hand-off race guard: `59c11c9`, `handoff_race_guard: True` in `execution.launch.py`. Floor: `config/safety/safety_floor020.yaml` (`c41913f0`, `hard_contact_floor_m: 0.20`), swapped in for the run. |

Offline evidence for the runtime (2026-11-13; see §9 for the VM-only items):

- At `68e67b5`, the five IB10 closure artifacts (R1, R2, P1, P2, P3) re-ground to byte-identical `junction_clear` phase commands under the remedy overlay. Every release phase carries `pull_off_lateral_m` ±0.33 and `passer_reference_at_dispatch: true`.
- Every `OrchestratorConfig` field added after `0f10791` loads at a behaviour-preserving default under this overlay: off or null, plus `reasoning_enabled: true`. `config/rag.yaml` is unchanged since the closure wave.
- The pinned scorer reproduces the stored `ib10_score.json` of all five closure bundles exactly.
- No IB10 episode has run on this tree. The smoke episode is its first live test.

---

## 3. Design

| Item | Value |
|---|---|
| Arm A | Layer 2 on, live `gemini-robotics-er-2-preview` (`BACKEND=gemini`). |
| Arm B | Layer 2 off (`reasoning_enabled: false`): no congestion detection, no M2 or M3 call, no dispatch. M5 still loads `initial_tasks` and logs the M1 scene, and M4 runs the base missions. |
| n | 5 episodes per arm, 10 in all. |
| Order | Interleaved, fixed in advance: E01 A, E02 B, E03 A, E04 B, E05 A, E06 B, E07 A, E08 B, E09 A, E10 B. |
| Smoke | E01 runs alone (`run_ib.sh smoke`). If it passes every harness gate, it counts as A1 whatever its outcome. The follow-up (E02–E10) starts only after the owner inspects E01 and writes the acceptance marker. |
| Labels | `ib10L_eNN_armX_aK` (episode NN, arm X, attempt K). |

---

## 4. Outcomes (fixed before any episode)

All scoring uses the frozen IB10 criteria in `docs/reports/2026-10-03-step7b-oracle-freeze.md`, section "IB10 scoring frozen". The scorer is the pinned `scripts/coverage_scene_scores.py ib10` (`score_ib10`), wrapped by the kit's `score_ib.py`.

### Primary

- **Frozen `resolved`:** criterion 1 (formed-jam validity gate on GT) AND criterion 6 (all four robots arrived by `score_ground_truth`'s position rule).
- **Episode success:** frozen `resolved` is True, AND M4 logged zero hard-contact-floor stops, AND the GT minimum pairwise centre distance after t0 is at least 0.18 m. A floor stop or a GT contact makes the episode a failure, whatever the arrivals.

### Secondary

- **Time to full resolution:** the last arrival minus the GT jam onset (`formed_jam.onset_sec`), in sim-s. Also reported as the last arrival after t0. Censored at the horizon when not resolved.
- **Minimum pairwise distance:** computed from GT robot positions over all pairs after t0. It does not use the GT contacts field.
- **Floor-stop count:** M4 lines `hard_contact_floor_m=0.2 pairs=`.
- **Arrivals:** the count out of 4, and `outcome_rank` (criterion 11).

### Attribution (Arm A)

For every dispatched decision, the scorer reports the strategy, `plan.provenance` (`vlm_verbatim`, `repaired` or `m3_default`) and `dispatch_matches_plan`.

- **Episode attribution label:** the provenance of the dispatched `junction_clear` decision when there is one; otherwise the provenance of the last dispatch before the final arrival. An episode with no dispatch is labelled `none`.
- **Not used:** criterion 2's `order_correct`, because of open ruling (c) in `2026-10-08-ib10-closure.md`.

---

## 5. Exclusions

| Case | Treatment |
|---|---|
| Nav2 bring-up abort (`NAV2_BRINGUP_FAILED`) | Not counted. The same episode slot is retried, up to 3 attempts. Three aborts skip the slot, and two skipped slots in a row stop the run. |
| Invalid jam (criterion 1 fails) | Excluded from the primary denominator and reported (`resolved: None`). |
| Harness failure (no `logs saved to`, a failed per-episode restore, floor or hand-off-guard startup line missing, an arm check refused, a failed condition gate, or no M5 session line) | Excluded and reported. The chain stops. |
| Arm A with M5 running but no analysis | Counted, as data. |
| Truncated (cost cap or wall-clock stop, GT end < 299 sim-s) | Counted only if all four robots had arrived before the stop. Otherwise excluded as `truncated` and reported. The slot is not re-run, so its arm has one episode fewer. |
| Harness failure, re-run | The slot is not marked as run. A later invocation, started by the owner after inspecting the failure, re-runs it under a new attempt label. |
| Gemini probe failure before an Arm A episode | The episode never starts. The run stops on HTTP 429 or 402 and on any other probe error. |

---

## 6. What Is Not Claimed

- **The episodes are not independent samples.** One scene, one seed label and one VM give repeated runs of a near-deterministic system. There are no p-values and no confidence claims beyond the counts.
- **This is exploratory.** Nothing here confirms or amends any prereg-v3 hypothesis.
- **Model vs grounder.** M3 can repair or replace the model's plan, and in the earlier live pilot every IB10 plan was repaired or replaced. A resolved Arm A episode therefore shows that the pipeline resolves the jam, not that the model's choice did. The provenance labels in §4 bound the model's contribution, and they are reported beside every outcome.
- **The B → A contrast is pipeline on vs pipeline off.** It is not a comparison against a classical coordinator.

---

## 7. Safety Rules

- **Floor.** The 0.20 m hard-contact floor (`c41913f0`) is installed for both arms. Every episode is gated on M4's startup line `hard_contact_floor_m=0.2`.
- **Floor stops are outcomes.** Any floor stop counts as a failure (§4) and is reported. The run continues: this is a simulation, and stopping would truncate the comparison.
- **Open caveat: the cross-cluster exemption.** One command exempts every pair of robots inside it from M4's proximity check. A `junction_clear` phase command names all four robots, so the proximity latch does not protect the robots inside one command from each other. The floor is the only backstop for those pairs, and it fires at or after contact at about 0.3 m/s closing speed (`2026-10-08-ib10-remedy-validation.md`). This is open and unfixed.
- **The VM ends at the v3 pin on every exit path.** The kit restores the pin, md5-verifies it and stops the VM. The VM-side dead-man restores and powers off at cap + 20 min.

---

## 8. Caps

| Cap | Value | Status |
|---|---|---|
| Wall clock | 6 h per invocation, from VM start to TERMINATED. An episode starts only if it can end before the chain deadline (cap − 45 min teardown reserve). | Default |
| Spend per episode | $0.50 est. This is a safety ceiling: `cost_watch.py` ends the episode when est + one call reaches it. | Proposed |
| Spend in total | $3.00 est across all invocations; no Arm A episode starts with less than $0.50 left. | Proposed |
| Analyses per episode | No count cap (`MAX_ANALYSES=0`), as in tranche 1. | Default |

At an expected $0.02–$0.04 per Arm A episode (the 2026-10 live IB10 episodes), the caps only bind on a runaway re-trigger loop.

---

## 9. Verified Only on the VM

- That the VM matches the v3 pin plus the IB10-path files, at `68e67b5` md5s: the scene yaml, `scene_geometry.py`, `crossing_chain.py`, `coordination_client_node.py`, `execution.launch.py` and the installed IB10 map.
- That the IB10 USD builds and validates on this VM.
- That the M4 changes made after the closure wave behave on IB10 as they did there. One of them, A19's yielder latch waiver (`4e1b5bf`), is not gated by any command parameter. The smoke episode is the first test.
- The per-episode wall clock (estimated 28–35 min) and the Gemini quota.
