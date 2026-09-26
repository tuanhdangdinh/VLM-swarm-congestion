# Implementation Notes

**Prepared:** 2026-07-11

**Revision history:**

- Initial draft: living log created; seeded with verified notes from M1/M4/M6 work through 2026-07-08 and the congestion-reasoner program state.

---

## Purpose and Maintenance Rules

This is the project's **living implementation log**: dated, append-only notes
recording decisions, verified fixes, gotchas, and open items that do not fit a
one-shot report. It complements — never replaces — the other document types:

- **Specs** (`docs/specs/`, `docs/superpowers/specs/`) define what to build.
- **Plans** (`docs/superpowers/plans/`) define how to build it, task by task.
- **Reports** (`docs/reports/`) are one-shot deep dives on a completed module
  or investigation (structure in `docs/standards/doc_style.md`).
- **This file** captures the connective tissue: "we learned X on date Y,
  evidence at Z" — the facts you need before touching a subsystem.

Rules for maintaining it:

- One bullet per note: `- **YYYY-MM-DD** — fact (pointer to commit, doc, or file).`
- Append under the matching module section, newest entry first. Do not rewrite
  or delete old entries; if a note is superseded, append the new fact and mark
  the old one `superseded by <date> entry`.
- Convert relative dates to absolute before writing.
- Link evidence (commit hash, spec, report, config file) instead of restating
  detail that lives elsewhere.
- Update the header revision history only for structural changes to this
  document, not for routine entries.

---

## Congestion-Resolution Experiment (research program: M2/M3/M5)

- **2026-09-26** — **`_bshort` validated on both sides at the ±2.6 passer
  goal; adopted as the pre-registration T2a scenario.** Six ER-2 runs on
  tree `cf4899f` (east K1–K3 first-ever, west K4–K6 re-run after the
  `dcfa144` widening): 6/6 position-verified, correct yielder executed 6/6
  (gate `swap` fired 2/6), 0 refusals on 39 calls, 0 Nav2 recoveries, passer
  backtrack 0.000–0.003 m. Discharges prereg amendment A1's condition and
  the Rev 6 §W item 6 scenario question. Two caveats recorded: realised
  escort margin is 0.063–0.096 m (Nav2 stops the passer short of the
  nominal 2.6), and K1 is a second G4-class 0.076 m interpenetration during
  ER-2's opening non-yield phase with all safety layers silent
  (pre-Arm-B blocker, amendment A5). Findings Rev 10 §AI; artifacts
  `data/logs/vm_runs/bshort2/` (git-ignored).
- **2026-09-26** — **Pre-registration amendment set drafted from the pilot
  campaign**: `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`
  binds the 2026-09-24/26 adjudications (`_bshort` T2a instrument, random
  presentation order with order-conditioned analysis, gate `swap` scored
  pre-gate, position-verified episode outcome primary, distance-channel
  safety columns, `max_attempts: 4` + ER-2 as secondary backend replacing
  `llama_server`) for absorption into the research design spec as rev 9 at
  the `prereg-v1` tag. Its freeze-blocker list records that
  `reasoning/baselines/classical_reasoner.py` (Arm B) is specified but not
  implemented — the largest open work item — plus the `_bshort` east
  validation, the failure-context depth decision, and the credit-blocked
  gpt-4o arms. Draft only; nothing frozen until the tag.
- **2026-09-26** — **`scripts/rescore_arrivals.py` flags accepted arrivals
  whose pose reaches into a static obstacle box** (`8e77bc4`). For each
  `within_tolerance` accept it reads `static_obstacles` from the run's
  scenario YAML (`--scenarios-dir`, default `isaac/config/scenarios`) and
  sets `box_overlap` / `box_overlap_obstacle` when the M1 position lies in a
  box grown by `ROBOT_HALF_WIDTH_M` = 0.175 m, with a stderr warning.
  Reporting only; verdicts unchanged. Motivation: the `_bshort` blocked-side
  goal sits 0.20 m from the box near face, so the 0.35 m tolerance band
  reaches inside the box. 0.175 m is conservative against the 0.14 × 0.18 m
  Nav2 footprint: on `_bshort` any accept ≥ 0.025 m past the goal toward the
  box flags. Local re-run over 41 runs: 0 flags (no `_bshort` runs synced).
- **2026-09-25** — **Every pre-`4f39899` run re-scored against M1's position
  check; exactly one arrival flips.** `scripts/rescore_arrivals.py` re-runs
  `arrival.py::classify_arrival` offline over all 31 `data/logs/vm_runs/`
  runs (55 reported arrivals) plus a ground-truth cross-check. Only
  `20260925_124609` (ER-2 pilot `E1` `robot_2`, the known Nav2 false success)
  rejects; M1-vs-GT bias is ~6 mm everywhere including that case. ER-2 pilot
  both-arrived count corrects 3/6 → 2/6; the other seven batches are
  unchanged. Detail: `docs/reports/2026-09-25-arrival-rescoring.md`.
- **2026-09-25** — **M3 can now refuse or re-ground a yield the scene makes
  impossible** (`8362178`, feature branch `feat/m3-yield-feasibility`, not
  merged). The feasibility rule the family oracle already encoded moved into
  `reasoning/rag/scene_geometry.py` (`required_room_m`, `yield_retreat_room_m`,
  `yield_feasible`), so `isaac/vgu_sim/family_oracle.py` and the executed
  maneuver now score off one function; a test regenerates the three committed
  family `oracle:` blocks unchanged (`06feaf8`). `ground_reasoner_result` gains
  `static_obstacles` + `yield_feasibility_mode` (`off`/`swap`/`refuse`; M5 key
  `grounding_yield_feasibility`), `swap` recording `yield_robot_grounded_from`
  on the yield action. **Ships off, and is a no-op while `static_obstacles`
  stays commented out in `orchestrator.yaml`** — turning it on is an
  experimental condition, since it changes which robot executes.
- **2026-09-25** — **The yielder the VLM names follows presentation order, not
  geometry; the 2026-09-19 confound is resolved.** A counterbalanced offline
  probe (`scripts/probe_presentation_order.py`, 360 calls, 0 parse failures, 0
  API errors) ran the three head-on asymmetric family scenarios x
  `id_asc`/`id_desc` x static-obstacle channel on/off, at temperature 0.0 (n=5)
  and 0.6 (n=10), through the production `Reasoner`/`openai` path. Reversing the
  presentation order collapses `P(yield_robot == robot_1)` from 20/20 to 5/20 for
  gpt-4o (Fisher p = 7.7e-07) and from 20/20 to 0/20 for gpt-4o-mini
  (p = 1.5e-11). `P(yield_robot == correct_yielder)` stays at chance
  (0.40–0.59) in every condition, with or without the obstacle channel, and no
  justification string ever cited the obstacle. **gpt-4o-mini matches `H_slot`
  outright; gpt-4o is slot-dominant with a residual `robot_1` pull** (under
  `id_desc` it does not commit, 0.75 at T=0.0 and 0.53 at T=0.6, so its signature
  verdict is "mixed" rather than clean `H_slot`). The bias is not
  instruction-compliance: the "first listed robot backs up" clause was removed
  before this probe and a guard test asserts its absence. **Consequence: every
  decision artifact collected before `922dd36` was rendered at `id_asc` and
  carries this bias, so the obstacle-channel A/B cannot be reported as a modality
  result until the order confound is removed from the historical artifacts too.**
  Probe is offline with a synthetic plan-view image — a deviation from the live
  pipeline that a counterbalanced live run must confirm. Modality added in
  `922dd36` (`ReasonerRequest.robot_presentation_order`, M5
  `prompt_robot_order`, shipped `id_asc`); probe and raw data in `dadb3f5`
  (`data/experiments/2026-09-25-presentation-order/`). Full detail:
  `docs/reports/2026-09-25-presentation-order-probe.md`.
- **2026-09-19** — **Paired A/B run on the head-on-asymmetric blocked
  variant is a null result, confounded by presentation order.** Two recorded
  gpt-4o runs on `head_on_asymmetric_w0p2_eopen_o0` (Run A modality off
  `20260919_042935`, Run B modality on `20260919_044729`) both chose
  `yield`/`yield_robot=robot_1` — the side the parked blocker makes
  infeasible — both `FAILED` at a ~0.093 m standoff (the robot's own
  half-width against the box), both followed with `reverse` (dispatched
  symmetrically, so it cannot resolve a two-robot head-on), and neither
  produced an arrival. **Supplying the obstacle's id/centre/extent produced
  no measurable change in the decision under test — but this is a single
  paired run, not a distribution, and `robot_1` is also the first robot the
  prompt presents (states rendered "sorted by ID"), so the model's choice
  and presentation order are perfectly confounded in both runs; the result
  bounds nothing about the modality in general and does not by itself
  distinguish a positional default from a spatial judgement.** Breaking the
  confound needs a counterbalanced `involved_robots`-order condition —
  applies to every artifact collected to date, not just these two runs.
  Full detail: `docs/reports/2026-09-18-head-on-family-validity.md`, "RQ5
  recovery runs (gpt-4o), modality A/B" (`6d9f540`).
- **2026-09-19** — **VM harness traps found running the head-on-asymmetric
  family (Tasks 7–8), all three would recur.** (1) `rsync --delete` without
  a curated exclude list will delete VM-only build outputs and secrets
  (`.env`, generated Isaac assets); even a previously-curated exclude list
  can miss stray VM-only files, so prefer an explicit synced-file list over
  `--delete` for small changesets, or dry-run and read the deletion list
  line by line. (2) `rsync -a` preserves source mtimes, so a source file
  older than the VM's last build output is silently *not* recopied by
  `colcon build`/setuptools `build_py` even though the build reports
  success — after any `rsync -a`, touch every source file and wipe
  `ros2_ws/{build,install,log}` before rebuilding, or the run executes
  another branch's installed code (this produced a `GeminiBackendConfig`
  `ImportError` from a stale install). (3) `grep -c <symbol>` on an
  installed file is not a sync check — a different branch's independent
  implementation of the same field name gives a false positive; use
  `md5sum`/`sha256sum` against the worktree source instead. Detail:
  `docs/reports/2026-09-18-head-on-family-validity.md`, "Harness Findings".
- **2026-09-19** — `build_backend`'s mock branch (`reasoning/vlm/backend_factory.py`)
  now accepts a JSON array in `VGU_MOCK_DECISION_FILE`, scripted into
  `MockBackend(response_sequence=...)`, which holds its last entry once
  exhausted; a single-object file keeps the unchanged `response_text=...`
  behaviour. Added `config/mock_decisions/head_on_yield_once.json` and
  `head_on_yield_robot_2_once.json` (existing yield decision, then a
  `congestion_detected: false` decision) so key-less runs can represent a
  scene that clears instead of replaying the same decision forever. This
  was root-caused from the T1 control run in
  `docs/reports/2026-09-18-head-on-family-validity.md` Rev 2: the frozen
  single-decision mock, not an M4 defect, caused `robot_1` to be
  re-commanded (and re-cancelled) on all 16 stall-triggered M2 analyses.
  `head_on_yield.json` / `head_on_yield_robot_2.json` are left frozen —
  a later task needs that form for an arm where the forced maneuver is
  expected to fail. Supersedes the 2026-09-16 entry below only insofar as
  the hook now supports a scripted sequence, not just a single decision.
- **2026-09-17** — Phase 2 slice landed ahead of Phase 1: failure-context
  feedback (rev-8 A.1) is wired end-to-end — `AttemptMemory` in M5, `FailureContext`
  + prompt block in M2, context recorded in decision artifacts. Episode rule =
  time window after resolution, any outcome (rev 8.2). Design:
  `docs/superpowers/specs/2026-09-17-failure-context-closed-loop-design.md`;
  plan: `docs/superpowers/plans/2026-09-17-failure-context-closed-loop.md`.
  Host verification pending (see M2/M5 section).
- **2026-07-11** — Phase 1 execution deliberately deferred. Prerequisites
  before data collection: commit the rev-8 spec + Phase 1 plan; fill the two
  REQUIRED pre-registration fields (primary `openai` `model_id` — blocked on
  API key — and secondary `llama_server` `model_id`); then tag `prereg-v1`.
- **2026-07-08** — Phase 1 implementation plan written:
  `docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md`
  (15 TDD tasks, offline reasoning core + Arm B). Not yet executed. Key
  decision: `GroundingParams.mode` = `legacy` (default) / `derived`;
  `config/rag.yaml` stays `legacy` until Phase 2 flips the M5 call site, so
  the live loop is untouched by Phase 1. Planned phase split: 1 reasoning
  core, 2 M5/M1 integration, 3 M4 execution semantics, 4 scenario battery +
  oracle blocks, 5 harness + pre-registration freeze.
- **2026-07-08** — Spec rev 8 applied (external design review):
  `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`.
  Adds run matrix + statistical plan (paired-seed, N=30 pairs per T1 scenario
  with a one-time extension rule), full Arm B classical-reasoner
  specification with tuning-parity rule, T0 log-only negative probes,
  RQ1–RQ5 renaming (was H1–H5, collided with the "H3" run series),
  model/decoding pre-registration table, and rev-6 mechanism detail restored
  as Appendix A.
- **2026-07-08** — Open reconciliation item for the pre-registration freeze:
  the rev-8 model table pins temperature 0.0 (classification rule), but
  `ReasonerConfig` deliberately defaults to 0.6/0.95/20 because Cosmos
  Reason 2 is a chain-of-thought model that degrades at temperature 0.0
  (comment in `reasoning/vlm/models.py`). Resolution: 0.0 for non-CoT
  backends, model-card preset for CoT models, exact values recorded at
  freeze.

---

## M1 Perception

- **2026-09-16** — **Marker-plane calibration: 7.5 % radial bias removed.**
  `pixel_to_world_homography` computed the homography for the ground
  plane z = 0, but the ArUco marker sits at z = 0.21 m; for the nadir
  camera at 3.0 m every world coordinate M1 reported was inflated by
  3.0/(3.0−0.21) = 1.0753 (measured: spawn −1.5 read as −1.62; errors of
  0.178 m at GT −2.268 and 0.156 m at −2.074, ratios 1.075–1.081). Fix:
  `pixel_to_world_homography(config, plane_height_m=0.0)` translates the
  camera centre down by the plane height (exact for the general tilted
  case); `build_calibration_dict` defaults `plane_height_m` to
  `MARKER_HEIGHT_M` (0.21, defined locally with a parity test against
  `marker_asset`, which cannot be imported without Isaac) and records it in
  the artifact. Regenerated `swarm_perception/config/calibration.yaml`:
  scale 0.004686 → 0.004358 m/px, offsets −2.999/2.249 → −2.789/2.092;
  intrinsics unchanged. Residuals on the three measured instances after
  the fix: 7 mm, 7 mm, 0 mm. The old test oracle used the camera height
  as the plane height — it had encoded the bias. **Consequences:** M5's
  proximity/stall geometry now sees true distances (≈7 % smaller than
  before); `annotation.py` draws registry goals (floor points) through
  the inverted marker-plane homography, so goal markers in the VLM's
  annotated frame now render ~7 % too far from the image centre —
  cosmetic, open. Host verification of M1-vs-GT with the new artifact is
  part of run D.

- **2026-07-03** — Colliding/overlapping ArUco markers make robots go STALE
  (marker lost), not STOPPED, which delays stall detection. Mitigation:
  `stale_after_sec` ≥ 3.0 and `velocity_alpha` ≈ 0.15 in the perception
  config for congestion scenarios.
- **2026-06-17** — Marker placement contract: the ArUco marker prim must live
  under `aruco_marker_link` (a `base_link` child inside the physics
  hierarchy), not under the robot root, or physics parses fail;
  `isaac/vgu_sim/validation.py` checks this and must be updated in sync with
  any marker-asset change (silent crash otherwise). See
  `docs/superpowers/specs/2026-06-17-aruco-markers-on-sim-robots-design.md`.

---

## M2 VLM / M5 Orchestrator Pipeline

- **2026-09-26** — **Rev 7 consolidates the night: two live batches and two
  safety-metric corrections** (`docs/reports/2026-09-25-overnight-findings.md`
  §X–§AC). Detail is in the per-topic entries — the two 2026-09-26 entries below
  (image fallback; batch-2 replay replication), the 2026-09-25 re-scoring entry
  under **Congestion-Resolution Experiment**, the 2026-09-26 `_gshort` entry
  under **M6**. New: batch 2 (gpt-4o random order, 5/6, but draws aligned with
  side so the gate rate is confounded; refusals 37.5% a-1 / 14.3% terminal) and
  batch 3 (ER-2 forced order, 5/6, 0 refusals) — **ER-2 has no `robot_1` anchor**
  (1/3 where gpt-4o is 124/125), so the slot/ID artifact is model-specific.
  **Binds every prior run: `safety.yaml min_distance_m: 0.45` is breached in
  every Arm A run (0.23–0.28 m by design; G4 wedged at 0.076 m ~18 s), and a
  zero `robot_robot_contacts` count is detector silence — use min pairwise distance.**
- **2026-09-26** — **Neutral-image fallback lands in M2; its validation arm is
  coded but unrun (no OpenAI credits).** `ReasonerConfig.image_fallback_after_attempts`
  (shipped `2`, `openai` only) makes a refused attempt `k >= threshold` re-send the
  *unchanged* prompt with a mid-grey PNG of the frame's size — once per request, no
  re-ask suffix, backends untouched; cost recorded in
  `diagnostics.{refusal_attempts,image_fallback_used,image_fallback_attempt}`. Spec
  §M2.5 FR2.5.4-5; `9d7328f`, `a255cc8`. Arm X (168 cells) aborted on
  `insufficient_quota` with **zero** rows — resume with
  `python scripts/replay_live_decisions.py --arm X --runs batch2 --n 4 --pace-sec 8.0`.
