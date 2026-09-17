# Failure-Attribution Ladder — Five Live Runs of the Closed Loop

**Prepared:** 2026-09-17

**Revision history:**

- Initial draft: runs 1–5 on the GCP Isaac Sim host, root cause of the mid-scenario re-approach, and what each fix isolates.

---

## Headline

Across five live runs of the same scenario (`head_on_deadlock`, seed 42,
gpt-4o) on the same stack, almost everything that first looked like "VLM
behaviour" — repeated interventions, robots driven back into the aisle,
strategy oscillation — was attributable to specific layers of the pipeline
around the model: the stall detector, a heading heuristic in the prompt,
sampling temperature, and a missing grounding guard. Fixing those one layer at
a time took the loop from 11 dispatches and a self-inflicted re-deadlock
(run 3) to one dispatch and silence after both robots parked (run 5), with
the VLM's own decisions changing in the expected direction at each rung.

The method matters more than the numbers: a VLM controller cannot be
evaluated until the layers feeding it are shown to be innocent, and the
recorded runs below are the evidence that they were not. This report is the
basis for the ablation ladder to be pre-registered before Arm A/B data
collection (rev-8 design, `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`).

---

## Setup (constant across runs)

- Host: GCP `vgu-canary-base-isaac-workstation-vm` (g2-standard-8, L4), Isaac
  Sim 6.0 source build, headless, `--seed 42`, ~0.35× real time.
- Stack: M1 perception (camera-based `map→odom` localisation), Nav2 per robot
  with the scenario map, M4 execution (command bus, safety monitor,
  coordination client), M5 orchestrator, M2 via the `openai` backend (gpt-4o).
- Scenario: two robots spawn at x = ∓1.5 with goals at x = ±2.5 and meet in a
  0.7 m gap between two barrier blocks (corridor half-length 1.0 m).
- Recording (runs 3–5): `scripts/record_topic_video.py` on
  `/perception/annotated_frame`, re-timed with ffmpeg to the achieved capture
  rate (≈ 3.5–4 fps under load although the topic runs at 7–9.5 Hz).
- Every run: 13 min of M5 uptime; M5 log, M4 log, Nav2 logs, decision
  artifacts, and ground truth kept under `data/logs/fc_check_20260917/` on the
  VM host (`run<N>_*`); videos under `data/logs/recordings/2026-09-17/`
  (git-ignored).

---

## The ladder

| Run | UTC | Change under test | Analyses | Dispatches | `none` | Outcome |
|---|---|---|---|---|---|---|
| 1 | 07:03–07:24 | failure-context block (rev 8.1/8.2), T = 0.6 | 16 | 15 | 2 | yield → reverse → … alternation; robots 6.5 m apart still "deadlocked" |
| 2 | 08:20–09:32 | + explicit `none` option, executed-maneuver detail (rev 8.3) | 91 | 23 | 58 | oscillation reduced, not removed; both robots at goals at the end |
| 3 | 09:46–09:59 | same as 2, recorded | 12 | 11 | 2 | correct first yield, then a false `deadlock/reverse` re-created the standoff |
| 4 | 10:33–10:47 | + fix B: pairwise geometry in prompt, facing-based head-on, T = 0.0 | 32 | 1 | 31 | one yield, no re-approach; detector still firing on parked robots |
| 5 | 11:02–11:15 | + fix A (arrival signal) + fix C (reverse guard) | 5 | 1 | 4 | one yield; no analyses after both arrivals |

Counts are from the M5 log (`starting analysis`, `dispatch request=`,
`congestion_detected=false`); run 1's dispatch count includes degraded
commands.

---

## Root cause of the re-approach (run 3, fully instrumented)

Ground truth: the first resolution is correct — robot_1 yields, robot_2 passes
and reaches its goal at sim t ≈ 90 s (0.04 m from −2.5; Nav2 `Goal succeeded`
09:50:11). At sim t ≈ 105 s (09:50:56) M5 dispatches `reverse` to both robots;
robot_2 backs east from its goal into the aisle mouth and robot_1 backs west;
at t = 120–155 s they are 0.39 m apart — a new, self-inflicted conflict. Every
later command swaps them around; robot_1 ends 7.8 m from its goal.

Three layers contributed, each with its own evidence:

