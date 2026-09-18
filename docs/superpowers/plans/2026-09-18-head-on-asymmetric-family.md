# Head-On Asymmetric Scenario Family Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate the T1/T2a scenario battery as a parametric `head_on_asymmetric` family (parked blocker behind one spawn point, computed oracle), give static and timed obstacles real collision geometry, bake static obstacles into per-scenario Nav2 maps, and verify the family on the VM (validity pairs + one recorded gpt-4o run).

**Architecture:** `isaac/vgu_sim/config.py` grows a `family` field, free-form `name`, `static_obstacles`, obstacle `size`, `parameters` and `oracle`. A pure module `isaac/vgu_sim/family_oracle.py` computes yield feasibility from the same `reasoning.rag.scene_geometry` functions M3 grounds with. A generator script writes the committed variant yamls + manifest; the map generator and USD builder consume `static_obstacles`. A repo-tracked VM launch script parametrised by `SCENARIO` replaces the ad-hoc VM scripts.

**Tech Stack:** Python 3.12, Pydantic v2, PyYAML, numpy/Pillow (map), pxr (USD, host-only tests), bash (VM launch), ROS 2 Jazzy in the `vgu_ros` container, Isaac Sim 6.0 on the VM.

**Spec:** `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md` (rev 2). Parent: `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` (Scenario battery, FCFS + commitment tiebreak).

## Global Constraints

- Blocker box is **0.3 × 0.3 × 0.5 m**, static collider (`UsdPhysics.CollisionAPI` only, no rigid body), aisle-centred (y = 0), yaw 0.
- `blocker_<side>_m` = near-face distance **behind that side's spawn point**; box centre `|x| = 1.5 + blocker + 0.15`. v1 grid: blocker ∈ {0.2, null}, `arrival_offset_m = 0.0` fixed.
- Variant id `w<west>_e<east>_o<offset>`, `open` for null, floats printed with `:g` and the decimal point spelled `p` (`0p2`, `0`) because scenario names must match `^[a-z][a-z0-9_]*$`. Scenario name `head_on_asymmetric_<variant>`. v1 variants: `w0p2_eopen_o0`, `wopen_e0p2_o0`, `wopen_eopen_o0`. The `w0p2_e0p2` cell is skipped (printed, not written).
- Oracle: feasible iff `0.5 + blocker >= park_offset_m(geometry) - corridor.half_length_m + robot.half_width_m + 0.2` (null → feasible). `fcfs_yielder`: later arriver; tie (offset 0) → `robot_1`. `correct_yielder`: the feasible side's robot, else `fcfs_yielder`. `contrasts_fcfs` is derived (property), never stored.
- Scene geometry is loaded from `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml` key `scenario_geometry` (top-level key), never duplicated.
- The three legacy yamls (`head_on_deadlock`, `intersection_bottleneck`, `dynamic_anomaly`) must parse unchanged; `family` is inferred from their names.
- Everything not named by the family (seed 42, duration 300, aisle barrier 0.55 × 2.0, goals ±2.5, expected_conflict, runtime) is copied from `isaac/config/scenarios/head_on_deadlock.yaml`.
- Committed generated artifacts (family yamls, manifest, maps) must match what the generators produce — each has a staleness-guard test.
- Coding standards: CLAUDE.md (type hints `X | Y`, Google docstrings on public functions, frozen Pydantic models, tests named `test_<behavior>_<condition>`, one behavior per test). Commit messages: Conventional Commits, subject only, no body, no trailers.
- Test command: `pytest tests/unit/<file>` from the worktree root (`/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/.worktrees/failure-context-closed-loop`); lint: `ruff check <paths>` (must exit 0 on touched files; `reasoning/rag/command_grounder.py:65` and `coordination_client_node.py` carry pre-existing errors — leave them).
- The suite has 13 pre-existing failures (M6/Isaac asset tests, `test_close_pair_timer_resets_when_robots_separate`, `test_write_decision_artifact_preserves_m2_result_on_grounding_failure`, `test_factory_requires_config_for_openai`); do not fix or add to them.
- Never log or commit secrets; the VM's `/ws/.env` is sourced only inside the container.
- VM: `ubuntu@34.68.133.240`, key `/Users/tuanhdangdinh/Documents/IsaacAutomator/state/canary-base/key.pem`, repo copy `/home/ubuntu/vgu-vlm-swarm` (not a git checkout — rsync), container `vgu_ros` mounts it at `/ws`; colcon: `sudo docker exec vgu_ros bash -lc 'source /opt/ros/jazzy/setup.bash && cd /ws/ros2_ws && colcon build --merge-install --packages-select <pkg>'`; kill launches with `pkill -f "[r]os2 launch"`; `sudo docker restart vgu_ros` is the clean reset; `--duration-sec 900` does not stop Isaac — kill `python.sh` by hand.

## Dispatch notes (controller only)

Model per task: 1, 2, 4, 6, 10, 11 → `sonnet` (brief carries the code or an exact contract); 3, 5, 12 → `opus` (yaml rendering / pxr judgement / cross-module M2+M5 plumbing); 7, 8, 9 → `opus` (VM, SSH, log forensics). Final whole-branch review → `opus`. Tasks 7–9 are sequential and long (≈ 15 min per sim run); they write their evidence to files under `data/logs/family_check_20260918/` (git-ignored) and a short report file the docs task links.

**Execution order: 6 → 7 → 11 → 12 → 13 → 8 → 9 → 10.** Task 13 (one-shot mock decisions) unblocks Task 8; see its rationale. Tasks 11 and 12 build the observability channels Task 9's paired runs depend on; Task 10 documents everything last.

---

### Task 1: Scenario config schema — family, free name, obstacle geometry, parameters, oracle

**Files:**
- Modify: `isaac/vgu_sim/config.py` (models `TimedObstacleConfig`, `ScenarioConfig`; add `ObstacleSize`, `StaticObstacleConfig`, `HeadOnAsymmetricParams`, `OracleConfig`, `FAMILY_BY_LEGACY_NAME`)
- Test: `tests/unit/test_m6_config.py`

**Interfaces:**
- Produces (used by Tasks 2–5):

```python
FAMILY_BY_LEGACY_NAME: dict[str, str] = {
    "head_on_deadlock": "head_on",
    "intersection_bottleneck": "intersection",
    "dynamic_anomaly": "dynamic_anomaly",
}
ScenarioFamily = Literal["head_on", "intersection", "dynamic_anomaly"]

class ObstacleSize(BaseModel):            # frozen, extra=forbid; each field > 0
    x_m: float = 0.3
    y_m: float = 0.3
    z_m: float = 0.5

class StaticObstacleConfig(BaseModel):    # frozen, extra=forbid
    obstacle_id: str                       # non-empty
    pose: Pose2D
    size: ObstacleSize = ObstacleSize()

class TimedObstacleConfig(BaseModel):     # existing + new field
    size: ObstacleSize = ObstacleSize()

class HeadOnAsymmetricParams(BaseModel):  # frozen, extra=forbid
    blocker_west_m: float | None = None    # >= 0 when set
    blocker_east_m: float | None = None    # >= 0 when set
    arrival_offset_m: float = 0.0          # >= 0

class OracleConfig(BaseModel):            # frozen, extra=forbid
    correct_yielder: str
    fcfs_yielder: str
    feasible_yielders: tuple[str, ...]     # non-empty; must contain correct_yielder
    objective: Literal["min_total_time_to_goal"] = "min_total_time_to_goal"
    rationale: str
    @property
    def contrasts_fcfs(self) -> bool: return self.correct_yielder != self.fcfs_yielder

class ScenarioConfig(BaseModel):
    name: str                              # ^[a-z][a-z0-9_]*$
    family: ScenarioFamily                 # filled by a mode="before" validator from FAMILY_BY_LEGACY_NAME when absent; absent + non-legacy name → ValueError "family is required for scenario name ..."
    static_obstacles: tuple[StaticObstacleConfig, ...] = ()
    parameters: HeadOnAsymmetricParams | None = None
    oracle: OracleConfig | None = None
    # existing cross-field validator additionally checks: obstacle ids unique across static + timed; every oracle robot id (correct, fcfs, feasible) in robots
```