- **2026-09-26** — **Batch-2 replication weakens the obstacle-text finding;
  raw-frame arm unrun (credits).** `docs/reports/2026-09-25-frame-replay.md`
  Rev 4; Arm S2 187/288 runs, $1.24, aborted on `insufficient_quota`. The
  text-on → text-off contrast replicates in direction (pooled 0.714 → 0.375,
  p = 1.1e-3; 7/9 scenes) but **Rev 3's level does not**: P(feasible) 0.962
  (batch 1) vs 0.435 (batch 2) on prompts differing only in pose decimals, so
  the side signal is fragile and scene-dependent. Frame-amplification contrast
  (b) is now unconfirmed (batch 2 has no headroom to test it). Frame refusal
  trigger replicates: 17/96 real, 0/91 grey.
- **2026-09-25** — **Sampling config and the raw camera frame are now on record**
  (M2 §7.1 `EffectiveSamplingConfig`, M5 FR5.3.11). Every decision artifact and
  reasoner JSONL line carries `reasoner_config_effective` (model_id,
  temperature, top_p/top_k/presence_penalty, max_attempts, max_tokens, gemini
  seed/thinking_level, `unsupported_sampling`), as configured from
  `config/models.yaml` — no prior artifact proved gpt-4o ran at 0.0, the gap the
  ER-2 pilot logged as "sampling uncontrolled"; failure cycles record it too.
  `keep_raw_frames: true` (needs `keep_debug_frames`) also dumps M1's input frame
  as `<request_id>_raw.png` with `raw frame skew_sec=`; the M2 request is unchanged.
- **2026-09-25** — **Rev 6 consolidates the day: side-signal carrier, ER-2
  pilot, position-verified arrival** (`docs/reports/2026-09-25-overnight-findings.md`
  §S–§W). The three entries below carry the detail (obstacle-text side signal,
  FR5.1.9 arrival check, `max_attempts` 2 → 4). New in Rev 6: the six-run ER-2
  pilot (`data/logs/vm_runs/ER2_PILOT_SUMMARY.txt`, runs
  `20260925_{124609,130115,132335,133841,135334,140824}`) — 0/115 refusals,
  gate 2/6, episode outcome 3/6 by log but 2/6 physically, sampling
  uncontrolled; the earlier "geometry unused / channel inert" claims marked
  superseded for gpt-4o; the ER-2 opening `reverse` marked trigger-confounded
  (3/4 solo-stall vs gpt-4o 0/6). **Do not quote any pre-`4f39899` arrival
  count until it is re-scored from the scene log at 0.35 m.**
  (`docs/reports/2026-09-25-frame-replay.md` Rev 3; Arms S and D, 348 runs,
  $2.66). Within-artifact ablation on the six genuine standoffs (3/side) x order
  x obstacle-text x image: withholding the text with the real frame kept
  collapses P(feasible) 0.962 → 0.556 (p = 8.8e-4); the frame amplifies; states
  alone carry nothing. Still **0/288** traces cite the blocker — **never read
  trace silence as a channel being unused; ablate.** `id_asc` picks `robot_1`
  124/125 whatever the channels, so the slot bias *suppresses* this one.
- **2026-09-25** — **Base-goal arrival is now position-verified (FR5.1.9).** M5
  marked a robot arrived on Nav2's own "Goal succeeded": in run
  `20260925_124609` `bt_navigator` succeeded for robot_2 while M1 put it 0.59 m
  away (logged `distance_to_goal_m={'robot_2': 0.59}` 21 times after).
  `swarm_orchestrator/arrival.py` cross-checks it at 0.35 m (> M1's ≈0.1 m bias,
  ≤ `arrived_radius_m`); a rejected arrival stays stall-eligible and is accepted
  late once M1 reaches tolerance. Episode closure now follows the verdict, so
  `prompt_robot_order: random` draw sequences shift too. **Prereg:** episode
  outcome must be position-verified in both arms — re-score pre-fix runs from
  `scene_log_dir`, and treat their order draws as not comparable either.
- **2026-09-25** — **`openai` reasoner `max_attempts` raised 2 → 4.**
  `config/models.yaml` nests `max_attempts: 4` under `vlm.openai.reasoner`.
  Per Arm M (`docs/reports/2026-09-25-frame-replay.md` Rev 2), conditional
  on a refused first attempt, terminal refusal is 57.1% shipped vs 26.9% at
  `max_attempts=4` (p = 0.031); trigger is the annotated frame, not text.
- **2026-09-25** — **Rev 5: Arm A pilot green on the adopted defaults; the
  refusal class is bigger and image-driven**
  (`docs/reports/2026-09-25-overnight-findings.md` §O–§R, consolidating the
  three entries below). Six runs (`20260925_063520`/`065143`/`070637`/`072130`/
  `073621`/`075116`, gpt-4o T=0.0, obstacles ON, order `random`, gate `"swap"`,
  `keep_debug_frames: true`): M2 named an infeasible yielder in 4/6, the gate
  re-grounded all four, first yield COMPLETED 6/6 (142.2–147.9 s), episode
  outcome 4/6 — both misses the blocker-on-goal-path property, not coordination
  failures. First `yield_robot` = `robot_1` in 5/6 (ID-anchored); zero `reverse`
  openings. **Supersedes the "3 of 22" refusal figure in the §K–§N entry
  below**: 23/101 attempt-1, 12/101 terminal, 9 of 12 obstacle-ON, Rev 1 §6(b)
  included. Replay Arms O/M/grey stay blocked on OpenAI credit.
- **2026-09-25** — **Frame replay complete (rev 2); supersedes the "Arm O n=1 /
  Arms M, grey not run" entry below.** 546 runs, 708 calls, $3.97
  (`docs/reports/2026-09-25-frame-replay.md`). Grey sub-arm settles the refusal
  trigger within one design: **0/120** refusals on grey images against 22/60 on
  the same prompts with their real frames (p = 1.5e-12). Arm R over all 74
  artifacts: 42/222 attempt-1 (18.9%), terminal 9.9%. Arm O (n=8): P(robot_1)
  0.979 `id_asc` vs 0.468 `id_desc` (p = 5.0e-9); under `id_desc` **only**, the
  choice covaries with obstacle side (west 2/23 vs east 20/24) — mechanism OPEN:
  0/95 decisions and 0/95 `<think>` traces cite the obstacle, and n = 3
  artifacts per side. Do NOT flip the default to `id_desc`; keep
  `prompt_robot_order: random`. Arm M: `max_attempts=4` cuts terminal refusals
  from 57.1% to 26.9% of refused analyses (p = 0.031); retrying the ORIGINAL
  prompt is worse than the re-ask (85.7%). **Action: set `max_attempts: 4` for
  the gpt-4o reasoner.**
- **2026-09-25** — **The real annotated frame is the gpt-4o refusal trigger**
  (`scripts/replay_live_decisions.py`, report
  `docs/reports/2026-09-25-frame-replay.md`). All 74 pilot prompts re-render
  byte-identically from `scene` + `orchestrator.yaml.used` + stored order (74/74
  SHA-256, failure-context artifacts included). Replaying 36 of them x n=3 with
  the real PNG gives 27/108 attempt-1 refusals (25.0%) against 0/240 on the same
  prompts with synthetic images (p = 1.2e-13) and 8/36 live (p = 0.83); terminal
  11.1%, re-ask recovers 55.6%. Arm O reached only n=1/cell and Arms M/grey did
  not run — the OpenAI credit balance was exhausted mid-run (HTTP 429
  `insufficient_quota`, now a `QuotaAbort`; resume with the same commands, cells
  are keyed and skipped).
- **2026-09-25** — **gpt-4o refuses ~23% of M2 calls; the re-ask recovers half,
  and the prompt is not the trigger.** Census of all 163 local decision
  artifacts: 12 terminal refusals (not 3) spread over obstacle-ON *and* -OFF
  runs, plus 11 `parse_status="invalid"` artifacts with the same
  "no JSON object" signature that the re-ask rescued — so 23/101 gpt-4o calls,
  0/62 ER-2. Every prompt-side split (obstacles p=1.0; failure context
  0.0030→0.094; time window 0.013→0.080) collapses once attempt 1 is scored,
  two refusals differ from a success by two characters, and a 240-call offline
  replay of the stored prompts (± re-ask suffix, T=0/0.6, wording ablations,
  gpt-4o-mini) produced **0 refusals** in 30/30 cells, $1.21. Act:
  `max_attempts` 2→4, and
  persist per-attempt `raw_text`. `docs/reports/2026-09-25-gpt4o-refusals.md`.
- **2026-09-25** — **The offline presentation-order probe does not predict live
  behaviour; gpt-4o has a refusal failure class.** Five gate-`off` runs on
  `w0p2_eopen` (`20260925_035042`/`040539`/`042022` ER-2, `043512`/`045004`
  gpt-4o, tree `e6be85c`). ER-2 without the gate reproduces the gpt-4o failure
  (D2 named the blocked `robot_1`, yield FAILED, arrested at the same 0.1020 m)
  but not deterministically — 3/6 `robot_1` across all six ER-2 asymmetric runs.
  gpt-4o with the obstacle channel OFF still names `robot_1` (9/11 live, 5/6
  under `id_desc`) against 0.25 offline: **the live pipeline is ID-anchored, the
  synthetic probe slot-anchored** — treat the probe as a stimulus study. New:
  3 of 22 gpt-4o analyses returned `"I'm sorry, I can't assist with that."`
  (`VLMOutputParseError`, `attempts=2`), 0 of 37 on ER-2; and ER-2's opening
  `reverse` is 5/6, not 3/3. `docs/reports/2026-09-25-overnight-findings.md` §K–§N.
- **2026-09-25** — **ER-2 verified live as an M2 backend; its signature is an
  opening `reverse`.** Four closed-loop runs (`20260925_021549`/`023122`/
  `024628`/`030129`, tree `e6be85c`) all reached 2/2 arrivals with 25/25
  artifacts `attempts=1`, `parse_status=valid`, no `decision=None`, no 429s. ER-2
  matches gpt-4o on the symmetric baseline and on the gate cell (G1 named the
  blocked `robot_1`; M3 `swap` re-grounded to `robot_2`), but on **every**
  asymmetric scene it opens with `reverse`, which completes in ~35 s without
  resolving the standoff — failure context then steers it to `yield`, one extra
  analysis per episode. So **ER-2's first decision is not comparable to
  gpt-4o's**; use episode outcome as the primary metric. Permanent confounds:
  the Interactions API drops sampling and emits no `<think>` block though
  thinking is billed. `docs/reports/2026-09-25-overnight-findings.md` §F–§J.
- **2026-09-25** — **ER-2 arm of the offline presentation-order probe**
  (`docs/reports/2026-09-25-presentation-order-probe.md` Rev 2).
  `probe_presentation_order.py --backend gemini --seeds N` sweeps seeds `0..N-1`
  (one backend per seed) because the Interactions API has no temperature; records
  carry `seed` + `unsupported_sampling` and rows key on `temperature="seeded"`,
  leaving the gpt-4o rows byte-identical. 180 calls, 0 parse failures: ER-2 chose
  `reverse` in 155/180, `P(correct)=6/13`, and the textual obstacle channel drives
  `yield` to zero (60/60 vs 47/60, p=1.2e-04) with no justification naming it.
- **2026-09-25** — **`feat/gemini-er2-backend` merged onto the FR2.1.9 line**
  (`c7a08e7`, a `--no-ff` merge of `7d6e1c4`). Select ER-2 with
  `reasoning_backend_id: gemini` in
  `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml` plus a
  `GEMINI_API_KEY` in the environment; `config/models.yaml`'s `vlm.gemini`
  block carries no `reasoner:` override on purpose, so the backend inherits the
  shared sampling defaults (temperature 0.6) and reports what the Interactions
  API drops in `ReasonerDiagnostics.unsupported_sampling`. `vlm.openai` still
  resolves to temperature 0.0, unchanged. Prompt-block order after the merge:
  robot states → pairwise geometry → static obstacles → known IDs → failure
  context → guidance → visual cross-check → output format, so the cross-check
  block's "the pairwise geometry above" still refers to a block above it.
  **Re-pin:** the crosscheck baselines `_BASELINE_PROMPT_SHA256` (`5a57c937…`
  → `3b77d224…`) and `_BASELINE_PROMPT_SHA256_NO_GEOMETRY` (`4664ff95…` →
  `a9c8abfc…`) in `tests/unit/test_prompt_builder.py` were generated at
  7f5e075, which predates the permanent `yield_robot` stimulus change; a
  rendered diff of `_request()` at 7d6e1c4 vs the merge shows only the three
  documented FR2.1.9 edits, so the pins were re-pointed, not the prompt fixed
  (`590ac23`). The geometry-on value is now identical to
  `_PRE_OBSTACLE_OFF_PROMPT_SHA256` by construction; both constants are kept
  because they pin the same string for different reasons. Artifacts under
  `data/logs/er2_grounding` were collected under the 7f5e075 prompt and are
  comparable with each other, not byte-identical to post-FR2.1.9 renders.
- **2026-09-25** — **Five live gpt-4o runs validate the feasibility gate; `swap`
  is the recommended default.** L1 `20260925_002713` (`id_asc`, `swap`)
  re-grounded `robot_1`→`robot_2` → COMPLETED yield, 2/2 arrivals, on the cell
  that fails deterministically ungated (L4 `011246`, `off`: FAILED at 0.102 m,
  0/2). The gate is a no-op when the yielder is already feasible (L2 `004252`,
  L3 `005754`); `refuse` is inferior (L5 `012747`, 1/2). Random order is
  mechanically correct (provenance verified, `episode_index` stable at 0 across
  an episode) but changes no outcome alone. **Corrects the order entry below:
  live, the slot effect is weaker than offline — `robot_1` named in 7/9 pooled
  obstacle-ON live runs regardless of order, and L1 vs L3 (identical config)
  disagreed, so T=0.0 is not run-to-run deterministic.** Caveat: all five runs
  ran obstacles ON, so order and channel co-vary. `docs/reports/2026-09-25-overnight-findings.md` §B–§D.
- **2026-09-25** — **M3's yield feasibility gate is now visible in the M5
  decision artifact.** Merging `feat/order-random` and
  `feat/m3-yield-feasibility` left a provenance gap: with
  `grounding_yield_feasibility` on, the robot that executes a yield need not be
  the one `decision.yield_robot` names, and nothing outside the grounded
  command said so. `summarize_yield_grounding` (`reasoning_pipeline.py`) reads
  the gate's outcome back off that command — a swap tags the yield action's
  parameters with `yield_robot_grounded_from`, a refusal drops the yield action
  and fans out `temporary_wait` with a `"yield refused:"` reason — and
  `write_decision_artifact` records `yield_robot_grounded_from`,
  `yield_regrounded_reason`, `yield_refusal_reason` plus the configured
  `grounding_yield_feasibility` mode. Gotcha: the refusal test must be the
  `"yield refused:"` **prefix**, not the presence of `reason` — a yield that
  grounded normally also carries one, the M2 root cause. The node logs
  `yield re-grounded request=… from=… to=… reason=…` /
  `yield refused request=… reason=…` on the same helper, so the log and the
  artifact cannot drift. Spec FR5.3.10 in `docs/specs/module5_orchestrator.md`.
- **2026-09-25** — **`prompt_robot_order: random` counterbalances the
  presentation order per congestion episode, with the drawn order auditable.**
  `swarm_orchestrator/presentation_order.py` adds a pure
  `PresentationOrderPolicy(mode, seed).order_for_episode(k)` plus an
  `EpisodeOrderTracker` that holds one episode's order across its re-analyses;
  each decision artifact now carries `robot_presentation_order` (read off the
  request, so it cannot disagree with the persisted prompt hashes),
  `prompt_robot_order_mode`, `prompt_robot_order_seed` and `episode_index`.
  Gotcha: the episode scope is **not** `AttemptMemory`'s — that memory returns
  nothing at `failure_context_window_sec: 0` (the RQ5 memoryless control), which
  would re-draw the order inside a single deadlock. `prompt_robot_order_seed:
  null` derives the seed from `VGU_RUN_ID` via SHA-256, not `hash()`
  (`PYTHONHASHSEED` randomizes string hashes per process). Default stays
  `id_asc`. Commit `43bf941`; spec FR5.3.9 in `docs/specs/module5_orchestrator.md`.
- **2026-09-25** — **Live counterbalanced runs confirm the offline verdict: the
  yielder M2 names follows presentation order, not feasibility.** Four gpt-4o
  runs, obstacle modality ON: R1 `20260924_195708` `w0p2_eopen`/`id_desc` →
  `robot_2`, COMPLETED 146.4 s; R2 `20260924_201328` `w0p2_eopen`/`id_asc` →
  `robot_1`, FAILED 243.7 s arrested 0.102 m from the blocker; R3
  `20260924_203437` / R4 `20260924_205009` `wopen_e0p2`/`id_desc` → `robot_1`
  twice, COMPLETED. **Caveat: the three `id_desc` runs yielding a feasible robot
  is a design coincidence — each bias aligns with feasibility in one variant —
  not feasibility reasoning; no justification cited the obstacle.** Gotcha:
  `static_obstacles` ships commented out in `swarm_orchestrator/config/orchestrator.yaml`,
  so `prompt_static_obstacles: true` alone renders no obstacle block while the
  MODALITY guard reports ON. Detail: `docs/reports/2026-09-25-overnight-findings.md`.
