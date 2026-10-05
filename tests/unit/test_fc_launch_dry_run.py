"""Pins scripts/vm/fc_launch.sh's DRY_RUN command sequence.

The two-robot goldens under tests/unit/data/fc_launch/ were recorded from the
launcher BEFORE its robot loop (tree 3ebb7ea, hard-coded robot_1/robot_2), so
a two-robot scenario must keep producing byte-identical commands. The
three-robot cases check the loop itself.

Two stages were added after the goldens (the lifecycle-gate fold, 2026-09-29):
the Nav2 lifecycle gate after the action-server waits and the M5 log
pre-create before M5 starts. They print only the lines `GATE_LINE_PREFIXES`
matches, so the goldens stay byte-identical once those lines are removed, and
the new lines are pinned on their own below.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "vm" / "fc_launch.sh"
GOLDEN_DIR = Path(__file__).parent / "data" / "fc_launch"

# case name -> (scenario, extra env)
TWO_ROBOT_CASES: dict[str, tuple[str, dict[str, str]]] = {
    "head_on_deadlock": ("head_on_deadlock", {}),
    "wopen_eopen": ("head_on_asymmetric_wopen_eopen_o0", {}),
    "obstacle_in_candidate_mock": (
        "obstacle_in_candidate",
        {
            "MOCK_DECISION_FILE": "config/mock_decisions/obstacle_in_candidate_yield_once.json",
            "MOCK_RETREAT_CHOICE_FILE": "config/mock_decisions/retreat_choice_b.json",
        },
    ),
    "normal_flow_record": ("normal_flow", {"RECORD": "1"}),
    "blocked_path_object": ("blocked_path_object", {}),
}

_CLEARED_ENV = (
    "BACKEND_ID", "MOCK_DECISION_FILE", "MOCK_RETREAT_CHOICE_FILE", "MODALITY",
    "RECORD", "REC_SEC", "SIM_SEC", "SEED", "CONTAINER", "REPO", "NAV2_ACTIVE_TIMEOUT_SEC",
    "MAP_SCENARIO",
)


def dry_run(scenario: str, extra_env: dict[str, str]) -> str:
    """Run the launcher in DRY_RUN mode and return its normalized output."""
    env = {k: v for k, v in os.environ.items() if k not in _CLEARED_ENV}
    # The host-python spawn parse needs pyyaml: the venv's interpreter first.
    env["PATH"] = f"{Path(sys.executable).parent}:{env.get('PATH', '')}"
    env.update({"DRY_RUN": "1", "SCENARIO": scenario, **extra_env})
    completed = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
    return normalize(completed.stdout + completed.stderr)


def normalize(text: str) -> str:
    """Drop the per-run clock, stamp and checkout path from launcher output."""
    text = re.sub(r"^\[fc-launch \d\d:\d\d:\d\d\] ", "[fc-launch] ", text, flags=re.M)
    text = re.sub(r"\d{8}_\d{6}", "<STAMP>", text)
    return text.replace(str(ROOT), "<REPO>")


GATE_LINE_PREFIXES = (
    "[fc-launch] waiting for Nav2 lifecycle: ",
    "[fc-launch] [DRY_RUN] poll /tmp/fc_<STAMP>_nav2_r",
    "[fc-launch] [DRY_RUN] sudo docker exec vgu_ros touch /tmp/fc_<STAMP>_m5.log",
)


def without_gate_lines(output: str) -> str:
    """Drop the lines of the stages added after the goldens were recorded."""
    return "".join(
        line for line in output.splitlines(keepends=True)
        if not line.startswith(GATE_LINE_PREFIXES)
    )


@pytest.mark.parametrize("case", sorted(TWO_ROBOT_CASES))
def test_two_robot_dry_run_matches_pre_loop_golden(case):
    scenario, extra_env = TWO_ROBOT_CASES[case]
    golden = (GOLDEN_DIR / f"{case}.txt").read_text(encoding="utf-8")
    assert without_gate_lines(dry_run(scenario, extra_env)) == golden


@pytest.mark.parametrize("case", sorted(TWO_ROBOT_CASES))
def test_two_robot_dry_run_adds_exactly_the_three_gate_lines(case):
    scenario, extra_env = TWO_ROBOT_CASES[case]
    output = dry_run(scenario, extra_env)
    added = [line for line in output.splitlines() if line.startswith(GATE_LINE_PREFIXES)]
    assert added == [
        "[fc-launch] waiting for Nav2 lifecycle: 2 stack(s) active (<= 240s)",
        "[fc-launch] [DRY_RUN] poll /tmp/fc_<STAMP>_nav2_r1.log /tmp/fc_<STAMP>_nav2_r2.log "
        "every 2s for /lifecycle_manager_navigation\\]: .*Managed nodes are active/ in all 2, "
        "abort on /Aborting bringup/",
        "[fc-launch] [DRY_RUN] sudo docker exec vgu_ros touch /tmp/fc_<STAMP>_m5.log",
    ]


def test_lifecycle_gate_runs_after_the_action_waits_and_before_m4():
    lines = dry_run("dynamic_anomaly", {}).splitlines()
    gate = lines.index("[fc-launch] waiting for Nav2 lifecycle: 4 stack(s) active (<= 240s)")
    servers_live = lines.index("[fc-launch] Nav2 action servers live")
    m4 = next(i for i, line in enumerate(lines) if line.startswith("[fc-launch] starting M4"))
    assert servers_live < gate < m4
    assert all(f"/tmp/fc_<STAMP>_nav2_r{n}.log" in lines[gate + 1] for n in (1, 2, 3, 4))
    assert "in all 4," in lines[gate + 1]


def test_m5_log_is_created_before_m5_is_launched_and_tailed():
    lines = dry_run("dynamic_anomaly", {}).splitlines()
    touch = lines.index("[fc-launch] [DRY_RUN] sudo docker exec vgu_ros touch /tmp/fc_<STAMP>_m5.log")
    m5_launch = next(
        i for i, line in enumerate(lines) if "orchestrator.launch.py >/tmp/fc_<STAMP>_m5.log" in line
    )
    tail = next(i for i, line in enumerate(lines) if "tail -f /tmp/fc_<STAMP>_m5.log" in line)
    assert touch < m5_launch < tail


def test_gate_budget_env_overrides_the_default():
    output = dry_run("head_on_deadlock", {"NAV2_ACTIVE_TIMEOUT_SEC": "90"})
    assert "[fc-launch] waiting for Nav2 lifecycle: 2 stack(s) active (<= 90s)" in output


def _nav2_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if "nav2_robot.launch.py" in line]


def test_four_robot_scenario_launches_one_nav2_stack_per_robot():
    output = dry_run("dynamic_anomaly", {})
    launches = _nav2_lines(output)
    assert [re.search(r"robot_id:=(robot_\d+)", line).group(1) for line in launches] == [
        "robot_1", "robot_2", "robot_3", "robot_4",
    ]
    assert ["start_map_server:=true" in line for line in launches] == [
        True, False, False, False,
    ]
    for n in (1, 2, 3, 4):
        assert f"grep -qx /robot_{n}/odom" in output
        assert f"grep -qx /robot_{n}/scan" in output
        assert f"grep -qx /robot_{n}/navigate_to_pose" in output
        assert f"/tmp/fc_<STAMP>_nav2_r{n}.log 2>&1" in output


def _scratch_repo(tmp_path: Path, robots_yaml: str) -> Path:
    scenarios = tmp_path / "isaac" / "config" / "scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "scratch.yaml").write_text(f"robots:\n{robots_yaml}", encoding="utf-8")
    orch = tmp_path / "ros2_ws" / "src" / "swarm_orchestrator" / "config"
    orch.mkdir(parents=True)
    (orch / "orchestrator.yaml").write_text(
        "prompt_static_obstacles: false\nreasoning_backend_id: openai\n", encoding="utf-8"
    )
    return tmp_path


def test_robots_launch_in_robot_number_order_with_first_serving_the_map(tmp_path):
    robots = "".join(
        f"  - robot_id: {rid}\n    spawn: {{x: {x}, y: 0.0, yaw_rad: 0.0}}\n"
        for rid, x in (("robot_3", -2.45), ("robot_1", -1.5), ("robot_2", 1.5))
    )
    repo = _scratch_repo(tmp_path, robots)
    output = dry_run("scratch", {"REPO": str(repo)})
    launches = _nav2_lines(output)
    assert [re.search(r"robot_id:=(robot_\d+) x:=(\S+)", line).groups() for line in launches] == [
        ("robot_1", "-1.5"), ("robot_2", "1.5"), ("robot_3", "-2.45"),
    ]
    assert "start_map_server:=true" in launches[0]
    assert "spawn poses parsed (robot_1 x=-1.5 y=0.0 yaw=0.0; robot_2 x=1.5 y=0.0 " \
        "yaw=0.0; robot_3 x=-2.45 y=0.0 yaw=0.0)" in output
    # A 3 s settle precedes every stack after the first, as before the loop.
    lines = output.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("[fc-launch] starting Nav2")]
    assert [lines[i - 1].endswith("sleep 3") for i in starts] == [False, True, True]


def test_scenario_without_robots_is_refused(tmp_path):
    repo = _scratch_repo(tmp_path, "  []\n")
    env = {k: v for k, v in os.environ.items() if k not in _CLEARED_ENV}
    env["PATH"] = f"{Path(sys.executable).parent}:{env.get('PATH', '')}"
    env.update({"DRY_RUN": "1", "SCENARIO": "scratch", "REPO": str(repo)})
    completed = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=False
    )
    assert completed.returncode == 1
    assert "no robots parsed" in completed.stderr


def test_seed_env_sets_the_isaac_seed():
    output = dry_run("head_on_deadlock", {"SEED": "7"})
    assert "(headless, seed 7, 1200s)" in output
    assert "--headless --seed 7 --duration-sec" in output


def test_free_flow_variant_resolves_from_its_dir_and_reuses_the_parent_map():
    output = dry_run(
        "t2b_flow_ordering_ff_robot_3", {"MAP_SCENARIO": "t2b_flow_ordering"}
    )
    assert "--scenario <REPO>/isaac/config/scenarios/free_flow/t2b_flow_ordering_ff_robot_3.yaml" \
        in output
    launches = _nav2_lines(output)
    assert len(launches) == 1
    assert "robot_id:=robot_3 x:=-2.45" in launches[0]
    assert "map_yaml:=/ws/ros2_ws/install/share/swarm_simulation/maps/" \
        "warehouse_map_t2b_flow_ordering.yaml" in launches[0]


def test_map_defaults_to_the_scenario_name():
    output = dry_run("t2b_flow_ordering_ff_robot_3", {})
    assert "warehouse_map_t2b_flow_ordering_ff_robot_3.yaml" in _nav2_lines(output)[0]