- [ ] **Step 1: Write the failing tests** (append to `tests/unit/test_m6_config.py`; reuse `VALID_HEAD_ON`)

```python
def test_legacy_name_infers_family():
    cfg = ScenarioConfig.model_validate(VALID_HEAD_ON)
    assert cfg.family == "head_on"

def test_explicit_family_accepted_for_generated_name():
    cfg = ScenarioConfig.model_validate(
        {**VALID_HEAD_ON, "name": "head_on_asymmetric_w0p2_eopen_o0", "family": "head_on"}
    )
    assert cfg.family == "head_on"

def test_generated_name_without_family_rejected():
    with pytest.raises(ValidationError, match="family is required"):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "name": "head_on_asymmetric_x"})

def test_name_with_uppercase_or_dash_rejected():
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "name": "Head-On", "family": "head_on"})

def test_static_obstacle_parses_with_default_size():
    cfg = ScenarioConfig.model_validate({**VALID_HEAD_ON, "static_obstacles": [
        {"obstacle_id": "blocker_west", "pose": {"x": -1.85, "y": 0.0, "yaw_rad": 0.0}}]})
    assert cfg.static_obstacles[0].size.x_m == pytest.approx(0.3)
    assert cfg.static_obstacles[0].size.z_m == pytest.approx(0.5)

def test_timed_obstacle_size_defaults():
    cfg = ScenarioConfig.model_validate({**VALID_HEAD_ON, "timed_obstacles": [
        {"obstacle_id": "box", "asset": "dynamic_obstacle", "spawn_at_sec": 1.0,
         "pose": {"x": 0.0, "y": 0.0, "yaw_rad": 0.0}}]})
    assert cfg.timed_obstacles[0].size.y_m == pytest.approx(0.3)

def test_obstacle_size_must_be_positive():
    with pytest.raises(ValidationError):
        ObstacleSize(x_m=0.0)

def test_duplicate_obstacle_id_across_static_and_timed_rejected():
    with pytest.raises(ValidationError, match="obstacle_id"):
        ScenarioConfig.model_validate({**VALID_HEAD_ON,
            "static_obstacles": [{"obstacle_id": "box", "pose": {"x": 0.0, "y": 0.0, "yaw_rad": 0.0}}],
            "timed_obstacles": [{"obstacle_id": "box", "asset": "dynamic_obstacle", "spawn_at_sec": 1.0,
                                 "pose": {"x": 0.0, "y": 0.0, "yaw_rad": 0.0}}]})

def test_oracle_with_unknown_robot_rejected():
    with pytest.raises(ValidationError, match="robot_9"):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "oracle": {
            "correct_yielder": "robot_9", "fcfs_yielder": "robot_1",
            "feasible_yielders": ["robot_9"], "rationale": "x"}})

def test_oracle_feasible_yielders_must_contain_correct_yielder():
    with pytest.raises(ValidationError):
        OracleConfig(correct_yielder="robot_2", fcfs_yielder="robot_1",
                     feasible_yielders=("robot_1",), rationale="x")

def test_oracle_contrasts_fcfs_when_yielders_differ():
    oracle = OracleConfig(correct_yielder="robot_2", fcfs_yielder="robot_1",
                          feasible_yielders=("robot_2",), rationale="x")
    assert oracle.contrasts_fcfs is True

def test_parameters_round_trip_through_json_dump():
    cfg = ScenarioConfig.model_validate({**VALID_HEAD_ON, "parameters": {
        "blocker_west_m": 0.2, "blocker_east_m": None, "arrival_offset_m": 0.0}})
    again = ScenarioConfig.model_validate(cfg.model_dump(mode="json"))
    assert again == cfg
```

Import `ObstacleSize`, `OracleConfig` at the top of the test file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_m6_config.py -q`
Expected: the new tests FAIL (ImportError for `ObstacleSize`/`OracleConfig`, or `name` Literal rejections); every pre-existing test in the file still PASSES once imports are fixed — verify by temporarily commenting the import if needed.

- [ ] **Step 3: Implement the models** in `isaac/vgu_sim/config.py` exactly as in Interfaces. Notes: `name` validator uses `re.fullmatch(r"[a-z][a-z0-9_]*", v)`; `family` inference is a `@model_validator(mode="before")` classmethod that returns a new dict with `family` filled from `FAMILY_BY_LEGACY_NAME.get(data.get("name"))` when the key is missing and raises `ValueError(f"family is required for scenario name {name!r}")` when no legacy mapping exists; the existing `_cross_field_validation` gains the obstacle-id uniqueness check (message contains `obstacle_id`) and the oracle robot-membership check (message names the offending id). `OracleConfig` has a `model_validator(mode="after")` enforcing non-empty `feasible_yielders` containing `correct_yielder`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_m6_config.py tests/unit/test_generate_warehouse_map.py tests/unit/test_m6_acceptance_logging.py -q`
Expected: all new tests PASS; no previously passing test in these files regresses. Then `ruff check isaac/vgu_sim/config.py tests/unit/test_m6_config.py` → exit 0.

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/config.py tests/unit/test_m6_config.py
git commit -m "feat: add scenario family, obstacle geometry, parameters and oracle to M6 config"
```

---

### Task 2: Computed oracle module

**Files:**
- Create: `isaac/vgu_sim/family_oracle.py`
- Test: `tests/unit/test_family_oracle.py`

**Interfaces:**
- Consumes: `HeadOnAsymmetricParams`, `OracleConfig` (Task 1); `reasoning.rag.scene_geometry.SceneGeometry`, `park_offset_m`.
- Produces:

```python
SPAWN_OFFSET_M: float = 0.5          # spawn sits 0.5 m outside the corridor mouth
FEASIBILITY_MARGIN_M: float = 0.2
BOX_LENGTH_M: float = 0.3            # blocker size along the corridor axis
SIDE_ROBOT: dict[str, str] = {"west": "robot_1", "east": "robot_2"}

def load_scene_geometry(orchestrator_yaml: Path) -> SceneGeometry
    # yaml.safe_load(path)["scenario_geometry"] → SceneGeometry.model_validate
def required_room_m(geometry: SceneGeometry) -> float
    # park_offset_m(geometry) - geometry.corridor.half_length_m + geometry.robot.half_width_m + FEASIBILITY_MARGIN_M
def room_from_mouth_m(blocker_m: float | None) -> float | None
    # None → None; else SPAWN_OFFSET_M + blocker_m