- **2026-09-25** — **Closed loop replicated on the new host** (run_id
  `20260924_193112`, `head_on_deadlock`, openai gpt-4o at temperature
  0.0, obstacle modality OFF). First analysis 34.6 s after components
  started, both robots stalled at 0.26 m nose-to-nose (a third onset
  mode between the 0.08 m contact and the ≈0.45 m planner-stall standoff
  recorded 2026-09-16); one `yield` (`yield_robot=robot_1`), `COMPLETED`
  after 148 s; robot_2 arrived at +3.3 min, robot_1 at +5.5 min; 12 m
  52 s wall; 0 analyses after both arrivals (2 348 `trigger suppressed`
  lines). Deviation worth keeping: after robot_2 had arrived, a *solo*
  stall of robot_1 (`robots=['robot_1']`, distance 1.18 m, not facing)
  triggered a second analysis that the model answered `anomaly`/`reroute`
  — the congestion gate fires on single-robot stalls, which the
  pre-registration's episode rule should account for. Component logs
  live inside the container (`/tmp` of `vgu_ros`); `docker cp` them
  before the launcher's exit-trap restart. Artifacts (git-ignored):
  `data/logs/vm_runs/20260924_193112/` on the workstation.
- **2026-09-19** — **Correction: the OFF-condition comparability claim below
  overstates what the byte-identity test proves, and the 44/44 census
  over-reads compliance as absence-of-signal** (final whole-branch review,
  Finding 1). (a) `yield_robot` (FR2.1.9) has **no OFF condition** — it is a
  permanent prompt change (adds the output-format bullet, extends the
  `<think>` step, and removes the `strategy="yield" (first listed robot
  backs up)` clause) applied to every request from `c4072d0`/`0efd01e`
  onward. Rendering the shared `_request()` fixture at branch base
  `e21326f` (3171 chars, sha `5a57c937…`) versus HEAD with the obstacle
  modality off (3338 chars, sha `3b77d224…`) shows the 167-char delta these
  edits introduced. The obstacle modality's byte-identity test (`056fa22`,
  below) pins the OFF obstacle condition against the tree *after* this
  change — a true and useful guarantee for isolating that one modality, but
  it does not establish that the OFF condition at HEAD matches the
  pre-2026-09-19 stimulus, which the entry below implies. (b) The 44/44
  `robot_1`-first census below (design review Finding 2) was collected
  under a prompt that *instructed* "first listed robot backs up", so it is
  substantially evidence of compliance with that instruction, not only
  evidence that the position channel went unused when free to vary. Full
  reasoning: `docs/specs/module2_vlm_reasoning.md` FR2.1.8/FR2.1.9,
  `docs/reports/2026-09-18-head-on-family-validity.md` Rev 6.