1. **Detector (M5).** From 09:50:17 `2 robot(s) stalled` fired every cooldown.
   robot_1's stall was Nav2 fighting the gap (4 progress-failure/recovery
   events in its log 09:48–09:51); robot_2's was spurious — parked at its goal,
   but M1's camera estimate sat outside the 0.15 m `goal_reached_tolerance_m`
   (the exact value could not be proven at the time: `scene_state` was not
   logged; that gap is closed by the measurement plumbing added afterwards).
2. **Prompt + sampling (M2).** On an unchanged scene the model answered `none`
   at 09:50:17 and 09:50:37 and `deadlock/reverse` at 09:50:56 ("Both robots
   are stopped and facing opposite directions"). The frame shows robot_2 at the
   far left heading west and robot_1 1.1 m away heading east — diverging. The
   prompt's heuristic "`|θ1 − θ2| ≈ π` ⇒ head-on" cannot distinguish facing
   each other from facing away, the deadlock definition never required the
   0.5 m proximity stated elsewhere, and temperature 0.6 (the Cosmos Reason 2
   preset applied to gpt-4o) made the third answer a coin flip. The
   previous-attempt block was not the cause: the two `none` answers carried the
   same block.
3. **Grounding (M3/M4).** `reverse` had no guard; the yield branch already
   refused when both robots were past the corridor on one side, reverse did
   not. M4 executed it (09:51:00–09:52:01 in its log).

---

## What each fix isolates

| Fix | Layer | Change | Effect observed |
|---|---|---|---|
| rev 8.3 | prompt (memory) | closing advice names `congestion_detected=false`; detail names the executed maneuver | `none` rate 12 % → 64 % (runs 1 → 2); oscillation persists on real re-stalls |
| B | prompt + decoding | pairwise distance and mutual facing stated per pair; head-on = facing + ≤ 0.5 m; gpt-4o at T = 0.0 (per-backend override) | run 4: the re-analysis that flipped in run 3 answers `none` three times; 1 dispatch; no re-approach |
| A | detector + M4 | M4 reports `base_mission COMPLETED`; M5 excuses the robot within 0.5 m of that goal; distances logged | run 5: zero analyses after both arrivals (run 4: ~25); the 4 remaining analyses are a real Nav2 slowdown, all `none` |
| C | grounding | reverse refused when both robots are past the corridor on one side (mirrors the yield refusal) | not exercised in run 5 — no false deadlock left to refuse; safety net |

Fix B was tested alone first (run 4) and A + C together afterwards (run 5), so
B's effect is isolated; A and C are separable in the logs (A shows as the
`arrived at base goal` lines and the missing triggers; C would show as
`requested_strategy: reverse` in an artifact, which never occurred).

---

## Threats to validity

- One scenario, one seed, one run per rung: the standoff onset is known to vary
  run to run (runs 4 and 6 in June formed different standoffs), so the counts
  are illustrative, not estimates. The pre-registered matrix (N = 30 paired
  seeds per cell) is the instrument for claims.
- Runs 1–2 were not recorded and used a slightly different prompt (before the
  executed-maneuver detail); their counts come from the M5 log only.
- Fix B adds a classical geometry summary to the VLM's input, which weakens
  RQ1 as originally posed; it is therefore a switchable modality
  (`prompt_pairwise_geometry`) and an ablation axis (rev 8.5), not a fixed
  part of Arm A.
- The recorder's capture rate lags the topic under load; playback was re-timed
  from the recorder's reported achieved rate, so video time is accurate to
  ~1 s, not frame-exact.

---

## Evidence index

- Ground truth per run: `data/logs/simulation/head_on_deadlock-seed42-rep000/ground_truth.jsonl` (overwritten per run; run 3's is summarised in `docs/implementation_notes.md`, M2/M5 section, 2026-09-17).
- M5/M4/M1/Nav2/Isaac logs, raw video segments, artifact summaries:
  `data/logs/fc_check_20260917/run{1..5}_*` on the VM host.
- Videos and event timelines: `data/logs/recordings/2026-09-17/run{3,4,5}_failure_context_annotated.mp4` + `README_run*`.
- Decision artifacts: `data/logs/m5_decisions/<request_id>.json` (from run 6 on, also carrying `run_id`, `session_id`, the rendered prompt with hashes, the scene snapshot, and detector distances).
- Code: branch `feat/failure-context-closed-loop` — fix B `c8d5956`, `21c5562`; fix C `51e0db9`; fix A `d914417`; measurement plumbing `2f7a93f`; geometry modality switch `cc9e83f`.
