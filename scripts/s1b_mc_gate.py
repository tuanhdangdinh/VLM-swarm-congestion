"""S1b Monte Carlo gate: thresholds derived from S1a data, then evaluated.

prereg-v3 R3.6a item 4: the S1b gate thresholds are derived from S1a's own
Monte Carlo and its live episodes plus the statistical requirement of at
least one congestion event per episode, with the SAME conflict definition
as S1a's MC (scripts/s1_mc.py: centre gap < 0.45 m, both freeze). Every
threshold below is computed from a stated input; none is a free number.
PROPOSED for Step 6.

Live S1a inputs (scripts/s1_live_conflict_stats.py on the gitignored
bundles; times relative to robot_1's release, GT clock):
  E1 (seed 1, sim stagger 4.0): first encounter 17.94 sim-s
  E2 (seed 2, sim stagger 4.0): first encounter 18.74 sim-s
  pilot ep1 used a wall-clock stagger (Delta 4.4-6.9) and is reported, not
  used for the lag factor.

Usage:
    python scripts/s1b_mc_gate.py [--n 400]

Prints one JSON object (inputs, thresholds, S1a and S1b MC rows, verdict).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import s1_mc as M  # noqa: E402
import s1b_layout as L  # noqa: E402

# --- registered / measured inputs -----------------------------------------
H_SIM_S = 600.0  # S1 horizon (scene design S1 "Runs")
STOP_WINDOW_SIM_S = 300.0  # pin stop window, updated per A14's 277 s self-free
R_PER_ARM = 20  # confirmatory n per arm (scene design S1)
PILOT_EPISODES = 2  # S1b echo pilot size (this program)
S1A_MC_FIRST_MEDIAN_S = 15.0  # S1a registered MC row (scene design S1, row D)
S1A_MC_JUNCTION_SHARE = 309 / 400
S1A_LIVE_FIRST_S = {"E1": 17.94, "E2": 18.74}
DELTA_S1A = 4.0
DELTA_S1B = 3.0


def thresholds() -> dict:
    """Each gate threshold with its derivation."""
    # G1: >= 1 congestion event per episode. With R = 20 episodes per arm,
    # P(>=1 event) >= 1 - 1/(2R) keeps the expected number of event-free
    # episodes in a cell <= 0.5.
    p_event = 1.0 - 1.0 / (2 * R_PER_ARM)
    # G2: MC -> live lag from S1a (live first encounter / MC median), max
    # over the two sim-stagger episodes. A first conflict must form early
    # enough that a pin it causes can still be observed for the full stop
    # window before H: k * p90 <= H - W_stop.
    k = max(v / S1A_MC_FIRST_MEDIAN_S for v in S1A_LIVE_FIRST_S.values())
    p90_max = (H_SIM_S - STOP_WINDOW_SIM_S) / k
    # G4: Delta artifacts (an arriver meeting a not-yet-released occupant)
    # are a release-schedule defect, not congestion; S1a's MC had 0/400. The
    # tolerance is G1's: <= 1/(2R) of first conflicts.
    artifact_max = 1.0 / (2 * R_PER_ARM)
    # G5a: the pilot must be able to show a resolution: P(first conflict
    # resolvable by one yield) = q with 1 - (1 - q)^2 >= 0.95 over the
    # 2-episode pilot -> q >= 1 - sqrt(0.05).
    q_min = 1.0 - math.sqrt(0.05)
    return {
        "G1_p_event_min": p_event,
        "G2_lag_factor_k": k,
        "G2_p90_first_max_s": p90_max,
        "G3_window_share_max": "S1a's own share under the same router (computed)",
        "G4_artifact_max": artifact_max,
        "G5a_first_resolvable_min": q_min,
        "G5b_multi_contact_max": "S1a's own rate under the same router (computed)",
    }


def mc_row(floor, routes, delta, finished, n, reroute=False) -> dict:
    seeds = M.mc_seeds(n)
    frozen = [
        M.run_episode(
            floor, routes, s, delta=delta, finished=finished, freeze=True, reroute=reroute
        )
        for s in seeds
    ]
    free = [
        M.run_episode(floor, routes, s, delta=delta, finished=finished, freeze=False) for s in seeds
    ]
    return {"freeze": M.summarise(frozen), "free_flow": M.flow_summary(free)}


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    args = ap.parse_args()
    th = thresholds()
    s1a = M.s1a_floor()
    s1b = L.s1b_floor()
    ra_grid = M.build_routes(s1a, "grid")
    ra_nom = M.build_routes(s1a, "nominal")
    rb = M.build_routes(s1b, "grid")
    rows = {
        "s1a_nominal_wander_d4 (published-row reproduction)": mc_row(
            s1a, ra_nom, DELTA_S1A, "wander", args.n
        ),
        "s1a_grid_park_d4": mc_row(s1a, ra_grid, DELTA_S1A, "park", args.n),
        "s1a_grid_park_d4_reroute": mc_row(s1a, ra_grid, DELTA_S1A, "park", args.n, reroute=True),
        "s1b_grid_park_d3": mc_row(s1b, rb, DELTA_S1B, "park", args.n),
        "s1b_grid_park_d3_reroute": mc_row(s1b, rb, DELTA_S1B, "park", args.n, reroute=True),
        "s1b_grid_wander_d3": mc_row(s1b, rb, DELTA_S1B, "wander", args.n),
        "s1b_grid_park_d4 (S1a's Delta on S1b)": mc_row(s1b, rb, DELTA_S1A, "park", args.n),
    }
    a = rows["s1a_grid_park_d4"]
    b = rows["s1b_grid_park_d3"]
    fa, fb = a["freeze"], b["freeze"]
    n = fb["episodes"]
    gates = {
        "G1 P(>=1 encounter)": (fb["with_encounter"] / n, ">=", th["G1_p_event_min"]),
        "G2 first-encounter p90 (s)": (fb["first_t_p90"], "<=", th["G2_p90_first_max_s"]),
        "G3 max 1.2 m-window share of first conflicts": (
            fb["max_window_share"],
            "<",
            fa["max_window_share"],
        ),
        "G4 Delta-artifact share of first conflicts": (
            fb["first_delta_artifact"] / n,
            "<=",
            th["G4_artifact_max"],
        ),
        "G5a first conflict resolvable by one yield": (
            fb["first_resolvable"] / fb["with_encounter"],
            ">=",
            th["G5a_first_resolvable_min"],
        ),
        "G5b >=3-robot contact onsets / episode (pass-through)": (
            b["free_flow"]["multi_contact_events_per_episode"],
            "<",
            a["free_flow"]["multi_contact_events_per_episode"],
        ),
    }

    def ok(v, op, t) -> bool:
        return {">=": v >= t, "<=": v <= t, "<": v < t}[op]

    verdict = {
        k: {"value": v, "op": op, "threshold": t, "pass": ok(v, op, t)}
        for k, (v, op, t) in gates.items()
    }
    print(
        json.dumps(
            {
                "n": args.n,
                "thresholds": th,
                "rows": rows,
                "gates": verdict,
                "gate_pass": all(g["pass"] for g in verdict.values()),
                "registered_s1a_junction_share": S1A_MC_JUNCTION_SHARE,
            },
            indent=1,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