- **2026-09-19** — **Two observability channels landed as declared,
  default-off Arm A modalities** (owner instruction: "do your
  recommendations", responding to the 2026-09-19 design review). (1)
  `CongestionDecision.yield_robot: str | None`, meaningful only when
  `strategy == "yield"`, never required — module-2 FR2.1.9
  (`c4072d0`, `0efd01e`: `feat: add explicit yield_robot field to the
  congestion decision`, `fix: scope yield_robot reordering to yield and drop
  the list-order hint`). `reasoning.rag.command_grounder.resolve_robot_order`
  moves it to the front of `involved_robots` only for `strategy == "yield"`,
  leaving `reroute` (which reads `robot_ids[0]` as the rerouter) and every
  other strategy untouched. Before this field, list position in
  `involved_robots` was the only yielder channel; a census of 524 decision
  artifacts found `robot_1` listed first in 44/44 `yield` decisions — never
  once `robot_2` — i.e. position had never been observed to carry a choice
  (`docs/superpowers/specs/2026-09-19-head-on-asymmetric-family-design-review.md`,
  Finding 2; caveated by the 2026-09-19 correction above — the prompt
  instructed this exact convention, so 44/44 is compliance evidence too).
  (2) `ReasonerRequest.include_static_obstacles` /
  `static_obstacles: list[StaticObstacleInput]`, rendered as a
  "Static obstacles (world-frame axis-aligned boxes):" block (id, centre,
  extent only — no wording naming a robot, maneuver, or blocked side) —
  module-2 FR2.1.8, M5 `prompt_static_obstacles` (`bf2d89d`, `501bb49`:
  `feat: add static-obstacle prompt modality behind a default-off flag`,
  `fix: keep prompt-facing obstacle ids neutral and gate the ON clause`).
  Both default **off**; an off prompt (or an on prompt with no obstacles
  configured) is byte-identical to the pre-modality prompt, pinned by a
  length + SHA-256 test (provenance commit `056fa22`), because every
  decision artifact collected before 2026-09-19 was produced without either
  channel and comparability depends on the off condition never changing a
  byte. **Superseded by the 2026-09-19 correction above**: "both default
  off" is true of the obstacle channel but not of `yield_robot`, which has
  no off switch, and the byte-identity test only isolates the obstacle
  modality — it does not establish comparability with the pre-2026-09-19
  corpus. `orchestrator.yaml`'s shipped `static_obstacles` ids are
  deliberately neutral (`obstacle_1`, not the scenario yaml's `blocker_west`)
  and must not be synced to the scenario yaml's descriptive names — the id
  renders verbatim into the prompt and would otherwise hand the model the
  inference the modality exists to measure (fix round 1, `501bb49`, after a
  review caught the initial `blocker_west` id as exactly that leak). Specs:
  `docs/specs/module2_vlm_reasoning.md` FR2.1.8/FR2.1.9,
  `docs/specs/module5_orchestrator.md` (config table), rev-8 spec rev 8.6.
- **2026-09-18** — **`include_visual_crosscheck` does NOT transfer to
  `gpt-4o`: a prompt-level change with a model-level effect. Do not turn the
  flag on for the `openai` arm.** Full five-cell x two-variant matrix against
  `openai`/`gpt-4o` at its pinned temperature 0.0 (resolved via
  `resolve_reasoner_config`, recorded per artifact), same two stimuli
  (SHA-256 re-verified `1dea9aed…3589` / `ad5db360…ea31`, re-measured at 0.251 m
  and 4.884 m), n = 5 per cell per variant, 50 calls: Experiment 6 in
  `docs/reports/2026-09-18-gemini-er2-image-grounding.md`; artifacts
  `data/logs/er2_grounding/grounding_run4_gpt4o_xcheck_{off,on}.jsonl` (VM,
  git-ignored). No harness change was needed — the probe already drove
  `--backend openai --experiment 4`. Results: both gates 5/5 in both variants;
  the cross-check-off half **replicates the earlier n = 3 baseline exactly**;
  the added Fix-B regression cell E stayed no-congestion **5/5 in both
  variants**, so the wording does not reopen run 3 on the arm that produced it.
  But the incongruent cells answer per the image **1/10** against ER-2's 10/10
  (cell B 1/5, cell C 0/5), missing the pre-stated ≥ 3/5 criterion in both — so
  the flag is ineffective, not unsafe, here. Three consequences: (a) **new
  hazard** — justifications mentioning the image go 0/25 → 18/25 with the flag
  on, and 9/10 contradiction-cell calls assert the image *confirms* the states
  while the frame grossly contradicts them, so `justification` text cannot be
  read as evidence of image use (register A8); (b) **A3's scope changes** —
  `gpt-4o` never returned ER-2's `anomaly`/`priority_override`, but its one
  detecting call misclassified too (`crowding`/`reroute`), and in a *different
  way*: ER-2 mislabelled the input-integrity condition (a missing enum slot),
  `gpt-4o` mislabelled the physical configuration (a wrong pick among existing
  slots — `deadlock` was available). So A3's conflation claim still rests on
  ER-2 alone, the recommended `state_disagreement` type would not have fixed
  `gpt-4o`'s error, and A3 is the binding blocker for `gemini` only since
  `gpt-4o` mostly fails to detect at all (register A3 now carries a
  minimal-ontology-fix recommendation — not implemented); (c) **two
  prior observations narrowed** — `gpt-4o` at temperature 0.0 is *near*-, not
  fully, deterministic (2–5 unique raw responses per 5 repeats, so every n = 5
  "5/5" here is ~n = 1 plus a stability check), and the `<think>` block is a
  verbatim template echo in 23/25 and 19/25 rather than 12/12, with the added
  content landing only in the congruent cells (contradiction cells: pure echo
  10/10). VM protocol as before: `reasoning/vlm/{models,prompt_builder}.py` and
  the probe script installed for the run and restored byte-verified afterwards
  (`7cf02340…b071d7` / `e1441903…41ea6e4`), probe script not left resident.
  Register open item 2 closed (`docs/reports/2026-09-18-research-findings-register.md`).

- **2026-09-18** — **The 2026-09-18 null result was our prompt, and it is
  apparatus-wide: an opt-in image/state cross-check inverts it without
  breaking Fix B.** *(Partly superseded by the entry above: the null result is
  apparatus-wide, but the cross-check fix is ER-2-specific.)* New modality flag
  `ReasonerRequest.include_visual_crosscheck` (default `False`;
  `reasoning/vlm/models.py`, `reasoning/vlm/prompt_builder.py`) appends a block
  that gives the image precedence over the state block **only on a clear
  contradiction**, leaving Fix B's "do not re-derive distances or facing from
  the coordinates" clause verbatim; the off-variant prompt is byte-identical to
  the pre-flag one, pinned by SHA-256 in `tests/unit/test_prompt_builder.py`.
  Measured on the same two stimuli, n = 5 per cell, both variants (report
  Experiments 4–5 in `docs/reports/2026-09-18-gemini-er2-image-grounding.md`;
  artifacts `data/logs/er2_grounding/grounding_run3_{xcheck_off,xcheck_on,gpt4o_off}.jsonl`,
  VM, git-ignored): ER-2's incongruent cells go from **0/10 to 10/10
  image-consistent** answers with both gates still 5/5, and the added Fix-B
  regression cell (1.2 m apart, `|Δθ| = π`, diverging, both MOVING) still
  answers no-congestion 5/5 under the new prompt — run 3 is **not**
  reintroduced. Two facts that block adoption and one that changes the
  preregistration: (a) cell B's detection is right but 4/5 of its answers are
  `type=anomaly` with `priority_override`/`reroute` rather than
  `deadlock`+`yield`/`reverse`, so the flag would dispatch the wrong command —
  do not turn it on in production yet; (b) the same 2x2 against
  `openai`/`gpt-4o` at its pinned temperature 0.0 followed the text 6/6, so
  "Arm A's decision is text-driven under the production prompt" applies to the
  primary cell too, and the parent spec's modality table now carries the axis
  as `—`/unregistered (rev 8.6); (c) `gpt-4o` does emit a `<think>` block
  (12/12) but its content is a verbatim echo of the prompt's template sentence,
  settling ER-2 design doc §4(d)'s unverified claim in the direction of "no
  usable trace from either hosted arm".

- **2026-09-18** — **Gemini ER-2 reads our overhead frame but does not decide
  from it: decision-level image grounding is NOT demonstrated.** Report:
  `docs/reports/2026-09-18-gemini-er2-image-grounding.md`; harness
  `scripts/probe_gemini_er2_grounding.py`; artifacts
  `data/logs/er2_grounding/grounding_run{1,2_exp3_n9}.jsonl` (VM, git-ignored).
  Two frames from `run_id=gemini_20260918_084649`, measured at 0.251 m
  (nose-to-nose) and 4.884 m apart, were crossed with synthetic 0.35 m-facing
  and 2.50 m-diverging text states through the unmodified prompt and
  `Reasoner` at `thinking_level: low` with no `seed`. Both congruent gate
  cells passed 3/3; in the incongruent cells the decision followed the
  **text** — 6/6 calls with `include_pairwise_geometry=True` (n = 3/cell) and
  22/24 with it `False` (n = 12/cell), the 2 exceptions being the only
  responses in 36 decision calls whose justification reads visual rather than
  numeric. ER-2's native pointing, by contrast, hit both robots in both
  frames (12/12 points inside half a robot width, 0.005–0.125 m, including
  the pair 0.25 m apart), so the image is readable to it and still does not
  move the answer. Prereg consequence: for this scenario and prompt the
  `gemini` Arm A cell is equivalent to a text-only reasoner (spec Rev 5 open
  item). **Gotcha:** the ArUco detector cannot be re-run reliably on M1
  *annotated* frames — the 40x40 px status box and the velocity arrow are
  drawn over the 28 px marker and destroy its quiet zone (both markers
  recovered in 3 of 121 sampled frames) — so ground truth for an annotated
  frame comes from `data/logs/m5_scene/<session>.jsonl` at the header stamp
  `scripts/record_topic_video.py` burns into the frame, which agrees with
  re-detection to ~1 mm where both are available.
- **2026-09-18** — **Gemini ER-2 live-run recipe committed as
  `scripts/run_gemini_er2_demo.sh`, generalized over `BACKEND_ID`.** The
  launch sequence behind the `gemini_20260918_084649` run (entry directly
  below) existed only as `/tmp/gem_record_launch.sh` on the VM and would not
  have survived a reboot; retrieved and landed in the repo. Backend is now a
  parameter (`BACKEND_ID`, default `gemini`) instead of hardcoded: the script
  sets `reasoning_backend_id` in `ros2_ws/src/swarm_orchestrator/config/
  orchestrator.yaml` and runs `colcon build --merge-install --packages-select
  swarm_orchestrator` before launching, because `orchestrator.launch.py`
  loads the **installed** copy via `get_package_share_directory` — a source
  edit alone is inert (same trap noted in the entry below). The cleanup trap
  now restores the previous `reasoning_backend_id` and rebuilds again on
  exit, so a run can no longer silently leave the VM pointed at a different
  model — that exact revert had to be done by hand after the live run this
  script is derived from. Matches `scripts/run_phase3_demo.sh` house
  conventions (`set -euo pipefail`, `log`/`wait_topic`/`wait_action`
  helpers, `sudo timeout` not `timeout sudo`, cleanup trap) and preserves the
  bracketed-`pkill` convention (`"[i]saac.scripts.run_simulation"`) from
  `docs/superpowers/plans/2026-09-18-head-on-asymmetric-family.md` so a kill
  pattern can't match its own invocation. ffmpeg re-timing (`setpts=<stamped
  fps / achieved fps>*PTS`, per the entry below's 2.1033 factor) is
  documented as a manual post-step in the script header, not automated —
  achieved fps is only known from the recorder's own exit line after the
  run. Verified with `bash -n` and a read-through only; not re-run on the VM
  (that would repeat the ~20 min live demo).
- **2026-09-18** — **Full closed-loop `head_on_deadlock` demo run live on the
  `gemini` backend (Gemini Robotics-ER 2); both robots reached their goals and
  the entry directly below's artifact fix is confirmed live.** Run
  `run_id=gemini_20260918_084649` on the GCP VM (run-H recipe:
  `localization:=camera`, M1 before Nav2, seed 42). Five analyses, all
  `backend_id=gemini-robotics-er-2-preview`, all `parse_status=valid` at
  `attempts=1` — so **`force_schema=false` held up live with zero re-asks and
  zero parser rejections**, and no fallback to `openai` occurred. Sequence:
  `deadlock`/`reverse` dispatched and `completed` but did not clear the
  standoff; the next analysis carried `failure_context` and ER-2 explicitly
  cited it ("the previous attempt to reverse both robots did not successfully
  resolve the deadlock, the yield strategy is now selected"), returning
  `deadlock`/`yield`, which M3 grounded, M4 dispatched, and which resolved the
  conflict — robot_2 arrived at `(-2.5, 0.0)`, robot_1 at `(2.5, 0.0)`. This
  is the first end-to-end evidence that the failure-context loop changes a
  *live* second decision, not just a unit-test fixture.
  **Artifact confirmation of the fix below:** every one of the five
  `data/logs/m5_decisions/<request_id>.json` files carries
  `diagnostics.unsupported_sampling = {"presence_penalty": 0.0,
  "temperature": 0.6, "top_k": 20.0, "top_p": 0.95}` (`top_k` renders as
  `20.0` because `_extract_unsupported_sampling` casts through `float`).
  Correction to that entry's wording: the M5 path writes no *reasoner* JSONL —
  `write_reasoner_log` is called only by tests, and M5's JSONL is the M1 scene
  log (`append_scene_log` → `data/logs/m5_scene`), which carries no
  diagnostics. The confound is checkable only from the per-request JSON that
  `swarm_orchestrator.reasoning_pipeline.write_decision_artifact` writes,
  which dumps `ReasonerDiagnostics.model_dump(mode="json")` wholesale.
  **Measured, single run, not a claim about the models:** ER-2 latency mean
  3384 ms (min 3162, max 3765) against the tagged gpt-4o run
  `run_id=20260917_163714` at 3863 ms; total tokens mean 2297 vs 1826, the
  gap explained by ER-2's `thought_tokens` (137–224/call), which has no
  gpt-4o counterpart. ER-2 returned `congestion_detected=false` on three of
  five analyses with explicit numeric grounds (robots "1.20 meters apart",
  above the 0.5 m threshold) while robots were still flagged stalled — i.e.
  it declined to declare deadlocks on separated/parked robots, the inverse of
  gpt-4o's spurious-deadlock failure mode recorded for run 3. One run and
  five calls: directional only, not a measured difference.
  **Two setup traps confirmed, one brief correction.** The backend switch is
  `reasoning_backend_id` in `ros2_ws/src/swarm_orchestrator/config/
  orchestrator.yaml`, not `config/models.yaml`, and `orchestrator.launch.py`
  loads the **installed** copy via `get_package_share_directory`, so the
  source edit only takes effect after `colcon build --merge-install
  --packages-select swarm_orchestrator` (plain `colcon build` errors in this
  workspace). Contrary to the dispatch brief, the VM's **source**
  `orchestrator_node.py` also lacked the `gemini` branch of
  `_load_vlm_config`, as did `reasoning/vlm/{reasoner,models}.py` (VM is not a
  git checkout; files are hand-copied) — all three needed copying from
  `85b4b18`. Also contrary to the brief, the `Path("config/models.yaml")`
  CWD trap was never live here: container `vgu_ros` already has
  `WorkingDir=/ws`, so prior `openai` runs were not silently falling back;
  `-w /ws` was passed anyway to make that definitive. Isaac must be launched
  as the `ubuntu` user (`/home/ubuntu` is mode 0750). Evidence:
  `data/logs/recordings/2026-09-18/` (git-ignored; 566 s real-time capture,
  recorder achieved 3.941 fps against a stamped 8.289, so playback needs
  `setpts=2.1033*PTS`).

- **2026-09-18** — **`unsupported_sampling` now reaches the persisted run
  artifact, not just `BackendResponse.raw`/stderr.** Closes the gap the
  entry directly below flagged: `GeminiBackend` recorded dropped
  `temperature`/`top_p`/`top_k`/`presence_penalty` in
  `BackendResponse.raw["unsupported_sampling"]`, but `Reasoner.run()`
  (`reasoning/vlm/reasoner.py`) only threaded `latency_ms`/`token_usage`/
  `parse_status` into `ReasonerDiagnostics`, so a preregistered run's JSONL
  trace never carried the confound. Added
  `ReasonerDiagnostics.unsupported_sampling: dict[str, float] | None = None`
  (`reasoning/vlm/models.py`; `None` means "backend honoured everything or
  didn't report," distinct from an empty dict). `Reasoner.run()` now
  validates and threads `BackendResponse.raw.get("unsupported_sampling")`
  through every diagnostics-construction site — first-attempt success,
  re-ask-then-success, and exhausted-retries via `build_failed_result`
  (malformed values, e.g. non-dict or non-numeric entries, are dropped to
  `None` rather than raised). `write_reasoner_log` emits the key only when
  set. This is backend-agnostic: `AnthropicBackend`/`OpenAIBackend`/
  `LlamaServerBackend` are untouched and get `None`, so `AnthropicBackend`'s
  equivalent silent drop (`anthropic_backend.py:42`) remains invisible in its
  own artifacts until it adopts the same `raw["unsupported_sampling"]`
  convention — see the open-items list in
  `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`
  (Rev 4). Tests: `tests/unit/test_reasoner.py` (new cases covering presence,
  absence, malformed input, the re-ask path, and the JSONL artifact).

- **2026-09-18** — **`gemini` VLM backend landed and live-verified through the
  real reasoner path.** Supersedes the "backend code remains untouched" line
  in the probe entry directly below: `GeminiBackend`
  (`reasoning/vlm/gemini_backend.py`), `GeminiBackendConfig`
  (`reasoning/vlm/models.py`), the `"gemini"` branch in
  `reasoning/vlm/backend_factory.py`, and a `vlm.gemini` block in
  `config/models.yaml` are implemented (`force_schema` defaults `False`, per
  the probe's gate result) and unit-tested
  (`tests/unit/test_gemini_backend.py`, 20 tests, mocked `requests`).
  `AnthropicBackend`'s silent drop of `temperature`/`top_p`/`top_k` is not
  repeated: `GeminiBackend` records the four `ReasonerConfig` sampling fields
  it cannot send in `BackendResponse.raw["unsupported_sampling"]` on every
  call and logs one WARNING per backend instance. Verified live on
  `vgu-canary-base-isaac-workstation-vm` (container `vgu_ros`) through
  `reasoning.vlm.reasoner.Reasoner` — not the probe script — via a throwaway
  scratchpad driver wrapping `build_backend("gemini", GeminiBackendConfig())`
  in a response-recording shim, against the same real frame the probe used
  (`data/logs/m5_frames/0cad824071954e21832da19a6fcb588b.png`) with two
  robots 0.35 m apart and mutually facing (a genuine head-on configuration,
  unlike the probe's non-conflicting 1.00 m synthetic states). Result: HTTP
  200 (implied — the backend raises `ConnectionError` on ≥400), latency 2492
  ms, 1 attempt, `token_usage={"prompt_tokens": 1907, "completion_tokens":
  138, "thought_tokens": 121, "total_tokens": 2166}`,
  `raw["unsupported_sampling"] = {"temperature": 0.6, "top_p": 0.95, "top_k":
  20, "presence_penalty": 0.0}` populated as designed, and a correctly parsed
  decision: `congestion_detected=true type=deadlock strategy=yield
  involved_robots=[robot_1, robot_2]` — the textually correct answer for a
  0.35 m head-on pair under the prompt's 0.5 m threshold rule, extracted from
  a markdown-fenced JSON block despite `force_schema=False`. This also
  confirmed the real usage-block shape empirically: the provider nests usage
  under a top-level `"usage"` key with `total_input_tokens`,
  `total_output_tokens`, `total_thought_tokens`, `total_tokens` present
  exactly as named in the Rev 2 probe's §6 cost table, plus additional
  per-modality breakdown fields (`input_tokens_by_modality`,
  `model_invocation_token_counts`) not used by the mapping but preserved
  verbatim in `raw`. `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py`'s
  `_load_vlm_config` also gained a `"gemini"` branch (`GeminiBackendConfig(**backend_raw)`)
  so the `vlm.gemini` config block resolves through the production path, not
  only through direct `build_backend` calls. Full design rationale, the
  request/response schema, and the reproducibility/confound discussion:
  `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`
  (Rev 3).
- **2026-09-18** — **Gemini Robotics-ER 2 probe run live on the VM: §7 gate
  PASSED.** Supersedes the "not yet run against a live key" line in the
  entry directly below. `scripts/probe_gemini_er2.py` ran inside container
  `vgu_ros` on `vgu-canary-base-isaac-workstation-vm`
  (`sudo docker exec -w /ws vgu_ros bash -lc "set -a && source /ws/.env &&
  set +a && python3 scripts/probe_gemini_er2.py --schema --thinking-level
  low"`; key sourced from `/home/ubuntu/vgu-vlm-swarm/.env` so it never
  reached argv; `x-goog-api-key` worked on the first attempt, no bearer
  fallback needed). The probe's repo search found a real committed-on-VM
  frame, `data/logs/m5_frames/0cad824071954e21832da19a6fcb588b.png`
  (`data/logs/` is git-ignored, hence "no image found" on a fresh checkout);
  no placeholder was synthesized. **Both** conditions passed: `--schema
  --thinking-level low` (HTTP 200, 3562 ms, 2166 total tokens: input 1907 /
  output 88 / thought 171) and `--no-schema --thinking-level low` (HTTP 200,
  2605 ms, 2194 total tokens: input 1907 / output 85 / thought 202) each
  returned a payload satisfying `reasoning/schemas/vlm_decision.schema.json`
  and passed both `parse_decision_text` (tolerant) and `parse_vlm_decision`
  (strict): `congestion_detected=false, type=none, strategy=none` on the
  probe's hardcoded robots (1.00 m apart, prompt threshold 0.5 m) — the
  textually correct answer, though the states are synthetic against a
  real-but-arbitrary scene frame, so this is schema conformance and
  threshold arithmetic, not demonstrated image grounding (one sample per
  condition). **New confound:** both responses billed `total_thought_tokens`
  (171 / 202) but returned **no visible `<think>…</think>` block** at all —
  ER-2 withholds its reasoning trace regardless of `response_format`,
  breaking trace-level comparability with the `llama_server`/Cosmos arm's
  visible-trace design (`llama_server_backend.py` deliberately omits
  `response_format` to preserve that trace); untested candidate mitigation
  `generation_config.thinking_summaries`
  (<https://ai.google.dev/api/interactions-api>). **Measured cost:**
  ≈$0.0032/analysis at standard pricing from Result 1's counts (both probe
  calls actually ran free tier, $0.00), roughly half the project's measured
  ≈$0.006/analysis for `gpt-4o`; latency 2.6–3.6 s. Full evidence,
  reproduction recipe, limitation discussion, and updated cost arithmetic:
  `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`
  (rev 2, "Gate result and open questions" + "Cost"). Backend code
  (`reasoning/vlm/gemini_backend.py`, `backend_factory.py`,
  `config/models.yaml`) remains untouched: passing the gate does not by
  itself authorize landing the backend, which stays pending the user's
  decision on research design.
- **2026-09-18** — **Gemini Robotics-ER 2 evaluated as a candidate third Arm A
  backend; gated on a probe, not landed.** The page originally proposed for
  this evaluation (`ai.google.dev/gemini-api/docs/generate-content/robotics-spatial`)
  is marked "(Legacy)"; the live transport is the **Interactions API**
  (`POST https://generativelanguage.googleapis.com/v1beta/interactions`), not
  `:generateContent` — request field `input` (Content items, not a
  `messages`/`role` list), response text at `steps[].content[].text`, no
  `messages`. Target model `gemini-robotics-er-2-preview` (the
  `-streaming-preview` Live API variant does not support structured output;
  `-er-1.6-preview` is being shut down end of August 2026). **Key finding:**
  `generation_config` has no `temperature`/`top_p`/`top_k` field at all — not
  merely unsupported values, absent from the schema — so this backend cannot
  be pinned to greedy decoding the way `openai` is (`config/models.yaml`
  `temperature: 0.0`, pinned after run 3's `|Δθ| ≈ π` diverging-robots
  misread, rev-8 spec 8.4). Nearest controls are `seed` and `thinking_level`
  (low/high), a new ablation axis with no counterpart in `openai`/`llama_server`.
  Noted in passing: `anthropic` (`reasoning/vlm/anthropic_backend.py`) already
  drops `temperature`/`top_p`/`top_k` for the same reason (HTTP 400) and is
  **not** in the parent spec's "Model and decoding pre-registration" table —
  an existing, unrecorded between-arm confound that a `gemini` cell must not
  repeat. Design doc (full transport delta table, Option A backend sketch,
  Option B spatial-primitives-as-grounding deferral, cost estimate):
  `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`.
  Gate: `scripts/probe_gemini_er2.py` (real M2 prompt + schema
  `response_format` against the live API) must pass before
  `reasoning/vlm/gemini_backend.py`/`backend_factory.py`/`config/models.yaml`
  are touched; not yet run against a live key as of this entry — superseded
  by 2026-09-18 entry above (probe run live on the VM, gate PASSED).
- **2026-09-17** — **Research-readiness items 2–4 landed.** (2) The derived
  pairwise-geometry lines are a switchable modality
  (`ReasonerRequest.include_pairwise_geometry`, M5 `prompt_pairwise_geometry`,
  default on) and an ablation axis — rev-8 spec 8.5, module-2 FR2.1.7
  (`feat: derived pairwise geometry becomes a switchable prompt modality`).
  (3) Measurement plumbing (`feat: artifacts carry run/session ids, rendered
  prompt, scene; 1 Hz scene log`): every decision artifact now records
  `run_id` (from `VGU_RUN_ID`, exported by the launch scripts as the STAMP),
  `session_id` (per M5 process), the rendered prompt with SHA-256 hashes
  (rebuilt by the pure prompt builder; a re-ask suffix on retry is not
  captured), the M1 `scene` snapshot the request came from, and the detector's
  `distance_to_goal_m`; the request is now built on the callback thread so the
  artifact records exactly what was sent. M5 also writes one scene snapshot
  per second to `data/logs/m5_scene/<session_id>.jsonl` (`scene_log_dir`,
  `scene_log_period_sec`). (4) Investigation report:
  `docs/reports/2026-09-17-failure-attribution-ladder.md`. Host check for (3)
  done (run 6, 16:38–16:48 UTC, unrecorded): artifact `6bbcadbb…` carries
  `run_id=20260917_163714`, `session_id`, the rendered prompt (3 597 chars,
  both hashes), the scene with both robots and `distance_to_goal_m`; scene log
  `data/logs/m5_scene/c76c9c10….jsonl` had 493 lines after ~8 min (≈ 1 Hz).
  Aside: this run's onset differed (first analysis 9 min in, `bottleneck/
  reroute` on robot_1 at 3.7 m from goal) — the run-to-run variance the paired
  design exists for; stopped right after the check.
- **2026-09-17** — **Run 5 (recorded) confirms fix A: silence once parked.**
  Same stack, 11:02–11:15 UTC. M4 reported `base goal reached` for robot_2 at
  11:06:08 and robot_1 at 11:08:11; M5 logged `arrived at base goal` for both.
  5 analyses in total: the initial `deadlock/yield` (distances 2.61/2.63 m),
  then four `none` answers on robot_1 alone while it was genuinely slow in
  the gap (`distance_to_goal_m` 3.82 → 3.46), and **none at all after
  11:08:11** — seven minutes where run 4 made ~25 needless gpt-4o calls.
  robot_2 was never analysed after its arrival. Ground truth at the end:
  0.09 / 0.04 m from goals, 4.9 m apart. Runs 3 → 4 → 5: 12 → 32 → 5
  analyses, 11 → 1 → 1 dispatches. Fix C was not exercised (no false
  deadlock to refuse after fix B). Video + timeline:
  `data/logs/recordings/2026-09-17/run5_failure_context_annotated.mp4`,
  `README_run5_after_fixes_a_c.md` (git-ignored; logs and segments on the VM
  host under `data/logs/fc_check_20260917/run5_*`). Side note: 2 682
  `trigger suppressed … frame_ready=True` lines during the yield (the detector
  fires at frame rate while robots are busy/cooling down — pre-existing log
  noise, harmless).
- **2026-09-17** — **Fixes A and C landed** (`feat: arrived signal from M4
  excuses parked robots from stall evidence`, `fix: refuse reverse when both
  robots are past the corridor on one side`). C: M3 now refuses `reverse` under
  the same rule as the yield refusal — both robots past the corridor mouth on
  one side → `temporary_wait` for both with `requested_strategy: reverse`
  (shared helper `_beyond_corridor_same_side`; run-3 positions −1.22/−2.46 are
  the test case). A: M4's coordination client publishes
  `CoordinationStatus(command_id="base_mission", status="COMPLETED")` when
  Nav2 reports a base goal reached (module-4 README); M5 routes it to
  `CongestionDetector.mark_arrived`, which excuses the robot from stall
  evidence while M1 keeps it within `arrived_radius_m` (0.5 m,
  `orchestrator.yaml`) of that goal (module-5 FR5.1.8); `CongestionEvent.
  distance_to_goal_m` + the `starting analysis` log now show M1's distance
  per stalled robot. Host check: run 5 (recorded) pending — expect no
  analyses once both robots are parked, and the logged distances to reveal
  M1's offset at the goals.
- **2026-09-17** — **Run 4 (recorded) confirms fix B: no mid-scenario
  re-approach.** Same stack, 10:33–10:47 UTC, gpt-4o at temperature 0.0 with
  the pairwise-geometry prompt. 32 analyses, **1 dispatch** (the initial
  `deadlock/yield` at 10:34:39), **31 `congestion_detected=false`** — including
  the three attached re-analyses right after the yield completed (10:37:36,
  10:37:54, 10:38:13), the exact point where run 3 flipped to `deadlock/
  reverse`. Ground truth at the end: robot_1 0.08 m and robot_2 0.04 m from
  their goals, 4.9 m apart. Video + timeline:
  `data/logs/recordings/2026-09-17/run4_failure_context_annotated.mp4`,
  `README_run4_after_fix_b.md` (git-ignored; logs and segments on the VM host
  under `data/logs/fc_check_20260917/run4_*`). Still open: the detector
  re-fired `2 robot(s) stalled` every cooldown on two parked robots for 9 min
  (31 gpt-4o calls answering `none`) — fix A; and fix C as a safety net.
- **2026-09-17** — **Root cause of the mid-scenario re-approach (runs 1–3):
  M5-induced.** Evidence (run 3 ground truth + frames + M4 log): the first
  yield resolves correctly and robot_2 reaches its goal (`Goal succeeded`
  09:50:11, GT 0.04 m). Then (1) the detector re-fires `2 robot(s) stalled`
  every cooldown — robot_1 legitimately (Nav2 progress failures in the 0.7 m
  gap, 4 recoveries 09:48–09:51), robot_2 spuriously although parked at its
  goal (M1's camera estimate must exceed `goal_reached_tolerance_m` 0.15;
  unverifiable — scene_state is not logged); (2) on the same scene the VLM
  answered `none` twice (09:50:17, 09:50:37) then `deadlock/reverse`
  (09:50:56, `parse=invalid` re-ask) with "stopped and facing opposite
  directions" — the robots were 1.1 m apart and heading AWAY from each other,
  which the prompt's `|Δθ| ≈ π` heuristic could not distinguish from head-on;
  temperature 0.6 made the flip stochastic; (3) M3 grounded `reverse` for
  both with no guard for a robot at its goal, M4 executed it (09:51:00), and
  robot_2 backed east into the aisle mouth: GT 0.39 m at sim 120–155 s, a
  self-inflicted deadlock that seeded the yield/reverse alternation (robot_1
  ended at x = −5.3). **Fix B landed** (`feat: pairwise geometry and
  facing-based head-on definition in the prompt`, `feat: per-backend reasoner
  sampling override; gpt-4o samples greedily`): the prompt now states each
  pair's distance and mutual facing (60° cone) and defines head-on as facing
  + ≤ 0.5 m (module-2 FR2.1.7); `openai` samples at 0.0 via
  `vlm.openai.reasoner` in `config/models.yaml` while Cosmos keeps its preset
  (FR2.2.3; rev-8 spec 8.4). Not yet done: fix C (grounding guard: never back
  up a robot at its goal / past the corridor) and fix A (arrived = M4 goal
  status, log detector distances). Host check: run 4 (recorded) in progress.
- **2026-09-17** — **Run 3, recorded: degraded-yield wording verified live.**
  Same stack, 09:46–09:59 UTC, `scripts/record_topic_video.py` on
  `/perception/annotated_frame` (8.7 Hz stamped, 3.5 fps achieved under load →
  re-timed with ffmpeg); video and event timeline at
  `data/logs/recordings/2026-09-17/run3_failure_context_annotated.mp4` +
  `README_run3_failure_context.md` (git-ignored; raw segments and logs on the
  VM host under `data/logs/fc_check_20260917/run3_*`). 12 decisions, 2 `none`
  right after the first yield completed (09:50:17, 09:50:37 — the rev-8.3
  advice), then yield/reverse alternation on genuine re-stalls (`close/slow`
  triggers 09:53:01, 09:56:59). M3 refused two yields (both robots past the
  corridor), and the next blocks read `"yield completed 18 s ago (executed as
  temporary_wait); …"` (09:53:01, 09:58:44 attaches; artifact justification:
  "Previous yield strategy was ineffective") — supersedes the "unit-tested
  only" caveat in the run-2 entry below.
