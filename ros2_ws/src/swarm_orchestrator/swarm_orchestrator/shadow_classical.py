"""Arm B shadow for M5: snapshot ring buffer, classical shadow record (no rclpy).

The rev-8 design ("Experimental arms, pairing, and shadow logging" in
`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`)
requires that in Arm A the classical answer is also computed and logged for
every decision, with disagreements as first-class events. Everything here is
observational: nothing in this module dispatches, touches the M2 request, or
edits the VLM decision, and every entry point the node calls converts its own
failures into a recorded `shadow_error` instead of raising.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from reasoning.baselines import (
    ClassicalClassification,
    ClassicalParams,
    ClassicalResolution,
    ConflictZone,
    DisagreementRecord,
    compare_decisions,
    load_classical_params,
    resolve_classical,
)
from reasoning.rag.command_grounder import (
    YieldFeasibilityMode,
    prepare_retreat_selection,
    resolve_yield_roles,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)
from reasoning.vlm.motion_table import derive_motion_table
from swarm_orchestrator.models import SceneSnapshot

GoalLookup = Callable[[str], tuple[float, float] | None]
# Registry lookup of whether a robot's base mission is still held back
# (`TaskRegistry.is_pending`, published as `start_pending`).
HeldLookup = Callable[[str], bool]
ResolveFn = Callable[..., ClassicalResolution]
# (vlm, classical, *, classical_blocker_kind=..., classical_passing_order=...)
CompareFn = Callable[..., DisagreementRecord]


def snapshot_to_frame(
    snapshot: SceneSnapshot, goal_of: GoalLookup, held_of: HeldLookup | None = None
) -> SnapshotFrame:
    """Project one M5 scene snapshot into the reasoning-side `SnapshotFrame`.

    Args:
        snapshot: M1 scene as M5 received it.
        goal_of: Registry lookup of a robot's effective goal; M1's SceneState
            goal is not carried by `RobotView`, so the task registry M5 owns is
            the goal source. Returns None for a robot with no assignment.
        held_of: Registry lookup of whether a robot is still held back
            (`start_pending`); its answer at this call is the frame's
            `held_robot_ids`, which Arm B's held-robot exclusion reads. None
            marks no robot held (every frame before the rule existed).

    Returns:
        Frame stamped with the scene stamp (M1's clock), one state per robot.
    """
    robots = [
        RobotStateInput(
            robot_id=view.robot_id,
            x=view.x,
            y=view.y,
            theta=view.theta,
            # M1 currently reports metres per wall-second (about 0.38x real at
            # the sim's real-time factor; a fix is landing in swarm_perception).
            # Passed through unscaled on purpose: Arm B's stopped_speed_mps is
            # tuned against whatever M1 reports on T1, so compensating here
            # would double-correct once M1 is fixed.
            linear_velocity=view.linear_velocity,
            status=view.status,
            goal=goal_of(view.robot_id),
        )
        for view in snapshot.robots
    ]
    held = (
        ()
        if held_of is None
        else tuple(sorted(view.robot_id for view in snapshot.robots if held_of(view.robot_id)))
    )
    return SnapshotFrame(stamp=snapshot.stamp, robots=robots, held_robot_ids=held)


def find_censored_arrivals(
    frames: Sequence[SnapshotFrame], classification: ClassicalClassification
) -> list[str] | None:
    """Name the involved robots whose FCFS arrival stamp is censored.

    FCFS dates a robot's arrival by the first buffered frame with it inside
    the conflict zone, so a robot already in the zone at the oldest frame
    gets that frame's stamp whether it arrived then or long before (the
    `simtime_shadow_val` S2 run: spawns sit exactly on the 1.5 m zone
    boundary). Uses the same zone and the same `derive_motion_table` rule
    FCFS used, so it flags exactly the stamps FCFS compared.

    Args:
        frames: The frames the classical resolver ran on.
        classification: The resolver's classification of those frames.

    Returns:
        Sorted ids of involved robots whose arrival stamp equals the oldest
        frame's stamp; empty when none is censored; None when the scenario
        carries no conflict zone (no FCFS order was computed) or `frames` is
        empty.
    """
    center = classification.conflict_center
    radius = classification.conflict_radius_m
    if center is None or radius is None or not frames:
        return None
    oldest = min(frame.stamp for frame in frames)
    involved = set(classification.involved_robots)
    table = derive_motion_table(frames, center, radius)
    return sorted(
        entry.robot_id
        for entry in table.entries
        if entry.robot_id in involved and entry.arrival_stamp == oldest
    )


class SnapshotRingBuffer:
    """Time-windowed, decimated history of `SnapshotFrame`s on M1's stamp clock.

    `derive_motion_table` dates a robot's zone entry by the first buffered frame
    that has it inside the conflict zone, so the history must reach back past
    the entry. Expiry and decimation both use frame stamps, not M5's monotonic
    clock, because the arrival stamps FCFS compares are frame stamps.

    A stamp that goes backwards (sim reset, M1 restart) clears the history:
    frames from before the reset describe a different episode.
    """

    def __init__(self, window_sec: float, sample_period_sec: float) -> None:
        """Create an empty buffer.

        Args:
            window_sec: History kept, in stamp seconds, behind the newest frame.
            sample_period_sec: Minimum stamp gap between stored frames.

        Raises:
            ValueError: If either is not positive, or the period is not below
                the window.
        """
        if window_sec <= 0.0 or sample_period_sec <= 0.0:
            raise ValueError(
                f"window_sec ({window_sec}) and sample_period_sec ({sample_period_sec}) "
                "must be positive"
            )
        if sample_period_sec >= window_sec:
            raise ValueError(
                f"sample_period_sec {sample_period_sec} must be below window_sec {window_sec}"
            )
        self._window_sec = window_sec
        self._sample_period_sec = sample_period_sec
        self._frames: deque[SnapshotFrame] = deque()

    def __len__(self) -> int:
        return len(self._frames)

    def accepts(self, stamp: float) -> bool:
        """Return whether `add` would store a frame with this stamp.

        Lets the caller skip building a frame that decimation would discard.
        """
        if not self._frames:
            return True
        last = self._frames[-1].stamp
        return stamp < last or stamp - last >= self._sample_period_sec

    def add(self, frame: SnapshotFrame) -> bool:
        """Store a frame if decimation allows, then expire old frames.

        Args:
            frame: Snapshot to store.

        Returns:
            True if the frame was stored.
        """
        if not self.accepts(frame.stamp):
            return False
        if self._frames and frame.stamp < self._frames[-1].stamp:
            self._frames.clear()
        self._frames.append(frame)
        cutoff = frame.stamp - self._window_sec
        while self._frames and self._frames[0].stamp < cutoff:
            self._frames.popleft()
        return True

    def frames(self, latest: SnapshotFrame | None = None) -> list[SnapshotFrame]:
        """Return the buffered history, oldest first.

        Args:
            latest: Frame the caller is deciding on. When given it becomes the
                newest returned frame whatever decimation did with it: the
                classifier reads only the newest frame, so without this it
                could classify a frame up to one sample period older than the
                scene the VLM request was built from. Buffered frames not older
                than it are replaced by it, and the window is measured back
                from its stamp. The buffer itself is not modified.

        Returns:
            Frames within the window, sorted by stamp.
        """
        if latest is None:
            return list(self._frames)
        cutoff = latest.stamp - self._window_sec
        kept = [f for f in self._frames if cutoff <= f.stamp < latest.stamp]
        return [*kept, latest]


class ClassicalRetreatContext(BaseModel):
    """The derived-grounding inputs M5 hands the grounder, for Arm B's stage 2.

    The same params, geometry, obstacles and gate mode the pipeline grounds
    and runs stage 2 with, so Arm B's candidates are the ones the VLM chose
    among.
    """

    model_config = ConfigDict(frozen=True)

    params: GroundingParams
    geometry: SceneGeometry | None = None
    static_obstacles: tuple[StaticObstacleInput, ...] = ()
    yield_feasibility_mode: YieldFeasibilityMode = "off"


class ClassicalRetreat(BaseModel):
    """Arm B's stage-2 answer: the geometry-max candidate for its own yielder.

    `ranked[0]` of `prepare_retreat_selection` is by construction the
    stage-2 default, the stage-2 fallback and Arm B's stage-2 answer
    (rev-8 A.3); this records it for the classical decision's yielder.
    """

    model_config = ConfigDict(frozen=True)

    # computed: a candidate exists; not_applicable: no classical yield, or
    # grounding is not derived (no stage 2); unavailable: the yield is not
    # executable (gate refusal, infeasible backup, no candidate); error: the
    # computation raised (also in the record's `shadow_error`).
    status: Literal["computed", "not_applicable", "unavailable", "error"]
    reason: str | None = None
    # The yielder the grounder would use (after the feasibility gate), and
    # the classical decision's own `yield_robot` when the gate moved it.
    yielder_id: str | None = None
    regrounded_from: str | None = None
    crossing_order: list[str] = Field(default_factory=list)
    # The geometry-max candidate, in M3's label and world-frame metres.
    candidate_label: str | None = None
    x: float | None = None
    y: float | None = None
    backup_m: float | None = None
    lateral_m: float | None = None
    candidate_count: int = Field(default=0, ge=0)
    # Set by `ClassicalShadow.finalize` against the executed command: whether
    # the VLM arm's executed retreat is Arm B's (same yielder, same position
    # at the command's 3-decimal rounding). `comparable` False says why not.
    comparable: bool | None = None
    comparison_reason: str | None = None
    same_yielder: bool | None = None
    equals_executed: bool | None = None
    executed: dict[str, Any] | None = None


def classical_retreat_answer(
    decision: CongestionDecision, frame: SnapshotFrame, context: ClassicalRetreatContext | None
) -> ClassicalRetreat:
    """Compute Arm B's stage-2 answer for one classical decision.

    Args:
        decision: The classical decision.
        frame: The scene it was classified on (the analysed snapshot).
        context: The grounder's derived-mode inputs; None when M5 did not
            wire them.

    Returns:
        The geometry-max candidate for the classical yielder, or a
        non-`computed` status saying why there is none. Exceptions propagate
        to the caller, which isolates them.
    """
    if decision.strategy != "yield":
        return ClassicalRetreat(
            status="not_applicable", reason=f"classical strategy={decision.strategy}"
        )
    if context is None:
        return ClassicalRetreat(status="not_applicable", reason="no grounding context wired")
    if context.params.mode != "derived":
        return ClassicalRetreat(
            status="not_applicable", reason=f"grounding mode={context.params.mode}: no stage 2"
        )
    roles = resolve_yield_roles(
        decision,
        frame,
        geometry=context.geometry,
        static_obstacles=context.static_obstacles,
        yield_feasibility_mode=context.yield_feasibility_mode,
    )
    base: dict[str, Any] = {
        "yielder_id": roles.yielder_id,
        "regrounded_from": roles.grounded_from,
        "crossing_order": list(roles.crossing_order),
    }
    if roles.refusal_reason is not None:
        return ClassicalRetreat(status="unavailable", reason=roles.refusal_reason, **base)
    selection = prepare_retreat_selection(
        frame,
        roles.yielder_id,
        roles.crossing_order,
        context.params,
        geometry=context.geometry,
        static_obstacles=context.static_obstacles,
    )
    if not selection.backup.feasible:
        return ClassicalRetreat(
            status="unavailable", reason=f"backup infeasible: {selection.backup.reason}", **base
        )
    if not selection.candidates:
        return ClassicalRetreat(status="unavailable", reason="no valid candidate", **base)
    best = selection.candidates[0]
    return ClassicalRetreat(
        status="computed",
        candidate_label=best.label,
        x=best.x,
        y=best.y,
        backup_m=best.backup_m,
        lateral_m=best.lateral_m,
        candidate_count=len(selection.candidates),
        **base,
    )


def compare_classical_retreat(
    retreat: ClassicalRetreat, grounded_command: dict[str, Any] | None
) -> ClassicalRetreat:
    """Compare Arm B's stage-2 answer with the retreat the VLM arm executed.

    Compared by yielder and position (rounded like the command, 3 decimals),
    never by letter: the letters are M3 labels on one side and permuted
    display letters on the other.

    Args:
        retreat: The record's `classical_retreat`.
        grounded_command: The pipeline's grounded command, or None.

    Returns:
        `retreat` with the comparison fields set.
    """
    if retreat.status != "computed":
        return retreat.model_copy(
            update={
                "comparable": False,
                "comparison_reason": f"no classical retreat: {retreat.status}",
            }
        )
    yields = [
        action
        for action in (grounded_command or {}).get("actions", [])
        if action.get("action") == "yield"
    ]
    parameters = (yields[0].get("parameters") or {}) if yields else {}
    if "retreat_x_m" not in parameters or "retreat_y_m" not in parameters:
        reason = (
            "no grounded command"
            if grounded_command is None
            else "no executed derived yield"
        )
        return retreat.model_copy(update={"comparable": False, "comparison_reason": reason})
    executed = {
        "yielder_id": yields[0].get("robot_id"),
        "x": parameters["retreat_x_m"],
        "y": parameters["retreat_y_m"],
        "retreat_choice": parameters.get("retreat_choice"),
    }
    same_yielder = executed["yielder_id"] == retreat.yielder_id
    same_position = (
        retreat.x is not None
        and retreat.y is not None
        and round(retreat.x, 3) == executed["x"]
        and round(retreat.y, 3) == executed["y"]
    )
    return retreat.model_copy(
        update={
            "comparable": True,
            "same_yielder": same_yielder,
            "equals_executed": same_yielder and same_position,
            "executed": executed,
        }
    )


class ClassicalParamsSource(BaseModel):
    """Which Arm B thresholds the shadow runs on, and where they came from."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    section_present: bool
    params: ClassicalParams | None
    # Set when params are unavailable; every shadow record then carries it.
    error: str | None = None