def side_feasible(blocker_m: float | None, geometry: SceneGeometry) -> bool
def fcfs_yielder(arrival_offset_m: float) -> str
    # "robot_2" if arrival_offset_m > 0 else "robot_1"
def blocker_center_x_m(side: Literal["west", "east"], blocker_m: float, arrival_offset_m: float, geometry: SceneGeometry) -> float
    # h = geometry.corridor.half_length_m
    # west: -(h + SPAWN_OFFSET_M + blocker_m + BOX_LENGTH_M / 2)
    # east: +(h + SPAWN_OFFSET_M + arrival_offset_m + blocker_m + BOX_LENGTH_M / 2)
def compute_oracle(params: HeadOnAsymmetricParams, geometry: SceneGeometry) -> OracleConfig | None
    # None when neither side feasible. rationale templates:
    #   one side infeasible: f"{side} blocker {b:.2f} m behind the spawn leaves {room:.2f} m from the mouth < {req:.2f} m required; {robot} cannot park"
    #   both feasible:       f"both sides can park (required room {req:.2f} m); FCFS tiebreak yields {fcfs}"
```

- [ ] **Step 1: Write the failing tests** (`tests/unit/test_family_oracle.py`)

```python
from pathlib import Path
import pytest
from reasoning.rag.scene_geometry import SceneGeometry, park_offset_m
from isaac.vgu_sim.config import HeadOnAsymmetricParams
from isaac.vgu_sim import family_oracle as fo

ORCHESTRATOR_YAML = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")

@pytest.fixture
def geometry() -> SceneGeometry:
    return fo.load_scene_geometry(ORCHESTRATOR_YAML)

def test_load_scene_geometry_reads_m5_block(geometry):
    assert geometry.corridor.half_length_m == pytest.approx(1.0)
    assert park_offset_m(geometry) == pytest.approx(1.79, abs=0.02)

def test_required_room_matches_spec_value(geometry):
    assert fo.required_room_m(geometry) == pytest.approx(1.08, abs=0.02)

def test_open_side_is_feasible(geometry):
    assert fo.side_feasible(None, geometry) is True

def test_blocker_0p2_is_infeasible(geometry):
    assert fo.side_feasible(0.2, geometry) is False

def test_blocker_beyond_required_room_is_feasible(geometry):
    assert fo.side_feasible(0.6, geometry) is True   # 0.5 + 0.6 = 1.1 >= 1.08

def test_fcfs_tie_breaks_to_robot_1():
    assert fo.fcfs_yielder(0.0) == "robot_1"

def test_fcfs_later_arriver_yields():
    assert fo.fcfs_yielder(0.4) == "robot_2"

def test_west_blocker_center(geometry):
    assert fo.blocker_center_x_m("west", 0.2, 0.0, geometry) == pytest.approx(-1.85)

def test_east_blocker_center(geometry):
    assert fo.blocker_center_x_m("east", 0.2, 0.0, geometry) == pytest.approx(1.85)

def test_west_blocker_oracle_contrasts_fcfs(geometry):
    oracle = fo.compute_oracle(HeadOnAsymmetricParams(blocker_west_m=0.2), geometry)
    assert oracle.correct_yielder == "robot_2"
    assert oracle.feasible_yielders == ("robot_2",)
    assert oracle.fcfs_yielder == "robot_1"
    assert oracle.contrasts_fcfs is True
    assert "robot_1 cannot park" in oracle.rationale

def test_east_blocker_oracle_agrees_with_fcfs(geometry):
    oracle = fo.compute_oracle(HeadOnAsymmetricParams(blocker_east_m=0.2), geometry)
    assert oracle.correct_yielder == "robot_1"
    assert oracle.contrasts_fcfs is False

def test_open_variant_oracle_is_fcfs(geometry):
    oracle = fo.compute_oracle(HeadOnAsymmetricParams(), geometry)
    assert oracle.correct_yielder == "robot_1"
    assert set(oracle.feasible_yielders) == {"robot_1", "robot_2"}

def test_double_blocker_has_no_oracle(geometry):
    assert fo.compute_oracle(HeadOnAsymmetricParams(blocker_west_m=0.2, blocker_east_m=0.2), geometry) is None
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/unit/test_family_oracle.py -q` → ImportError on `family_oracle`.
- [ ] **Step 3: Implement** `isaac/vgu_sim/family_oracle.py` per Interfaces (Google docstrings on every public function; import `yaml`, `Path`, `Literal`).
- [ ] **Step 4: Run to verify pass** — same command → all PASS; `ruff check isaac/vgu_sim/family_oracle.py tests/unit/test_family_oracle.py` → 0.
- [ ] **Step 5: Commit** — `git add isaac/vgu_sim/family_oracle.py tests/unit/test_family_oracle.py && git commit -m "feat: add computed yield-feasibility oracle for the head-on family"`

---

### Task 3: Family generator + committed variant yamls + manifest

**Files:**
- Create: `isaac/scripts/generate_head_on_family.py`
- Create (generated, committed): `isaac/config/scenarios/family/head_on_asymmetric_w0p2_eopen_o0.yaml`, `…_wopen_e0p2_o0.yaml`, `…_wopen_eopen_o0.yaml`, `isaac/config/scenarios/family/family_manifest.csv`
- Test: `tests/unit/test_generate_head_on_family.py`

**Interfaces:**
- Consumes: Task 1 models; Task 2 `load_scene_geometry`, `compute_oracle`, `blocker_center_x_m`, `SPAWN_OFFSET_M`, `SIDE_ROBOT`.
- Produces:

```python
FAMILY_DIR = Path("isaac/config/scenarios/family")
BASE_SCENARIO = Path("isaac/config/scenarios/head_on_deadlock.yaml")
def variant_id(params: HeadOnAsymmetricParams) -> str          # "w0p2_eopen_o0"
def scenario_name(params: HeadOnAsymmetricParams) -> str       # "head_on_asymmetric_" + variant_id
def grid_v1() -> list[HeadOnAsymmetricParams]                  # 4 combos of {0.2, None}² × offset 0.0, west-major order
def build_variant(base: ScenarioConfig, params: HeadOnAsymmetricParams, geometry: SceneGeometry) -> ScenarioConfig | None
    # None when compute_oracle is None. Otherwise base with: name, family "head_on", robot_2 spawn x = SPAWN_OFFSET_M + half_length + arrival_offset (robot_1 unchanged), static_obstacles = [StaticObstacleConfig("blocker_west"/"blocker_east", Pose2D(center_x, 0.0, 0.0), ObstacleSize(0.3, 0.3, 0.5))] for each non-null side, parameters, oracle. Use base.model_copy(update=...) then re-validate via ScenarioConfig.model_validate(model_dump()).
def render_yaml(config: ScenarioConfig, geometry: SceneGeometry) -> str
    # header comment lines: generator name, "frozen at prereg-v1", the variant's parameters, room/required numbers, box near/centre/far faces; then yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False)
def manifest_rows(configs: list[ScenarioConfig]) -> list[dict[str, str]]
    # columns: name, variant, blocker_west_m, blocker_east_m, arrival_offset_m, correct_yielder, fcfs_yielder, feasible_yielders ("robot_1|robot_2"), contrasts_fcfs ("true"/"false"), tier ("T1" when both feasible else "T2a")
