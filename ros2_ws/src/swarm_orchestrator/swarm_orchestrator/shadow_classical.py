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
from reasoning.vlm.models import CongestionDecision, RobotStateInput, SnapshotFrame
from swarm_orchestrator.models import SceneSnapshot

GoalLookup = Callable[[str], tuple[float, float] | None]
ResolveFn = Callable[..., ClassicalResolution]
CompareFn = Callable[[CongestionDecision, CongestionDecision], DisagreementRecord]


def snapshot_to_frame(snapshot: SceneSnapshot, goal_of: GoalLookup) -> SnapshotFrame:
    """Project one M5 scene snapshot into the reasoning-side `SnapshotFrame`.

    Args:
        snapshot: M1 scene as M5 received it.
        goal_of: Registry lookup of a robot's effective goal; M1's SceneState
            goal is not carried by `RobotView`, so the task registry M5 owns is
            the goal source. Returns None for a robot with no assignment.

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
    return SnapshotFrame(stamp=snapshot.stamp, robots=robots)


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
    prior_attempts_source: Literal["episode_analyses"] = "episode_analyses"
    zone_ids: list[str]
    window_sec: float
    sample_period_sec: float
    # Extent of the history actually classified. A robot already inside the
    # zone at `oldest_stamp` has a censored arrival (FCFS then falls back to
    # commitment and robot_id), detectable offline from these fields.
    frame_count: int = Field(ge=0)
    oldest_stamp: float | None
    latest_stamp: float | None
    decision: CongestionDecision | None
    classification: ClassicalClassification | None
    passing_order: list[str] | None
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
        self._episode_index: int | None = None
        self._episode_analyses = 0
        self._feed_errors = 0
        self._last_feed_error: str | None = None

    @property
    def params_error(self) -> str | None:
        """Why the shadow cannot run on frozen params, or None when it can."""
        return self._source.error

    def observe(self, snapshot: SceneSnapshot, goal_of: GoalLookup) -> None:
        """Feed one received scene into the buffer; never raises.

        Dropped frames (M1's late-frame suppression) and robot-less scenes are
        skipped: either would become the newest frame and classify as `none`.
        A conversion failure is counted and reported in the next record.

        Args:
            snapshot: Scene as received on the scene-state topic.
            goal_of: Registry lookup of a robot's effective goal.
        """
        try:
            if snapshot.dropped_frame or not snapshot.robots:
                return
            if not self._buffer.accepts(snapshot.stamp):
                return
            self._buffer.add(snapshot_to_frame(snapshot, goal_of))
        except Exception as exc:  # the shadow must never fail a scene callback
            self._feed_errors += 1
            self._last_feed_error = f"{type(exc).__name__}: {exc}"

    def evaluate(
        self,
        request_id: str,
        snapshot: SceneSnapshot,
        goal_of: GoalLookup,
        episode_index: int,
    ) -> ShadowClassicalRecord:
        """Compute Arm B's answer on the evidence of one analysis; never raises.

        Args:
            request_id: The analysis the VLM request was minted for.
            snapshot: The scene that request was built from.
            goal_of: Registry lookup of a robot's effective goal.
            episode_index: M5's congestion-episode index for this analysis.

        Returns:
            Record with the classical decision, or with `shadow_error` set.
        """
        prior_attempts = self._next_prior_attempts(episode_index)
        feed_errors, last_feed_error = self._feed_errors, self._last_feed_error
        self._feed_errors, self._last_feed_error = 0, None
        params = self._source.params
        base: dict[str, Any] = {
            "request_id": request_id,
            "params_path": self._source.path,
            "params_section_present": self._source.section_present,
            "params": params,
            "prior_attempts": prior_attempts,
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
                latest = snapshot_to_frame(snapshot, goal_of)
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
            return ShadowClassicalRecord(
                **{
                    **base,
                    "decision": resolution.decision,
                    "classification": resolution.classification,
                    "passing_order": resolution.passing_order,
                }
            )
        except Exception as exc:  # recorded, never raised into the analysis
            return ShadowClassicalRecord(**base, shadow_error=f"{type(exc).__name__}: {exc}")

    def finalize(
        self,
        record: ShadowClassicalRecord,
        vlm_decision: CongestionDecision | None,
        vlm_failure_reason: str | None,
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

        Returns:
            The record with `comparison` set, and `shadow_error` set if the
            comparison itself failed.
        """
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
            disagreement = self._compare_fn(vlm_decision, record.decision)
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
