# IB10 Lead-Flip Diagnosis: Release Contact on `071f9c1`

**Prepared:** 2026-10-08

**Revision history:**

- Initial draft: offline diagnosis (no VM, no API) of the v3 Step 0 IB10 failure (1 / 4 arrivals in `ib10_s42` and `ib10_s42_rep2`, robot_4-led release contact) against the fix-branch 4 / 4 run. Covers the release-lead code path, χ components from 11 local IB10 bundles, a counterfactual re-grounding under both trees, a code diff audit of `0b2e755..071f9c1`, and the release pass geometry from GT.

---

## Summary

The brief's framing ("the release order flipped") describes a symptom, not the defect. The release lead has always been a coin flip. A robot_4 lead worked before. Every IB10 release has always parked the non-lead receder dead on the lead's lane, and fix_s42's 4 / 4 was a near miss: 11 mm of lateral clearance.

| Question | Answer |
|---|---|
| (a) Root cause of the lead flip | **Input noise in jam-formation geometry.** Neither a code change nor tie-break instability. The χ margin between robot_3 and robot_4 ranges 0.000–0.133 m across 11 bundles, always below ε = 0.15. robot_4 led 5 times and robot_3 led 6. |
| (b) Defect commit? | **None in `0b2e755..071f9c1`.** Re-grounding all four relevant snapshots under both exported trees gives byte-identical phases, pockets, lead and `crossing_order`. M4, M1, Nav2 and the phase queue have empty diffs. The failure comes from a pre-existing release-geometry fragility. The clearing half of the costmap fix (H, `e87dc89`) likely exposed it (hypothesis: no IB10 release has a costmap bag). |
| (c) Remedy | Make the release robust to **either** lead by giving the held receder lateral clearance off the lead's lane. M4's existing `pull_off_lateral_m` sidestep is the candidate; a lateral pocket offset is the alternative. Optionally add an un-exempted hard-contact floor. Do **not** register "robot_3 leads". The registered rule is "lead = χ rank 0", and the ε rule makes both orders equivalent. Needs a spec ruling. |
| (d) VM arm? | **Yes, but not a code-attribution arm** (settled offline) and not one ordered by lead (the lead cannot be forced). Run IB10 on `071f9c1` with the lead's costmaps, scan and plan bagged through the release, replicating until both leads are observed. Then validate the remedy under both leads. |

All numbers below are reproducible with two gitignored scripts:

- `data/logs/vm_runs/v3_step0/_analysis/ib10_lead_flip.py` (χ components, release gates, GT pass geometry)
- `data/logs/vm_runs/v3_step0/_analysis/ib10_regound_cf.py` (counterfactual re-grounding)

---

## 1. Who Decides the Release Lead, and From What

The decision is pure M3, made once on the triggering decision's single snapshot. M5 and M4 only execute it.

