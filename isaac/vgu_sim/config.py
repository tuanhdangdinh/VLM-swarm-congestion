import re
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
            "correct_order", "margin", "correct_strategy", "accepted_strategies", "platoon"
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
    parameters: HeadOnAsymmetricParams | None = None
    oracle: (
        OracleConfig
        | BlockerOracleConfig
        | RetreatOracleConfig
        | PriorityOracleConfig
        | None
    ) = None
    # Required but nullable: every scenario must state its conflict, and null
    # is the explicit "none expected" of a conflict-free family.
    expected_conflict: ExpectedConflictConfig | None
    runtime: ScenarioRuntimeOverrides = Field(default_factory=ScenarioRuntimeOverrides)

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


class ResolvedRunConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    scenario_path: Path
    scenario: ScenarioConfig
    headless: bool
    repetitions: int
    output_dir: Path
    topic_timeout_sec: float
    ros_domain_id: int | None


class RunResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: str
    repetition: int
    completed: bool
    elapsed_simulation_sec: float
    manifest_path: Path
    failure: str | None