- **2026-09-17** — **Run 2 with the rev-8.3 block: the memoryful VLM now
  answers `none`** (08:20–09:32 UTC, same run-H stack, gpt-4o; logs on the VM
  host under `data/logs/fc_check_20260917/run2_*`). 91 analyses, 43 with
  `failure_context`, **58 `congestion_detected=false` (64 %) vs 2 of 16 in
  run 1**; 23 dispatches; both robots ended at their goals (GT 0.06 / 0.07 m
  from goal). First yield completed 08:24, then three consecutive attached
  re-analyses (08:25:11/30/51, `strategy=yield executed=yield`) answered
  `none`, and the memory expired; later `none` answers with a reroute context
  attached read e.g. "Robots are significantly apart with no opposing headings
  or physical conflict" (08:36–08:37 artifacts). Strategy rotation
  still occurred mid-run (yield/reverse alternation 08:4x–09:0x while the
  robots re-stalled), so the closing-advice change reduces but does not
  remove post-resolution intervention. Defect found and fixed (`fix: name the
  executed maneuver by the decided strategy's own action`): a `reroute` fans
  out as `reroute` + `temporary_wait`, which the first summarizer labelled
  `mixed`, so three blocks read "reroute completed … (executed as mixed)";
  `summarize_executed_strategy(actions, strategy)` now names the decided
  strategy whenever its own action ran (unit-tested; label change not re-run
  on the host). No M3-degraded yield occurred this run, so the "(executed as
  temporary_wait)" wording is unit-tested only. Gotchas: `run_simulation
  --duration-sec 900` did not stop Isaac (GT sim time reached 1 608 s;
  stopped by hand); with both robots parked at their goals M5 still fired
  `1 robot(s) stalled` for robot_1 every cooldown — M1's camera estimate of
  distance-to-goal sits outside `goal_reached_tolerance_m` (0.15) where GT
  says 0.06 — worth a look before Arm A/B collection.
- **2026-09-17** — **Previous-attempt block: executed maneuver + explicit
  `none` option** (`feat: report the executed strategy in the previous-attempt
  block`, `feat: previous-attempt advice names congestion_detected=false`;
  rev-8 spec 8.3, design rev 3). `AttemptRecord.executed_strategy` is derived
  from the fanned-out action names (`summarize_executed_strategy`) and, when it
  differs from the decided strategy, `failure_detail` reads e.g. `"yield
  completed 15 s ago (executed as temporary_wait); …"`; the block's closing
  advice now says to report `congestion_detected=false` when the congestion is
  gone. **Why:** the entry below — M3-degraded yields were told to the VLM as
  "yield completed", and the memoryful model rotated strategies on stalls that
  were no longer congestion. Host check pending (next entry).
- **2026-09-17** — **Failure-context attach verified on the VM** (run
  07:03–07:24 UTC, `localization:=camera` stack, gpt-4o; logs on the VM host
  under `data/logs/fc_check_20260917/`). First decision 07:03:57
  `deadlock/yield` (artifact `d012f061…`, `failure_context: null`) →
  `COMPLETED` 07:06:36 → **natural** re-detection 07:06:52 (`2 robot(s)
  stalled`) → M5 logged `failure_context attached command=…-yield
  strategy=yield outcome=completed` → artifact `52b76ea6…` carries
  `failure_context = {strategy: yield, yield_robot: robot_1, outcome_status:
  completed, failure_detail: "yield completed 15 s ago; congestion re-detected
  for the same robots"}` and the decision changed to `deadlock/reverse`. Over
  the run: 16 decisions, 15 with context attached, all `parse_status=valid`
  (one `invalid` recovered by re-ask), 2.1–6.0 s latency; the model cites the
  block in its justifications ("The previous 'yield' strategy did not resolve
  the issue, so 'reverse' is recommended" — `7501e9ff…`, also `6583a8ba…`,
  `ff81d9d3…`, `9b37ef9c…`, `3118df9d…`). Manual
  `/orchestrator/trigger_analysis` calls were all rejected `suppressed`
  because a command was always active; the natural path covered the check.
  This closes the "host check pending" item in the entry below. Two
  observations for the experiment, not defects of the mechanism: (1) the
  memoryful VLM alternated yield/reverse across 14 cycles on post-resolution
  stalls of robots ~6.5 m apart (ground truth 07:22: robot_2 overshot its goal
  by 2.1 m after a `reroute`), answering `none` only twice — RQ5's measurable
  behaviour; the `failure_context_window_sec: 0` ablation is the control.
  (2) `AttemptMemory` records the decision's strategy, so a yield that M3
  degraded to `temporary_wait` (`yield_robot: null`) is still reported to the
  VLM as "yield completed" — recording the grounded strategy would be more
  faithful; open item. Also visible now: `resolved status=` logs 3–5× per
  command because `_on_status` re-enters `_resolve_command` on every status
  message once the command is terminal (pre-existing; harmless).
- **2026-09-17** — **Previous-attempt context on re-analysis** (commits
  `feat: add FailureContext and ReasonerRequest.failure_context` through
  `feat: M5 attaches previous-attempt context on re-analysis`). M5 records
  each dispatched attempt (`strategy`, `yield_robot` = the robot whose
  fanned-out action is `yield`), finalizes it on resolution with
  `timed_out > failed > completed` precedence, and attaches it to the next
  `ReasonerRequest` for overlapping robots inside `failure_context_window_sec`
  (default 60 s; must exceed cooldown + stall threshold = 27 s, enforced at
  config load; 0 = off). The prompt gains a "Previous attempt in this episode"
  block; the artifact gains `failure_context`. **Why:** runs G/H re-derived
  every cooldown with no memory (rev-8 A.1, run 12). Host check pending: force
  a re-analysis via `/orchestrator/trigger_analysis` inside the window and
  confirm `failure_context != null` in the artifact.
- **2026-09-17** — **Robots within goal tolerance are excluded from stall
  detection.** `CongestionDetector.update` now skips a robot whose
  distance-to-goal ≤ `goal_reached_tolerance_m` (new `OrchestratorConfig`
  field, default 0.15; `orchestrator.yaml`), clearing its stall
  bookkeeping the same way STALE robots are handled; the close/slow-pair
  rule is untouched (two robots jammed at a goal still trigger).
  **Why:** an arrived robot is stationary by definition and read as
  `stalled ≥ 12 s` forever; in runs C, D, G and H that re-triggered
  analyses every cooldown on parked robots, and in G and H gpt-4o
  eventually answered deadlock/yield for two robots sitting at their
  goals, pulling one off its goal. Spec: module5 FR5.1.7. Host check
  pending (M5 should stay idle with both robots parked at ±2.5).
- **2026-09-16** — **Yield refused when both robots are past the corridor
  on the same side.** In the geometry-aware path, if
  `|yielder − center| > half_length` and `|passer − center| > half_length`
  with the same sign, the grounder emits `temporary_wait` (8 s,
  `requested_strategy: yield`, reason string) for every involved robot
  instead of a yield — the "park on the yielder's own side" rule would
  otherwise pick the far side and reverse the yielder through the whole
  corridor with backup/escort at their clamps (observed in run C after
  localization failed and M5 re-triggered). No-geometry and inside/
  straddling cases unchanged; `command_id` keeps the `-yield` suffix like
  the other degraded strategies. `expected_resolution_time_sec` is 8.0 for
  the refused case. Not yet exercised live (the trigger needs a
  post-resolution re-detection).
- **2026-09-16** — **Yield sizing derived from declared scene geometry**
  (`8cfb186`). Supersedes the constant-based sizing in the two entries
  below: `PARK_ABS_X_M` (1.8), `pull_off_lateral_m` (0.35) and
  `PASSER_CLEARANCE_M` (0.65) remain only as the no-geometry fallback.
  M5 now loads a `scenario_geometry` block from `orchestrator.yaml`
  (corridor axis/centre/half-length 1.0, aisle half-width 0.6, occluder
  height 0.9, camera 3.0, marker 0.21, robot half-width 0.09, marker
  half-size 0.06, safety radius 0.45, margins 0.3/0.15/0.2) and the
  pipeline passes it to `ground_reasoner_result(…, geometry=…)`.
  `reasoning/rag/scene_geometry.py` derives: visibility boundary
  = half_length·(cam−marker)/(cam−occluder) = 1.329; park offset =
  boundary + marker half + park margin = **1.689**; side-step =
  aisle half − robot half − wall margin = **0.36**; passer clearance =
  safety radius + margin = 0.65. The grounder works along the declared
  corridor axis (x or y) relative to `center_m`, emits `park_axis` and
  `park_coord_m` (and `park_x_m` when the axis is x), and its
  already-parked test is centre-relative (the old `park_x < 0` test
  silently assumed a corridor at 0). **Why:** the constants were
  scenario knowledge hidden in M3; the derivation makes the dependence
  explicit and lets another scenario declare different geometry instead
  of retuning code. The head_on park offset moves 1.80 → 1.69 m (still
  0.36 m outside the projected silhouette).
  **Verified live (run A, 09:47–09:52 UTC, gpt-4o):** dispatched yield
  carried `park_axis x, park_coord_m = park_x_m = −1.689,
  pull_off_lateral_m 0.36, backup 1.678, escort = clear 2.477` — every
  value reproducible from the standoff (backup = |−0.011 + 1.689|; escort
  ⇒ passer at 0.138 vs GT 0.119). Yielder parked at GT x −1.668 (2 cm from
  target); both robots resumed to their ±2.5 goals; 1 777 tokens, no
  errors. **But** with the 0.3 m margin the yielder had one **7.6 s
  detection blackout** starting 0.3 s before hold start (right after the
  side-step) plus ~5 % scattered misses while parked — versus 1.6 % /
  0.86 s max at the 1.8 m park (run 8) and minutes-long loss at 1.47 m
  (run 7). Monotonic in margin across three distances: the rendered block
  edge is softer than the geometric projection, and 7.6 s exceeds
  `stale_after_sec 3.0`. `park_margin_m` raised 0.3 → 0.4 (park ≈ 1.789,
  the distance verified clean), keeping the derivation; the margin is now
  documented as empirical.
  The geometry block must be kept in sync with
  `isaac/config/scenarios/head_on_deadlock.yaml`, `isaac/config/warehouse.yaml`
  and `CameraConfig` by hand until M5 reads the scenario file.
- **2026-09-16** — **Yield grounding is now scene-aware** (`039d92e`).
  `ground_reasoner_result(result, robot_positions=...)` takes the robots'
  world (x, y) — the pipeline passes them from `request.robot_states`, one
  hop from `SceneSnapshot.robots` — and, for `yield`, parks the yielder at
  `park_x = ∓PARK_ABS_X_M` (1.5 m; its own side, away from the passer) with
  `backup = clamp(|yielder_x − park_x|, 0.3, 2.5)` and
  `escort = passer_clear = clamp(|passer_x − park_x| + 0.65, 0.5, 4.0)`
  (0.45 m safety radius + 0.2 m). `park_x_m` is emitted in the params for
  traceability. Without positions the old 1.3 m / 2.4 m constants remain as
  the fallback, so `reverse` and all prior tests are unchanged. **Why:**
  the fixed distances were sized for one standoff position; onset is
  bimodal (run 4 stall at ~1 m vs run 6 standoff at ~0.1 m), and the
  fixed park spot sat in the 0.9 m barrier's camera shadow (see run 6
  finding below). 1.5 m clears the block top by ≥ 0.24 m for any y.
  Base goals also moved ±3.0 → ±2.5 (`orchestrator.yaml`,
  `head_on_deadlock.yaml`): ±3.0 is the ROI edge (`roi_width_m 6.0`), so a
  robot at its goal was half off-frame. Goal spheres are baked into the
  scenario USD, so this needs `build_scenario` on the sim host. `GroundFn`
  became a `Protocol` to express the keyword. 11 new unit tests; suite
  failures unchanged from the pre-existing 21.
  **Live verification (run 7, 07:32–07:38 UTC, gpt-4o):** grounded from
  the real standoff — `park_x_m −1.5`, `backup 1.528` (yielder at x≈+0.03),
  `escort = passer_clear 2.287` (passer at ≈+0.14; M1 read 0.143). Yielder
  parked at world ≈ −1.47 (odom), passer escorted 2.291 m then Nav2 to
  −2.5; **both robots reached their ±2.5 goals and were detected there
  (`STOPPED`, not `STALE`)** — the ROI change works, and it is the first
  run in which the yielder completed its mission afterwards rather than
  looping in DWB recovery (runs 4, 6). gpt-4o: deadlock/yield, 1 743
  tokens, 5.5 s; 9 post-resolution analyses all `congestion_detected=false`.
  **Open defect:** at the poll nearest `COMPLETED`, M1 reported
  `markers_detected: 1, ids_missing: ["robot_1"]` — the yielder was
  undetected while parked at ≈(−1.47, +0.35). The barrier-occlusion model
  does **not** explain this pose (the camera ray crosses x = −1 at y ≈ 0.24,
  over the corridor gap, at z ≈ 1.1 m), so occlusion by the 0.9 m blocks is
  at most a partial explanation of run 6 and not the mechanism here. Common
  factor across runs 6/7 is the +0.35 m lateral offset near the corridor
  mouth; spawn (−1.5, 0) and the goals are detected.
  **Resolved by static render probe (same day):** rendering the stage with
  robot_1 placed at five poses and running `cv2.aruco` on each frame:
  spawn (−1.5, 0) ✓, parked (−1.47, +0.35) ✓, mirror (−1.47, −0.35) ✓,
  parked facing +y ✓, but (−1.20, +0.35) ✗ — the block covers all but a
  sliver. In the (−1.47, +0.35) crop the marker sits flush against the
  block's projected silhouette. The correct occlusion model is the block's
  *projected footprint on the marker plane*, not the ray to the marker
  centre: the block top (z = 0.9) projects to |x| ≈ 1.0·(3−0.21)/(3−0.9)
  ≈ 1.33 and |y| ≥ 0.275·1.329 ≈ 0.37, so a 0.12 m marker centred at
  |x| = 1.47 has ~0.08 m of clearance — inside the odometry error of a
  1.5 m reverse plus a turn-drive-turn sidestep, and inside anti-aliasing
  flicker at the silhouette. Fix: `PARK_ABS_X_M` 1.5 → 1.8
  (= 1.33 + 0.06 half-width + 0.3 margin). Downstream still fits: worst-case
  backup ≈ 2.4 (< 2.5 cap), escort ≈ 3.04 (< 4.0 cap, < 45 s hold), passer
  parks at ≈ −2.45 (goal −2.5).
  **Verified live (run 8, 08:11–08:17 UTC, gpt-4o):** yield params
  `park_x_m −1.8, backup 1.697, escort = clear 2.466` (yielder at −0.103);
  yielder parked at world (−1.785, +0.361), passer escorted 2.468 m; both
  `COMPLETED` at T+2 m 28 s; both robots reached their goals. A continuous
  `/perception/status` recording (4 022 msgs over the 5.5 min window,
  `dropped_frame` never true) shows **robot_1 missing in 13 of 835 frames
  (1.6 %) while parked, longest gap 0.86 s** — versus minutes-long loss in
  run 6 and a miss at the only sample in run 7. The occlusion defect is
  closed. What remains is detection flicker on *moving* robots: 483/4 022
  frames (12 %) miss one marker, max gap 1.5 s; robot_1's three longest
  gaps (1.30 / 1.02 / 0.90 s) all fall inside the turn-drive-turn sidestep,
  robot_2's 65 gaps (max 0.59 s) all inside its escort. All gaps are under
  `stale_after_sec: 3.0`, so none reached M5 as STALE. One frame reported
  `ids_unexpected: ['robot_41']` (a spurious id-41 detection), handled by
  M1's unexpected-id path. Safety monitor latched both robots at the
  standoff before dispatch and released for the backup, as designed.
