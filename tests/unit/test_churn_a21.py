"""prereg-v3 A21: churn measurement, the default-off bound, and two apparatus minors.

(a) MEASURE: `swarm_orchestrator.churn` (dispatch identity, latch cluster,
    alternation) and `scripts/s1_churn_stats.classify_churn`, the predicate
    derived from S1b pilot 2's E3 (livelock: 9 unproductive resolutions) vs
    S1a A1 (one yield, then task progress).
(b) BOUND, DEFAULT-OFF: `ChurnBoundConfig` (values unset; enabled without
    them is rejected) and M5's per-cluster clearing-dispatch budget and
    alternation check. Off, the node is byte-identical.
Minors: the echo names ONE cluster (the closest pair), and the ambiguous-lane
refusal names the 45 deg heading-lane cap when the cap is what refused
(S1b pilot 2, E4 analysis 0b1a0d8d).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError
from swarm_orchestrator.churn import (
    ChurnLedger,
    alternation_count,
    dispatch_identity,
    identity_repeats,
    latch_cluster,
    longest_identical_run,
)
from swarm_orchestrator.models import (
    ChurnBoundConfig,
    PipelineOutcome,
    TerminalStage,
    load_config,
)

from reasoning.vlm.models import CongestionDecision
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _make_node,
    _result,
    node_env,
)
from tests.unit.test_m5_reanalysis_suppression import BASE, COOLDOWN, _feed
from tests.unit.test_s1b_rulings_a20 import _ground, _refusal

REPO = Path(__file__).resolve().parents[2]
ORCH = REPO / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
SCENES = json.loads((Path(__file__).parent / "data/churn_a21/scenes.json").read_text())


def _yield(yielder: str, passer: str, *, order: list[str] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"passer_robot_id": passer, "backup_distance_m": 1.3}
    if order is not None:
        params = {"crossing_order": order, "backup_distance_m": 1.3}
    return {
        "command_id": f"cmd-{yielder}",
        "actions": [
            {"robot_id": yielder, "action": "yield", "parameters": params},
            {"robot_id": passer, "action": "temporary_wait", "parameters": {}},
            {"robot_id": "robot_1", "action": "temporary_wait", "parameters": {}},
        ],
    }


# E3's dispatch sequence (s1b_E3_seed3_echo_a2): r3->r2 at box N, then the
# period-2 alternation r2->r5 (lane x) / r3->r5 (box N) to the horizon.
E3 = [("robot_3", "robot_2")] + [("robot_2", "robot_5"), ("robot_3", "robot_5")] * 4


# ---- (a) identity, cluster, alternation ----


def test_yield_identity_is_yielder_and_first_passer():
    assert dispatch_identity(_yield("robot_2", "robot_5")) == ("yield", "robot_2", "robot_5")


def test_yield_identity_falls_back_to_the_crossing_order():
    command = _yield("robot_3", "robot_5", order=["robot_5", "robot_1", "robot_4"])
    assert dispatch_identity(command) == ("yield", "robot_3", "robot_5")


def test_all_wait_command_is_not_a_clearing_dispatch():
    command = {"actions": [{"robot_id": "robot_1", "action": "temporary_wait"}]}
    assert dispatch_identity(command) is None
    assert dispatch_identity(None) is None


def test_non_yield_identity_lists_the_acting_robots():
    command = {
        "actions": [
            {"robot_id": "robot_2", "action": "reroute"},
            {"robot_id": "robot_1", "action": "reroute"},
            {"robot_id": "robot_3", "action": "temporary_wait"},
        ]
    }
    assert dispatch_identity(command) == ("robot_1:reroute", "robot_2:reroute")


def test_latch_cluster_grows_by_the_latch_graph():
    positions = {"robot_2": (0.0, 1.2), "robot_5": (0.35, 1.2), "robot_3": (0.65, 1.3),
                 "robot_1": (-1.8, 0.0)}
    cluster = latch_cluster(("yield", "robot_2", "robot_5"), positions)
    assert cluster == frozenset({"robot_2", "robot_5", "robot_3"})


def test_e3_sequence_alternates_but_never_repeats_identically():
    identities = [("yield", y, p) for y, p in E3]
    assert longest_identical_run(identities) == 1
    assert identity_repeats(identities, 1) == 0
    assert alternation_count(identities) == 6
    assert identity_repeats(identities, 2) == 6


def test_identical_run_is_not_alternation():
    identities = [("robot_1:reroute",)] * 12
    assert longest_identical_run(identities) == 12
    assert alternation_count(identities) == 0


# ---- (a) the churn class predicate ----


def _scorer():
    sys.path.insert(0, str(REPO / "scripts"))
    import s1_churn_stats

    return s1_churn_stats


@pytest.mark.parametrize(
    ("productive", "unproductive", "expected"),
    [
        (0, 9, "intermittent"),  # E3: 9 resolutions, no task progress after any
        (1, 0, "resolved"),  # A1: one yield, then robot_2's task
        (0, 0, "clogged"),  # E2 / A2: nothing broke a latch
        (0, 1, "clogged"),  # one futile resolution is not repetition
        (1, 2, "intermittent"),  # churn after a productive one still churns
    ],
)
def test_churn_class_predicate(productive, unproductive, expected):
    assert _scorer().classify_churn(productive, unproductive) == expected


def test_union_length_merges_overlapping_windows():
    assert _scorer()._union_length([(0.0, 10.0), (5.0, 12.0), (20.0, 25.0)]) == 17.0


# ---- (b) the bound: config ----


def test_churn_bound_defaults_off_with_values_unset():
    bound = ChurnBoundConfig()
    assert (bound.enabled, bound.budget_k, bound.window_sim_sec, bound.alternation_max) == (
        False, None, None, None
    )


def test_churn_bound_enabled_without_values_is_rejected():
    with pytest.raises(ValidationError, match="never defaulted"):
        ChurnBoundConfig(enabled=True)
    with pytest.raises(ValidationError, match="alternation_max"):
        ChurnBoundConfig(enabled=True, budget_k=3, window_sim_sec=300.0)


def test_churn_bound_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        ChurnBoundConfig(enabled=False, budget=3)


def test_pinned_orchestrator_yaml_keeps_the_bound_off():
    config = load_config(yaml.safe_load(ORCH.read_text()))
    assert config.churn_bound == ChurnBoundConfig()


# ---- (b) the bound: ledger ----


def _ledger_e3(upto: int) -> ChurnLedger:
    ledger = ChurnLedger()
    cluster = frozenset({"robot_2", "robot_3", "robot_5"})
    for k, (y, p) in enumerate(E3[:upto]):
        ledger.record(40.0 * k, ("yield", y, p), cluster)
    return ledger


def test_budget_withholds_once_the_cluster_spent_it():
    ledger = _ledger_e3(3)
    verdict = ledger.check(
        120.0, ("yield", "robot_2", "robot_5"), frozenset({"robot_2", "robot_5"}),
        budget_k=3, window_sec=600.0, alternation_max=99,
    )
    assert (verdict.withhold, verdict.reason, verdict.cluster_dispatches_in_window) == (
        True, "budget", 3
    )


def test_window_forgets_old_dispatches():
    ledger = _ledger_e3(3)
    verdict = ledger.check(
        500.0, ("yield", "robot_2", "robot_5"), frozenset({"robot_2", "robot_5"}),
        budget_k=3, window_sec=100.0, alternation_max=99,
    )
    assert verdict.withhold is False
    assert verdict.cluster_dispatches_in_window == 0


def test_alternation_withholds_past_its_maximum():
    ledger = _ledger_e3(3)  # C, A, B
    verdict = ledger.check(
        120.0, ("yield", "robot_2", "robot_5"), frozenset({"robot_2", "robot_5"}),
        budget_k=99, window_sec=600.0, alternation_max=0,
    )
    assert (verdict.withhold, verdict.reason, verdict.cluster_alternations_in_window) == (
        True, "alternation", 1
    )


def test_other_cluster_does_not_count():
    ledger = _ledger_e3(5)
    verdict = ledger.check(
        200.0, ("yield", "robot_1", "robot_4"), frozenset({"robot_1", "robot_4"}),
        budget_k=1, window_sec=600.0, alternation_max=0,
    )
    assert verdict.withhold is False


# ---- (b) the bound: node ----


class _YieldPipeline:
    def __init__(self) -> None:
        self.run_calls: list[str] = []

    def run(self, request):
        self.run_calls.append(request.request_id)
        command = _yield("robot_2", "robot_1")
        command["command_id"] = f"cmd-{request.request_id}"
        command["actions"] = command["actions"][:2]
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id),
            grounded_command=command,
            terminal_stage=TerminalStage.OK,
        )

    def analyze(self, request):  # pragma: no cover - probe mode is off here
        raise AssertionError("no probe expected")


def _cycle(node, clock) -> None:
    clock.t += COOLDOWN + 1.0
    _feed(node, clock.t - 900.0, BASE)
    if node._future is not None:
        node._future.result(timeout=WAIT_SEC)
        node._on_timer()


def _artifact(node, request_id: str) -> dict:
    return json.loads((Path(node._config.decision_log_dir) / f"{request_id}.json").read_text())


def test_bound_off_node_builds_no_ledger_and_dispatches_as_before(node_env, tmp_path):  # noqa: F811
    pipeline = _YieldPipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline, t0_probe_mode=False)
    assert node._churn is None
    _cycle(node, clock)
    assert len(node._cmd_pub.published) == 2
    assert "dispatch_withheld" not in _artifact(node, pipeline.run_calls[0])
    assert node.get_logger().matching("churn") == []


def test_bound_on_records_a_dispatched_clearing_command(node_env, tmp_path):  # noqa: F811
    pipeline = _YieldPipeline()
    node, clock = _make_node(
        node_env, tmp_path, pipeline, t0_probe_mode=False,
        churn_bound={"enabled": True, "budget_k": 2, "window_sim_sec": 600.0,
                     "alternation_max": 1},
    )
    _cycle(node, clock)
    assert len(node._cmd_pub.published) == 2
    (record,) = node._churn.records
    assert record.identity == ("yield", "robot_2", "robot_1")
    assert record.cluster == frozenset({"robot_1", "robot_2"})
    assert node.get_logger().matching("churn bound request=")


def test_bound_on_withholds_a_spent_cluster(node_env, tmp_path):  # noqa: F811
    pipeline = _YieldPipeline()
    node, clock = _make_node(
        node_env, tmp_path, pipeline, t0_probe_mode=False,
        reanalysis_suppression={"enabled": True, "applies_to": "all"},
        churn_bound={"enabled": True, "budget_k": 1, "window_sim_sec": 600.0,
                     "alternation_max": 5},
    )
    node._churn.record(0.0, ("yield", "robot_1", "robot_2"), frozenset({"robot_1", "robot_2"}))
    _cycle(node, clock)
    assert node._cmd_pub.published == []
    withheld = _artifact(node, pipeline.run_calls[0])["dispatch_withheld"]
    assert withheld["reason"] == "churn_budget"
    assert withheld["identity"] == ["yield", "robot_2", "robot_1"]
    assert withheld["cluster_dispatches_in_window"] == 1
    assert node.get_logger().matching("churn bound withheld request=")
    assert node.get_logger().matching("outcome=churn_budget")
    assert len(node._churn.records) == 1


# ---- minors: one-cluster echo, cap text ----


def test_echo_names_one_cluster_on_two_latched_pairs():
    from reasoning.vlm.mock_backend import EchoRobot, echo_select

    # E3-like: r1+r4 latched in the west passage (0.29 m), r3+r5 at N (0.38 m).
    robots = [
        EchoRobot("robot_1", -1.79, -0.08, True),
        EchoRobot("robot_2", -0.10, 1.40, True),
        EchoRobot("robot_3", -0.30, 1.05, True),
        EchoRobot("robot_4", -1.85, 0.21, True),
        EchoRobot("robot_5", 0.05, 1.10, True),
    ]
    assert echo_select(robots) == ["robot_1", "robot_4"]


def test_cap_refusal_names_the_45_degree_cap():
    scene = SCENES["s1b_e4_cap_live"]
    command = _ground(scene["rows"], CongestionDecision(**scene["decision"]))
    reason = _refusal(command)
    assert reason is not None
    assert reason.startswith("yield refused: ambiguous lane: robot_1 heads 41 deg")
    assert "robot_1 is the node-handoff arriver, but it heads 49 deg off the pair's y bearing" in (
        reason
    )
    assert "45 deg heading-lane cap" in reason
    assert "robot_5's x lane crosses" not in reason
    assert "grounding=dynamic_arms:ambiguous_refused:robot_1:41" in command["degradations"]