def write_family(out_dir: Path, geometry_yaml: Path) -> list[Path]   # writes yamls + manifest, prints skipped cells, returns written paths
def main(argv: list[str] | None = None) -> None
    # --out-dir (default FAMILY_DIR), --geometry (default ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml)
```

- [ ] **Step 1: Write the failing tests** (`tests/unit/test_generate_head_on_family.py`): `test_variant_id_prints_open_and_p_floats` (`HeadOnAsymmetricParams(blocker_west_m=0.2)` → `w0p2_eopen_o0`; defaults → `wopen_eopen_o0`), `test_grid_v1_has_four_cells`, `test_build_variant_skips_double_blocker`, `test_build_variant_west_places_static_blocker_at_minus_1p85` (obstacle_id `blocker_west`, `pose.x == -1.85`, size 0.3/0.3/0.5, robots' spawns unchanged), `test_build_variant_open_matches_base_geometry` (no static obstacles, same aisle_barrier, oracle correct_yielder robot_1), `test_render_yaml_round_trips` (`ScenarioConfig.model_validate(yaml.safe_load(text)) == config`), `test_manifest_rows_mark_tier_and_contrast` (3 rows; west → T2a/true, east → T2a/false, open → T1/false), `test_write_family_writes_three_yamls_and_manifest(tmp_path)`, and the staleness guard `test_committed_family_matches_generator_output(tmp_path)` — run `write_family(tmp_path, geometry_yaml)` and assert each committed file under `FAMILY_DIR` has identical text.
- [ ] **Step 2: Run to verify failure** — `pytest tests/unit/test_generate_head_on_family.py -q` → ImportError.
- [ ] **Step 3: Implement** the script (importable as `isaac.scripts.generate_head_on_family`; `sys.path` handling only if the existing `generate_warehouse_map.py` does it — mirror that file's conventions), then run `python isaac/scripts/generate_head_on_family.py` to write the three yamls + manifest. Inspect one yaml by eye: name, family, static obstacle at ±1.85, oracle block present, `parameters` block present with `null` for the open side.
- [ ] **Step 4: Run to verify pass** — the test file plus `pytest tests/unit/test_m6_config.py -q`; `ruff check isaac/scripts/generate_head_on_family.py tests/unit/test_generate_head_on_family.py` → 0.
- [ ] **Step 5: Commit** — `git add isaac/scripts/generate_head_on_family.py isaac/config/scenarios/family tests/unit/test_generate_head_on_family.py && git commit -m "feat: generate the head-on asymmetric scenario family with computed oracles"`

---

### Task 4: Bake static obstacles into per-scenario Nav2 maps

**Files:**
- Modify: `isaac/scripts/generate_warehouse_map.py` (`build_occupancy_grid` signature + `main`)
- Create (generated, committed): `ros2_ws/src/swarm_simulation/maps/warehouse_map_head_on_asymmetric_{w0p2_eopen_o0,wopen_e0p2_o0,wopen_eopen_o0}.{pgm,yaml}`
- Test: `tests/unit/test_generate_warehouse_map.py`

**Interfaces:**
- Consumes: `StaticObstacleConfig`, `ObstacleSize` (Task 1); family yamls (Task 3).
- Produces: `build_occupancy_grid(config, obstacles, resolution_m, aisle_barrier=None, static_obstacles: Sequence[StaticObstacleConfig] = ())` — each static obstacle marked via the existing `_mark_obstacle(grid, config, (pose.x, pose.y, size.x_m, size.y_m), resolution_m)` (yaw ignored, axis-aligned). `main` passes `scenario.static_obstacles`. Timed obstacles are never baked.

- [ ] **Step 1: Write the failing tests** (append; reuse the file's `_cell_at`, `load_scenario`, `MAPS_DIR` helpers): `test_static_obstacle_footprint_is_occupied` (grid from a `StaticObstacleConfig` at (-1.85, 0.0), size 0.3 → cells at (-1.85, 0.0), (-1.75, 0.1), (-1.95, -0.1) == 0), `test_static_obstacle_flanks_stay_free` (cells at (-1.85, ±0.45) == 255), `test_timed_obstacle_is_not_baked` (a scenario with only a timed obstacle produces a grid equal to the base grid), and a parametrized staleness guard `test_committed_family_maps_match_scenario_yamls` over `sorted(Path("isaac/config/scenarios/family").glob("head_on_asymmetric_*.yaml"))` mirroring `test_committed_head_on_deadlock_map_matches_scenario_yaml` (passes `aisle_barrier` and `static_obstacles`).
- [ ] **Step 2: Run to verify failure** — `pytest tests/unit/test_generate_warehouse_map.py -q` → TypeError on the new kwarg / missing map files.
- [ ] **Step 3: Implement** the kwarg and `main` change; generate the three maps: `for f in isaac/config/scenarios/family/head_on_asymmetric_*.yaml; do python isaac/scripts/generate_warehouse_map.py --out-dir ros2_ws/src/swarm_simulation/maps --scenario "$f"; done`. Confirm `warehouse_map_head_on_asymmetric_wopen_eopen_o0.pgm` is byte-identical to `warehouse_map_head_on_deadlock.pgm` (`cmp`) — it must be, since that variant adds no geometry.
- [ ] **Step 4: Run to verify pass** — the test file; `ruff check isaac/scripts/generate_warehouse_map.py tests/unit/test_generate_warehouse_map.py` → 0.
- [ ] **Step 5: Commit** — `git add isaac/scripts/generate_warehouse_map.py ros2_ws/src/swarm_simulation/maps tests/unit/test_generate_warehouse_map.py && git commit -m "feat: bake scenario static obstacles into per-scenario Nav2 maps"`

---

### Task 5: USD authoring of static/timed obstacle geometry, validation, family dispatch

**Files:**
- Modify: `isaac/vgu_sim/scenario_builder.py` (`build_scenario_stage`, `_author_obstacle`; add `_author_box`, `_author_static_obstacles`)
- Modify: `isaac/vgu_sim/validation.py` (add `validate_scenario_obstacles`)
- Modify: `isaac/vgu_sim/acceptance_logging.py:85` (`scenario.name == "head_on_deadlock"` → `scenario.family == "head_on"`)
- Modify: `isaac/vgu_sim/cmd_vel_watchdog_node.py:141` docstring only (`head_on_deadlock` → `head_on family`)
- Test: `tests/unit/test_scenario_builder.py`, `tests/unit/test_m6_validation.py`, `tests/unit/test_m6_acceptance_logging.py`

**Interfaces:**
- Consumes: Task 1 models.
- Produces:

```python
def _author_box(stage, path: str, translate, yaw_rad: float, size: ObstacleSize, color: tuple[float, float, float]) -> None
    # UsdGeom.Cube size 2.0, AddTranslateOp (x, y, size.z_m / 2), AddRotateZOp(degrees) only when yaw != 0, AddScaleOp (size.x_m/2, size.y_m/2, size.z_m/2), CreateDisplayColorAttr([color]), UsdPhysics.CollisionAPI.Apply
