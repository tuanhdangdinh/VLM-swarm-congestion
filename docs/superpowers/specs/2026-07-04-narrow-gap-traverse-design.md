# Narrow-Gap Traverse Fix — Design

**Date:** 2026-07-04
**Status:** Approved (user, 2026-07-04)
**Problem source:** H3 verification runs 4–5 of the deadlock-resolution branch.

## Problem

The yield protocol now executes perfectly (backup 1.3 m → sidestep 0.35 m →
hold with event-driven release), but the passing robot cannot physically
traverse the 0.55 m `aisle_barrier` gap. After the standoff it sits angled
(~30°) inside the gap where the inflated walls leave a ±0.085 m band for the
robot center; every DWB trajectory sample collides, the controller outputs
zero velocity, and `SimpleProgressChecker` aborts into recovery loops until
the hold backstop expires. Verified twice with different yielder geometry
(runs 4 and 5); safety latching ruled out (zero robot_2 latches during the
hold window).

Root causes, in order of leverage:
1. **Gap margin:** 0.55 m gap − 2×(0.09 m half-width + 0.10 m inflation)
   = 0.17 m total band. Too tight for sampling-based recovery from an
   angled pose.
2. **Abort cadence:** default `movement_time_allowance` (10 sim-s) fires
   before DWB can work out of a near-wedged pose, discarding progress into
   spin/backup recoveries that also fail in the tight band.

## Decision

Apply both mitigations together (user choice: fastest path to a working
end-to-end demo; each fix covers the other's weak spot).

### Change 1 — scenario gap (Option B)

`isaac/config/scenarios/head_on_deadlock.yaml`:
`aisle_barrier.effective_width_m: 0.55 → 0.70`.

Deadlock semantics preserved: passing two-abreast needs ≥ 0.45 m
center-to-center (safety latch threshold) while the 0.70 m gap offers only
0.70 − 2×0.16 = 0.38 m of usable band, so simultaneous entry still
deadlocks. Update the yaml comment with this math. No regeneration step:
`scenario_builder._author_aisle_barrier` reads the yaml at sim start.

### Change 2 — Nav2 softening (Option A)

`ros2_ws/src/swarm_simulation/config/nav2_params.yaml`:

- **local** costmap `inflation_layer.inflation_radius: 0.10 → 0.07`.
  Inflated half-width 0.19 → 0.16 m; combined with Change 1 the free band
  for the robot center grows ±0.085 → ±0.19 m (4.5×). Keeps a 2 cm buffer
  above the 0.05 m costmap resolution (0.05 would risk single-cell
  tangency). Global costmap keeps 0.10 — planning conservatism there costs
  nothing and keeps global paths centered.
- `progress_checker.movement_time_allowance: 20.0` (explicit; default was
  implicit 10.0). Sim-seconds (controller runs `use_sim_time`). Doubles the
  window DWB has to escape an awkward pose before aborting to recovery.

### Explicitly not changed (YAGNI)

DWB sampling counts, robot footprint, safety config (`min_distance_m`,
holds), global costmap inflation, goal tolerances.

## Verification

Rerun the autonomous phase-3 demo on the GCP host (existing
`run_phase3_demo.sh`, 300 s recording). Success = exactly the criteria that
failed in run 5:

1. Passer transits the gap during the hold — yield terminal arrives well
   before the ~112 s-wall backstop (detail "yield complete: passer
   cleared").
2. Single analysis/dispatch cycle (no re-deadlock).
3. Both robots reach their goals (video + M4 log evidence).
4. Unchanged from run 5 (must not regress): separation maintained, wait
   released at hold start, demo self-completes.

Unit-test impact: none of the changed values are pinned by unit tests
(scenario yaml and nav2 params are host-side configs); the scenario-config
validator only requires `effective_width_m > 0`.

## Files touched

- `isaac/config/scenarios/head_on_deadlock.yaml`
- `ros2_ws/src/swarm_simulation/config/nav2_params.yaml`