- **2026-09-16** — **First live-VLM closed loop on the new VM** (run 6,
  06:27–06:33 UTC, `reasoning_backend_id: openai`, `gpt-4o-2024-08-06`):
  one analysis (`2 robot(s) close/slow >= 12.0s`) → decision
  `type=deadlock, strategy=yield, involved=[robot_1, robot_2]`,
  `parse_status=valid`, 1 attempt, 4.5 s latency, 1 814 tokens (≈ $0.006) →
  dispatch → M4 yield/temporary_wait → `COMPLETED` both at T+2 m 16 s →
  robot_2 reached its goal (odom 4.415 m ≈ run 4's 4.43). Zero backend
  errors. Artifact: `data/logs/m5_decisions/9fa91fded10c41a5ab3d0764077ec8d2.json`
  (on the VM). The model's `<think>` trace is sound: pairwise distance from
  M1 positions (0.12 m), opposing headings (Δθ ≈ π), both STALE → deadlock →
  first-listed robot yields. Findings:
  - **Scenario dynamics are not deterministic across runs.** Run 4 stalled
    at ~1 m (planner failure, single-robot stall trigger); run 6 formed a
    tight nose-to-nose standoff (M1 centres 0.12 m apart, close/slow
    trigger). Both are consistent with the new lidar visibility (see M6
    note); the experiment needs several runs to characterise the onset
    distribution before Arm A/B collection, and the congestion spec should
    admit both signatures or pin one.
  - **The yielder parks in the barrier's camera shadow.** M1 lost robot_1
    (`markers_detected: 0`, `ids_missing: [robot_1, robot_2]`) 1–3 min after
    dispatch in both runs 4 and 6. Geometry: barrier blocks are 0.90 m tall
    (`z_center 0.45, z_half 0.45`, `scenario_builder._author_aisle_barrier`)
    over x ∈ [−1, 1]; the overhead camera is at (0, 0, 3). After backing
    1.3 m and side-stepping +0.35 m the yielder sits near (−1.3, +0.35); the
    camera→marker ray crosses the block's west face at z ≈ 0.92 m (marker
    centre) and lower for the near half — partially occluded at run 6's
    pose, fully occluded (z ≈ 0.64 m) at run 4's (−1.18, 0.27). robot_2 is
    separately lost at its goal (x ≈ −2.93 is 15 px from the ROI edge). Net
    effect: M5 is blind to both robots exactly when it should confirm
    resolution or catch a re-deadlock. Options (undecided): lower the
    barrier (≈ 0.3 m keeps it a lidar wall at z = 0.172 while clearing the
    camera ray); widen the ROI; or park the yielder short of the block end.
  - Pre-flight gotcha: `/ws/.env` had `OPENAI_API_KEY= sk-…` (space after
    `=`), so `source` set the key empty and returned non-zero, which would
    have short-circuited the `set -a && source … && ros2 launch` chain.
    Fixed in place on the VM (untracked file). Worth a startup check in the
    demo script.
  - At analysis time both M1 tracks were already STALE (near-contact
    markers, the known 2026-06 behaviour), so the VLM decided on the last
    good positions. Fine here, but it means the decision input is frozen
    for the duration of any standoff.
