# Narrow-Gap Traverse Fix — Implementation Plan

**Date:** 2026-07-04
**Spec:** `docs/superpowers/specs/2026-07-04-narrow-gap-traverse-design.md`
**Branch:** main (two config-value changes; no code, no schema changes)

## Problem Statement

The yield protocol works end-to-end, but the passing robot cannot DWB-traverse
the 0.55 m `aisle_barrier` gap from the angled pose the standoff leaves it in:
the inflated walls leave a ±0.085 m band for the robot center, every
trajectory sample collides, and `SimpleProgressChecker` aborts into recovery
loops until the hold backstop expires (H3 runs 4–5). Fix: widen the gap to
0.70 m AND soften the local costmap/progress checker, applied together per
the approved spec.

## Global Constraints

- Exact values from the spec: gap `0.70`, local `inflation_radius: 0.07`,
  `movement_time_allowance: 20.0`. Global costmap inflation stays `0.10`.
- Comments must carry the geometry math (spec §Decision) — these files'
  existing comments are load-bearing documentation and must stay consistent
  with the new values (the 0.55/0.085 m narrative appears in BOTH files).
- Nothing else changes: DWB sampling, footprint, safety config, goal
  tolerances untouched.
- Conventional Commits, subject < 72 chars, no body, no trailer.
- Offline tests: `python3 -m pytest tests/unit/test_scenario_builder.py
  tests/unit/test_m6_config.py -q` must not regress (test_m6_config has one
  pre-existing env failure; the scenario yaml values themselves are not
  pinned by unit tests — verify by grepping tests for `0.55` before claiming
  so).

## Task 1 — Scenario gap 0.70 (offline)

**File:** `isaac/config/scenarios/head_on_deadlock.yaml`

1. `aisle_barrier.effective_width_m: 0.55 → 0.70`.
2. Rewrite the comment block above it: 0.70 m gap, robot inflated
   half-width 0.16 m (0.09 + local inflation 0.07) → ±0.19 m center band,
   single-robot navigable including angled-pose recovery; two-abreast needs
   ≥ 0.45 m center separation (safety latch) > 0.38 m usable band → head-on
   entry still deadlocks.
3. Grep the repo for other references to the 0.55 m value tied to this
   scenario (docs/specs/module4 phase3 doc, memory of prior greps:
   `docs/specs/module6_simulation.md` may cite it) — update only statements
   of fact about this scenario's current width, not historical narratives.

Commit: `fix: widen head-on aisle gap to 0.70m for angled-pose recovery`

## Task 2 — Nav2 local softening (offline)

**File:** `ros2_ws/src/swarm_simulation/config/nav2_params.yaml`

1. **Local** costmap `inflation_layer.inflation_radius: 0.10 → 0.07`; update
   its comment (currently derives 0.55-gap math) to the new numbers and the
   local-vs-global rationale (global stays 0.10 for centered planning).
2. Under `progress_checker:` add explicit `movement_time_allowance: 20.0`
   with a comment: sim-seconds (controller on use_sim_time); doubled from
   the 10.0 default so DWB can escape an awkward pose before recovery
   aborts discard progress (H3 runs 4–5).
3. Verify the global costmap section still carries 0.10 (it inherits from a
   separate block — confirm by reading, do not assume).

Commit: `fix: soften local inflation and progress checker for gap transit`

## Task 3 — Host verification (controller-run)

1. Sync both files to the VM (`/home/ubuntu/vgu-vlm-swarm/...`); nav2 params
   need no rebuild (read at launch); scenario yaml read by Isaac at start.
2. Launch `run_phase3_demo.sh --rec-sec 300`; wait for self-completion.
3. Analyze M4/M5 logs against spec §Verification: single dispatch cycle;
   yield terminal well before the ~112 s-wall backstop; robot_2 released at
   hold start; both robots reach goals; no regression on separation.
4. Download video, extract frames, visually confirm transit + goal runs;
   save as `data/logs/recordings/h3_final_demo_v6.mp4` locally.
5. On success: update memory (`project_deadlock_fix_h3_status.md`) and
   report against all five H3 criteria. On failure: diagnose from
   nav2_r2/M4 logs + frames, report honestly, stop.