1. **Candidates.** `_junction_recede_candidates(decision, geometry)` returns the cross-axis robots with a declared arm: robot_3 (y, side −1) and robot_4 (y, side +1).
2. **χ ranking.** `maneuver_geometry.rank_recede_candidates` scores each candidate as χ = `junction_recede_cost_space_weight` · D_SPACE + `junction_recede_cost_follower_weight` · N_f, with weights 1.0 / 0.5 (defaults; IB10's `rag.yaml` sets neither). Candidates are sorted by `(χ, robot_id)`.
   - **D_SPACE** = `junction_recede_offset_m` (1.2) − the robot's outward offset along its own arm at the snapshot (`recede_axis_offset_m`), floored at 0.
   - **N_f** = other robots farther out on the same arm. It is 0 in every IB10 bundle.
   - **Tie-break:** lexical `robot_id`, applied only on an exact χ tie.
3. **Recede dispatch order** (`ground_junction_clear_phases`): `ranked` under the default `plan_dispatch_order_source: chi`. Under R3.3's `model_when_verified` it is the verbatim plan's order.
4. **Pockets.** Assigned by χ rank, never by dispatch position: rank 0 gets 1.2 m and rank 1 gets 1.2 − 0.2 (stagger) = 1.0 m.
5. **Release lead** = `ranked[0]` in **both** modes (`lead_id = ranked[0]`, `command_grounder.py:2194`). The lead is addressed by no release action, so it resumes immediately. The other receder gets a passive `yield` (`backup_distance_m: 0.0`) with `passer_robot_id = lead` and `passer_clear_m` = 1.2 + 1.0 + 0.45 = 2.65. The yielder (robot_1) gets `crossing_order: [lead, other]` and `crossing_clear_m: [2.65, 2.05]`.
6. **M5** (`orchestrator_node._advance_junction_phase` / `junction_phase_queue`) dispatches the precomputed phases in order and never re-derives them. **M4**'s `CrossingChain` admits the passers in `crossing_order` and ends each hold on the passer's own odometry displacement.

The lead is therefore the χ-cheapest receder: whichever of robot_3 and robot_4 stopped farther out on its own arm when the jam formed. The release order is `[χ rank 0, χ rank 1, yielder]`.

**Is the lead rule registered?** Yes, as "lead = χ rank 0":

- the IB10 oracle rationale (`scenario.yaml`: "the receded robots re-enter after it, the chi lead first")
- step-7a / 7b rulings (iv) and (vi), and the grounder docstrings

No rule names a robot. "Yielder last" (ruling vi) is registered and held in every run here. The ε rule (`junction_recede_order_epsilon`, RULED 2026-10-03) explicitly treats both recede orders as one equivalence class whenever the χ margin is below 0.15. That is true in all 11 bundles, so the design commits to the release working under either lead. **robot_3-first in fix_s42 was a draw, not a behaviour.**

---

## 2. χ Components per Run

These come from each bundle's dispatched `junction_clear` decision artifact (`scene` snapshot), recomputed with the repo's `recede_cost`. N_f = 0 everywhere, so χ = D_SPACE. "Off" is the outward offset along the robot's own arm.

| Run | Tree | Snapshot (sim s) | robot_3 off / χ | robot_4 off / χ | χ(r3) − χ(r4) | χ rank (= release lead first) | Proposed (mock) | Provenance | Arrivals |
|---|---|---|---|---|---|---|---|---|---|
| step-7a rerun 1 | pre-fix | 32.9 | 0.259 / 0.941 | 0.267 / 0.933 | +0.008 | [r4, r3] | [r4, r3] | vlm_verbatim | 2 / 4 (pre-ruling-vi) |
| step-7b rerun 2 | pre-fix | 33.5 | 0.242 / 0.958 | 0.274 / 0.927 | +0.031 | [r4, r3] | [r4, r3] | vlm_verbatim | **4 / 4** |
| `verbatim_pilot` vp08 (ER-2) | pre-fix | 34.5 | 0.269 / 0.931 | 0.316 / 0.884 | +0.047 | [r4, r3] | live | repaired | (no ib10 score in bundle) |
| `plan_grammar_cal` cal_ep1 | pre-fix | 30.2 | 0.262 / 0.939 | 0.262 / 0.939 | **0.000** (lexical tie-break → r3) | [r3, r4] | live | repaired | 4 / 4 |
| `v2_demo` ep1_scripted | pre-fix | 38.2 | 0.264 / 0.936 | 0.220 / 0.980 | −0.044 | [r3, r4] | [r4, r3] | repaired | 4 / 4 |
| `v2_demo` ep2_live_er2 | pre-fix | 31.9 | 0.291 / 0.909 | 0.259 / 0.941 | −0.032 | [r3, r4] | live | m3_default | 4 / 4 |
| `verbatim_pilot` vp09 (ER-2) | pre-fix | 34.8 | 0.218 / 0.982 | 0.214 / 0.986 | −0.004 | [r3, r4] | live | repaired | (no ib10 score in bundle) |
| `costmap_fix` ib10_prefix_s42_r4 | pre-fix | 39.4 | 0.329 / 0.871 | 0.315 / 0.885 | −0.014 | [r3, r4] | [r4, r3] | vlm_verbatim (`order_equivalent`) | 4 / 4 |
| **`costmap_fix` ib10_s42 (fix branch)** | **post-fix** | 41.1 | 0.368 / **0.832** | 0.235 / 0.965 | **−0.133** | **[r3, r4]** | [r4, r3] | vlm_verbatim (`order_equivalent`) | **4 / 4** |
| **v3 ib10_s42** | **post-fix (`071f9c1`)** | 40.9 | 0.198 / 1.002 | 0.211 / **0.989** | **+0.013** | **[r4, r3]** | [r4, r3] | vlm_verbatim | **1 / 4** |
| **v3 ib10_s42_rep2** | **post-fix (`071f9c1`)** | 38.0 | 0.230 / 0.970 | 0.292 / **0.908** | **+0.062** | **[r4, r3]** | [r4, r3] | vlm_verbatim | **1 / 4** |

**Dispatched recede and pockets for the four decisive runs** (re-grounded; v3 values equal the artifact's `junction_phases` exactly):

| Run | Recede dispatch (robot, reverse m) | Pocket (rank 0 / rank 1) | Release |
|---|---|---|---|
| fix ib10_s42 | robot_3 0.832 → robot_4 0.765 (M5 log: recede-robot_3 dispatched first, robot_4 at completion) | r3 1.2 / r4 1.0 (GT: r4 parked at y = +1.013) | lead robot_3; held robot_4, robot_1; `crossing_order` [r3, r4], clear [2.65, 2.05] |
| fix prefix_r4 | robot_3 0.871 → robot_4 0.685 | r3 1.2 / r4 1.0 | lead robot_3 |
| v3 ib10_s42 | robot_4 0.989 → robot_3 0.802 | r4 1.2 / r3 1.0 (GT: r3 parked at y = −1.014) | lead robot_4; held robot_3, robot_1; [r4, r3], [2.65, 2.05] |
| v3 ib10_s42_rep2 | robot_4 0.908 → robot_3 0.770 | r4 1.2 / r3 1.0 (GT: r3 at y = −1.018) | lead robot_4 |

M4 executed exactly this release in every run. The `gate_admit` lines are `junction-release yielder=<held> passer=<lead> clear_m=2.650`, then `yielder=robot_1 passer=<held> clear_m=2.050`.

**Why the margin flipped.**

- The robot_3 vs robot_4 margin is set by where the two cross-axis robots happened to stop when the jam formed. The spread is centimetres in a nominally symmetric scene. `GroundingParams`' own comment already records "between-run jam-formation margins up to 0.142 m".
- In fix_s42, robot_3 stopped unusually far out (0.368 m, the largest offset in all 11 runs), which made it the cheapest by 0.133 m. In v3 ib10_s42 the two were 13 mm apart.
- **A supporting correlation, not a mechanism.** Of the 6 runs where the two cross-axis robots' GT departure times (≥ 0.02 m from spawn, 10 Hz GT) differ by ≥ 0.3 s, all 6 led with the later departer, which stops farther out and so has the lower χ:
  - fix_s42: robot_3 departed 1.2 s after robot_4
  - v3 rep2: robot_4 departed 0.3 s after robot_3
- Departure stagger is bring-up and harness timing; no tree controls it.
- The lexical tie-break fired only at the exact tie in cal_ep1, so there is no tie-break instability.

---

## 3. Code Diff Audit (`0b2e755..071f9c1`)

**Counterfactual re-grounding.** `git archive` of `reasoning/` and `config/` at `0b2e755` (the fix branch tip) and at `071f9c1` (the merged tree) went to `/tmp`. `ground_junction_clear_phases` was then run under each tree on the snapshots of fix ib10_s42, fix prefix_r4, v3 ib10_s42 and v3 rep2, with each bundle's own overlay geometry and `rag.yaml`. **The output is identical under both trees for all four snapshots:** recede order, reverse distances, pocket ranks, release lead, held set, `crossing_order` and `crossing_clear_m`. Under the merged tree the fix-branch snapshot still yields lead robot_3; under the fix tree the v3 snapshots still yield lead robot_4.

**Grounder diff** (`git diff 0b2e755..071f9c1 -- reasoning/rag/command_grounder.py reasoning/rag/maneuver_geometry.py`), by item:

| Item | Change | Effect on ordering / lead |
|---|---|---|
| R3.3 (`a98574b`) | `recede_order=None` parameter. `dispatch_order = ranked` when None. Pockets use `chi_rank[robot_id]`, which equals the old `enumerate(ranked)` rank. `lead_id = ranked[0]` and `release_held` are untouched. `plan_recede_order` is a pure refactor of the inline `plan_order` comprehension in `junction_clear_dispatch_match`. | None in default mode (the v3 artifacts record `plan_dispatch_order_source: chi`, `dispatch_order_source: chi`). The "dispatch always follows χ" rewording in four places is docstring-only. The lead is χ rank 0 in both modes. |
| A4 (`8cce46c`) | `_tag_discarded_order` wraps the cross-phase and fallback `_ground_derived` results. | Edits the `degradations` tags only. `_as_yield_decision` still clears `crossing_order` exactly as before. |
| A5a (`7ca6473`) | Tags reverse legs shortened by the tracked-band clamp (legacy grounder). | Not on the junction path. |
| A7 (`6ef47c6`) | `no_candidates` fallback merges tags. | Not reached (candidates exist). |
| `maneuver_geometry.py` | Two comments reworded. | None. χ arithmetic is unchanged. |

**M5** (`orchestrator_node.py`, `reasoning_pipeline.py`, `command_lifecycle.py`, `models.py`, `contradiction_trigger.py`):

- **A5b.** `registry_dispatch` is computed once before the artifact write and passed to `_dispatch`. It filters the same command the old inline `filter_command_robot_ids` did.
- **A1.** The `junction_phases` serialization is artifact-only.
- **R3.4.** The `ContradictionMonitor` is `None` when the trigger is disabled (the pinned yaml has it off). `_dispatch` skips `watch` for junction sequences anyway. The `actions=` / `leg_outcomes=` additions only feed `AttemptMemory` bookkeeping.
- **Phase advance.** The only `_advance_junction_phase` change is `leg_outcomes` passed to `self._attempts.resolve`.

**Everything else is empty:**

```text
git diff --stat 0b2e755..071f9c1 -- ros2_ws/src/swarm_orchestrator/swarm_orchestrator/junction_phase_queue.py \
  ros2_ws/src/swarm_execution ros2_ws/src/swarm_perception ros2_ws/src/swarm_simulation
(no output)
```

The Isaac changes (`runner.py`, `run_simulation.py`) add only the stop-flag poll and abort manifest keys. **No commit in the range touches the release-order path, M4's crossing chain or safety monitor, M1, or Nav2 parameters.** Both the fix-branch run and the v3 runs include the costmap fix (`e87dc89` H and A′).

---

## 4. The Exemption-Window Contact: Pass Geometry From GT

**Geometry is mirror-symmetric.** Both pockets sit on the N-S centreline (x ≈ 0): the lead at ±1.2 and the held receder at ∓1.0. The lead's goal (0, ∓1.75) lies **beyond** the held receder's pocket. So under **either** lead, the lead's straight path runs through the held robot. Step-7b ruling (iv) designed the pass this way ("no lateral room to pass it closer"), protected only by:

- the release `yield`'s pair exemption from the 0.45 m min-distance latch
- Nav2 steering around the held robot

M4's own `command_bus_node.py` yield comment names this exact problem: "a straight backup alone leaves the yielder on the passer's line". The release's passive hold uses no `pull_off_lateral_m`.

**Lateral clearance is what discriminates.** The metrics run from the lead's admit to the held robot's own gate release. The Nav2 footprint is 0.14 × 0.18 m, so side-by-side bodies touch at a centre separation of about 0.18 m.

| Run | Era | Lead | Lead lateral offset at along-arm gap 0.6 / 0.4 / 0.2 m | Min centre distance | Margin vs 0.18 m | Held displaced before its release | Lead longest stop | Lead Nav2 events (run) | Transit admit → held release |
|---|---|---|---|---|---|---|---|---|---|
| 7a r1 | pre | r4 | 0.236 / 0.233 / 0.218 | 0.221 | +41 mm | 0.034 | 18.4 s | 1 FTMP, 3 clears | 44.1 s |
| 7b r2 | pre | r4 | 0.327 / 0.296 / 0.272 | 0.248 | +68 mm | 0.002 | 37.3 s | 2 FTMP, 3 clears | 56.1 s |
| vp08 | pre | r4 | 0.072 / 0.100 / 0.164 | 0.214 | +34 mm | 0.015 | 26.3 s | 1 FTMP, 3 clears | 46.3 s |
| cal_ep1 | pre | r3 | 0.378 / 0.371 / 0.349 | 0.318 | +138 mm | 0.004 | 38.2 s | 2 FTMP, 7 clears | 57.0 s |
| ep1_scripted | pre | r3 | 0.406 / 0.379 / 0.368 | 0.334 | +154 mm | 0.036 | 10.9 s | 2 FTMP, 3 clears | 55.9 s |
| ep2_live_er2 | pre | r3 | 0.390 / 0.378 / 0.351 | 0.346 | +166 mm | 0.044 | 36.5 s | 2 FTMP, 3 clears | 56.4 s |
| vp09 | pre | r3 | 0.049 / 0.053 / 0.133 | 0.196 | +16 mm | 0.038 | 15.7 s | 1 FTMP, 6 clears | 35.7 s |
| prefix_r4 | pre | r3 | 0.372 / 0.327 / 0.285 | 0.256 | +76 mm | 0.041 | 17.6 s | 1 FTMP, 2 clears | 38.2 s |
| **fix ib10_s42** | **post** | **r3** | −0.121 / −0.150 / −0.190 | **0.191** | **+11 mm** | 0.037 | 0.4 s | 0 FTMP, 1 clear | **17.7 s** |
| **v3 ib10_s42** | **post** | **r4** | 0.096 / 0.115 / 0.118 | **0.084** | **contact (−96 mm)** | **0.558** | 1.4 s | **none** | 42.3 s (pushing) |
| **v3 rep2** | **post** | **r4** | 0.076 / 0.102 / 0.113 | **0.089** | **contact (−91 mm)** | **0.547** | 5.3 s | **none** | 47.7 s (pushing) |

(FTMP = Nav2 "Failed to make progress"; "clears" = costmap clear-entirely requests.)

**Reading.**

1. **Not caused by which robot leads.** robot_4-led releases passed in 3 / 3 pre-fix runs (0.214–0.248 m), including the 7b rerun-2 4 / 4. Pre-fix robot_3 leads ranged 0.196–0.346 m.
2. **Not caused by timing.**
   - In both v3 runs robot_3 sat still (≤ 0.0002 m/s) until contact.
   - robot_4 never paused. It drove a near-straight line at about 0.15 m/s with a lateral offset that settled near 0.11–0.12 m, and reached robot_3 at sim ~120 (s42; within 0.2 m at 115.0 in rep2).
   - It then pushed robot_3 about 0.55 m south-west inside the exemption until the gate counted its 2.65 m of odometry (sim 148.0 / 149.4).
   - The latch followed when the exemption dropped.
   - A robot_4 lead with different timing would only have worked had Nav2 swung wider. Nothing in the timing changes that.
3. **The only post-fix robot_3 pass was also tight.** A post-fix direction effect is not excluded at n = 1 (robot_3 lead) vs n = 2 (robot_4 lead).
   - fix_s42's robot_3 lead passed at 0.191 m. That is 11 mm from footprint contact, the tightest contact-free pass of all 11 runs.
   - Its 4 / 4 was a near miss, not evidence that a robot_3 lead is safe.
   - The pre-fix passes were wider (16–166 mm) and came after an 11–38 s pause with FTMP and costmap clears. The post-fix leads never pause, show 0–1 Nav2 events and transit up to 3× faster.
4. **Mechanism (hypothesis, unverified).**
   - `isaac/vgu_sim/config.py` records that the lidar's single scan plane (0.182 m) sees only another burger's ~7 cm LDS head: it "cannot close a passage a robot can drive through, so Nav2 would plan past it".
   - With inflation 0.07 (local) / 0.10 (global) and an inscribed radius of 0.08 (Nav2's own startup ERROR flags inflation < inscribed), the planner keeps the lead's centre roughly LDS radius + inscribed ≈ 0.115 m from the held robot's LDS. That matches the 0.11–0.12 m v3 offset. The physical bodies need about 0.18 m.
   - Pre-fix, with `clearing` defaulted off, the held robot's LDS returns from many viewpoints, including mis-registered ones, persisted and grew a wider lethal blob. That widened the pass and also caused the pre-fix pause.
   - H (`e87dc89`, `clearing: true`, `raytrace_max_range: 3.5`) removes the stale part, so the planner sees only the 7 cm head.
   - **What the hypothesis does not explain.** It predicts every clean-costmap pass skims at about 0.115 m, but fix_s42 reached 0.191 m with a late swing (−0.121 → −0.190 m between the 0.6 m and 0.2 m gaps).
     - All 9 contact-free runs widen their lateral offset between those gaps. vp08 and vp09 swing late, from 0.05–0.07 to 0.13–0.16 m.
     - Both contacts stay flat (0.096 → 0.118 and 0.076 → 0.113 m).
     - The observable is therefore "no close-range reaction to the held robot". The bag arm (5d) must explain that late swing versus the flat approach, so its `/scan` capture must cover the closest-approach window.
   - **Gap:** no IB10 release has a costmap or plan bag. fix_s42's bag holds only odom and `scene_state`, and the v3 IB10 runs were not bagged.
5. **Two caveats on evidence used elsewhere.**
   - GT `robot_robot_contacts` is **blind** to this contact. It is empty in every v3 row despite a 0.084 m centre distance and a 0.55 m push. "GT recorded zero robot contacts" (step-7b report) is therefore no evidence of a clean pass.
   - vp08 / vp09 are live ER-2 pilot runs whose bundles carry no `ib10` score. Their pass geometry is used here, not their outcome.

---

## 5. Verdict

**(a) Root cause of the lead flip.**

- **Input noise in jam-formation geometry.** The lead is χ rank 0. The robot_3 / robot_4 χ margin is 0–0.133 m in every recorded IB10 run, always inside ε, and it follows centimetre differences in where the two cross-axis robots stopped (correlated with sub-second departure stagger).
- It is not a code change: the counterfactual re-grounding is identical under both trees.
- It is not tie-break instability: the lexical tie-break fired only once, at an exact 0.000 tie.

**(b) Defect commit, or pre-existing fragility?**

- **No commit in `0b2e755..071f9c1` is implicated.** R3.3, A1, A4, A5b, A7 and R3.4 each leave the release lead, pockets and phase order unchanged in default mode. M4, M1, Nav2 and the phase queue are untouched.
- The failure is a **pre-existing fragility in the release design** (step-7b rulings iv / vi, `4d7ee48` lineage): the non-lead receder is parked on the lead's lane and the pass relies on Nav2 swinging wide inside a min-distance exemption.
- It was **likely exposed by the costmap fix's clearing half (H, `e87dc89`)**. Post-fix passes are 0.191 m, contact, contact; pre-fix passes are 0.196–0.346 m, 8 / 8 contact-free. This is a correlation (n = 3 post-fix) without costmap evidence.
- The merge into v3 changed which robot happened to lead, not whether the pass is safe.

**(c) Recommended remedy and scope.**

- **Make the release robust to either lead. Do not pin a lead.** The registered rule is "lead = χ rank 0", and the ε rule treats both orders as equivalent, so registering "robot_3 leads" would encode one 11 mm near miss as policy.
- **Candidate (M3 only, smallest scope):** give the non-lead receder's release `yield` a `pull_off_lateral_m`, sized so that the centre separation is ≥ 0.18 m + margin, within the arm's free band.
  - This reuses M4's existing raw-cmd_vel sidestep (`command_bus_node.py`, `adapter.sidestep`). That sidestep exists precisely because "a straight backup alone leaves the yielder on the passer's line", and the release hold already runs the yield branch with `backup_distance_m: 0.0`.
  - Alternative: a declared lateral pocket offset for rank ≥ 1 (`SceneGeometry`), applied at recede time.
- **Optional M4 hardening (separate ruling):** an un-exempted hard-contact floor (e.g., about 0.2 m centre distance) inside admitted pairs. The exemption currently lets a lead push a held robot for 28 s with no stop.
- **Not recommended:** raising Nav2 inflation scene-wide. It touches every scene, and the 0.07 / 0.10 values are pinned for the 0.55 m corridor family.
- All of this needs a spec ruling before implementation, plus an IB10 re-validation under both leads.

**(d) Is a VM attribution arm still needed?**

- **A code-attribution arm (`a823aeb` / pre-fix, ordered by lead) is not needed.** Code attribution is settled offline, and 8 pre-fix passes already exist. The lead cannot be forced either: it is χ rank 0 of the live jam.
- **One diagnostic arm is needed**, to confirm or refute the costmap mechanism behind the remedy:
  - IB10 on `071f9c1`, mock `intersection_junction_clear_vlm_verbatim_once.json`, overlay `35734f4e`, `REC_SEC=1400`.
  - Bag both cross-axis robots' `/robot_{3,4}/local_costmap/costmap`, `/robot_{3,4}/global_costmap/costmap` (plus `_updates`), `/robot_{3,4}/plan` and `/robot_{3,4}/scan` from the cross phase through the held robot's gate release.
  - Replicate until both leads are observed (the lead is about 50 / 50; budget 3–4 runs).
  - Measured outcome per run: lead identity, min centre distance, the lead's lateral offset at 0.6 / 0.4 / 0.2 m gaps (`_analysis/ib10_lead_flip.py`), and the held robot's lethal footprint in the lead's costmaps at the pass.
  - Optionally add one pre-fix (`clearing` off) replicate with the same bag, to show the stale-blob width directly.
- **Then validate the remedy** with IB10 runs under both observed leads (min centre distance ≥ 0.18 m + margin, 4 / 4, yielder last).

---

## Evidence and Files

- **v3 bundles:** `data/logs/vm_runs/v3_step0/ib10/ib10_s42` (`20261007_113945`) and `ib10_s42_rep2` (`20261007_122116`) in this worktree.
- **Fix-branch and pre-fix A/B (read-only):** `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/data/logs/vm_runs/costmap_fix/ib10_s42` (`20261005_162933`) and `ib10_prefix_s42_r4`.
- **Older IB10 bundles (read-only):**
  - main checkout `data/logs/vm_runs/v2_demo/{ep1_scripted,ep2_live_er2}`
  - `plan_grammar_cal/cal_ep1_rerun`
  - `verbatim_pilot/{vp08_er2_ib10_s42,vp09_er2_ib10_s43}`
  - step-7a / 7b reruns `ib10_7b_20261003_022532` and `ib10_7b_vi_20261003_030944`. The only local copies are at `/private/tmp/claude-501/-Users-tuanhdangdinh-Documents-vgu-vlm-swarm/2099aa03-979b-42be-962f-e1aab91f6b17/scratchpad/step7b/` (temporary storage; VM originals under `/home/ubuntu/step7b_runs/`). They carry the only pre-fix robot_4-led 4 / 4 evidence.
- **Scripts (gitignored):** `data/logs/vm_runs/v3_step0/_analysis/ib10_lead_flip.py` and `ib10_regound_cf.py`.
- **Code:**
  - `reasoning/rag/command_grounder.py` (`ground_junction_clear_phases`, lead at line 2194)
  - `reasoning/rag/maneuver_geometry.py` (`recede_cost`, `rank_recede_candidates`, `recede_pocket_offset_m`)
  - `ros2_ws/src/swarm_execution/swarm_execution/command_bus_node.py` (yield `pull_off_lateral_m`)
  - `ros2_ws/src/swarm_simulation/config/nav2_params.yaml` (H, inflation)
  - `isaac/vgu_sim/config.py` (lidar-plane note)
- **Related reports:** `docs/reports/2026-10-08-v3-step0-rebaseline.md` (Stage 4), `docs/reports/2026-10-05-costmap-fix-validation.md` (3a), `docs/reports/2026-10-03-step7b-oracle-freeze.md` (rulings iv / vi).