- **2026-09-16** — **Full closed loop verified key-less on the new VM** (run 4,
  05:19–05:28 UTC): Isaac → M1 → M5 stall detection → scripted mock decision
  (`VGU_MOCK_DECISION_FILE=config/mock_decisions/head_on_yield.json`) → M3
  grounding → `dispatch` → M4 `command received ... action=yield` (robot_1)
  + `temporary_wait` (robot_2) → backup → pull-off → hold + escort → both
  `COMPLETED` → `resume base mission`. Stage durations (36 s backup, 33 s
  pull-off, 74 s escort) match the grounded 1.3 m / 0.35 m / 2.4 m at
  0.1 m/s and a ~0.35× realtime factor; robot_2 finished at map x≈−2.93
  (goal −3.0). This is the first time M3/M4 dispatch has been driven
  without a live VLM. Caveats, all observed in the same run:
  - **The trigger was not the July standoff.** No `safety stop` fired and
    `/safety/holds` stayed empty; M5 fired on `robots=['robot_2'] reason=1
    robot(s) stalled` after robot_2's planner failed (`Failed to create a
    plan from potential`) at ~1 m separation (odom: robot_1 +1.03 m,
    robot_2 +0.91 m from ±1.5 spawns). Leading hypothesis, unconfirmed: the
    newly added visual meshes make each robot visible to the other's RTX
    lidar, so Nav2 blocks earlier than the 0.45 m safety envelope. If true,
    the experiment's "deadlock" now manifests as a planner stall, not a
    nose-to-nose standoff — revalidate the congestion spec's onset
    assumptions before collecting Arm A/B runs.
  - robot_1 stuck after resume (`Failed to make progress` ×3 from
    1789536382), parked at odom (0.46, 0.34) near the wall — the open
    pull-off Nav2 recovery-loop item from 2026-07-03, reproduced.
  - M1 reported both robots `STALE` from 05:25:45 with byte-identical
    `scene_state` payloads thereafter; robot_2 at x≈−2.93 is at the ±3 m ROI
    edge, but robot_1 at x≈−1.18 was in view, so this looks like frames
    stopping rather than detection failing. Not yet diagnosed.
  - Nav2 ERROR on both robots: `inflation radius (0.070) is smaller than
    the computed inscribed radius (0.080) of your footprint`. Pre-existing
    and deliberate, not a regression: `local_costmap.inflation_radius: 0.07`
    has been set since `05ab38f` (2026-06-28) because Nav2's 0.55 m default
    is wider than the aisle; the 0.14×0.18 m footprint's inscribed radius is
    0.08, so Nav2 logs this on every launch. Safe to ignore.
  - Perception stamps ran ~9 s ahead of M5's clock (wall vs sim time);
    `frame_scene_max_skew_sec` did not block this run but worth knowing.
- **2026-09-16** — Key-less closed loop on the new VM stalls at M2 by design,
  not by fault: with `reasoning_backend_id: mock` M5 detected the standoff
  (`2 robot(s) close/slow >= 12.0s`, later `stalled >= 12.0s`), started an
  analysis every ~15 s and wrote a decision artifact each time, but every one
  ended `no dispatch stage=vlm reason=congestion_detected=false` — the mock's
  hard-coded `_DEFAULT_RESPONSE`. M4 therefore never received a command. The
  ~41k `trigger suppressed ... frame_ready=True` lines are just cooldown/busy
  gaps between those analyses, not a blocker. `build_backend("mock")` had no
  way to script a decision; a `VGU_MOCK_DECISION_FILE` hook was added so the
  loop can be exercised end-to-end without an API key (fixture:
  `config/mock_decisions/head_on_yield.json`). This supersedes the reading of
  the 2026-07-05 entry that only the openai swap remained: M3/M4 dispatch had
  never actually been driven from a mock decision.
- **2026-07-05** — M6→M1→M5→M2 closed loop runs end-to-end on the GCP/Isaac
  host with the mock backend; the only remaining swap for live reasoning is
  `backend_id: openai`, blocked on an API key.
- **2026-06-15** — Offline input-encoding ablation harness spec:
  `docs/superpowers/specs/2026-06-15-m2-input-ablation-design.md`. Rev-8 of
  the congestion spec governs live-loop modality conditions; the 06-15 doc
  remains the spec for the offline benchmark runner and encoder seam.

---

## M4 Execution & Nav2

- **2026-09-17** — **Run H: creep-while-latched fixed and verified;
  resolution and goals on video.** Latch at GT 0.4406 m with a 0.263 m/s
  closing rate; rest 1.0 sim-s later at 0.1693 m. Over the next 100 sim-s
  (1 027 GT records) separation stayed **0.1693–0.1698 m (0.5 mm
  drift)**, both markers detected in 1 909/1 918 frames (99.5 %). One
  `cancel-all … return_code=0 goals_canceling=1` per robot, `cmd_vel
  relay hold engaged` for both, and **zero** `Received a goal, begin
  computing control effort` / `Failed to make progress` for the whole
  run (run G: dozens). Resolution: gpt-4o deadlock/yield (1 765 tokens);
  relay holds released 0.11 s after dispatch (the yielder freed for its
  backup); park achieved (−1.799, 0.371) vs commanded (−1.789, 0.36);
  escort 2.528 vs 2.527 m; both `COMPLETED`; `Goal succeeded` once each
  (robot_2 final −2.450). Recording: `data/logs/recordings/2026-09-17/
  runH_annotated.mp4` (frame numbers in its README). Two observations:
  (1) the robots stop at 0.17 m, not 0.45 — stopping distance at
  0.26 m/s closure, not creep; contact is 0.076 m, so ~9 cm of clearance
  and separated markers; raise `min_distance_m` if more margin is wanted.
  (2) Post-resolution re-trigger again: with both robots parked at their
  goals the stall detector kept firing (`stalled ≥ 12 s`), and after
  seven correct `congestion_detected=false` answers gpt-4o produced one
  spurious yield (analysis #9) that pulled robot_1 from 2.43 back to
  2.15. A robot within goal tolerance is not stalled — detector rule
  fix in progress. Sim ran at 0.349× wall.
- **2026-09-17** — **Fixes for the creep-while-latched defect (below),
  host-unverified.** (1) `99edaca` — the Isaac-side `cmd_vel` relay
  (`isaac/vgu_sim/cmd_vel_watchdog{,_node}.py`) now subscribes
  `/safety/holds` once and returns zero on `cmd_vel_safe` for any listed
  robot before the silence-timeout logic runs; malformed payloads keep the
  previous set (fail-closed); transitions logged once. Cannot stall a
  commanded backup because the safety monitor already removes
  coordinating robots from `held` at the source. Spec: safety-monitor.md
  §8, FR6.4.8 amended. (2) `5f9394a` — `Nav2Adapter.cancel()` sends a
  real cancel-all (`action_msgs/srv/CancelGoal`, zero uuid + zero stamp)
  to `/<robot>/{navigate_to_pose,follow_waypoints}/_action/cancel_goal`,
  cached per (robot, action), logging the server's `return_code` /
  `goals_canceling` or a WARNING — replacing `cancel_goals_async`, which
  does not exist on rclpy's `ActionClient` (verified against the jazzy
  source) and was silenced by a bare `except`. (3) The safety monitor
  turned out not to use `Nav2Adapter` at all: `safety_monitor_node.
  _cancel_nav2_goal` had its own copy of the same dead call and logged
  `nav2 goal cancelled` regardless — being replaced by the shared adapter
  cancel. Host check for all three: after a latch, no `Received a goal,
  begin computing control effort` for either robot, `cancel-all …
  goals_canceling=1`, `cmd_vel relay hold engaged`, and GT
  `min_pairwise_distance_m` ≥ 0.4 m for ≥ 3 min with both markers
  detected.
- **2026-09-17** — **Defect: the safety latch does not hold the robots
  still — they creep into contact while latched.** Seen by the user on
  the run-G video and confirmed frame by frame: at the latch (frame 6878)
  the robots are ~0.45 m apart with both markers detected; 47 s later
  (frame 7400), still latched and before any M5 decision, the two ArUco
  quads fully overlap and M1 shows both as `STALE`. Ground truth in run E
  showed the same: 0.354 → 0.085 m over ~36 sim-s via intermittent
  velocity blips ≤ 0.062 m/s. Every earlier "standoff" (runs 6–8, A, C,
  D) also ended at ~0.08–0.12 m — contact — so this has been the norm,
  masked because contact happened to occur before or during M5's
  decision. Consequence chain: contact ⇒ overlapping markers ⇒ M1 blind
  ⇒ VLM reasons on stale poses and the annotated frame shows a merged
  blob. **Root cause (run G Nav2 logs, both robots):** after the monitor
  logged `nav2 goal cancelled` (t = 494) no new `NavigateToPose` was ever
  received, yet `controller_server` kept executing `follow_path` —
  `Failed to make progress` → `Aborting handle` → `Received a goal, begin
  computing control effort` at t = 553 and again at t = 617 — i.e. the
  original navigation goal's behavior tree was still running and DWB kept
  nudging the robot into the obstacle at creep speed until contact. The
  cancel never happened: `Nav2Adapter.cancel()` cancels goals it did not
  send via `client.cancel_goals_async(goals_to_cancel=None)` inside a bare
  `try/except: pass`, and rclpy's `ActionClient` has no such method — the
  `AttributeError` is swallowed and "cancelled" is logged regardless. So
  the safety monitor has never been able to stop a goal issued by
  `coordination_client`. (The command bus's `cancel()` before a backup
  has the same dead branch, but its handle-based cancel of its own goals
  works, which is why yields still executed.) Publishers on
  `/robot_1/cmd_vel`: `safety_monitor_node` (zero twists),
  `collision_monitor` (relaying the still-running controller — the creep
  source), `command_bus_node` (idle). Two fixes in progress: a **real
  cancel-all** through the action's `CancelGoal` service (zero uuid + zero
  stamp), logged with the response instead of silenced; and an
  **authoritative hold in the Isaac-side `cmd_vel` relay** — any robot in
  `/safety/holds` gets zero on `cmd_vel_safe` regardless of publishers
  (coordination lift is already expressed by removal from `held`). Side
  observation from the same
  logs: in the 60 s before the latch `bt_navigator` received a "goal
  preemption request" every ~1 s — `coordination_client` is re-issuing
  the base goal continuously, restarting DWB each time; worth a look at
  `BaseMissionDriver` acceptance tracking.
- **2026-09-16** — **Run G (recorded): resolution on film under camera
  localization; two runbook fragilities.** `scripts/record_topic_video.py`
  (new; cv2 `mp4v`, one frame per message stamped at a fixed fps,
  segment files so a crash keeps earlier footage) recorded
  `/perception/annotated_frame` (8.6 Hz → 11 fps) and `/camera/image_raw`
  (5.2 Hz, only 1.7 Hz captured under load). Run F was lost to a GCE host
  `REPAIRING` event mid-yield (both MP4s truncated, `moov atom not
  found`); run G delivered: latch 16:34:54 UTC, gpt-4o deadlock/yield
  dispatched 16:36:05, robot_2 `COMPLETED` 16:40:22 and **`Goal
  succeeded` 16:46:04 on film**, robot_1 `Goal succeeded` 59 s after the
  film ends. Videos and logs under `data/logs/recordings/2026-09-16/`
  (gitignored). Two fragilities: (1) `ros2 topic pub --once` for the
  latched `/coordination/tasks` registry can exit before DDS matches M4's
  subscriber — nothing latched and the robots sat at spawn ~7 min; use
  `timeout 15 ros2 topic pub -r 1 …` (run F's `--once` worked by timing
  luck). (2) **Post-resolution re-triggering:** after the yield, M5 fired
  two more analyses while robot_1 crossed the aisle toward its goal and
  gpt-4o answered `deadlock/yield` both times although the robots were
  metres apart; the second yield `FAILED` for robot_1 (it still reached
  its goal). Same pattern as runs C/D. Not a grounding-guard case (one
  robot inside the corridor); it is a detector/VLM false-positive question
  for the Arm A/B evaluation — the VLM reasserting "deadlock" from stale
  context after a resolution is exactly the kind of error the experiment
  should measure, not suppress silently. Both publishers on the recorded
  topics are RELIABLE, not BEST_EFFORT.
- **2026-09-16** — **Run E: deadlock resolved end to end under camera
  localization; both robots reached their goals.** Stack: marker-plane
  calibration, `localization:=camera` + scenario map, geometry-derived
  yield (margin 0.4), STALE fail-safe, yield-refusal guard, fixed GT
  oracle; one live gpt-4o decision. Sequence: safety latch
  `min_distance_violation` at GT 0.443 m with both markers detected
  (before contact) → M5 `2 robot(s) close/slow` → gpt-4o deadlock/yield
  (1 835 tokens, 6.2 s) → grounded `park −1.789, backup 0.971,
  pull_off 0.36, escort = clear 1.724` → achieved park −1.804/−1.811,
  pull-off 0.368, escort 1.729 m → both `COMPLETED` → base missions
  resumed → **robot_1 at +2.419, robot_2 at −2.490, Nav2 `Goal
  succeeded` twice each, separation 4.9 m, `conflict_active false`**.
  Eleven follow-up analyses all `congestion_detected=false`. Camera
  localization vs GT during the maneuver **10.1 / 7.9 mm mean** (max 33 /
  59 mm); whole span 14.6 / 21.9 mm mean. Zero errors in M1/M4/M5.
  Observations: (1) the STALE fail-safe never fired — the min-distance
  rule alone held the latch through a 430 s marker blackout because it
  evaluates carried STALE poses (~0.14 m); why run D lost its latch is
  therefore still unexplained, and the fail-safe remains as a second
  line. (2) While latched, small `cmd_vel` blips (≤ 0.062 m/s) let the
  pair creep from 0.354 m to 0.085 m (contact) over ~36 sim-s; source
  undiagnosed — `/robot_1/cmd_vel` has four publishers (safety monitor,
  collision monitor, docking server, watchdog). (3) **Bring-up race:**
  robot_1's `global_costmap` timed out (~1.5 s) waiting for `map → odom`
  because the camera localizer publishes only after its first fix; the
  lifecycle manager aborted and Nav2 was activated by hand. Fix: seed
  the localizer with the spawn pose at startup (AMCL's `initial_pose`
  semantics) — **landed** the same day: `CameraLocalizer(initial_map_to_odom=…)`
  + node params `set_initial_pose` / `initial_pose.{x,y,yaw}` wired from
  the launch `x/y/yaw` args; valid because odometry is spawn-relative
  (identity at t = 0), so the spawn pose in map *is* `map → odom` at
  startup. The first real fix replaces the seed (logged once with
  `replaced_seed=true`); a STALE hold before any fix keeps it. Host-
  unverified. (4) M1 both-marker rate 85.7 % over the M5
  window, 83.8 % during the parked hold (per-robot split lost to a
  recorder truncation). (5) The yield-refusal guard was not exercised.
- **2026-09-16** — **Safety monitor STALE fail-safe.** `safety.py`
  `evaluate_latches` now unions a second rule onto the min-distance rule:
  a `STALE` robot keeps any latch it had, and a pair in which either
  robot is `STALE` is latched if its last *both-fresh* distance was below
  `stale_unsafe_distance_m` (default `min_distance_m + 0.15` = 0.60;
  `safety.yaml` keys `stale_pose_is_unsafe: true`,
  `stale_unsafe_distance_m: 0.6`, loaded with `.get` so an old installed
  yaml cannot throw). The distance memory is refreshed only from
  both-fresh pairs, so a carried stale pose never launders into the
  trusted datum; the existing coordination lift (a commanded backup may
  proceed) is honoured. Reason logged once per latch
  (`reason=stale_pose_unsafe`); `/safety/holds` payload unchanged.
  **Why:** run D — overlapping markers made both robots `STALE`, and the
  monitor treated them as absent while they were interpenetrating. Spec:
  `docs/specs/module4/safety-monitor.md` §7 (rev 5), which also records
  two residual blind windows: a wedged `ACTIVE` command (bounded by the
  command bus's 20 s nav2-leg watchdog) and the empty-`robots[]`
  dropped-frame path (re-latches on the next good frame). 35 safety
  tests pass. Host-unverified.
- **2026-09-16** — **Run D: camera localization verified; robots found
  interpenetrating; safety monitor blind under marker loss.** With
  `localization:=camera` (+ marker-plane calibration): M1 vs GT at spawn
  **0.96 cm / 0.41 cm** (was 12 cm); both `camera_localizer` nodes
  acquired within 1 cm of the spawn poses; Nav2 active and navigating from
  the camera TF; localization error vs GT **0.4 / 1.8 cm mean** while
  driving (N=62), **2.9 / 0.6 cm mean** during the yield (N=223), worst
  16 cm in a 509 s span that included a period of physical contact. No
  degeneracy — the held correction stays valid because odometry is
  drift-free. **Loop outcome was poor for reasons upstream of
  localization:** gpt-4o's first decision was `reverse` (both back up
  1.3 m, both resume); the robots re-approached and came to rest
  **nose-to-nose in contact (0.078 m centre distance), pressed against
  the south wall (y ≈ −0.18)**, anti-aligned (relative heading 3.145
  rad) — a live camera crop shows the two ArUco quads overlapping
  (`scratchpad/runD_live_zoom.png` of this session). With overlapping
  quads neither marker is detectable: `markers_detected == 0` in 13 449
  of 19 607 status frames, robot_1 gap 401 s, both `STALE`, so M5
  reasoned on stale poses (`temporary_wait`/anomaly, then two `yield`s;
  one FAILED), Nav2 planning failed from inside inflated wall cost
  (44 + 13 `failed to create plan`), no goal reached.
  **Collision is enforced — an earlier reading of this as
  interpenetration was wrong.** Host probe (same day): driving robot_1
  into an uncommanded robot_2 at 0.1 and 0.2 m/s pushed robot_2 by 0.57 m
  and 1.55 m, and the centre distance plateaued at 0.0760 / 0.0765 m —
  exactly nose-to-nose for this URDF (`base_link` at the wheel axle,
  chassis collision box origin x −0.032 with half-length 0.07 ⇒ front at
  +0.038 ⇒ 2 × 0.038 = 0.076 m). All five collider prims per robot have
  `collisionEnabled`, no `CollisionGroup`/`FilteredPairs` exist, no
  tunnelling at the speed limit. `min_pairwise_distance_m` is a
  centre-to-centre metric; `robot_robot_contacts` in the acceptance log is
  hard-coded `[]` (never measured — do not read it as "no contact").
  **The actual systemic findings:** (1) the 0.12 m markers are centred on
  `base_link`, 0.038 m behind the nose, so **at physical contact the two
  quads necessarily overlap and M1 loses both robots at exactly the
  physical deadlock**; the designed 0.45 m safety envelope normally stops
  robots before that, and run D reached contact only because `reverse`
  resumed both base missions into each other. Options, undecided: a
  smaller or rear-offset marker (M1 would need the offset), or accept
  the blind window and rely on the fail-safe. (2) **The safety monitor
  had no fail-safe for perception loss** — a `STALE` robot last seen 8 cm
  from another was treated as absent; fixed the same day (see the STALE
  fail-safe entry). The yield-refusal guard correctly did not fire
  (robots were inside the corridor). 4 gpt-4o calls, 7 097 tokens.
- **2026-09-16** — **`localization:=camera` added, host-unverified**
  (`4c1b697`). Third localization mode: a per-robot
  `swarm_perception/camera_localizer_node` (launched inside the namespaced
  Nav2 group; no static TF, no AMCL) turns M1's world pose into
  `map → <robot>/odom` = T_map_base ∘ T_odom_base⁻¹, where T_odom_base is
  the LATEST `odom → base_footprint` TF from Isaac (never looked up at the
  scene stamp: Isaac fills the image header with system time while TF and
  nodes run sim time; latency error ≤ 0.2 m/s × 0.1 s = 2 cm). Publishes
  at 20 Hz stamped +0.3 s (AMCL's convention) and holds the last value
  while the marker is `STALE` — valid because odometry is drift-free.
  Pure SE(2) core in `camera_localizer.py` (yaw normalised via atan2 so a
  π-heading robot does not flip sign each cycle); node importable without
  rclpy; 15 unit tests. **Why:** AMCL degenerates in this symmetric
  warehouse after the yield maneuver (run C), while the apparatus already
  has a global sensor whose pose error is 3–7 cm (now ≤ 3 cm with the
  marker-plane calibration). Prerequisite: M1 must be up before Nav2
  activates. Verification = run D.
- **2026-09-16** — **AMCL localizes to 2 cm with the scenario map (run B2);
  degenerates after the yield maneuver (run C).** With
  `localization:=amcl map_yaml:=…warehouse_map_head_on_deadlock.yaml`,
  stamp-matched error vs ground truth over the approach and standoff was
  **mean 0.022 m, max 0.052 / 0.085 m** (robot_1 N=29, robot_2 N=33;
  time alignment solved via odom↔GT with 0.3 mm residual) — on par with
  M1 (0.03–0.07 m). Nav2 planned and drove from the AMCL pose. First run
  in the project with self-localized robots. **Run C** (full loop under
  AMCL, gpt-4o): deadlock/yield, `park_coord_m −1.789`, yielder held at
  GT (−1.75, 0.37), M1 missed it in 10/790 frames (longest 0.35 s) — the
  0.4 m park margin is confirmed. But as each robot moved west of the
  barrier, its AMCL estimate jumped ~2 m in y within ~5 s (robot_1 to
  y≈−1.76 at t 426→431, robot_2 to y≈+2.15 at t 458→465) while x stayed
  right; C-window error mean 1.6 / 1.3 m. Both reported poses lie in
  **solid rack** in the map (49/49 occupied cells around them), so this is
  a degenerate filter output (split/bimodal cloud), not a relocalization
  to a look-alike place — no parallel aisle exists (at x = −2 the only free
  band is y ∈ [−0.6, 0.6]). Timing coincides with the side-step turns and
  the unmapped other robot at < 1 m. Consequences: `GridBased … failed to
  plan`, `Goal failed`, neither robot reached its goal, and M5 re-triggered
  a second analysis (2 live calls total) whose yield was nonsensical —
  both robots were now on the same side, so "park on the yielder's own
  side" flipped to `+1.789` with backup/escort at their clamps (2.5 / 4.0).
  Open items: (1) AMCL post-maneuver degeneracy — diagnose with
  `/robot_N/particle_cloud` at the jump; candidate levers `z_rand`,
  `laser_likelihood_max_dist`, `resample_interval`, `recovery_alpha_*`;
  (2) grounder guard for a re-triggered yield when no robot is inside the
  corridor extent. **Default remains `localization:=static`.**
- **2026-09-16** — **Per-scenario Nav2 map with the barrier** (`1d53053`).
  `isaac/scripts/generate_warehouse_map.py --scenario <yaml>` now
  rasterizes `aisle_barrier` with the same geometry as
  `scenario_builder._author_aisle_barrier` (blocks over x ∈ center ±
  length/2, |y| ∈ [effective/2, nominal_aisle/2]) into
  `maps/warehouse_map_<scenario>.pgm/.yaml`; the default map is untouched
  (byte-identical re-generation checked). `warehouse_map_head_on_deadlock`
  adds exactly 480 occupied cells (240 per block, purely additive; aisle
  core still free). Cell rounding puts the map corridor walls at |y| = 0.30
  vs the physical 0.275, i.e. a 0.60 m map corridor — the global planner
  gets ±0.11 m instead of ±0.085 m and now sees the barrier at plan time
  rather than only via lidar. `nav2_robot.launch.py` gains `map_yaml`
  (default: the base map) feeding the shared `map_server`;
  `run_phase3_demo.sh` passes the head_on map. **Why:** AMCL cannot
  localize against a map missing the dominant lidar feature (run B).
  Verification against AMCL pending (run B2).
- **2026-09-16** — **AMCL option executed on host (run B): mechanism
  verified, localization fails because the map lacks the barrier.**
  With `localization:=amcl` both `/robot_N/amcl` reached `active`, the
  static `map_to_odom_ground_truth` was correctly absent, AMCL published
  `map → robot_N/odom` equal to the spawn poses, params bound under the
  namespace (`base_frame_id robot_1/base_footprint`, `scan_topic
  /robot_1/scan`), Nav2 navigated from the AMCL pose, and there were
  **zero** TF/map/scan warnings — the launch/params design holds. But
  once the robots moved, stamp-matched error vs the (now correct)
  ground truth settled at 0.77–1.10 m for robot_2 (five samples, mean
  0.93) and 1.40 m for robot_1 (one sample), against M1's 0.03–0.07 m;
  robot_2's lateral error alone (~0.6 m) would place it inside the aisle
  wall. Cause found offline: `warehouse_map.pgm` was generated from
  `WarehouseConfig` on 2026-06-25 (`494cbba`), before the `aisle_barrier`
  existed; it has **0 occupied cells** in x∈[−1,1], y∈[0.275,0.6] where the
  0.90 m block is, so AMCL fits scans of 0.55 m corridor walls to a map
  that says the aisle is 1.2 m wide. Fix in progress: per-scenario map
  (`generate_warehouse_map.py --scenario`) rasterizing the barrier, and a
  `map_yaml` launch argument. Measurement gotcha for future checks:
  `/robot_N/amcl_pose` is RELIABLE + TRANSIENT_LOCAL and only updates on
  ≥ `update_min_d` motion, so `topic echo --once` returns a possibly
  minutes-old pose; compare by `header.stamp`, not sample time.
- **2026-09-16** — **`localization:=amcl` option added, host-unverified.**
  `nav2_robot.launch.py` now takes `localization:=static|amcl` (default
  `static`, behaviour unchanged). Under `amcl`, the static
  `map_to_odom_ground_truth` node is not launched; instead a namespaced
  `nav2_amcl` node (params via the same `RewrittenYaml(root_key=robot_id)`
  wrapper the vendored navigation launch uses; initial pose from the
  `x/y/yaw` args; no node-level `/tf` remaps, per the launch docstring's
  findings) plus a `lifecycle_manager_localization` managing only `amcl`.
  `nav2_params.yaml` gains an `amcl:` block: Jazzy nav2_bringup defaults
  except namespace-token frames, absolute `scan_topic`/`map_topic`
  literals (same failure class as `global_costmap.map_topic`),
  `laser_{min,max}_range` = LDS 0.12/3.5, `update_min_d/a` tightened to
  0.05 m / 0.1 rad so a short backup still triggers filter updates.
  nav2_bringup's `localization_launch.py` is deliberately not used (it
  hardcodes its own `map_server`, colliding with the shared one).
  **Why:** the static transform is a ground-truth shortcut (disclosed in
  the experiment spec, App. A.7); AMCL leaves `/odom` untouched, so M4's
  odometry-closed primitives are unaffected by this step alone. Plan,
  risks (symmetric-corridor particle flip; `xy_goal_tolerance 0.1` margin;
  M1/map alignment unverified) and the odometry-noise follow-up:
  `docs/superpowers/plans/2026-09-16-amcl-localization-plan.md`. Host
  checks still to run are listed in `docs/specs/module4/phase2-nav2-stack.md`
  (2026-09-16 section).
- **2026-09-16** — Goal coordinates verified end-to-end on the rebuilt stack:
  with `nav2_robot.launch.py` given the scenario spawns (`x:=-1.5` /
  `x:=1.5 yaw:=3.14159265`), Nav2 logged `Begin navigating from current
  location (-1.50, -0.00) to (3.00, 0.00)` for robot_1 and `(1.50, 0.00) →
  (-3.00, 0.00)` for robot_2 — map-frame pose equals the YAML spawn, goal
  equals `orchestrator.yaml`'s `initial_tasks`. Both robots then drove into
  the aisle (M1 placed robot_1 at x≈0.00; `/robot_1/odom` on a fresh run
  showed 0.8 m forward travel), met head-on, and the safety monitor latched
  `min_distance_violation` on both — the intended standoff. Two caveats:
  (1) `scripts/run_phase3_demo.sh` still hardcodes `x:=-0.6 / 0.6` (stale
  since commit `0a0604c` moved spawns to ±1.5), which would misplace
  `map→odom` by 0.9 m — do not use it unpatched. (2) `safety_monitor_node`
  emitted 58 `safety stop ... min_distance_violation` WARN lines in 0.48 s
  at latch time (alternating robots) — noisy but not yet shown to be harmful.
- **2026-07-03** — Deadlock fix "H3" branch merged and verified (runs 8–13):
  separation and single-cycle resolution fixed; motion BVH requires the
  triple kit-arg. Open item at merge time: Nav2 pull-off recovery loop
  (superseded in design by the rev-8 derived-candidate retreat).
- **2026-07-02/03** — Backup-not-moving fix (commit `05ab38f`): robots stayed
  stationary despite backup COMPLETED because of a cancel-all race plus
  `collision_monitor` `stop_pub_timeout: 2.0` both zeroing `cmd_vel`.
  Odometry-based `backup()` then verified end-to-end on a fresh natural
  deadlock: 0.8 m backup + hold + yield complete.
- **2026-06-28** — Nav2 stall (M4 Phase 2 Task 8) resolved in `09778fa`:
  scan-namespace remap + DWB goal-tolerance fixes; clean rebuild reproduced
  goal reach at 0.0964 m.
- **2026-06-25** — Nav2 Jazzy parameter typing: integer parameters supplied
  as floats crash `bt_navigator` silently (`default_server_timeout: 60`
  works, `60.0` dies). Applies to all Nav2 YAML in
  `ros2_ws/src/swarm_simulation`.
- **2026-06-24** — M4 Phase 2 runs Nav2 in a `ros:jazzy` container with the
  Isaac side overridden to `ROS_DISTRO=jazzy`; transport/TF/map remap bugs
  from the pivot are confirmed fixed. See `docs/specs/module4/`.
- **2026-06-21** — Drive-chain fixed-base bug: the URDF importer's `fix_base`
  welded `base_link` to the world; freeing the chassis requires disabling
  the generated `base_joint`. Verified and landed (M4 Phase 1; report:
  `docs/reports/2026-06-21-m4-phase1-completion.md`).

---

## M6 Simulation / Isaac Sim

- **2026-09-26** — **`_bshort` open-side passer goal widened from ±2.5 to
  ±2.6** (`dcfa144`). At ±2.5 the goal cleared the M3 escort endpoint
  (`park_offset_m` 1.789 + `passer_clearance_m` 0.65 = 2.439 m) by only
  0.061 m, under the ≈0.1 m drift `FEASIBILITY_MARGIN_M` budgets for; ±2.6
  clears it by 0.161 m (0.811 m past the park point). Blocked-side goal,
  spawns, blockers, oracle and maps unchanged; `beyond` and `_gshort`
  untouched. Constant `BLOCKED_SHORT_PASSER_GOAL_M` in
  `isaac/scripts/generate_head_on_family.py`; both `_bshort` YAML headers now
  print the margins, and a test asserts ≥ 0.15 m on both sides.
  **Operator step:** for `_bshort`, hand-set `orchestrator.yaml`
  `initial_tasks` to `[2.6, 0.0]` (west) / `[-2.6, 0.0]` (east); only the
  comment table there was updated, the live block is unchanged. **USD not rebuilt** — rebuild both `_bshort` scenario USDs on the
  VM before the next run (a stale USD keeps the old goal).

- **2026-09-26** — **`_bshort` (blocked-side goal short) fixes the west
  park-beyond-goal failure with no reintroduced blocker-path loss.** Commit
  `e708ffa`. Three-run ER-2 pilot, west variant: 3/3 position-verified
  arrivals (J1–J3), gate fired once per run, 0 refusals. Ground truth shows
  the passer's backtrack after its max x was 0.000 m in all three (versus
  0.580 m in `_gshort` H2) — the passer's goal now clears the M3 escort
  endpoint by only 0.050–0.061 m, a thin margin against ≈0.1 m drift. East
  variant built and validated, not yet run. Report
  `docs/reports/2026-09-25-overnight-findings.md` §AG–§AH; extends the
  `_gshort` pilot entry below. Margin superseded by 2026-09-26
  entry (goal widened to ±2.6).

- **2026-09-26** — **`_gshort` fixes the blocker-on-goal-path losses but
  symmetric ±1.5 goals park the yielder beyond the passer's goal.** Six-run
  ER-2 pilot at `c2d8491`: 4/6 position-verified against 2/6 on ±2.5, 0/6
  blocker-path losses. New failure: the yielder parks at `park_offset_m` =
  1.789 m, beyond the passer's goal at 1.5 m, so the arrived passer rests on
  the axis 0.437 m away — inside M4's 0.45 m — and holds it (H2, H3). East is
  3/3 and west 1/3, but that split is a race, not side-safety — the variants
  mirror. `_bshort` is the candidate fix. Container recipe now needs `pillow`;
  verify installs by `md5`, not `colcon` exit code. Report
  `docs/reports/2026-09-25-overnight-findings.md` §AD–§AF; extends the
  `_gshort` creation entry below.

- **2026-09-26** — **`_gshort` head-on variants put the blocker off every goal
  path**: `head_on_asymmetric_{w0p2_eopen,wopen_e0p2}_gshort_o0` goal on the
  opposing spawn (±1.5), not the inherited ±2.5 that lay beyond the box.
  Goal mode is a `--goal-mode` generator option, **not** a
  `HeadOnAsymmetricParams` field — a params field would rewrite the frozen v1
  `parameters:` blocks. **Operator step: set `orchestrator.yaml`
  `initial_tasks` to ±1.5 and rebuild `swarm_orchestrator`** — M5 reads goals
  from there, not the scenario YAML. Design rev 4, spec
  `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md`.

- **2026-09-25** — **New Isaac host stood up after the `summer-flux`
  project lost GPU quota.** Instance `vgu-vgu-thule-base-isaac-workstation-vm`,
  GCP project `project-355a9186-f6f8-4b89-a44`, zone `us-central1-c`
  (us-central1-a stocked out), g2-standard-8 + L4 (driver 595.84), deployed
  with Isaac Automator `--not-from-image --isaacsim v6.0.1`
  (`--from-image` needs a project-scoped image family and `--isaacsim
  latest` resolves to git `main` = 7.0.0a1 — pinned to v6.0.1, closest to
  the validated 6.0.0-rc.59). Isaac Sim source build at
  `/home/ubuntu/IsaacSim-source`, symlink `/home/ubuntu/IsaacSim`.
  `vgu_ros` container rebuilt from the 2026-09-16 recipe plus `pip3
  install --break-system-packages requests` (stock `ros:jazzy` lacks it;
  `reasoning/vlm/openai_backend.py` needs it). Full asset chain rebuilt:
  URDF import with the four ROBOTIS STLs staged next to the URDF (4
  visual meshes, `burger_base` 48 040 pts — the 2026-09-16 mesh-less
  import does not recur), `warehouse_base.usd`, all six scenario USDs,
  `validate_simulation` PASS on `head_on_deadlock` and the three
  `head_on_asymmetric` variants; headless `run_simulation` `completed:
  true`, 3 001 ground-truth records over 300 sim-s, render product `rgb
  (960,1280,4) mean=127.94` (old host 127.95). Two host facts: `pxr`
  imports only inside a `SimulationApp` (a bare `python.sh -c "from pxr
  import Usd"` fails), and each new extension set's first launch spends
  ≈5–7 min compiling shaders.
