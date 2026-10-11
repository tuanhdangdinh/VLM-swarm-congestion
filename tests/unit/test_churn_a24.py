"""prereg-v3 A24(iii): the productive-credit predicate fix and the attribution verdict.

(a) PRODUCTIVE credit: progress by any robot of the dispatched cluster within
    the window, INCLUDING an arrival enabled by the cleared path. E11
    (s1b_E11_seed11_er2_b1): r5's clearing reverse (c417cbff, cluster
    {r1, r5}) also broke the r4+r5 latch at 112.5 sim-s, and r4 reached S at
    112.9. The old predicate credited that arrival to neither event.
(b) ARCHITECTURE-CHURN needs BOTH the >= 3-dispatch opportunity bar AND
    >= 1 alternation, so "k of n opportunity episodes" can never read k > n
    (E11 printed "1 of 0").

Fixture `data/churn_a24/resolution_inputs.json` holds the exact inputs
`analyse_churn` passes to `score_resolution_events` for E11, E3, A1 and E6.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import s1_churn_stats as churn  # noqa: E402

FIXTURE = json.loads((Path(__file__).parent / "data/churn_a24/resolution_inputs.json").read_text())


def _events(label: str) -> list[dict]:
    case = FIXTURE[label]
    clearing = [
        {**c, "identity": tuple(c["identity"]), "cluster": frozenset(c["cluster"])}
        for c in case["clearing"]
    ]
    progress = [(t, rid) for t, rid in case["progress"]]
    return churn.score_resolution_events(clearing, case["breaks"], progress, case["end_sim"])


def _by_request(label: str) -> dict[str, dict]:
    return {e["request"]: e for e in _events(label)}


def _counts(label: str) -> tuple[int, int]:
    events = _events(label)
    productive = sum(e["productive"] for e in events)
    return productive, len(events) - productive


# ---- (a) the E11 flip ----


def test_e11_clearing_reverse_is_productive_through_the_enabled_arrival():
    event = _by_request("e11")["c417cbff"]
    assert event["productive"] is True
    assert event["progress"] == [
        "robot_4@112.9", "robot_4@117.9", "robot_4@154.3", "robot_4@159.3"
    ]
    assert event["credited_robots"] == ["robot_1", "robot_4", "robot_5"]


def test_e11_first_yield_stays_unproductive_when_its_window_closes_first():
    # The r1+r5 reverse at 107.3 intersects {r4, r5}; r4 had not progressed by then.
    event = _by_request("e11")["7a47f2f7"]
    assert event["productive"] is False
    assert event["progress"] == []


def test_e11_leaves_intermittent():
    assert _counts("e11") == (1, 1)
    assert churn.classify_churn(*_counts("e11")) == "resolved"


# ---- (a) anchors that must not move ----


def test_e3_livelock_stays_intermittent():
    assert _counts("e3") == (0, 9)
    assert churn.classify_churn(*_counts("e3")) == "intermittent"


def test_a1_stays_resolved():
    assert _counts("a1") == (1, 0)


def test_e6_counts_unchanged():
    assert _counts("e6") == (2, 1)


@pytest.mark.parametrize("label", ["e11", "e3", "a1", "e6"])
def test_progress_is_never_credited_to_two_events(label):
    credited = [p for e in _events(label) for p in e["progress"]]
    assert len(credited) == len(set(credited))


# ---- (a) the enabled-robot rule on synthetic inputs ----


def _synthetic(progress: list[tuple[float, str]], *, second: bool = False):
    clearing = [
        {"request": "d1", "sim_t": 10.0, "identity": ("robot_1:reverse",),
         "cluster": frozenset({"robot_1", "robot_2"}), "active_end": 30.0},
    ]
    breaks = [
        {"pair": "robot_1+robot_2", "break_sim_t": 12.0, "dispatch": "d1"},
        {"pair": "robot_2+robot_3", "break_sim_t": 20.0, "dispatch": "d1"},
    ]
    if second:
        clearing.append(
            {"request": "d2", "sim_t": 40.0, "identity": ("robot_4:reverse",),
             "cluster": frozenset({"robot_3", "robot_4"}), "active_end": 60.0}
        )
        breaks.append({"pair": "robot_3+robot_4", "break_sim_t": 41.0, "dispatch": "d2"})
    return churn.score_resolution_events(clearing, breaks, progress, 600.0)


def test_enabled_robot_is_credited_after_its_own_break():
    (event,) = _synthetic([(21.0, "robot_3")])
    assert event["productive"] is True
    assert event["credited_robots"] == ["robot_1", "robot_2", "robot_3"]


def test_enabled_robot_is_not_credited_before_its_own_break():
    (event,) = _synthetic([(15.0, "robot_3")])
    assert event["productive"] is False


def test_robot_outside_every_attributed_break_is_not_credited():
    (event,) = _synthetic([(21.0, "robot_5")])
    assert event["productive"] is False


def test_doubly_covered_progress_goes_to_the_most_recent_release():
    # robot_3's arrival at 45.0: d1's window (no cluster-intersecting dispatch
    # follows it) covers robot_3 from its 20.0 break, and d2's cluster covers
    # robot_3 from d2's 41.0 break. The most recent release gets the credit.
    first, second = _synthetic([(45.0, "robot_3")], second=True)
    assert (first["productive"], second["productive"]) == (False, True)


def test_singly_covered_progress_stays_with_the_earlier_event():
    first, second = _synthetic([(25.0, "robot_3")], second=True)
    assert (first["productive"], second["productive"]) == (True, False)


# ---- (b) the attribution verdict ----


def _churn(cls: str, max_clearing: int, max_alt: int) -> dict:
    return {
        "churn_class": cls,
        "max_clearing_dispatches_one_cluster": max_clearing,
        "max_alternations_one_cluster": max_alt,
    }


@pytest.mark.parametrize(
    ("churn_row", "expected"),
    [
        (_churn("intermittent", 9, 6), churn.ARCH),  # E3: 9 into one cluster, 6 A-B-A
        (_churn("intermittent", 2, 0), churn.INDETERMINATE),  # E11 under the old predicate
        (_churn("clogged", 12, 0), churn.APPARATUS),  # A3-like identical run
        (_churn("intermittent", 3, 1), churn.ARCH),
        (_churn("resolved", 3, 1), churn.APPARATUS),  # one alternation, not churning
        (_churn("resolved", 3, 2), churn.ARCH),
        (_churn("clogged", 2, 2), churn.INDETERMINATE),  # no opportunity
        (_churn(None, 0, 0), churn.INDETERMINATE),
    ],
)
def test_attribution_verdict(churn_row, expected):
    assert churn.attribution_verdict(churn_row) == expected


def test_arch_requires_opportunity_and_alternation_on_a_grid():
    for cls in ("intermittent", "resolved", "clogged"):
        for max_clearing in range(6):
            for max_alt in range(4):
                verdict = churn.attribution_verdict(_churn(cls, max_clearing, max_alt))
                if verdict == churn.ARCH:
                    assert max_clearing >= churn.OPPORTUNITY_MIN_DISPATCHES
                    assert max_alt >= 1


def test_pooled_verdict_cannot_read_more_arch_than_opportunity():
    rows = [_churn("intermittent", 2, 0), _churn("clogged", 1, 0)]
    pooled = churn.pooled_attribution(rows)
    assert pooled["verdict"] == "INDETERMINATE"
    assert (pooled["architecture_churn"], pooled["opportunity"]) == (0, 0)
    assert "1 of 0" not in pooled["text"]


def test_pooled_verdict_livelock_counts_k_of_opportunity():
    rows = [_churn("intermittent", 9, 6), _churn("resolved", 3, 0), _churn("clogged", 1, 0)]
    pooled = churn.pooled_attribution(rows)
    assert pooled["verdict"] == "LIVELOCK UNDER A REAL MODEL"
    assert (pooled["architecture_churn"], pooled["opportunity"]) == (1, 2)


def test_pooled_verdict_no_livelock_with_opportunity_and_no_arch():
    pooled = churn.pooled_attribution([_churn("resolved", 3, 0)])
    assert pooled["verdict"] == "NO LIVELOCK UNDER THE REAL MODEL"
