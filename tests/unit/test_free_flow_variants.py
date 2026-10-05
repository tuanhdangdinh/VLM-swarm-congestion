"""Unit tests for scripts/make_free_flow_variants.py (solo-in-space free-flow variants).

Pins the METHOD RULED (2026-10-05) contract: one variant per robot holding
ONLY that robot, the parent's course byte-equal except blocker cells' blockers,
a systematic name, a map identical to the parent's, an M5 tasks line the VM
driver's `patch_initial_tasks.py` accepts, and committed files equal to the
generator's output.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from isaac.scripts.generate_warehouse_map import build_occupancy_grid  # noqa: E402
from isaac.vgu_sim.config import ScenarioConfig, WarehouseConfig  # noqa: E402
from scripts import make_free_flow_variants as mffv  # noqa: E402

MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
PATCH_SCRIPT = REPO_ROOT / "scripts/vm/patch_initial_tasks.py"
FILES = mffv.generate()
MANIFEST = json.loads(FILES[mffv.MANIFEST_NAME])
VARIANTS = sorted(MANIFEST["variants"])


def _variant(name: str) -> dict:
    return yaml.safe_load(FILES[f"{name}.yaml"])


def _parent(name: str) -> dict:
    meta = MANIFEST["variants"][name]
    return yaml.safe_load((REPO_ROOT / meta["parent_path"]).read_text(encoding="utf-8"))


def _grid(config: ScenarioConfig) -> np.ndarray:
    grid, _ = build_occupancy_grid(
        WarehouseConfig(), obstacles=[], resolution_m=0.05,
        aisle_barrier=config.aisle_barrier, static_obstacles=config.static_obstacles,
        loop_map=config.loop_map,
    )
    return grid


def test_generator_emits_one_variant_per_robot_of_every_cell():
    expected = {
        mffv.variant_name(cell, robot["robot_id"])
        for cell, rel in mffv.FREE_FLOW_CELLS.items()
        for robot in yaml.safe_load((mffv.SCENARIOS_DIR / rel).read_text())["robots"]
    }
    assert set(VARIANTS) == expected
    assert len(VARIANTS) == 22


@pytest.mark.parametrize("name", VARIANTS)
def test_variant_holds_only_its_robot_verbatim(name):
    meta = MANIFEST["variants"][name]
    robots = _variant(name)["robots"]
    parent_robot = next(r for r in _parent(name)["robots"] if r["robot_id"] == meta["robot_id"])
    assert robots == [parent_robot]


@pytest.mark.parametrize("name", VARIANTS)
def test_variant_name_follows_the_ff_scheme(name):
    meta = MANIFEST["variants"][name]
    assert name == f"{meta['parent']}_ff_{meta['robot_id']}"
    assert re.fullmatch(r"[a-z][a-z0-9_]*_ff_robot_\d+", name)
    assert _variant(name)["name"] == name


@pytest.mark.parametrize("name", VARIANTS)
def test_variant_validates_as_a_conflict_free_scenario(name):
    config = ScenarioConfig.model_validate(_variant(name))
    assert config.family == "normal_flow"
    assert config.expected_conflict is None
    assert config.oracle is None
    assert config.duration_sec == mffv.VARIANT_DURATION_SEC
    assert config.runtime.duration_sec is None


@pytest.mark.parametrize("name", VARIANTS)
def test_variant_keeps_the_parent_course(name):
    variant, parent = _variant(name), _parent(name)
    assert variant["aisle_barrier"] == parent.get("aisle_barrier")
    assert variant["loop_map"] == parent.get("loop_map")
    assert variant["seed"] == parent["seed"]
    if MANIFEST["variants"][name]["parent"] not in mffv.BLOCKER_CELLS:
        assert variant["static_obstacles"] == list(parent.get("static_obstacles") or [])
        assert variant["timed_obstacles"] == list(parent.get("timed_obstacles") or [])


@pytest.mark.parametrize(
    "name", [n for n in VARIANTS if MANIFEST["variants"][n]["parent"] in mffv.BLOCKER_CELLS]
)
def test_blocker_cell_variant_strips_its_blockers(name):
    variant, parent = _variant(name), _parent(name)
    blockers = [o["obstacle_id"] for o in
                (*(parent.get("timed_obstacles") or []), *(parent.get("static_obstacles") or []))]
    assert blockers, "a registered blocker cell must carry a blocker"
    assert variant["timed_obstacles"] == []
    assert variant["static_obstacles"] == []
    assert MANIFEST["variants"][name]["stripped_obstacles"] == blockers


def test_head_on_blocker_west_is_course_geometry_and_is_kept():
    variant = _variant("head_on_asymmetric_w0p2_eopen_bshort_o0_ff_robot_2")
    assert [o["obstacle_id"] for o in variant["static_obstacles"]] == ["blocker_west"]


def test_blocked_path_cells_would_strip_their_timed_blocker():
    files = mffv.generate({"blocked_path_object": "blocked_path_object.yaml"})
    manifest = json.loads(files[mffv.MANIFEST_NAME])
    for name, meta in manifest["variants"].items():
        assert meta["stripped_obstacles"] == ["blocker"]
        assert yaml.safe_load(files[f"{name}.yaml"])["timed_obstacles"] == []


def test_non_blocker_cell_with_a_timed_obstacle_is_refused():
    parent = yaml.safe_load((mffv.SCENARIOS_DIR / "t2b_flow_ordering.yaml").read_text())
    parent["timed_obstacles"] = [{"obstacle_id": "x"}]
    with pytest.raises(ValueError, match="timed obstacles"):
        mffv.make_variant("t2b_flow_ordering", parent, "robot_1")


@pytest.mark.parametrize("name", VARIANTS)
def test_variant_map_is_byte_identical_to_the_parent_map(name):
    meta = MANIFEST["variants"][name]
    parent_cfg = ScenarioConfig.model_validate(_parent(name))
    variant_grid = _grid(ScenarioConfig.model_validate(_variant(name)))
    assert np.array_equal(variant_grid, _grid(parent_cfg))
    committed = MAPS_DIR / f"warehouse_map_{meta['map_scenario']}.pgm"
    assert np.array_equal(np.asarray(Image.open(committed)), variant_grid)


@pytest.mark.parametrize("name", VARIANTS)
def test_m5_task_line_carries_the_variant_goal(name):
    meta = MANIFEST["variants"][name]
    robot = _variant(name)["robots"][0]
    line = meta["m5_task_line"]
    assert re.fullmatch(r"  robot_\d+: \{.*\}", line)
    assert "start_delay_sec" not in line
    assert f"goal: [{float(robot['goal']['x'])}, {float(robot['goal']['y'])}]" in line
    assert line.startswith(f"  {meta['robot_id']}:")


def test_m5_task_line_patches_the_vm_pristine_orchestrator(tmp_path):
    pristine = subprocess.run(
        ["git", "show",
         "fix/deadlock-collision-resolution:ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    if pristine.returncode != 0:
        pytest.skip("VM-pristine orchestrator.yaml branch not available")
    config = tmp_path / "orchestrator.yaml"
    config.write_text(pristine.stdout)
    block = tmp_path / "tasks.txt"
    meta = MANIFEST["variants"]["t2b_flow_ordering_ff_robot_3"]
    block.write_text(meta["m5_task_line"] + "\n")
    subprocess.run([sys.executable, str(PATCH_SCRIPT), str(config), "--set", str(block)],
                   check=True, capture_output=True)
    patched = yaml.safe_load(config.read_text())
    assert patched["initial_tasks"] == {
        "robot_3": {"task": "cross_narrow_aisle", "goal": [1.85, 0.0]}
    }
    before = pristine.stdout.split("initial_tasks:")[0]
    assert config.read_text().startswith(before)


def test_priority_visual_r1_covers_its_registered_cells():
    base = yaml.safe_load((mffv.SCENARIOS_DIR / "priority_visual_r1.yaml").read_text())
    for cell, source in MANIFEST["covered_by"].items():
        assert source == "priority_visual_r1"
        other = yaml.safe_load((mffv.SCENARIOS_DIR / f"{cell}.yaml").read_text())
        pose = [(r["robot_id"], r["spawn"], r["goal"]) for r in other["robots"]]
        assert pose == [(r["robot_id"], r["spawn"], r["goal"]) for r in base["robots"]]
        for key in ("aisle_barrier", "static_obstacles", "timed_obstacles", "loop_map"):
            assert other.get(key) == base.get(key)
        assert (MAPS_DIR / f"warehouse_map_{cell}.pgm").read_bytes() == (
            MAPS_DIR / "warehouse_map_priority_visual_r1.pgm").read_bytes()


def test_committed_variants_equal_the_generator_output():
    assert mffv.main(["--check"]) == 0