# static: /World/Scenario/StaticObstacles/<obstacle_id>, colour (0.5, 0.5, 0.5), active
# timed:  /World/DynamicObstacles/<obstacle_id> via _author_box, colour (0.8, 0.3, 0.3), then SetActive(False) as today
# build_scenario_stage always defines /World/Scenario/StaticObstacles (empty Xform when none); Metadata customData gains "family"
def validate_scenario_obstacles(stage, config: ScenarioConfig) -> None   # raises ValidationError naming the first missing prim path (static or timed)
```

Call `validate_scenario_obstacles` from wherever the builder's post-build validation runs with the config in hand (grep `validate_scenario_stage(` and `_validate_references(` — add it beside the latter inside `build_scenario_stage`, before `stage.Save()`), so a stale/missing prim fails the build, not the run.

- [ ] **Step 1: Write the failing tests**
  - `tests/unit/test_scenario_builder.py`: `test_scenario_builder_authors_static_obstacle_as_collision_cube(tmp_path)` — VALID_HEAD_ON + one static obstacle at (-1.85, 0.0), default size → prim `/World/Scenario/StaticObstacles/blocker_west` is a `UsdGeom.Cube`, has `UsdPhysics.CollisionAPI`, translate ≈ (-1.85, 0.0, 0.25), scale ≈ (0.15, 0.15, 0.25), `IsActive()`; `test_scenario_builder_authors_timed_obstacle_geometry_inactive(tmp_path)` — a timed obstacle becomes a Cube with CollisionAPI and scale ≈ (0.15, 0.15, 0.25) under `/World/DynamicObstacles/<id>` with `IsActive() is False`; `test_scenario_builder_defines_empty_static_obstacles_root(tmp_path)`.
  - `tests/unit/test_m6_validation.py`: `test_validate_scenario_obstacles_raises_for_missing_prim` (stage with `/World` only, config with one static obstacle → `ValidationError` mentioning `/World/Scenario/StaticObstacles/blocker_west`), `test_validate_scenario_obstacles_passes_when_prims_exist`.
  - `tests/unit/test_m6_acceptance_logging.py`: `test_build_record_marks_conflict_for_head_on_family_variant` — the file's `_head_on_scenario()` config re-validated with `name="head_on_asymmetric_w0p2_eopen_o0"`, `family="head_on"`; same states as the existing close-and-stopped test → `conflict_active is True`.
- [ ] **Step 2: Run to verify failure** — `pytest tests/unit/test_scenario_builder.py tests/unit/test_m6_validation.py tests/unit/test_m6_acceptance_logging.py -q` (these import `pxr`; if `pxr` is not importable in this environment, report NEEDS_CONTEXT rather than skipping).
- [ ] **Step 3: Implement** per Interfaces.
- [ ] **Step 4: Run to verify pass**; `ruff check isaac/vgu_sim tests/unit/test_scenario_builder.py tests/unit/test_m6_validation.py tests/unit/test_m6_acceptance_logging.py` → 0.
- [ ] **Step 5: Commit** — `git commit -m "feat: author static and timed obstacles as collision boxes and dispatch on scenario family"`

---

### Task 6: Repo-tracked VM launch script + reversed mock decision

**Ruling (2026-09-19): port and extend, do not write from scratch.**
`scripts/run_gemini_er2_demo.sh` on branch `feat/gemini-er2-backend` (265
lines) already provides the bring-up ordering, `localization:=camera`, the
recorder plus its fps re-timing caveat, `-w /ws` on every `docker exec`, the
key sourced inside the container, per-run log collection, and a backend switch
that restores `reasoning_backend_id` on exit (`trap cleanup EXIT` plus
`trap 'exit 130' INT TERM HUP`). Base `scripts/vm/fc_launch.sh` on it — two VM
launchers would drift — and add only what the family needs: `SCENARIO`
resolution across `isaac/config/scenarios/` and `isaac/config/scenarios/family/`,
`warehouse_map_<name>` with an existence check, spawn poses read from the
scenario yaml rather than hardcoded ±1.5, `MOCK_DECISION_FILE`, and `DRY_RUN=1`.

**Files:**
- Create: `scripts/vm/fc_launch.sh` (ported from `git show feat/gemini-er2-backend:scripts/run_gemini_er2_demo.sh`)
- Create: `config/mock_decisions/head_on_yield_robot_2.json`

**Interfaces:**
- Produces `scripts/vm/fc_launch.sh` — bash, `set -euo pipefail`, same six-stage bring-up as `fc_record_launch.sh` (Isaac → topics → M1 → Nav2 ×2 → M4 → M5, recorder optional), with:
  - `SCENARIO` (default `head_on_deadlock`): yaml resolved as `$REPO/isaac/config/scenarios/$SCENARIO.yaml` if it exists, else `$REPO/isaac/config/scenarios/family/$SCENARIO.yaml`, else exit 1 with a message; `MAP=/ws/ros2_ws/install/share/swarm_simulation/maps/warehouse_map_${SCENARIO}.yaml`; the script checks the map exists inside the container before launching Nav2.
  - Spawn poses for Nav2 read from the yaml (`docker_ros "python3 -c 'import yaml,sys; ...'"` printing `x y yaw` per robot id) — no hard-coded ±1.5.
  - `RECORD=0|1` (default 0) enables the recorder stage exactly as in `fc_record_launch.sh` (`REC_SEC`, fps probe).
  - `MOCK_DECISION_FILE` (optional): when set, exported into the M5 launch environment as the variable the orchestrator reads for the mock backend — find the exact name and the backend switch by grepping `ros2_ws/src/swarm_orchestrator` and `config/models.yaml` for `mock_decision`/`VGU_MOCK` and mirror them; document both in the script header.
  - `VGU_RUN_ID=${STAMP}` and `.env` sourcing inside the container unchanged; logs `/tmp/fc_${STAMP}_*.log` inside the container as today; prints `STAMP`, `SCENARIO`, `MAP`, `M5_LOG`.
  - `DRY_RUN=1` prints every command instead of executing it (so the script can be checked without the VM).
- Produces `config/mock_decisions/head_on_yield_robot_2.json` — copy of `head_on_yield.json` with `involved_robots: ["robot_2", "robot_1"]` and the justification saying robot_2 yields.

- [ ] **Step 1: Fetch the VM scripts to the scratchpad and read them** (both), plus `config/mock_decisions/head_on_yield.json`, and grep the mock-backend switch.
- [ ] **Step 2: Write the script and the json.** Test: `bash -n scripts/vm/fc_launch.sh`; `DRY_RUN=1 SCENARIO=head_on_asymmetric_w0p2_eopen_o0 bash scripts/vm/fc_launch.sh` prints a Nav2 line with `x:=-1.5` for robot_1 and `map_yaml:=…warehouse_map_head_on_asymmetric_w0p2_eopen_o0.yaml` (in dry-run mode the yaml is parsed locally with the host `python3`); `SCENARIO=nope` exits non-zero. `python -c "import json; json.load(open('config/mock_decisions/head_on_yield_robot_2.json'))"`.
- [ ] **Step 3: Commit** — `git add scripts/vm/fc_launch.sh config/mock_decisions/head_on_yield_robot_2.json && git commit -m "feat: add scenario-parametrised VM launch script and reversed mock decision"`

---

### Task 7: VM sync, USD + map build, T1 control run

**Files:** none in the repo except the evidence report `docs/reports/2026-09-18-head-on-family-validity.md` (created here, extended by Tasks 8–9). VM evidence under `/home/ubuntu/vgu-vlm-swarm/data/logs/family_check_20260918/` (git-ignored).

- [ ] **Step 1: Sync** the worktree to the VM: `rsync -az --delete --exclude .git --exclude .worktrees --exclude .superpowers --exclude .venv --exclude data/logs --exclude 'isaac/scenarios/*.usd' -e "ssh -i <key>" ./ ubuntu@34.68.133.240:/home/ubuntu/vgu-vlm-swarm/`. Confirm `/home/ubuntu/vgu-vlm-swarm/isaac/config/scenarios/family/` lists the three yamls and `scripts/vm/fc_launch.sh` is executable.
- [ ] **Step 2: Build** — colcon `swarm_simulation` (maps install) in the container; then verify `/ws/ros2_ws/install/share/swarm_simulation/maps/warehouse_map_head_on_asymmetric_w0p2_eopen_o0.yaml` exists. Build the USD stages for the three variants with Isaac's python: find the builder entry point (`ls isaac/scripts`, `grep -l build_scenario_stage isaac/scripts/*.py`) and run it as the existing `head_on_deadlock` stage was built (same env as `scripts/run_simulation.sh`: `PYTHONPATH=$REPO`, `/home/ubuntu/IsaacSim/python.sh`). Confirm `isaac/scenarios/head_on_asymmetric_*.usd` exist and, for the west variant, `grep -c StaticObstacles` on the usda/usd text (or a small pxr script) finds `blocker_west`.
- [ ] **Step 3: Control run** — `SCENARIO=head_on_asymmetric_wopen_eopen_o0 MOCK_DECISION_FILE=/ws/config/mock_decisions/head_on_yield.json bash scripts/vm/fc_launch.sh`; wait until the M5 log shows both `base_mission … COMPLETED` (poll `/tmp/fc_<STAMP>_m5.log` inside the container every 60 s, ≤ 15 min), then stop everything (`pkill -f "[r]os2 launch"`, kill Isaac's `python.sh`, `sudo docker restart vgu_ros`). Copy the M5/M4/Isaac logs and `data/logs/m5_decisions/` artifacts for this `run_id` to `data/logs/family_check_20260918/control_wopen_eopen/` on the VM host.
- [ ] **Step 4: Report** — create `docs/reports/2026-09-18-head-on-family-validity.md` (doc_style header: Prepared 2026-09-18, revision history) with a "T1 control" section: STAMP, decisions count, dispatches, time to both arrivals, any anomaly. Commit: `git add docs/reports/2026-09-18-head-on-family-validity.md && git commit -m "docs: record head-on family T1 control run"`.

---

### Task 8: Authoring-time validity pairs (both T2a variants)

**Files:** extend `docs/reports/2026-09-18-head-on-family-validity.md`.

- [ ] **Step 1:** For each of `head_on_asymmetric_w0p2_eopen_o0` and `head_on_asymmetric_wopen_e0p2_o0`, run twice with the mock backend: `MOCK_DECISION_FILE=/ws/config/mock_decisions/head_on_yield.json` (robot_1 yields) and `…/head_on_yield_robot_2.json` (robot_2 yields). Each run: launch via `scripts/vm/fc_launch.sh`, wait ≤ 15 min, capture M5 log + M4 log + decision artifacts to `data/logs/family_check_20260918/<variant>/<yielder>/`, then full stop + `docker restart`.
- [ ] **Step 2:** Judge each run from the M5 attach/resolve log lines and M4 status messages: **oracle yielder run** must end with both `base_mission COMPLETED`; **other run** must show the yield's backup ending `FAILED` or `TIMED_OUT` (quote the line) — whether M5 then recovers is recorded but is not the criterion. If the blocked yield *succeeds* (robot parks despite the box) the variant fails validity: record it, do not re-author — stop with BLOCKED and the evidence.
- [ ] **Step 3:** Append a "Validity pairs" table (variant × forced yielder → outcome, quoted evidence line, run_id) to the report; commit `docs: record head-on family validity pairs`.

---

### Task 9: Recorded gpt-4o run on the blocked variant — RQ5 recovery episode

**Framing (ruling, 2026-09-19).** This run is an **RQ5 closed-loop recovery
episode**, NOT a T2a oracle-agreement cell. Per the design review
`docs/superpowers/specs/2026-09-19-head-on-asymmetric-family-design-review.md`
(both findings independently verified), the reasoner cannot observe which side
is blocked — `reasoning/vlm/prompt_builder.py` renders no obstacle channel and
the image is measured non-decisive — and cannot express a yielder choice, since
`involved_robots` order is a constant in practice (44/44 yields list `robot_1`
first). So the model's *first* answer carries no information about retreat
space, and nothing in this task may be reported as oracle agreement. What the
episode does measure is what happens **after** the blocked maneuver fails:
whether the failure context reaches the next decision and whether the loop
recovers. Record whatever happens either way.

Expect `reverse` as a plausible first strategy, not only `yield` — on the
simpler scenario the live model chose `deadlock`/`reverse` first, and `reverse`
is dispatched symmetrically so it cannot resolve a two-robot head-on at all.
Keep "failed because the strategy cannot work" separate from "failed because
the chosen side has no retreat space" in the write-up; conflating them is the
one analysis error this episode can produce.

**Files:** extend the report; deliver MP4 + timeline under `data/logs/recordings/2026-09-18/` in the worktree (git-ignored).

- [ ] **Step 1:** Two recorded runs on `head_on_asymmetric_w0p2_eopen_o0` (no mock file → openai backend from `/ws/.env`), each `RECORD=1 REC_SEC=780`, each stopped fully before the next starts (`pkill -f "[r]os2 launch"`, kill Isaac's `python.sh`, `sudo docker restart vgu_ros`):
  - **Run A — modality OFF** (`prompt_static_obstacles: false`, the default): the information-bound condition, comparable with every run collected so far.
  - **Run B — modality ON** (`prompt_static_obstacles: true` with the blocker mirrored into `static_obstacles`, plus the `yield_robot` field from Task 11 live in both runs): the spatial-reasoning condition.

  Capture both run_ids and keep their artifacts in separate directories. Neither run's first answer is evidence on its own — the **contrast between A and B** is the result.
- [ ] **Step 2:** Pull the MP4, retime with ffmpeg as in the 2026-09-17 recordings (`setpts=(stamped/achieved)*PTS`, achieved fps from the recorder log), and build a timeline (UTC, elapsed, decision → strategy/involved order → executed → outcome) from the decision artifacts for this run_id. Save `data/logs/recordings/2026-09-18/run1_rq5_w0p2_eopen_annotated.mp4` + `README.md` (timeline, counts: analyses, dispatches, `none`, failure-context blocks seen).
- [ ] **Step 3:** Append an "RQ5 recovery run (gpt-4o)" section to the report: the first strategy and which robot it targeted, whether the maneuver failed and how (`FAILED`/`TIMED_OUT`, quoted), whether the previous-attempt block appeared in the next prompt, what the second decision was, and whether both robots reached their goals. State explicitly that first-answer yielder identity is **not** evidence of spatial reasoning here, and why. Commit `docs: record RQ5 recovery run on the blocked head-on variant`.

---

### Task 10: Spec and notes sync

**Files:**
- Modify: `docs/specs/module6_simulation.md` (scenario list: family + generator; obstacle geometry now real collision boxes; static_obstacles/oracle/parameters schema fields; per-scenario maps)
- Modify: `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` (revision history line rev 8.6: T1/T2a realised as the `head_on_asymmetric` family; battery section points at the family spec and manifest; FCFS tie → lexicographic note; **modality table gains `static_obstacles` (default off) alongside `pairwise_geometry`, and the decision schema gains `yield_robot`** — both are Arm A changes and must be named in the decoding/prompt pre-registration, with the note that all artifacts before 2026-09-19 were collected without them)
- Modify: `docs/specs/module2_vlm.md` (new FR for `yield_robot` and for the static-obstacle modality) and `docs/specs/module5_orchestrator.md` (new FR for `prompt_static_obstacles` / `static_obstacles` config keys)
- Modify: `docs/implementation_notes.md` (M6 entry: family + obstacle geometry + maps, commits; M5/M2 entry: validity pairs and gpt-4o run outcome, link the report)
- Modify: `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md` (Status → implemented, link plan + report)

Additional corrections required by the 2026-09-19 design review (ruling):

- `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md`: qualify the **Status** line — the family realizes T1 and the T2a *geometry*, but the T2a oracle-agreement *claim* is not answerable by Arm A as currently prompted. Resolve the review banner at the top of that spec (it currently says "the owner decides", left open) by recording the decision actually taken: engineering proceeds; the paired variants are reported as an order-vs-scene demonstration; the `yield_robot` field and obstacle prompt modality are escalated to the owner as prerequisites for the Phase 1 paired-seed matrix, not for this plan.
- Record in the notes that the frozen `oracle:` blocks are **inert data** — verified consumed by nothing but config validation — so a frozen `correct_yielder` cannot silently become an Arm A score.
- Correct the review's one wrong claim in `docs/superpowers/specs/2026-09-19-head-on-asymmetric-family-design-review.md`: `tests/unit/test_m6_config.py::test_head_on_yaml_round_trip` is a genuine pre-existing baseline failure, **not** part of this work — `df047ae` does not touch the barrier assertions (`git log -S` traces them to `aa80d96` / `e7764bc` on `main`). Append the correction; do not rewrite the reviewer's text.
- Note the paired T2a variants' value as a pre-registered negative result: `w0p2_eopen_o0` (`correct_yielder: robot_2`, default order wrong) vs `wopen_e0p2_o0` (`correct_yielder: robot_1`, default order right), matched geometry — a clean demonstration that Arm A's yielder selection is order-driven rather than scene-driven, requiring no new features.

- [ ] **Step 1:** Read the maintenance rules at the top of `docs/implementation_notes.md` and the header conventions in `docs/standards/doc_style.md`; read the report from Tasks 7–9 and the 2026-09-19 design review.
- [ ] **Step 2:** Make the edits; every claim links a commit or the report; absolute dates.
- [ ] **Step 3:** Run `pytest tests/unit -q | tail -3` and confirm the failure count is exactly the 13 baseline failures listed in Global Constraints.
- [ ] **Step 4:** Commit `docs: sync M6 spec, rev-8 battery and notes for the head-on family`.

---

## Observability channels (owner-approved 2026-09-19)

The owner approved building both channels the design review identified as
missing, as **declared modalities run both ways**. Execution order is therefore
**6 → 7 → 8 → 11 → 12 → 9 → 10**: the channels must exist before Task 9's runs,
and Task 9 then records the blocked variant twice (modality off = the
information bound, comparable with every run collected so far; modality on =
the spatial-reasoning condition T2a was meant to be).

Both default to **OFF**. That is load-bearing for the pre-registration: every
artifact collected to date was produced without them, and an ON default would
silently break comparability with the 524 existing decisions.

### Task 11: Explicit `yield_robot` decision field

**Files:**
- Modify: `reasoning/vlm/models.py` (`CongestionDecision`)
- Modify: `reasoning/vlm/prompt_builder.py` (output-format lines)
- Modify: `reasoning/rag/command_grounder.py` (~line 146)
- Test: `tests/unit/test_vlm_models.py` (or the file that covers `CongestionDecision` — grep first), `tests/unit/test_prompt_builder.py`, `tests/unit/test_command_grounder.py`

**Why:** `command_grounder.py:146` (`robot_ids = decision.involved_robots`) makes list position the yielder channel, and list position is a measured constant — 44/44 yields listed `robot_1` first across 524 artifacts. Until the model has a named field, the battery measures an ordering convention rather than a choice.

**Interfaces produced:**

```python
# reasoning/vlm/models.py
class CongestionDecision(BaseModel):
    yield_robot: str | None = None   # only meaningful when strategy == "yield"
    # model_validator(mode="after"): if yield_robot is not None it MUST appear in
    # involved_robots — raise ValueError naming both. A decision that names a
    # yielder outside the involved set is a contract violation that would
    # mis-dispatch; M2's bounded-retry loop is the right place to catch it.
    # Do NOT require yield_robot when strategy == "yield" (older artifacts and
    # models that omit it must still parse).

# reasoning/rag/command_grounder.py
def resolve_robot_order(decision: CongestionDecision) -> list[str]
    # yield_robot first when set and present, remaining involved_robots in their
    # original order; otherwise involved_robots unchanged (backward compatible).
```

- [ ] **Step 1: Write the failing tests.** Schema: `yield_robot` defaults to `None`; accepts a member of `involved_robots`; raises when naming a non-member; a decision with `strategy="yield"` and no `yield_robot` still parses. Grounder: `resolve_robot_order` puts `yield_robot` first when it is listed second; returns `involved_robots` unchanged when `yield_robot is None` (the backward-compat case that protects every historical artifact). Prompt: the rendered output-format section names `yield_robot` and says it is null unless the strategy is `yield`.
- [ ] **Step 2: Run them and record the failures.**
- [ ] **Step 3: Implement.** In the prompt, add one output-format bullet — `- "yield_robot": the robot that should yield, or null when the strategy is not "yield"` — and extend the `<think>` step to ask which robot should yield and why. Do not describe *how* to choose; that is the thing being measured. Wire `resolve_robot_order` at the existing `robot_ids = decision.involved_robots` site and nowhere else.
- [ ] **Step 4: Run to verify pass**, plus `pytest tests/unit/test_command_grounder.py tests/unit/test_prompt_builder.py -q` and `ruff check` on the touched files (exit 0).
- [ ] **Step 5: Commit** `feat: add explicit yield_robot field to the congestion decision`.

### Task 12: Static-obstacle prompt modality

**Files:**
- Modify: `reasoning/vlm/models.py` (`StaticObstacleInput`, `ReasonerRequest`)
- Modify: `reasoning/vlm/prompt_builder.py` (slot, renderer, ON/OFF wording)
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` (`OrchestratorConfig`)
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` (`build_reasoner_request`)
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` (~line 335)
- Modify: `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`
- Test: `tests/unit/test_prompt_builder.py`, `tests/unit/test_reasoning_pipeline.py`, `tests/unit/test_orchestrator_models.py` (grep for the files that cover these)

**Why:** `grep -niE "obstacle|blocker|barrier|wall|rack|occupanc" reasoning/vlm/prompt_builder.py` returns nothing — the reasoner has no channel through which a parked blocker could be perceived, and the image is measured non-decisive. Follow the `include_pairwise_geometry` / `prompt_pairwise_geometry` pattern exactly (rev 8.5); it is the established modality shape in this codebase.

**Do not leak the answer.** Render obstacles as world-frame boxes only — id, centre, extent — the same way robot states are rendered as bare coordinates. The model must derive "that box blocks a retreat" itself. Any wording naming a robot, a retreat, or a blocked side invalidates the condition.

**Interfaces produced:**

```python
# reasoning/vlm/models.py
class StaticObstacleInput(BaseModel):     # frozen
    obstacle_id: str = Field(min_length=1)
    x: float
    y: float
    size_x_m: float = Field(gt=0)
    size_y_m: float = Field(gt=0)

class ReasonerRequest(BaseModel):
    static_obstacles: list[StaticObstacleInput] = []
    include_static_obstacles: bool = False     # default OFF — preserves comparability

# reasoning/vlm/prompt_builder.py
def format_static_obstacle_lines(obstacles: list[StaticObstacleInput]) -> list[str]
    # "blocker_west: centre (-1.85, 0.00) m, extent 0.30 x 0.30 m"
# {static_obstacle_block} slot; _OBSTACLES_ON / _OBSTACLES_OFF wording dicts.
# ON adds a clause stating the list is the complete set of fixed obstacles in
# the scene and that a robot can neither occupy nor drive through one.
# OFF renders the block as "- (not provided)" and adds no clause, leaving the
# prompt byte-identical to today's apart from that single line.

# M5
OrchestratorConfig.prompt_static_obstacles: bool = False
OrchestratorConfig.static_obstacles: tuple[StaticObstacleInput, ...] = ()
build_reasoner_request(..., static_obstacles=..., include_static_obstacles=...)
```

- [ ] **Step 1: Write the failing tests.** Renderer output for one and for several obstacles, sorted by `obstacle_id` for determinism. Prompt: with the modality ON the block lists each obstacle and the ON clause is present; with it OFF the block reads `- (not provided)` and the ON clause is absent; **an OFF prompt is byte-identical to a prompt built without the feature** (pin this — it is the comparability guarantee). Pipeline: `build_reasoner_request` forwards both fields. M5 config: both keys parse with the documented defaults, and `static_obstacles` accepts the mirrored mapping from yaml.
- [ ] **Step 2: Run them and record the failures.**
- [ ] **Step 3: Implement.** In `orchestrator.yaml`, add `prompt_static_obstacles: false` and a commented `static_obstacles:` block carrying the family blocker (`blocker_west`, centre `-1.85, 0.0`, extent `0.3 x 0.3`) with a comment saying it mirrors the scenario yaml the way `scenario_geometry` mirrors the aisle barrier, and that it must be set per scenario.
- [ ] **Step 4: Run to verify pass**; `ruff check` on the touched files (exit 0); confirm no previously passing test in the touched files regresses.
- [ ] **Step 5: Commit** `feat: add static-obstacle prompt modality behind a default-off flag`.

---

### Task 13: One-shot mock decisions (unblocks Tasks 8 and 9)

**Why this exists.** Task 7's T1 control run failed its criterion and the
run's report concluded an M4 defect. That conclusion is wrong and must be
corrected. The real cause is the harness: `build_backend`
(`reasoning/vlm/backend_factory.py:73-81`) wires `VGU_MOCK_DECISION_FILE` into
`MockBackend(response_text=...)`, which returns **the same decision on every
call**. So all 16 stall-triggered analyses replayed `deadlock / yield
[robot_1, robot_2]`, re-commanding both robots forever; each new command
cancels the target's in-flight navigate goal via the documented ownership
handoff (`_on_command` → `_adapter.cancel`), so `robot_1` never got a window
longer than a median 0.70 s when it needs ~17 s to cover 3.73 m at 0.22 m/s.
A live backend does not produce that stream — run 5 (2026-09-17, gpt-4o)
resolved in 1 dispatch with 31 `none` answers, because the failure-context
loop reports `congestion_detected=false` once the scene clears. A frozen mock
structurally cannot. Nothing in Tasks 1–6 is implicated, and the M4 resume
race is real but latent (it needs a pathological repeat-command stream).

**Files:**
- Modify: `reasoning/vlm/backend_factory.py` (`build_backend`, mock branch)
- Create: `config/mock_decisions/head_on_yield_once.json`, `config/mock_decisions/head_on_yield_robot_2_once.json`
- Modify: `docs/reports/2026-09-18-head-on-family-validity.md` (correct the root cause)
- Test: `tests/unit/test_vlm_config.py` or whichever file covers `build_backend` (grep first)

**Interfaces produced:**

```python
# build_backend, mock branch: VGU_MOCK_DECISION_FILE may now hold EITHER
#   - a single decision object  -> MockBackend(response_text=<file text>)   [unchanged]
#   - a JSON array of decisions -> MockBackend(response_sequence=[json.dumps(d) for d in arr])
# MockBackend already implements response_sequence and HOLDS THE LAST ENTRY once
# exhausted (reasoning/vlm/mock_backend.py:37-39) — so a 2-entry array is all that
# is ever needed regardless of how many analyses run. Do NOT pad the array, do not
# add an index reset, do not change mock_backend.py.
# An empty array is a config error: raise ValueError naming the file.
```

Each `*_once.json` is `[<the existing single decision verbatim>, <the no-congestion decision>]`, where the second entry matches `_DEFAULT_RESPONSE` in `reasoning/vlm/mock_backend.py` (`congestion_detected: false`, `type: "none"`, `strategy: "none"`, `involved_robots: []`). **Leave `head_on_yield.json` and `head_on_yield_robot_2.json` exactly as they are** — Task 8's forced-yielder-*fails* arm still wants the frozen form, since a yield that never completes produces no resolution for a `none` to describe.

- [ ] **Step 1: Write the failing tests.** A single-object file still yields one repeated response (backward compatibility — pin this). An array file yields entry 1 on the first call, entry 2 on the second, and **entry 2 again on the third and tenth** call. An empty array raises `ValueError` naming the file. A missing file still raises `FileNotFoundError` as today.
- [ ] **Step 2: Run them and record the failures.**
- [ ] **Step 3: Implement**, then validate both new json files parse and that each is a 2-element array whose first element equals the corresponding existing single-decision file.
- [ ] **Step 4: Run to verify pass**; `ruff check` on the touched files adds no new findings (`reasoning/rag/command_grounder.py:65` carries a pre-existing error — leave it).
- [ ] **Step 5: Correct the research artifact.** In `docs/reports/2026-09-18-head-on-family-validity.md`, amend the "Root cause" section: the control run failed because a frozen mock cannot represent a scene that changes, not because of an M4 defect. Keep the original forensics (the resume/cancel counts are accurate and worth preserving) but re-label them as the *mechanism* by which the repeated commands stopped `robot_1`, with the frozen mock as the *cause*. Record that the M4 resume race remains a real but latent issue needing its own investigation, and add a revision-history entry. Do not delete the original text — mark it superseded, per the project's documentation rules.
- [ ] **Step 6: Commit** `fix: allow scripted mock decision sequences and correct the control-run finding`.

**Verification gate for Task 8.** When Task 8 next runs a one-shot arm, check in its artifacts that `robot_1` receives an **uninterrupted navigation window longer than 17 s** after the last command resolves. If it does not, the M4 resume race is *not* latent and Tasks 8/9 stop until it is fixed — report rather than tune.