def load_shadow_params(path: Path) -> ClassicalParamsSource:
    """Load Arm B's thresholds for the shadow, once at M5 startup.

    `load_classical_params` falls back to the rev-8 defaults when the
    `classical:` section is absent. The shadow does not: those thresholds are
    tuned on T1 and frozen at `prereg-v1`, so a shadow answer computed on
    implicit defaults would be logged as if it came from the frozen control.
    A missing file or section therefore becomes a recorded error on every
    analysis instead of a silent default.

    Args:
        path: The RAG config (`config/rag.yaml`), relative to M5's cwd like
            `config/models.yaml`.

    Returns:
        The source, with `params` None and `error` set when the file or the
        section is missing.

    Raises:
        pydantic.ValidationError: If the section has unknown keys or
            out-of-range values (fail fast: a typo in a pre-registered
            threshold must not start a run).
        yaml.YAMLError: If the file is not valid YAML.
        ValueError: If the file is not a YAML mapping.
    """
    if not path.is_file():
        return ClassicalParamsSource(
            path=str(path),
            section_present=False,
            params=None,
            error=f"classical params unavailable: {path} not found",
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a YAML mapping, got {type(raw).__name__}")
    if not raw.get("classical"):
        return ClassicalParamsSource(
            path=str(path),
            section_present=False,
            params=None,
            error=f"classical params unavailable: no `classical:` section in {path}",
        )
    return ClassicalParamsSource(
        path=str(path), section_present=True, params=load_classical_params(path)
    )


class ShadowComparison(BaseModel):
    """Arm A vs Arm B agreement for one analysis, or why it could not be judged."""

    model_config = ConfigDict(frozen=True)

    comparable: bool
    # Set exactly when `comparable` is False.
    reason: str | None = None
    disagreement: DisagreementRecord | None = None


class ShadowClassicalRecord(BaseModel):
    """The `shadow_classical` block of one M5 decision artifact."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1)
    params_path: str
    params_section_present: bool
    params: ClassicalParams | None
    prior_attempts: int = Field(ge=0)
    # Analyses already made in this congestion episode (M5's episode tracker),
    # not AttemptMemory: that memory is off in the RQ5 memoryless control,
    # which would otherwise change Arm B's `unknown` policy with an Arm A
    # ablation.
    # "t0_probe": a log-only probe, which is never counted as an attempt.
    prior_attempts_source: Literal["episode_analyses", "t0_probe"] = "episode_analyses"
    zone_ids: list[str]
    window_sec: float
    sample_period_sec: float
    # Extent of the history actually classified. A robot already inside the
    # zone at `oldest_stamp` has a censored arrival (FCFS then falls back to
    # commitment and robot_id); `censored_arrivals` names such robots.
    frame_count: int = Field(ge=0)
    oldest_stamp: float | None
    latest_stamp: float | None
    # Involved robots already in the zone at `oldest_stamp`, whose FCFS
    # arrival is therefore censored (see `find_censored_arrivals`): the
    # classical answer stands but its passing order is suspect. None when no
    # FCFS order was computed. Defaulted so pre-flag artifacts still validate.
    censored_arrivals: list[str] | None = None
    decision: CongestionDecision | None
    classification: ClassicalClassification | None
    passing_order: list[str] | None
    # Arm B's stage-2 answer (`classical_retreat_answer`); None when no
    # classical decision was reached. Defaulted so older artifacts validate.
    classical_retreat: ClassicalRetreat | None = None
    # None until the VLM outcome arrives and `ClassicalShadow.finalize` runs.
    comparison: ShadowComparison | None = None
    # Scene frames the buffer failed to ingest since the previous analysis.
    feed_errors: int = Field(default=0, ge=0)
    last_feed_error: str | None = None
    shadow_error: str | None = None


class ClassicalShadow:
    """Arm B shadow the M5 node feeds with scenes and asks once per analysis.

    Holds the snapshot ring buffer, the params loaded at startup, and the
    per-episode analysis count. No method raises once constructed.
    """

    def __init__(
        self,
        params_source: ClassicalParamsSource,
        zones: Sequence[ConflictZone],
        window_sec: float,
        sample_period_sec: float,
        resolve_fn: ResolveFn = resolve_classical,
        compare_fn: CompareFn = compare_decisions,
        retreat_context: ClassicalRetreatContext | None = None,
    ) -> None:
        """Create the shadow.

        Args:
            params_source: Result of `load_shadow_params`.
            zones: Mapped conflict zones; empty is valid (the head-on rule
                derives its own pair zone).
            window_sec: Ring-buffer history in stamp seconds.
            sample_period_sec: Ring-buffer decimation period.
            resolve_fn: Arm B resolver; injectable for failure-path tests.
            compare_fn: Decision comparator; injectable for failure-path tests.
            retreat_context: The grounder's derived-mode inputs, for Arm B's
                stage-2 answer; None records it as not applicable.

        Raises:
            ValueError: If the buffer settings are invalid, or the sample
                period is not below the params' `arrival_tie_sec` (FCFS would
                then be quantized at the scale of its own tie threshold).
        """
        params = params_source.params
        if params is not None and sample_period_sec >= params.arrival_tie_sec:
            raise ValueError(
                f"shadow sample_period_sec {sample_period_sec} must be below "
                f"classical arrival_tie_sec {params.arrival_tie_sec}"
            )
        self._source = params_source
        self._zones = tuple(zones)
        self._buffer = SnapshotRingBuffer(window_sec, sample_period_sec)
        self._window_sec = window_sec
        self._sample_period_sec = sample_period_sec
        self._resolve_fn = resolve_fn
        self._compare_fn = compare_fn
        self._retreat_context = retreat_context
        self._episode_index: int | None = None
        self._episode_analyses = 0
        self._feed_errors = 0
        self._last_feed_error: str | None = None

    @property
    def params_error(self) -> str | None:
        """Why the shadow cannot run on frozen params, or None when it can."""
        return self._source.error

    def observe(
        self, snapshot: SceneSnapshot, goal_of: GoalLookup, held_of: HeldLookup | None = None
    ) -> None:
        """Feed one received scene into the buffer; never raises.

        Dropped frames (M1's late-frame suppression) and robot-less scenes are
        skipped: either would become the newest frame and classify as `none`.
        A conversion failure is counted and reported in the next record.

        Args:
            snapshot: Scene as received on the scene-state topic.
            goal_of: Registry lookup of a robot's effective goal.
            held_of: Registry lookup of whether a robot is held back; None
                marks none held.
        """
        try:
            if snapshot.dropped_frame or not snapshot.robots:
                return
            if not self._buffer.accepts(snapshot.stamp):
                return
            self._buffer.add(snapshot_to_frame(snapshot, goal_of, held_of))
        except Exception as exc:  # the shadow must never fail a scene callback
            self._feed_errors += 1
            self._last_feed_error = f"{type(exc).__name__}: {exc}"

    def evaluate(
        self,
        request_id: str,
        snapshot: SceneSnapshot,
        goal_of: GoalLookup,
        episode_index: int,
        held_of: HeldLookup | None = None,
    ) -> ShadowClassicalRecord:
        """Compute Arm B's answer on the evidence of one analysis; never raises.

        Args:
            request_id: The analysis the VLM request was minted for.
            snapshot: The scene that request was built from.
            goal_of: Registry lookup of a robot's effective goal.
            episode_index: M5's congestion-episode index for this analysis.
            held_of: Registry lookup of whether a robot is held back; None
                marks none held.

        Returns:
            Record with the classical decision, or with `shadow_error` set.
        """
        prior_attempts = self._next_prior_attempts(episode_index)
        feed_errors, last_feed_error = self._feed_errors, self._last_feed_error
        self._feed_errors, self._last_feed_error = 0, None
        return self._evaluate(
            request_id,
            snapshot,
            goal_of,
            prior_attempts,
            "episode_analyses",
            feed_errors,
            last_feed_error,
            held_of,
        )

    def evaluate_probe(
        self,
        request_id: str,
        snapshot: SceneSnapshot,
        goal_of: GoalLookup,
        held_of: HeldLookup | None = None,
    ) -> ShadowClassicalRecord:
        """Compute Arm B's answer for a T0 log-only probe; never raises.

        Unlike `evaluate`, this leaves the shadow's state alone: the probe is
        not counted as an episode attempt (`prior_attempts` is 0) and pending
        feed errors are reported without being consumed, so a probe between
        two triggered analyses cannot change what the second one records.

        Args:
            request_id: The probe's request id.
            snapshot: The scene the probe request was built from.
            goal_of: Registry lookup of a robot's effective goal.
            held_of: Registry lookup of whether a robot is held back; None
                marks none held.

        Returns:
            Record with the classical decision, or with `shadow_error` set.
        """
        return self._evaluate(
            request_id,
            snapshot,
            goal_of,
            0,
            "t0_probe",
            self._feed_errors,
            self._last_feed_error,
            held_of,
        )

    def _evaluate(
        self,
        request_id: str,
        snapshot: SceneSnapshot,
        goal_of: GoalLookup,
        prior_attempts: int,
        prior_attempts_source: str,
        feed_errors: int,
        last_feed_error: str | None,
        held_of: HeldLookup | None = None,
    ) -> ShadowClassicalRecord:
        params = self._source.params
        base: dict[str, Any] = {
            "request_id": request_id,
            "params_path": self._source.path,
            "params_section_present": self._source.section_present,
            "params": params,
            "prior_attempts": prior_attempts,
            "prior_attempts_source": prior_attempts_source,
            "zone_ids": [zone.zone_id for zone in self._zones],
            "window_sec": self._window_sec,
            "sample_period_sec": self._sample_period_sec,
            "frame_count": 0,
            "oldest_stamp": None,
            "latest_stamp": None,
            "decision": None,
            "classification": None,
            "passing_order": None,
            "feed_errors": feed_errors,
            "last_feed_error": last_feed_error,
        }
        try:
            latest = None
            if not snapshot.dropped_frame and snapshot.robots:
                latest = snapshot_to_frame(snapshot, goal_of, held_of)
            frames = self._buffer.frames(latest)
            if frames:
                base.update(
                    frame_count=len(frames),
                    oldest_stamp=frames[0].stamp,
                    latest_stamp=frames[-1].stamp,
                )
            if params is None:
                return ShadowClassicalRecord(**base, shadow_error=self._source.error)
            if not frames:
                return ShadowClassicalRecord(
                    **base, shadow_error="no snapshot frames with robots to classify"
                )
            resolution = self._resolve_fn(frames, self._zones, params, prior_attempts)
        except Exception as exc:  # recorded, never raised into the analysis
            return ShadowClassicalRecord(**base, shadow_error=f"{type(exc).__name__}: {exc}")
        resolved = {
            **base,
            "decision": resolution.decision,
            "classification": resolution.classification,
            "passing_order": resolution.passing_order,
        }
        errors: list[str] = []
        try:
            resolved["classical_retreat"] = classical_retreat_answer(
                resolution.decision, frames[-1], self._retreat_context
            )
        except Exception as exc:  # a failed stage-2 answer must not discard the decision
            error = f"classical retreat failed: {type(exc).__name__}: {exc}"
            resolved["classical_retreat"] = ClassicalRetreat(status="error", reason=error)
            errors.append(error)
        try:
            resolved["censored_arrivals"] = find_censored_arrivals(
                frames, resolution.classification
            )
        except Exception as exc:  # a failed flag must not discard the decision
            errors.append(f"censoring check failed: {type(exc).__name__}: {exc}")
        return ShadowClassicalRecord(**resolved, shadow_error="; ".join(errors) or None)

    def finalize(
        self,
        record: ShadowClassicalRecord,
        vlm_decision: CongestionDecision | None,
        vlm_failure_reason: str | None,
        grounded_command: dict[str, Any] | None = None,
    ) -> ShadowClassicalRecord:
        """Attach the Arm A vs Arm B comparison once the VLM outcome is known.

        A VLM `congestion_detected=false` decision is compared like any other;
        only a missing decision (parse failure, refusal, worker crash) or a
        missing classical decision is not comparable. Never raises.

        Args:
            record: The record `evaluate` returned for this analysis.
            vlm_decision: The VLM decision, or None when M2 produced none.
            vlm_failure_reason: The pipeline's `failure_reason`, quoted when
                the decision is missing.
            grounded_command: The VLM arm's grounded command, which Arm B's
                stage-2 answer is compared against; None when none grounded.

        Returns:
            The record with `comparison` (and `classical_retreat`'s
            comparison) set, and `shadow_error` set if a comparison itself
            failed.
        """
        record = self._compare_retreat(record, grounded_command)
        if record.decision is None:
            reason = f"no classical decision: {record.shadow_error}"
            return record.model_copy(
                update={"comparison": ShadowComparison(comparable=False, reason=reason)}
            )
        if vlm_decision is None:
            reason = f"vlm decision=None: {vlm_failure_reason}"
            return record.model_copy(
                update={"comparison": ShadowComparison(comparable=False, reason=reason)}
            )
        try:
            classification = record.classification
            disagreement = self._compare_fn(
                vlm_decision,
                record.decision,
                classical_blocker_kind=(
                    None if classification is None else classification.blocker_kind
                ),
                classical_passing_order=record.passing_order,
            )
            comparison = ShadowComparison(comparable=True, disagreement=disagreement)
            return record.model_copy(update={"comparison": comparison})
        except Exception as exc:  # recorded, never raised into outcome handling
            error = f"{type(exc).__name__}: {exc}"
            return record.model_copy(
                update={
                    "comparison": ShadowComparison(
                        comparable=False, reason=f"comparison failed: {error}"
                    ),
                    "shadow_error": error,
                }
            )

    @staticmethod
    def _compare_retreat(
        record: ShadowClassicalRecord, grounded_command: dict[str, Any] | None
    ) -> ShadowClassicalRecord:
        retreat = record.classical_retreat
        if retreat is None:
            return record
        try:
            compared = compare_classical_retreat(retreat, grounded_command)
            return record.model_copy(update={"classical_retreat": compared})
        except Exception as exc:  # recorded, never raised into outcome handling
            error = f"classical retreat comparison failed: {type(exc).__name__}: {exc}"
            failed = retreat.model_copy(
                update={"comparable": False, "comparison_reason": error}
            )
            errors = "; ".join(e for e in (record.shadow_error, error) if e)
            return record.model_copy(
                update={"classical_retreat": failed, "shadow_error": errors}
            )

    def _next_prior_attempts(self, episode_index: int) -> int:
        if episode_index != self._episode_index:
            self._episode_index = episode_index
            self._episode_analyses = 0
        prior = self._episode_analyses
        self._episode_analyses += 1
        return prior


def format_shadow_log(record: ShadowClassicalRecord) -> str:
    """Render the one-line-per-analysis shadow summary for the M5 log.

    Args:
        record: A finalized shadow record.

    Returns:
        `shadow request=... scenario=... strategy=... yield=... disagree=...`,
        with `disagree=n/a` when not comparable and an `error=` suffix when
        the shadow failed.
    """
    scenario = "none" if record.classification is None else record.classification.scenario
    strategy = "none" if record.decision is None else record.decision.strategy
    yielder = None if record.decision is None else record.decision.yield_robot
    comparison = record.comparison
    if comparison is None or comparison.disagreement is None:
        disagree = "n/a"
    else:
        disagree = "true" if comparison.disagreement.any_disagreement else "false"
    line = (
        f"shadow request={record.request_id} scenario={scenario} strategy={strategy} "
        f"yield={yielder or 'none'} disagree={disagree}"
    )
    if record.shadow_error is not None:
        line += f" error={record.shadow_error}"
    return line
