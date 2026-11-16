import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)


class Pose2D(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    x: float
    y: float
    yaw_rad: float


class Goal2D(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    x: float
    y: float


class RobotScenarioConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    robot_id: str
    marker_id: int
    spawn: Pose2D
    goal: Goal2D
    initial_task: str
    # B2-visual pair (priority_visual_r1/r2): a pallet/load prop rigidly
    # mounted behind the chassis (isaac.vgu_sim.load_prop_asset), with no
    # registry or text-channel signal. Additive and off by default, so every
    # existing scenario dump stays byte-identical (see `_omit_unset_loaded`).
    loaded: bool = False

    @field_validator("robot_id")
    @classmethod
    def _robot_id_format(cls, v: str) -> str:
        if not re.match(r"^robot_[1-9][0-9]*$", v):
            raise ValueError(f"robot_id must match robot_N (N >= 1); got {v!r}")
        return v

    @field_validator("marker_id")
    @classmethod
    def _marker_id_range(cls, v: int) -> int:
        if not (1 <= v <= 49):
            raise ValueError(f"marker_id must be in 1..49; got {v}")
        return v

    @model_serializer(mode="wrap")
    def _omit_unset_loaded(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # Every scenario authored before `loaded` existed, and every robot
        # that does not carry a load, dumps with no `loaded` key -- the same
        # byte-for-byte family-generator discipline as `OracleConfig`'s
        # ordering fields.
        data = handler(self)
        if data.get("loaded") is False:
            data.pop("loaded", None)
        return data


class ObstacleSize(BaseModel):
    """Bounding-box size in meters for a static or timed obstacle."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    x_m: float = Field(default=0.3, gt=0)
    y_m: float = Field(default=0.3, gt=0)
    z_m: float = Field(default=0.5, gt=0)


class StaticObstacleConfig(BaseModel):
    """A fixed-pose obstacle present for the entire scenario duration."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    obstacle_id: str = Field(min_length=1)
    pose: Pose2D
    size: ObstacleSize = ObstacleSize()


# Built-in timed-obstacle assets, selected by name in `TimedObstacleConfig.asset`.
# Any other value -- every scenario authored before these existed carries a file
# name such as `dynamic_obstacle.usd`, which was never referenced -- keeps the
# legacy authoring: a red collision box of `size`.
ROBOT_VISUAL_NO_MARKER_ASSET = "robot_visual_no_marker"
STATIC_BOX_ASSET = "static_box"
# Uniform scale of the marker-less robot visual. The tracked robots' lidar scans
# a single plane at 0.182 m (base_scan in turtlebot3_burger.urdf). At scale 1
# the only burger structure at that height is the 7 cm LDS head, which cannot
# close a passage a robot can drive through, so Nav2 would plan past it. At
# 1.82 the plane cuts the middle waffle plate (0.095-0.105 m unscaled, i.e.
# 0.173-0.191 m scaled, 9 mm margin each side), about 0.25 m wide, like a box.
# tests/unit/test_blocked_path_scenarios.py re-derives the band from the STL.
ROBOT_VISUAL_NO_MARKER_SCALE = 1.82
BUILTIN_TIMED_OBSTACLE_ASSETS: frozenset[str] = frozenset(
    {ROBOT_VISUAL_NO_MARKER_ASSET, STATIC_BOX_ASSET}
)


class TimedObstacleConfig(BaseModel):
    """An obstacle activated at `spawn_at_sec` and, optionally, removed later.

    `asset` selects what is authored: `robot_visual_no_marker` (the robot's
    visual meshes with no ArUco marker and no physics articulation, so M1
    cannot track it), `static_box` (a grey box of `size`, the look of a
    static obstacle), or any other label (legacy: a red box of `size`; the
    label is carried but never referenced). Scenario tests pin the exact
    built-in names, since a misspelt one silently falls back to the red box.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    obstacle_id: str
    asset: str
    spawn_at_sec: float
    remove_at_sec: float | None = None
    pose: Pose2D
    size: ObstacleSize = ObstacleSize()

    @field_validator("spawn_at_sec")
    @classmethod
    def _spawn_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"spawn_at_sec must be >= 0; got {v}")
        return v

    @model_validator(mode="after")
    def _remove_after_spawn(self) -> "TimedObstacleConfig":
        if self.remove_at_sec is not None and self.remove_at_sec <= self.spawn_at_sec:
            raise ValueError(
                f"remove_at_sec ({self.remove_at_sec}) must be > spawn_at_sec ({self.spawn_at_sec})"
            )
        return self


class AisleBarrierConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    effective_width_m: float
    center_x_m: float
    length_m: float

    @field_validator("effective_width_m")
    @classmethod
    def _effective_width_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"effective_width_m must be > 0; got {v}")
        return v

    @field_validator("length_m")
    @classmethod
    def _length_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"length_m must be > 0; got {v}")
        return v


class LoopMapConfig(BaseModel):
    """A second E-W aisle plus one new N-S connector, closing a cycle.

    The existing N-S strip (`\\|x\\| <= nominal_aisle_width_m / 2`) already
    connects the primary aisle to any y, for free, so only one new connector
    is authored (east of the primary aisle's junction square); the second
    aisle and the connector are carved out of the NE rack block only
    (`docs/reports/2026-10-02-loop-preemption-smoke.md`, "Minimal loop
    topology"). NW/SE/SW rack blocks are untouched.

    `connector_remnant_height_m` is lower than the shared warehouse's 0.9 m
    rack height by design: at the standard height the connector-flanking
    rack remnant's camera shadow blankets most of the second aisle (same
    report, "Visibility"); a low divider (still above the 0.182 m lidar
    scan plane, so Nav2 still sees it as solid) keeps the aisle visible to
    the overhead camera.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    second_aisle_center_y_m: float
    second_aisle_width_m: float = Field(gt=0)
    second_aisle_x_min_m: float
    second_aisle_x_max_m: float
    connector_center_x_m: float
    connector_width_m: float = Field(gt=0)
    connector_remnant_height_m: float = Field(default=0.3, gt=0)

    @field_validator("second_aisle_center_y_m")
    @classmethod
    def _second_aisle_north_of_primary(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"second_aisle_center_y_m must be > 0; got {v}")
        return v

    @model_validator(mode="after")
    def _second_aisle_extent_increasing(self) -> "LoopMapConfig":
        if self.second_aisle_x_min_m >= self.second_aisle_x_max_m:
            raise ValueError(
                "second_aisle_x_min_m must be < second_aisle_x_max_m; got "
                f"{self.second_aisle_x_min_m} >= {self.second_aisle_x_max_m}"
            )
        return self

    @model_validator(mode="after")
    def _connector_inside_second_aisle_extent(self) -> "LoopMapConfig":
        half = self.connector_width_m / 2.0
        c = self.connector_center_x_m
        if not (self.second_aisle_x_min_m <= c - half and c + half <= self.second_aisle_x_max_m):
            raise ValueError(
                "connector_center_x_m +- connector_width_m/2 must sit inside "
                f"[second_aisle_x_min_m, second_aisle_x_max_m]; got centre {c}, "
                f"half-width {half}, extent [{self.second_aisle_x_min_m}, "
                f"{self.second_aisle_x_max_m}]"
            )
        return self

    @model_validator(mode="after")
    def _second_aisle_south_edge_above_primary_aisle(self) -> "LoopMapConfig":
        base_half = WarehouseConfig().nominal_aisle_width_m / 2.0
        south_edge = self.second_aisle_center_y_m - self.second_aisle_width_m / 2.0
        if south_edge <= base_half:
            raise ValueError(
                "second aisle south edge "
                f"({south_edge}) must sit north of the primary aisle "
                f"(half-width {base_half}), leaving room for the connector band"
            )
        return self


class RackClearanceConfig(BaseModel):
    """An axis-aligned rectangle cleared of the four shared rack quadrants.

    v3 S1b (sparse-warehouse regime variant, prereg-v3 R3.6/R3.6a) keeps the
    S1 tracked-band footprint but removes its racks: every rack quadrant is
    cut back to its part OUTSIDE this rectangle, so the band becomes open
    floor bounded by the rack remnants at its edges. The scene's own rack
    islands are ordinary `static_obstacles`. Like the loop map, the shared
    warehouse asset is never edited: the scenario deactivates the four
    `/World/Environment/RackBlocks/*` cubes with an `over` and re-authors the
    remnants (`rack_clearance_remnants`), and the Nav2 map generator clears
    the identical cells.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    x_min_m: float
    x_max_m: float
    y_min_m: float
    y_max_m: float

    @model_validator(mode="after")
    def _extent_increasing_and_inside_the_walls(self) -> "RackClearanceConfig":
        if self.x_min_m >= self.x_max_m or self.y_min_m >= self.y_max_m:
            raise ValueError(
                "rack_clearance extents must increase; got "
                f"x [{self.x_min_m}, {self.x_max_m}], y [{self.y_min_m}, {self.y_max_m}]"
            )
        warehouse = WarehouseConfig()
        half_w = warehouse.width_m / 2.0
        half_d = warehouse.depth_m / 2.0
        if not (
            -half_w < self.x_min_m and self.x_max_m < half_w
            and -half_d < self.y_min_m and self.y_max_m < half_d
        ):
            raise ValueError(
                "rack_clearance must sit strictly inside the warehouse walls "
                f"(|x| < {half_w}, |y| < {half_d})"
            )
        return self


RackRect = tuple[str, float, float, float, float]


def rack_quadrant_rects(warehouse: "WarehouseConfig") -> list[RackRect]:
    """Return the four shared rack quadrants as `(name, x0, x1, y0, y1)`.

    Same geometry as `warehouse_builder._build_rack_blocks` and
    `generate_warehouse_map._rack_block_obstacles`: four blocks leave a cross
    aisle of `nominal_aisle_width_m` centred on the world origin.

    Args:
        warehouse: Warehouse geometry.

    Returns:
        One entry per quadrant, in NE, NW, SE, SW order.
    """
    aw = warehouse.nominal_aisle_width_m / 2.0
    hw = warehouse.width_m / 2.0
    hd = warehouse.depth_m / 2.0
    return [
        ("NE", aw, hw, aw, hd),
        ("NW", -hw, -aw, aw, hd),
        ("SE", aw, hw, -hd, -aw),
        ("SW", -hw, -aw, -hd, -aw),
    ]


def rack_clearance_remnants(
    warehouse: "WarehouseConfig", clearance: RackClearanceConfig
) -> list[RackRect]:
    """Cut each rack quadrant back to its part outside `clearance`.

    Each quadrant minus the clearance rectangle splits into at most four
    axis-aligned pieces (west, east, south, north of the cut; the south and
    north pieces span only the cut's x overlap). Empty pieces are dropped.
    The USD builder authors exactly these boxes and the map generator leaves
    exactly these cells occupied.

    Args:
        warehouse: Warehouse geometry.
        clearance: The rectangle to clear.

    Returns:
        Remnant boxes as `(name, x0, x1, y0, y1)`, named `<quadrant>_<side>`.
    """
    out: list[RackRect] = []
    for name, x0, x1, y0, y1 in rack_quadrant_rects(warehouse):
        cx0 = max(x0, clearance.x_min_m)
        cx1 = min(x1, clearance.x_max_m)
        cy0 = max(y0, clearance.y_min_m)
        cy1 = min(y1, clearance.y_max_m)
        if cx0 >= cx1 or cy0 >= cy1:
            out.append((f"{name}_whole", x0, x1, y0, y1))
            continue
        pieces = [
            ("west", x0, cx0, y0, y1),
            ("east", cx1, x1, y0, y1),
            ("south", cx0, cx1, y0, cy0),
            ("north", cx0, cx1, cy1, y1),
        ]
        for side, px0, px1, py0, py1 in pieces:
            if px1 - px0 > 1e-9 and py1 - py0 > 1e-9:
                out.append((f"{name}_{side}", px0, px1, py0, py1))
    return out


class ExpectedConflictConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    type: Literal["deadlock", "bottleneck", "anomaly"]
    involved_robots: tuple[str, ...]
    onset_window_sec: tuple[float, float]
    min_duration_sec: float

    @field_validator("involved_robots")
    @classmethod
    def _non_empty(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if not v:
            raise ValueError("involved_robots must be non-empty")
        return v

    @field_validator("onset_window_sec")
    @classmethod
    def _window_increasing(cls, v: tuple[float, float]) -> tuple[float, float]:
        if v[0] >= v[1]:
            raise ValueError(f"onset_window_sec must be increasing; got {v}")
        return v


class ScenarioRuntimeOverrides(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    physics_hz: int = 60
    rendering_hz: int = 30
    duration_sec: float | None = None

    @field_validator("physics_hz")
    @classmethod
    def _physics_hz_fixed(cls, v: int) -> int:
        if v != 60:
            raise ValueError("physics_hz must be 60 for schema_version 1")
        return v

    @field_validator("rendering_hz")
    @classmethod
    def _rendering_hz_fixed(cls, v: int) -> int:
        if v != 30:
            raise ValueError("rendering_hz must be 30 for schema_version 1")
        return v


class HeadOnAsymmetricParams(BaseModel):
    """Parametric knobs for the head-on-asymmetric scenario family."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    blocker_west_m: float | None = None
    blocker_east_m: float | None = None
    arrival_offset_m: float = 0.0

    @field_validator("blocker_west_m", "blocker_east_m")
    @classmethod
    def _blocker_non_negative(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError(f"blocker offset must be >= 0 when set; got {v}")
        return v

    @field_validator("arrival_offset_m")
    @classmethod
    def _arrival_offset_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"arrival_offset_m must be >= 0; got {v}")
        return v


# Mirrors reasoning.vlm.models (BlockerKind, CongestionDecision.strategy); kept
# local because isaac/ runs inside Isaac Sim's Python and must not import the
# reasoning package. tests/unit/test_blocked_path_scenarios.py pins the parity.
OracleBlockerKind = Literal["robot", "object", "transient"]
OracleStrategy = Literal[
    "none",
    "yield",
    "reroute",
    "convoy",
    "priority_override",
    "temporary_wait",
    "reverse",
    "junction_clear",
]

class OracleMarginRecord(BaseModel):
    """The authoring-time verification of an ordering oracle (T2b).

    Written by the forced-order harness (`scripts/t2b_forced_order.py score`)
    after scripted executions of both orders: the oracle order must beat the
    alternative by `threshold` in total time-to-goal, else the scenario is
    re-authored. `margin` is `alternative_total_sec / oracle_total_sec - 1`;
    with `censored` set, at least one alternative run never finished, so the
    alternative total (and the margin) is a lower bound.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    metric: Literal["total_time_to_goal_sec"] = "total_time_to_goal_sec"
    oracle_total_sec: float = Field(gt=0.0)
    alternative_total_sec: float = Field(gt=0.0)
    alternative_yielder: str
    alternative_order: tuple[str, ...]
    margin: float
    threshold: float = Field(default=0.20, ge=0.0)
    censored: bool = False
    n_per_order: int = Field(ge=1)
    run_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _margin_matches_totals(self) -> "OracleMarginRecord":
        expected = self.alternative_total_sec / self.oracle_total_sec - 1.0
        if abs(self.margin - expected) > 1e-3:
            raise ValueError(
                f"margin {self.margin} does not match alternative/oracle - 1 = {expected:.4f}"
            )
        return self

    @property
    def passes(self) -> bool:
        """Whether the oracle order dominates by at least the threshold."""
        return self.margin >= self.threshold


class OracleConfig(BaseModel):
    """The ground-truth yield decision and its rationale for a scenario.

    `correct_order` (T2b flow ordering) names the robots that cross, first to
    pass first; the correct yielder is not in it. `margin` records the
    authoring-time verification that the order is worth scoring.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    correct_yielder: str
    fcfs_yielder: str
    feasible_yielders: tuple[str, ...]
    objective: Literal["min_total_time_to_goal"] = "min_total_time_to_goal"
    rationale: str
    correct_order: tuple[str, ...] | None = None
    margin: OracleMarginRecord | None = None
    # Strategy-label tier (B3 convoy_counterflow): the label the decision is
    # scored against, the labels accepted as correct (they execute
    # identically), and the platoon the correct order must list consecutively
    # before the yielder. All three are set together or not at all.
    correct_strategy: OracleStrategy | None = None
    accepted_strategies: tuple[OracleStrategy, ...] | None = None
    platoon: tuple[str, ...] | None = None
    # First-to-slip tier (B3 `convoy_counterflow_slip`): the pre-registered
    # platoon member predicted to be the first to resume motion through the
    # gate once the yielder clears it. Scored from GT by
    # `scripts/coverage_scene_scores.score_b3` against `platoon`; needs no
    # other oracle field and is independent of `correct_strategy`.
    first_slipper: str | None = None

    @model_validator(mode="after")
    def _first_slipper_is_a_platoon_member(self) -> "OracleConfig":
        if self.first_slipper is not None:
            if not self.platoon:
                raise ValueError("first_slipper needs platoon")
            if self.first_slipper not in self.platoon:
                raise ValueError(
                    f"first_slipper {self.first_slipper!r} must be in platoon {self.platoon}"
                )
        return self

    @model_validator(mode="after")
    def _feasible_yielders_contain_correct(self) -> "OracleConfig":
        if not self.feasible_yielders:
            raise ValueError("feasible_yielders must be non-empty")
        if self.correct_yielder not in self.feasible_yielders:
            raise ValueError(
                f"feasible_yielders must contain correct_yielder "
                f"{self.correct_yielder!r}; got {self.feasible_yielders}"
            )
        if self.correct_order is not None:
            if len(self.correct_order) < 2:
                raise ValueError(
                    f"correct_order must order at least two crossing robots; "
                    f"got {self.correct_order}"
                )
            if len(set(self.correct_order)) != len(self.correct_order):
                raise ValueError(f"correct_order has duplicates: {self.correct_order}")
            if self.correct_yielder in self.correct_order:
                raise ValueError(
                    f"correct_order must not contain the correct yielder "
                    f"{self.correct_yielder!r}; got {self.correct_order}"
                )
        if self.margin is not None and self.correct_order is None:
            raise ValueError("margin records an ordering oracle; set correct_order")
        return self

    @model_validator(mode="after")
    def _strategy_label_fields_are_consistent(self) -> "OracleConfig":
        fields = (self.correct_strategy, self.accepted_strategies, self.platoon)
        if all(f is None for f in fields):
            return self
        if any(f is None for f in fields):
            raise ValueError(
                "correct_strategy, accepted_strategies and platoon are set together"
            )
        assert self.accepted_strategies is not None and self.platoon is not None
        if self.correct_strategy not in self.accepted_strategies:
            raise ValueError(
                f"accepted_strategies {self.accepted_strategies} must contain "
                f"correct_strategy {self.correct_strategy!r}"
            )
        order = self.correct_order
        if order is None:
            raise ValueError("platoon needs correct_order")
        n = len(self.platoon)
        if not any(tuple(order[i : i + n]) == self.platoon for i in range(len(order) - n + 1)):
            raise ValueError(
                f"platoon {self.platoon} must appear consecutively in correct_order {order}"
            )
        return self

    @model_serializer(mode="wrap")
    def _omit_unset_ordering(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # The generated family YAMLs are compared byte for byte against a fresh
        # dump; the ordering fields stay out of every dump that does not use them.
        data = handler(self)
        for key in (
            "correct_order", "margin", "correct_strategy", "accepted_strategies", "platoon",
            "first_slipper",
        ):
            if data.get(key) is None:
                data.pop(key, None)
        return data

    @property
    def contrasts_fcfs(self) -> bool:
        """Whether the correct yielder differs from the naive FCFS yielder."""
        return self.correct_yielder != self.fcfs_yielder


# The deterministic per-kind default of the research design's blocker-kind
# arbitration (rev 8.6, Appendix A.5): what a blocker of that kind calls for.
# `robot` has no single default (the full multi-robot set applies).
BLOCKER_KIND_DEFAULT_STRATEGY: dict[str, str] = {
    "object": "reroute",
    "transient": "temporary_wait",
}


class BlockerOracleConfig(BaseModel):
    """The ground-truth blocker verdict and strategy for a blocked-path scene.

    The T3a counterpart of `OracleConfig`: `correct_*` is the pre-registered
    answer, `classical_*` the Arm B answer it is contrasted with (the classical
    classifier has no image, so its `blocked_path` blocker is always `object`),
    as `fcfs_yielder` is for the yield oracle.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    correct_blocker_kind: OracleBlockerKind
    correct_strategy: OracleStrategy
    classical_blocker_kind: OracleBlockerKind
    classical_strategy: OracleStrategy
    objective: Literal["blocker_kind_default"] = "blocker_kind_default"
    rationale: str

    @model_validator(mode="after")
    def _strategy_is_the_kind_default(self) -> "BlockerOracleConfig":
        default = BLOCKER_KIND_DEFAULT_STRATEGY.get(self.correct_blocker_kind)
        if default is None:
            raise ValueError(
                f"correct_blocker_kind {self.correct_blocker_kind!r} has no default "
                f"strategy; expected one of {sorted(BLOCKER_KIND_DEFAULT_STRATEGY)}"
            )
        if self.correct_strategy != default:
            raise ValueError(
                f"correct_strategy for a {self.correct_blocker_kind!r} blocker must be "
                f"{default!r}; got {self.correct_strategy!r}"
            )
        return self

    @property
    def contrasts_classical(self) -> bool:
        """Whether the correct answer differs from the classical (Arm B) answer."""
        return (self.correct_blocker_kind, self.correct_strategy) != (
            self.classical_blocker_kind,
            self.classical_strategy,
        )


class PriorityOracleConfig(BaseModel):
    """The ground-truth answer for one member of the B2 priority-urgent pair.

    The semantic-channel counterpart of `OracleConfig` (unified scene design,
    "Oracle-block conventions"): urgency reaches the VLM only through the task
    label, and the registry `priority` M3 reads is never rendered. The urgent
    robot passes first, so the other robot yields. `classical_yielder` is Arm
    B's answer, which reads no label and is therefore the same in both
    members: it disagrees with urgency in exactly one member of every pair.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    urgent_robot: str
    correct_yielder: str
    correct_first_passer: str
    classical_yielder: str
    objective: Literal["urgent_first"] = "urgent_first"
    rationale: str

    @model_validator(mode="after")
    def _urgent_robot_passes_first(self) -> "PriorityOracleConfig":
        if self.correct_first_passer != self.urgent_robot:
            raise ValueError(
                f"correct_first_passer must be the urgent robot {self.urgent_robot!r}; "
                f"got {self.correct_first_passer!r}"
            )
        if self.correct_yielder == self.urgent_robot:
            raise ValueError(f"the urgent robot {self.urgent_robot!r} cannot be the yielder")
        return self

    @property
    def contrasts_classical(self) -> bool:
        """Whether Arm B's (label-blind) yielder is the urgent robot."""
        return self.classical_yielder != self.correct_yielder


# M3's retreat-candidate labels, in generation order (reasoning/rag/
# retreat_candidates.py `_LABELS`); kept local for the same reason as the
# literals above.
RETREAT_CANDIDATE_LABELS: tuple[str, ...] = ("A", "B", "C", "D")


class RetreatOracleConfig(BaseModel):
    """The ground-truth stage-2 retreat choice for an obstacle-in-candidate scene.

    The T3b counterpart of `OracleConfig`. Labels are M3's candidate labels
    (generation order, what the command's `yield.retreat_choice` and the
    stage-2 artifact's `grounded_label` carry), never the counterbalanced
    letters the VLM is shown. `occupied_candidate` is the one an untracked
    obstacle fills; every other candidate is correct. `classical_candidate` is
    `ranked[0]`, the stage-2 default and Arm B's answer. The oracle holds
    only when `yielder` is the robot that yields: another yielder has a
    different candidate set.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    yielder: str
    passer: str
    candidate_count: int = Field(ge=2, le=len(RETREAT_CANDIDATE_LABELS))
    occupied_candidate: str
    correct_candidates: tuple[str, ...]
    classical_candidate: str
    objective: Literal["avoid_occupied_candidate"] = "avoid_occupied_candidate"
    rationale: str

    @model_validator(mode="after")
    def _labels_partition_the_candidate_set(self) -> "RetreatOracleConfig":
        labels = set(RETREAT_CANDIDATE_LABELS[: self.candidate_count])
        if self.yielder == self.passer:
            raise ValueError(f"yielder and passer must differ; got {self.yielder!r}")
        if self.occupied_candidate in self.correct_candidates:
            raise ValueError(
                f"occupied_candidate {self.occupied_candidate!r} cannot also be correct"
            )
        partition = {self.occupied_candidate, *self.correct_candidates}
        if len(self.correct_candidates) != len(set(self.correct_candidates)) or (
            partition != labels
        ):
            raise ValueError(
                f"occupied_candidate plus correct_candidates must be exactly "
                f"{sorted(labels)}; got {sorted(partition)}"
            )
        if self.classical_candidate not in labels:
            raise ValueError(
                f"classical_candidate {self.classical_candidate!r} not in {sorted(labels)}"
            )
        return self

    @property
    def contrasts_classical(self) -> bool:
        """Whether the classical (geometry-max) answer is an incorrect one."""
        return self.classical_candidate not in self.correct_candidates

    @property
    def chance_rate(self) -> float:
        """Probability a uniform random choice avoids the occupied candidate."""
        return len(self.correct_candidates) / self.candidate_count


LoopDetourArm = Literal["temporary_wait", "reroute"]


class LoopDetourCostRecord(BaseModel):
    """The forced-arm cost table of one loop-detour cell (prereg-v2 (b)).

    Written from forced-wait and forced-reroute mock sweeps on the VM
    (`scripts/strategy_regret.py score`, the T2b forced-order precedent):
    each arm's time-to-goal from departure, from Isaac ground truth. A
    censored arm never reached the goal inside the episode, so its time is
    the episode end and only a lower bound. `winner` is the faster arm and
    must be uncensored; `margin` is `loser / winner - 1` (a lower bound when
    the loser is censored).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    metric: Literal["time_to_goal_sec"] = "time_to_goal_sec"
    wait_time_to_goal_sec: float = Field(gt=0.0)
    wait_censored: bool
    reroute_time_to_goal_sec: float = Field(gt=0.0)
    reroute_censored: bool
    winner: LoopDetourArm
    margin: float
    threshold: float = Field(default=0.20, ge=0.0)
    n_per_arm: int = Field(ge=1)
    run_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _winner_and_margin_match_the_table(self) -> "LoopDetourCostRecord":
        times = {
            "temporary_wait": (self.wait_time_to_goal_sec, self.wait_censored),
            "reroute": (self.reroute_time_to_goal_sec, self.reroute_censored),
        }
        win_sec, win_censored = times[self.winner]
        lose_sec, _ = times["reroute" if self.winner == "temporary_wait" else "temporary_wait"]
        if win_censored:
            raise ValueError(f"winner {self.winner!r} is censored: no oracle is defined")
        if win_sec > lose_sec:
            raise ValueError(
                f"winner {self.winner!r} ({win_sec}s) is slower than the other arm ({lose_sec}s)"
            )
        expected = lose_sec / win_sec - 1.0
        if abs(self.margin - expected) > 1e-3:
            raise ValueError(
                f"margin {self.margin} does not match loser/winner - 1 = {expected:.4f}"
            )
        return self

    @property
    def passes(self) -> bool:
        """Whether the winner dominates by at least the threshold."""
        return self.margin >= self.threshold


class LoopDetourOracleConfig(BaseModel):
    """The wait-vs-detour oracle for one loop-map cell (prereg-v2 (b)).

    The loop-map counterpart of `BlockerOracleConfig`: robot_1 is stopped
    short of a blocker in the primary aisle with a real detour round the
    loop's far aisle. The manipulated variable is the blocker's persistence,
    carried only by its look (a box never moves; a marker-less robot
    resumes), and the correct answer is the cheaper forced arm in `cost`:
    `reroute` (the far-aisle detour) or `temporary_wait`. A permanent
    blocker makes waiting unbounded, so its correct answer is `reroute` by
    construction; `classical_strategy` is Arm B's answer, which reads no
    image and is the same in both cells.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    persistence: Literal["permanent", "transient"]
    correct_strategy: LoopDetourArm
    accepted_strategies: tuple[LoopDetourArm, ...]
    classical_strategy: OracleStrategy
    classical_scenario: Literal["blocked_path", "unknown"]
    objective: Literal["min_time_to_goal"] = "min_time_to_goal"
    cost: LoopDetourCostRecord | None = None
    rationale: str

    @model_validator(mode="after")
    def _answer_matches_persistence_and_cost(self) -> "LoopDetourOracleConfig":
        if self.correct_strategy not in self.accepted_strategies:
            raise ValueError(
                f"accepted_strategies {self.accepted_strategies} must contain "
                f"correct_strategy {self.correct_strategy!r}"
            )
        if self.persistence == "permanent" and self.correct_strategy != "reroute":
            raise ValueError("a permanent blocker never clears: correct_strategy is reroute")
        if self.cost is not None and self.cost.winner != self.correct_strategy:
            raise ValueError(
                f"cost winner {self.cost.winner!r} disagrees with correct_strategy "
                f"{self.correct_strategy!r}"
            )
        return self

    @property
    def contrasts_classical(self) -> bool:
        """Whether the correct answer differs from Arm B's."""
        return self.classical_strategy not in self.accepted_strategies


# The ordinal partial score of a `junction_clear` episode (prereg-v2 (a)
# Scoring: "phase reached is the ordinal partial score"), in M5's own
# `JunctionPhaseReached` vocabulary (swarm_orchestrator.junction_phase_queue),
# kept local for the same reason as the literals above.
JUNCTION_PHASE_ORDINAL: tuple[str, ...] = ("recede", "cross", "release", "resolved")
JunctionPhase = Literal["recede", "cross", "release", "resolved"]


class JunctionOracleConfig(BaseModel):
    """The `junction_clear` resolution oracle for the IB10 four-way cell.

    The v2 counterpart of `OracleConfig` (prereg-v2 (a) Scoring, step-7b
    Part 3): the episode succeeds when every robot is position-verified at
    its goal; `recede_pair` is the cross-axis pair M3 recedes (its order is
    chi-ranked per episode, so none is registered); `inside_pair` crosses
    first, inside-first, except for its grounded yielder; a run counts only
    when the jam forms first, with `jam_robots_in_radius` robots inside
    `oracle.intersection_conflict_active`'s radius at onset.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    correct_strategy: Literal["junction_clear"] = "junction_clear"
    accepted_strategies: tuple[Literal["junction_clear"], ...] = ("junction_clear",)
    objective: Literal["min_total_time_to_goal"] = "min_total_time_to_goal"
    jam_robots_in_radius: int = Field(ge=3)
    recede_pair: tuple[str, str]
    inside_pair: tuple[str, str]
    phase_ordinal: tuple[JunctionPhase, ...] = JUNCTION_PHASE_ORDINAL
    rationale: str

    @model_validator(mode="after")
    def _pairs_partition_and_ordinal_is_canonical(self) -> "JunctionOracleConfig":
        if set(self.recede_pair) & set(self.inside_pair):
            raise ValueError(
                f"recede_pair {list(self.recede_pair)} and inside_pair "
                f"{list(self.inside_pair)} must be disjoint"
            )
        if self.phase_ordinal != JUNCTION_PHASE_ORDINAL:
            raise ValueError(
                f"phase_ordinal must be {list(JUNCTION_PHASE_ORDINAL)}; "
                f"got {list(self.phase_ordinal)}"
            )
        return self


# Mirrors reasoning.vlm.models.PlanLegAction (the `proposed_plan` leg
# vocabulary), kept local for the same reason as the literals above;
# tests/unit/test_s6_dual_conflict_scenario.py pins the parity.
OraclePlanLegAction = Literal["yield", "reverse", "cross", "wait", "reroute", "continue"]
DUAL_CONFLICT_ADDRESSING_ACTIONS: tuple[OraclePlanLegAction, ...] = (
    "yield", "reverse", "cross", "wait", "reroute",
)


class DualConflictPairConfig(BaseModel):
    """One of the two simultaneous head-on conflicts of the S6 dual-conflict cell."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    conflict_id: str = Field(min_length=1)
    involved_robots: tuple[str, str]
    correct_type: Literal["deadlock"] = "deadlock"
    # The jam midpoint the scene is authored for (world frame, metres): where
    # the pair's standoff forms when both members depart together at equal
    # speed. Scorers use it to attribute a decision to a conflict; it is not a
    # measured value.
    jam_midpoint_xy: tuple[float, float]

    @model_validator(mode="after")
    def _pair_has_two_distinct_robots(self) -> "DualConflictPairConfig":
        if self.involved_robots[0] == self.involved_robots[1]:
            raise ValueError(
                f"conflict {self.conflict_id!r} needs two distinct robots; "
                f"got {list(self.involved_robots)}"
            )
        return self


class DualConflictOracleConfig(BaseModel):
    """The decision-level oracle for the S6 dual-conflict cell (v3 scene design, S6).

    Two disjoint head-on pairs jam at the same time in two parallel C55
    aisles. Only the first triggered decision is scored; the executed outcome
    is not (the second aisle's head-on is ungroundable with axis-aligned
    escorts). `criterion_status` stays `proposed` until the v3 Step 6 freeze
    rules the criterion below.

    Criterion: a conflict is NAMED when both members of its pair are in the
    decision's `involved_robots`, and ADDRESSED when the decision's
    `proposed_plan` has a leg for at least one member whose action is in
    `addressing_actions` (every leg action but `continue`, the lenient default
    for an omitted robot). The plan addresses both conflicts when each is
    addressed. `plan_source` fixes which plan is scored: the model's own
    `proposed_plan` as parsed, never M3's verified plan. A plan the parser
    nulled, or an `m3_default` plan M3 derived in its place, scores as no
    plan, so M3's repairs cannot address a conflict the model did not.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    objective: Literal["address_both_conflicts"] = "address_both_conflicts"
    criterion_status: Literal["proposed", "frozen"]
    scored_decision: Literal["first_triggered"] = "first_triggered"
    plan_source: Literal["model_raw"] = "model_raw"
    execution_scored: Literal[False] = False
    conflicts: tuple[DualConflictPairConfig, DualConflictPairConfig]
    addressing_actions: tuple[OraclePlanLegAction, ...] = DUAL_CONFLICT_ADDRESSING_ACTIONS
    # Two conflicts count as separate events only when their jam midpoints are
    # farther apart than this (Arm B's r_conflict_m, config/rag.yaml).
    separate_event_radius_m: float = Field(gt=0.0)
    rationale: str

    @model_validator(mode="after")
    def _conflicts_are_disjoint_and_separate(self) -> "DualConflictOracleConfig":
        first, second = self.conflicts
        if first.conflict_id == second.conflict_id:
            raise ValueError(f"conflict_id values must differ; got {first.conflict_id!r} twice")
        shared = set(first.involved_robots) & set(second.involved_robots)
        if shared:
            raise ValueError(f"the two conflicts must be disjoint; both list {sorted(shared)}")
        gap = (
            (first.jam_midpoint_xy[0] - second.jam_midpoint_xy[0]) ** 2
            + (first.jam_midpoint_xy[1] - second.jam_midpoint_xy[1]) ** 2
        ) ** 0.5
        if gap <= self.separate_event_radius_m:
            raise ValueError(
                f"jam midpoints {gap:.3f} m apart are not separate events at "
                f"separate_event_radius_m {self.separate_event_radius_m}"
            )
        return self

    @model_validator(mode="after")
    def _addressing_actions_exclude_continue(self) -> "DualConflictOracleConfig":
        if not self.addressing_actions:
            raise ValueError("addressing_actions must be non-empty")
        if len(set(self.addressing_actions)) != len(self.addressing_actions):
            raise ValueError(f"addressing_actions has duplicates: {self.addressing_actions}")
        if "continue" in self.addressing_actions:
            raise ValueError("continue is the omitted-robot default and cannot address a conflict")
        return self

    @property
    def involved_robots(self) -> frozenset[str]:
        """Every robot of both conflicts."""
        return frozenset(r for c in self.conflicts for r in c.involved_robots)

    def conflicts_named(self, involved_robots: Sequence[str]) -> dict[str, bool]:
        """Return, per conflict id, whether a decision's involved set names the pair.

        Args:
            involved_robots: The decision's `involved_robots`.

        Returns:
            `{conflict_id: named}` for both conflicts.
        """
        listed = set(involved_robots)
        return {c.conflict_id: set(c.involved_robots) <= listed for c in self.conflicts}

    def conflicts_addressed(self, plan_legs: Sequence[tuple[str, str]]) -> dict[str, bool]:
        """Return, per conflict id, whether a proposed plan addresses the pair.

        Args:
            plan_legs: The decision's `proposed_plan` as `(robot_id, action)`
                pairs; an empty sequence for a decision with no plan.

        Returns:
            `{conflict_id: addressed}` for both conflicts.
        """
        acting = {robot for robot, action in plan_legs if action in self.addressing_actions}
        return {c.conflict_id: bool(acting & set(c.involved_robots)) for c in self.conflicts}

    def addresses_both(self, plan_legs: Sequence[tuple[str, str]]) -> bool:
        """Return whether a proposed plan addresses both conflicts."""
        return all(self.conflicts_addressed(plan_legs).values())


FAMILY_BY_LEGACY_NAME: dict[str, str] = {
    "head_on_deadlock": "head_on",
    "intersection_bottleneck": "intersection",
    "dynamic_anomaly": "dynamic_anomaly",
}
# normal_flow is the T0 negative-control family: no conflict is expected, so
# its scenarios carry `expected_conflict: null` (and only they may).
# blocked_path is the T3a blocker-kind counterfactual pair: one robot stopped
# by an untracked blocker on its lane. bottleneck (B1 bottleneck_merge) and
# convoy (B3 convoy_counterflow) are the unified scene design's coverage
# scenes; the B2 priority pair is a head-on and stays in head_on.
ScenarioFamily = Literal[
    "head_on",
    "intersection",
    "dynamic_anomaly",
    "normal_flow",
    "blocked_path",
    "bottleneck",
    "convoy",
]
CONFLICT_FREE_FAMILIES: frozenset[str] = frozenset({"normal_flow"})


class ScenarioConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1]
    name: str
    family: ScenarioFamily
    seed: int
    duration_sec: float
    robots: tuple[RobotScenarioConfig, ...]
    timed_obstacles: tuple[TimedObstacleConfig, ...] = ()
    static_obstacles: tuple[StaticObstacleConfig, ...] = ()
    aisle_barrier: AisleBarrierConfig | None = None
    loop_map: LoopMapConfig | None = None
    rack_clearance: RackClearanceConfig | None = None
    parameters: HeadOnAsymmetricParams | None = None
    oracle: (
        OracleConfig
        | BlockerOracleConfig
        | RetreatOracleConfig
        | PriorityOracleConfig
        | JunctionOracleConfig
        | LoopDetourOracleConfig
        | DualConflictOracleConfig
        | None
    ) = None
    # Required but nullable: every scenario must state its conflict, and null
    # is the explicit "none expected" of a conflict-free family.
    expected_conflict: ExpectedConflictConfig | None
    runtime: ScenarioRuntimeOverrides = Field(default_factory=ScenarioRuntimeOverrides)

    @model_serializer(mode="wrap")
    def _omit_unset_rack_clearance(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # Generated scenario YAMLs (the head-on family) are compared byte for
        # byte against a fresh dump; the S1b-only key stays out of every dump
        # that does not use it.
        data = handler(self)
        if data.get("rack_clearance") is None:
            data.pop("rack_clearance", None)
        return data

    @model_validator(mode="before")
    @classmethod
    def _infer_family_from_legacy_name(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "family" in data:
            return data
        name = data.get("name")
        family = FAMILY_BY_LEGACY_NAME.get(name)
        if family is None:
            raise ValueError(f"family is required for scenario name {name!r}")
        return {**data, "family": family}

    @field_validator("name")
    @classmethod
    def _name_format(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", v):
            raise ValueError(f"name must match ^[a-z][a-z0-9_]*$; got {v!r}")
        return v

    @field_validator("seed")
    @classmethod
    def _seed_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"seed must be >= 0; got {v}")
        return v

    @field_validator("duration_sec")
    @classmethod
    def _duration_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"duration_sec must be > 0; got {v}")
        return v

    @model_validator(mode="after")
    def _cross_field_validation(self) -> "ScenarioConfig":
        robot_ids = [r.robot_id for r in self.robots]
        if len(robot_ids) != len(set(robot_ids)):
            raise ValueError(f"robot_id values must be unique; got {robot_ids}")

        marker_ids = [r.marker_id for r in self.robots]
        if len(marker_ids) != len(set(marker_ids)):
            raise ValueError(f"marker_id values must be unique; got {marker_ids}")

        for r in self.robots:
            n = int(r.robot_id.split("_")[1])
            if r.marker_id != n:
                raise ValueError(
                    f"robot {r.robot_id!r} must have marker_id={n}; got {r.marker_id}"
                )

        for obs in self.timed_obstacles:
            end = obs.remove_at_sec if obs.remove_at_sec is not None else self.duration_sec
            if obs.spawn_at_sec >= self.duration_sec:
                raise ValueError(
                    f"obstacle {obs.obstacle_id!r} spawn_at_sec {obs.spawn_at_sec} "
                    f">= duration_sec {self.duration_sec}"
                )
            if end > self.duration_sec:
                raise ValueError(
                    f"obstacle {obs.obstacle_id!r} remove_at_sec {end} "
                    f"> duration_sec {self.duration_sec}"
                )

        robot_id_set = set(robot_ids)
        conflict_free = self.family in CONFLICT_FREE_FAMILIES
        if self.expected_conflict is None and not conflict_free:
            raise ValueError(
                f"expected_conflict may be null only for families "
                f"{sorted(CONFLICT_FREE_FAMILIES)}; got family {self.family!r}"
            )
        if self.expected_conflict is not None and conflict_free:
            raise ValueError(
                f"family {self.family!r} expects no conflict: expected_conflict must be null"
            )
        if self.expected_conflict is not None:
            for rid in self.expected_conflict.involved_robots:
                if rid not in robot_id_set:
                    raise ValueError(
                        f"involved_robot {rid!r} not in configured robots {robot_id_set}"
                    )

            w_start, w_end = self.expected_conflict.onset_window_sec
            if w_end > self.duration_sec:
                raise ValueError(
                    f"onset_window_sec end {w_end} > duration_sec {self.duration_sec}"
                )

        if self.rack_clearance is not None and self.loop_map is not None:
            # Both re-author the NE rack quadrant; composing them is undefined.
            raise ValueError("rack_clearance and loop_map are mutually exclusive")

        obstacle_ids = [o.obstacle_id for o in self.static_obstacles] + [
            o.obstacle_id for o in self.timed_obstacles
        ]
        if len(obstacle_ids) != len(set(obstacle_ids)):
            raise ValueError(
                f"obstacle_id values must be unique across static and timed "
                f"obstacles; got {obstacle_ids}"
            )

        if isinstance(self.oracle, OracleConfig):
            oracle_robot_ids = (
                self.oracle.correct_yielder,
                self.oracle.fcfs_yielder,
                *self.oracle.feasible_yielders,
            )
            for rid in oracle_robot_ids:
                if rid not in robot_id_set:
                    raise ValueError(
                        f"oracle robot {rid!r} not in configured robots {robot_id_set}"
                    )
            for rid in self.oracle.platoon or ():
                if rid not in robot_id_set:
                    raise ValueError(
                        f"oracle platoon robot {rid!r} not in configured robots {robot_id_set}"
                    )
            order = self.oracle.correct_order
            if order is not None:
                crossing = robot_id_set - {self.oracle.correct_yielder}
                if set(order) != crossing:
                    raise ValueError(
                        f"correct_order must be a permutation of every robot but the "
                        f"yielder {sorted(crossing)}; got {list(order)}"
                    )
                # oracle.head_on_conflict_active is defined for exactly the
                # standoff pair; a longer list would log conflict_active=false
                # for the whole run (three-robot feasibility report, Layer 1).
                involved = (
                    () if self.expected_conflict is None
                    else self.expected_conflict.involved_robots
                )
                if self.family == "head_on" and len(involved) != 2:
                    raise ValueError(
                        f"an ordering oracle on the head_on family keeps "
                        f"expected_conflict.involved_robots at the standoff pair; "
                        f"got {list(involved)}"
                    )
            margin = self.oracle.margin
            if margin is not None:
                for rid in (margin.alternative_yielder, *margin.alternative_order):
                    if rid not in robot_id_set:
                        raise ValueError(
                            f"margin robot {rid!r} not in configured robots {robot_id_set}"
                        )
        if isinstance(self.oracle, PriorityOracleConfig):
            for rid in (
                self.oracle.urgent_robot,
                self.oracle.correct_yielder,
                self.oracle.classical_yielder,
            ):
                if rid not in robot_id_set:
                    raise ValueError(
                        f"oracle robot {rid!r} not in configured robots {robot_id_set}"
                    )
        if isinstance(self.oracle, RetreatOracleConfig):
            for rid in (self.oracle.yielder, self.oracle.passer):
                if rid not in robot_id_set:
                    raise ValueError(
                        f"oracle robot {rid!r} not in configured robots {robot_id_set}"
                    )
        if isinstance(self.oracle, JunctionOracleConfig):
            for rid in (*self.oracle.recede_pair, *self.oracle.inside_pair):
                if rid not in robot_id_set:
                    raise ValueError(
                        f"oracle robot {rid!r} not in configured robots {robot_id_set}"
                    )
            if self.oracle.jam_robots_in_radius > len(self.robots):
                raise ValueError(
                    f"jam_robots_in_radius {self.oracle.jam_robots_in_radius} exceeds "
                    f"the {len(self.robots)} configured robots"
                )
        if isinstance(self.oracle, DualConflictOracleConfig):
            for rid in sorted(self.oracle.involved_robots):
                if rid not in robot_id_set:
                    raise ValueError(
                        f"oracle robot {rid!r} not in configured robots {robot_id_set}"
                    )
            if self.expected_conflict is not None and (
                set(self.expected_conflict.involved_robots) != self.oracle.involved_robots
            ):
                raise ValueError(
                    "expected_conflict.involved_robots must be the union of the dual "
                    f"conflict pairs {sorted(self.oracle.involved_robots)}; got "
                    f"{list(self.expected_conflict.involved_robots)}"
                )

        return self


class RobotAssetConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    asset_name: Literal["turtlebot3_burger"] = "turtlebot3_burger"
    left_wheel_joint: Literal["wheel_left_joint"] = "wheel_left_joint"
    right_wheel_joint: Literal["wheel_right_joint"] = "wheel_right_joint"
    # The URDF importer's fix_base default welds base_link to the world via this
    # joint; it must be disabled so the differential drive can move the chassis.
    base_fixed_joint: Literal["base_joint"] = "base_joint"
    base_link: Literal["base_link"] = "base_link"
    lidar_link: Literal["base_scan"] = "base_scan"
    wheel_radius_m: float = 0.033
    wheel_separation_m: float = 0.160
    max_linear_velocity_mps: float = 0.22
    max_angular_velocity_radps: float = 2.84
    wheel_drive_stiffness: float = 0.0
    wheel_drive_damping: float = 1000.0
    command_timeout_sec: float = 0.5
    wheel_static_friction: float = 0.8
    wheel_dynamic_friction: float = 0.6


class CameraConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    prim_path: Literal["/World/Sensors/OverheadCamera"] = "/World/Sensors/OverheadCamera"
    frame_id: Literal["overhead_camera"] = "overhead_camera"
    width: Literal[1280] = 1280
    height: Literal[960] = 960
    fps: Literal[30] = 30
    position_m: tuple[float, float, float] = (0.0, 0.0, 3.0)
    # Nadir orientation (w, x, y, z). Parameterized so tilted-camera mount (spec §13)
    # is a config-only change; default is identity = straight down.
    orientation_quat_wxyz: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    focal_length_mm: float = 10.48
    horizontal_aperture_mm: float = 20.955
    # Square-pixel vertical aperture; CameraInfo K and M1 homography must match.
    vertical_aperture_mm: float = 15.716
    # Central conflict ROI (PoC, not full room — spec FR6.6.5).
    roi_width_m: float = 6.0
    roi_depth_m: float = 4.5


class WarehouseConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    width_m: float = 12.0
    depth_m: float = 8.0
    nominal_aisle_width_m: float = 1.2
    wall_thickness_m: float = 0.1
    wall_height_m: float = 1.2


class GtContactLoggingConfig(BaseModel):
    """Sim-side switch for footprint contact fields in ground-truth rows.

    Off by default so rows keep the `68e67b5` schema (empty contact lists, no
    gap minima, no `contact_model`) that every evaluated run was logged with.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    enabled: bool = False


class _GtConfigFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    gt_contact_logging: GtContactLoggingConfig = GtContactLoggingConfig()


def load_gt_contact_logging_config(path: Path | None) -> GtContactLoggingConfig:
    """Load the `gt_contact_logging` section from an opt-in GT config file.

    Args:
        path: YAML file with a top-level `gt_contact_logging:` mapping (for
            example `config/gt/contact_logging_on.fragment.yaml`), or None.

    Returns:
        The parsed section; the default-off config when `path` is None or the
        file has no such section.

    Raises:
        FileNotFoundError: If `path` is given but does not exist.
        ValueError: If the file is not a YAML mapping or has unknown keys.
    """
    if path is None:
        return GtContactLoggingConfig()
    import yaml

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"GT config {path} is not a YAML mapping")
    return _GtConfigFile.model_validate(raw).gt_contact_logging


class ResolvedRunConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    scenario_path: Path
    scenario: ScenarioConfig
    headless: bool
    repetitions: int
    output_dir: Path
    topic_timeout_sec: float
    ros_domain_id: int | None
    gt_contact_logging: GtContactLoggingConfig = GtContactLoggingConfig()


class RunResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: str
    repetition: int
    completed: bool
    elapsed_simulation_sec: float
    manifest_path: Path
    failure: str | None
