"""Replay tests: recorded primitives through the real adapter with the stall abort on.

Fixtures (read-only extracts, `scripts/stall_abort_replay.py --pack`):
`tests/unit/data/stall_abort/replay_episodes.jsonl.gz` holds 221 raw-cmd_vel
primitives from 12 demo-campaign bundles (v7j), the October S1b bundles and
the IB10 rosbag bundles (v3), with poses from GT (or the bag's `/odom`).
`expected.json` names the 10 that must fire, each a GT footprint contact.
Report: docs/reports/2026-11-15-m4-stall-abort.md, section 6.
"""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path

import pytest
from swarm_execution.stall_abort import STALL_ABORT_DETAIL_PREFIX, StallAbortConfig

from scripts.stall_abort_replay import replay_episode

DATA = Path(__file__).resolve().parent / "data" / "stall_abort"
CONFIG = StallAbortConfig(enabled=True)


def _key(e: dict) -> str:
    return "|".join([e["bundle"], e["command_id"], e["robot_id"], e["primitive"]])


@pytest.fixture(scope="module")
def replays() -> list[tuple[dict, dict]]:
    with gzip.open(DATA / "replay_episodes.jsonl.gz", "rt", encoding="utf-8") as handle:
        episodes = [json.loads(line) for line in handle]
    return [(e, replay_episode(e, CONFIG)) for e in episodes]


@pytest.fixture(scope="module")
def expected() -> dict:
    return json.loads((DATA / "expected.json").read_text())["expected_fires"]


def _fired(result: dict) -> bool:
    return result["outcome"] == "FAILED" and result["detail"].startswith(STALL_ABORT_DETAIL_PREFIX)


def test_fixture_covers_campaign_october_and_bag_odometry(replays) -> None:
    bundles = {e["bundle"] for e, _ in replays}
    assert len(replays) == 221
    assert any(b.startswith("m5D") for b in bundles) and any(b.startswith("s1b_") for b in bundles)
    assert sum(e["odom_source"] == "bag" for e, _ in replays) >= 30


def test_every_expected_case_fires_as_a_stall(replays, expected) -> None:
    fired = {_key(e): r for e, r in replays if _fired(r)}
    assert set(fired) == set(expected)
    for result in fired.values():
        assert result["verdict"]["outcome"] == "stall"


def test_pinned_cases_fire_within_three_seconds_of_contact(replays, expected) -> None:
    for e, r in replays:
        if _key(e) in expected:
            lag = r["t"] - expected[_key(e)]["contact_onset_sim"]
            assert 0.0 < lag <= 3.1, (_key(e), lag)


def test_m5d_escort_aborts_long_before_its_deadline(replays) -> None:
    (e, r), = [
        (e, r)
        for e, r in replays
        if e["bundle"] == "m5D_t01_a1" and e["robot_id"] == "robot_3" and e["primitive"] == "escort"
    ]
    assert _fired(r)
    assert r["t"] < 150.0 < e["end_sim"] - 50.0
    assert r["log"].startswith("stall abort robot=robot_3 command=a15f3fc5")
    assert "primitive=escort phase=drive reason=stall" in r["log"]


def test_live_deadline_failures_fire_before_the_deadline(replays, expected) -> None:
    for e, r in replays:
        if _key(e) in expected and e["live_outcome"] == "FAILED":
            assert e["end_sim"] - r["t"] > 15.0, _key(e)


def test_no_contact_free_completed_primitive_fires(replays, expected) -> None:
    completed = [(e, r) for e, r in replays if e["live_outcome"] == "COMPLETED"]
    assert len(completed) == 193
    false_positives = [_key(e) for e, r in completed if _fired(r) and _key(e) not in expected]
    assert false_positives == []


def test_completed_primitives_keep_margin_to_the_threshold(replays, expected) -> None:
    for e, r in replays:
        if e["live_outcome"] != "COMPLETED" or _key(e) in expected:
            continue
        ratios = r["min_ratio"]
        assert ratios.get("linear", math.inf) >= 0.8, _key(e)
        assert ratios.get("angular", math.inf) >= 0.6, _key(e)


def test_latch_held_failures_do_not_fire(replays, expected) -> None:
    # Live FAILED / never ended, but the safety hold zeroed the wheels when
    # the robot stopped: no commanded motion reached it, so no stall.
    quiet = [
        (e, r)
        for e, r in replays
        if e["live_outcome"] != "COMPLETED" and _key(e) not in expected
    ]
    assert len(quiet) >= 20
    assert not any(_fired(r) for _, r in quiet)


def test_key_off_replay_never_aborts(replays) -> None:
    with gzip.open(DATA / "replay_episodes.jsonl.gz", "rt", encoding="utf-8") as handle:
        pinned = [
            e
            for e in map(json.loads, handle)
            if (e["bundle"], e["primitive"], e["robot_id"]) == ("m5D_t01_a1", "escort", "robot_3")
        ]
    result = replay_episode(pinned[0], None)
    assert result["outcome"] == "running"


def test_recorded_pinned_odometry_shows_no_movement() -> None:
    # Real /cmd_vel and /odom of two robots pinned on rack corners (v3
    # s1_resume bags): commanded 0.10-0.16 m/s, odometry under 2 mm.
    samples = json.loads((DATA / "pinned_bag_samples.json").read_text())
    for sample in samples:
        cmds, odom = sample["cmd_vel"], sample["odom"]
        commanded = sum(abs(c[1]) for c in cmds) / len(cmds) * (cmds[-1][0] - cmds[0][0])
        inside = [o for o in odom if cmds[0][0] <= o[0] <= cmds[-1][0]]
        moved = math.hypot(inside[-1][1] - inside[0][1], inside[-1][2] - inside[0][2])
        assert commanded > 0.1
        assert moved / commanded < 0.02, sample["robot_id"]