- **2026-09-25** — **`run_simulation.py --duration-sec` is a dead flag.**
  It is parsed and validated but never passed into `ResolvedRunConfig`
  (`isaac/vgu_sim/config.py` has no `duration_sec` field; the
  `ResolvedRunConfig(...)` call in `isaac/scripts/run_simulation.py`
  omits it), so the scenario YAML's `runtime.duration_sec`/`duration_sec`
  (300 s for `head_on_deadlock`) always governs. This is the root cause
  of the long-standing "`--duration-sec` does not stop Isaac" note
  (2026-09-17, M5/M2 entries above) — the flag was never wired, not
  ignored at shutdown. Not fixed (experiment night); fix = add the field
  and pass `args.duration_sec` through, with a unit test.
- **2026-09-19** — **`head_on_asymmetric` scenario family landed and
  hardware-verified.** `ScenarioConfig` gains `family` (inferred from legacy
  names, explicit for generated ones), `static_obstacles`/`ObstacleSize`, and
  `parameters`/`oracle` (`df047ae`). A pure `isaac/vgu_sim/family_oracle.py`
  computes yield feasibility from the same `reasoning.rag.scene_geometry`
  functions M3 grounds with, loaded from M5's `scenario_geometry` block
  (`2382aae`). `isaac/scripts/generate_head_on_family.py` writes the three
  committed v1 variant yamls plus `family_manifest.csv`
  (`isaac/config/scenarios/family/`) (`b6b6843`). Static and timed obstacles
  are now authored as real `UsdGeom.Cube` collision geometry
  (`_author_box`/`_author_static_obstacles`,
  `/World/Scenario/StaticObstacles/<id>`) instead of empty Xforms, dispatch
  keys on `family` not `name`, and `validate_scenario_obstacles` fails the
  build (not a later run) on a missing prim (`34686a5`). Per-scenario Nav2
  maps bake the `static_obstacles` footprint in addition to the aisle
  barrier (`539de1b`, `0583195`). Spec:
  `docs/specs/module6_simulation.md` Rev 4; design:
  `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md`
  (rev 2/3). Hardware evidence
  (`docs/reports/2026-09-18-head-on-family-validity.md`, "Validity Pairs
  (T2a)"): all four forced-yielder mock runs matched the frozen oracle —
  forced-infeasible yield `FAILED` with the robot stalled ~0.09 m (its own
  half-width) from the blocker's near face on both variants; forced-feasible
  yield `COMPLETED` with both robots arriving, mirrored east/west. The frozen
  `oracle:` block is consumed only by config validation
  (uniqueness/membership checks) — nothing in the M1–M5 runtime pipeline
  reads `correct_yielder`, so it cannot silently become part of a live Arm A
  score.
- **2026-09-16** — Simulation rebuilt and re-verified on a new host after the
  old VM was deleted: `vgu-canary-base-isaac-workstation-vm` (project
  `summer-flux-501516-n6`, us-central1-a, g2-standard-8 + L4, Isaac Sim
  6.0.0-rc.59 source build at `/home/ubuntu/IsaacSim`). Full asset chain
  rebuilt from a clean checkout — URDF import → `warehouse_base.usd` →
  `head_on_deadlock.usd` → `validate_simulation` **PASS** → headless run
  `completed: true, failure: null`, 451 ground-truth records over 45 sim-s,
  camera render product live (`rgb (960,1280,4) mean=127.95`). Isaac's bundled
  Jazzy `rclpy` loads inside Kit, so no host ROS 2 is needed for a sim-only
  run. Three facts worth keeping:
  - **Robot visual meshes were never in the repo.** The committed URDF
    references `meshes/{burger_base,left_tire,right_tire,lds}.stl`, which do
    not exist, so a plain import of it yields collision primitives only.
    Supplying the four ROBOTIS STLs next to the URDF imports 4 visual meshes
    (burger_base 48 040 pts). **Confirmed** as the cause of the bodyless robots
    in `data/logs/recordings/h3_final_demo_v13.mp4`: a fresh overhead render on
    this host (mean 127.93, matching the run's render product) shows chassis,
    both wheels, and a cast shadow where the July frame had only a floating
    marker quad. The meshes currently exist **only on the VM**, not in git, so
    a rebuild from `git archive HEAD` on a fresh host reproduces the mesh-less
    import. Note the marker renders offset from the body centroid — expected,
    not a perception bias: `aruco_marker_joint` is at `base_link` with no x/y
    offset, while the `base_link` visual mesh carries a `-0.032 m` origin and
    `base_link` itself sits at the wheel axis. M1's marker-derived pose is
    therefore in the same frame as odom and ground truth.
  - **Nothing validates visual geometry.** `validate_robot_asset` checks the
    articulation root, wheel `DriveAPI`, and disabled `base_joint`;
    `validation.py` checks metadata, namespace, camera frustum, marker mesh,
    and unresolved references. A mesh-less import passes every gate.
  - **Imported meshes are instanced**, so `Usd.Stage.Traverse()` reports zero
    `UsdGeom.Mesh` prims. Use `Traverse(Usd.TraverseInstanceProxies())` when
    checking an imported robot asset, or the geometry looks absent when it is
    not.
  - The `turtlebot3_burger_1/` import collision (2026-06-18 report, item 3) is
    avoidable without a post-hoc merge: move the committed URDF+meshes to a
    staging dir, free `isaac/assets/robots/turtlebot3_burger/`, then import —
    the importer writes the un-suffixed path `paths.robot_asset_path()` expects.
- **2026-09-16** — **Ground-truth oracle fixed for position; time axis
  still wrong.** `acceptance_logging.sample_robot_positions` now reads the
  chassis prim (`/World/Robots/<id>/Geometry/base_footprint/base_link`,
  the single `ArticulationRootAPI` prim; `base_link` name as fallback) via
  `ComputeLocalToWorldTransform(Usd.TimeCode.Default())`, resolved once
  per robot and cached by *path* so a stage reload cannot return a dead
  prim. Host probe compared four sources on the same step: root Xform
  frozen at spawn; chassis USD world pose = `RigidPrim.get_world_poses()`
  exactly; a raw Fabric attribute read returned only the local translate
  (rejected). Verified on the VM with both robots driven at 0.1 m/s:
  `x` now changes (robot_1 −1.5 → −0.049, robot_2 +1.5 → +0.021 at the
  deadlock), `speed_mps` non-zero while moving, `conflict_active` true for
  the first time, and the logged positions match spawn+odom to four
  decimals for both robots (opposite signs). That verification run then
  completed on its own (`run_manifest.json` `completed: true, failure:
  null`, 2 261 records); its final record has both robots parked
  nose-to-nose at the corridor centre — robot_1 (−0.057, −0.028),
  robot_2 (0.022, −0.019), `min_pairwise_distance_m 0.079`,
  `conflict_active: true` — the first acceptance log in the project to
  register a head-on conflict. Pre-fix file preserved on the VM as
  `ground_truth.jsonl.prefix_buggy_*`. Supersedes the "not a motion
  oracle" entry below for *positions*.
  **Still open — time axis:** `runner.py` advances `sim_time` by one
  `physics_dt` per `app.update()`, but at `rendering_hz 30` /
  `physics_hz 60` each update steps physics twice, so the counter runs at
  ~½ true sim time (GT 25.4 s vs `/clock` 48 s). Consequences: every
  velocity in `ground_truth.jsonl` is inflated ~1.9× (0.181 logged vs
  ~0.116 true), and a declared `duration_sec` runs ~1.9× longer in real
  sim time. **Fixed in code, host-unverified:** the loop now sets
  `sim_time = sim_ctx.current_time − loop_start_time`, anchored at
  recording start because `event_scheduler` `spawn_at_sec` and
  `duration_sec` are authored relative to it (a raw clock would include
  the topic-wait startup time). The step-count sampling gate was removed
  (it would have halved the log rate to 5 Hz); `AcceptanceLogger`'s own
  10 Hz throttle governs. **Verified on host (run A):** GT `sim_time_sec`
  vs `/clock` slope 1.008 over 127 s (0.992 over a shorter pair); robot_2's
  logged `speed_mps` during the 0.1 m/s escort max 0.092 / mean 0.089,
  independently matching 2.480 m over 27.2 sim-s = 0.091 m/s (the
  escort's lateral servo costs ~10 %); GT vs odom position agreement
  0.4 mm. `ground_truth.jsonl` is now usable as the experiment's metric
  source for position, distance, speed and `conflict_active`.
- **2026-09-16** — **Robots are now mutually visible to RTX lidar; they were
  not before the mesh fix.** Probe (fresh sim, no Nav2, robots parked at
  ±1.5 facing each other, 3.0 m apart): each robot's forward ±10° sector
  returns 1.6–2.3 m (the 0.55 m corridor wall, at exactly the ranges
  `0.275/sin(bearing)` predicts) and then a cluster at **2.99–3.12 m** —
  matching the other robot's front plate edge (~2.99), LDS body (~3.06)
  and rear structure (~3.1) from the observer's lidar origin. Nothing else
  in the scene lies 3 m straight ahead (far wall > 3.5 m `range_max`).
  Caveat: the probe kept bearings only for sector minima, so "at 0°" is
  inferred from geometry, not measured. Why this is new: the scan plane is
  z = 0.172 m; before the STLs the only render geometry on a robot was the
  marker quad at z = 0.21 m (see `lidar.exclude_from_rtx_lidar` docstring,
  2026-06-25), and collision prims are not rendered — so July's robots had
  no lidar cross-section at all, which is why motion-BVH work was needed to
  get *anything* into the costmap. **Consequence:** Nav2 now sees the
  oncoming robot from 3 m. In run 4 the planner blocked at ~1 m separation
  and no standoff formed; in run 6 (same config) a tight nose-to-nose
  standoff did form. So the 0.45 m standoff the July H3 runs and the
  congestion spec assume is now one of at least two onset modes, not the
  only one. The spec's onset window and the safety-monitor's role need
  revalidating over several runs before Arm A/B data collection.
  Options, not yet decided: accept planner-stall as the deadlock signature;
  or exclude robot meshes from the lidar (Isaac RTX-visibility / semantic
  filtering) to restore the July geometry while keeping the camera view.
- **2026-09-16** — OpenAI key verified on the VM for `gpt-4o`
  (`/v1/models/gpt-4o` 200; 2-token chat completion answered from
  `gpt-4o-2024-08-06`). Stored only in `/home/ubuntu/vgu-vlm-swarm/.env`
  (`chmod 600`), sourced inside the container via `set -a && source
  /ws/.env && set +a` immediately before launching M5 — never on a command
  line.
- **2026-09-16** — **`ground_truth.jsonl` does not track robot motion.**
  `acceptance_logging.sample_robot_positions` reads
  `UsdGeom.Xformable(/World/Robots/<id>).ComputeLocalToWorldTransform(0.0)` —
  the USD transform of the robot *root* prim, which physics never updates
  (Newton moves the articulation in Fabric; see the 2026-06-21 Fabric entry).
  Evidence from one run: the file reported `x=-1.5, speed=0.0` for both
  robots for 300 sim-s while Nav2 logged navigation from that spawn, M1 saw
  robot_1 at x≈0.00, and `/robot_1/odom` showed ~0.8 m of travel. So
  `conflict_active`, `min_pairwise_distance_m`, and `speed_mps` in the
  acceptance log are all constant-at-spawn and must not be used as a motion
  oracle until this is fixed (read the chassis/`base_link` prim through
  Fabric/usdrt, or reuse the odom bridge). `/robot_N/odom` is the honest
  arbiter in the meantime. Unclear whether the July H3 runs relied on this
  file; their conclusions were drawn from M1 and odom, per the M4 notes.
- **2026-09-16** — `vgu_ros` container rebuilt from scratch and verified
  against host Isaac. The container was never defined in the repo (only
  `.devcontainer/Dockerfile`, which is a *different* base —
  `osrf/ros:jazzy-desktop`), so it died with the old VM. Recipe that works,
  from plain `ros:jazzy` (the image every Nav2 param finding in
  `docs/specs/module4/phase2-nav2-stack.md` was validated against — do not
  swap the base without revalidating those):
  ```
  docker run -d --name vgu_ros --network host --ipc=host \
    -v /home/ubuntu/vgu-vlm-swarm:/ws -w /ws ros:jazzy sleep infinity
  apt-get install -y --no-install-recommends ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup python3-colcon-common-extensions python3-opencv \
    python3-jsonschema python3-pip
  pip3 install --break-system-packages "pydantic>=2.7"
  colcon build --symlink-install --merge-install   # in /ws/ros2_ws
  ```
  Verified: 5 swarm packages registered, `swarm_interfaces` msgs import,
  `/clock` delivering at ~12 Hz **inside** the container (data, not just
  discovery — the 2026-06-19 root cause), `/robot_1/odom` and `/tf` echoing,
  and `controller_server`/`planner_server`/`bt_navigator` all lifecycle
  `active` with `/robot_1/navigate_to_pose` live. Notes:
  - `--network host --ipc=host` plus `FASTRTPS_DEFAULT_PROFILES_FILE=
    /ws/config/dds/fastdds.xml` on **both** sides remains mandatory.
  - Stock `ros:jazzy` has numpy and yaml but **no** cv2, pydantic, or
    jsonschema, and zero nav2 packages.
  - apt `python3-opencv` is 4.6.0, which exposes `DetectorParameters` but
    **not** `ArucoDetector`. That is fine and deliberate: `detection.py`
    version-gates on `ArucoDetector` and takes the legacy
    `DetectorParameters_create()` path. Do **not** pip-install
    `opencv-contrib-python` on top — mixing the two is what the 4.6.0 segfault
    comment in `detection.py` warns about.
  - apt `jsonschema` is 4.10.3, below `requirements.txt`'s `>=4.22`. The only
    API used (`Draft202012Validator`) exists in 4.10, so it was left alone —
    revisit if schema validation misbehaves.
  - Without Isaac running, `local_costmap` blocks on
    `robot_1/base_link -> robot_1/odom` and Nav2 never activates. That is
    expected, not a container fault: the frame comes from Isaac. Nav2 activates
    on its own once the sim publishes TF.
- **2026-07-04** — Aisle-width congestion gap closed: 0.55 m × 2.0 m
  `aisle_barrier` corridor built and verified in
  `isaac/config/scenarios/head_on_deadlock.yaml`.
- **2026-07-01** — Scenario YAML edits are inert until `build_scenario`
  regenerates the USD; a stale USD cost ~10 debugging runs. Always rebuild
  after editing anything under `isaac/config/scenarios/`.
- **2026-06-30** — Host-launched Isaac needs
  `FASTRTPS_DEFAULT_PROFILES_FILE` forcing UDP transport; otherwise
  shared-memory transport silently drops all data to the Nav2 container and
  the system looks hung.
- **2026-06-21** — Fabric/USD sync for Newton articulations: enable
  `enable_fabric_usd_notice_handler` and write world positions to Fabric
  after each step; `omni.physx.fabric` does **not** work for Newton
  articulations (report:
  `docs/reports/2026-06-21-m6-fabric-sync-investigation.md`).
- **2026-06-18** — The Isaac Sim machine is Windows: guides and commands for
  that host use PowerShell and `python.bat` (see `docs/guides/`).
