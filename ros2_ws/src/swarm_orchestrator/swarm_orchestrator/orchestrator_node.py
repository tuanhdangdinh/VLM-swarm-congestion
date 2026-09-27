"""Thin ROS2 node wiring M5's pure logic to topics, services, and a worker thread."""
from __future__ import annotations

import json
import os
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rclpy
import yaml
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from swarm_interfaces.msg import CoordinationCommand, CoordinationStatus
from swarm_interfaces.srv import TriggerCongestionAnalysis

from reasoning.rag.command_grounder import filter_command_robot_ids, ground_reasoner_result
from reasoning.vlm import (
    RetreatChooser,
    backend_section,
    build_backend,
    build_retreat_choice_backend,
    describe_effective_sampling,
    resolve_reasoner_config,
)
from reasoning.vlm.models import (
    AnthropicBackendConfig,
    FailureContext,
    GeminiBackendConfig,
    LlamaServerBackendConfig,
    OpenAIBackendConfig,
    ReasonerConfig,
    ReasonerRequest,
    RobotPresentationOrder,
)
from reasoning.vlm.reasoner import Reasoner
from swarm_orchestrator.arrival import ArrivalDecision, ArrivalGate
from swarm_orchestrator.command_lifecycle import (
    AttemptMemory,
    CommandRecord,
    CommandTracker,
    CooldownTracker,
    summarize_executed_strategy,
    summarize_outcome,
)
from swarm_orchestrator.congestion_detector import CongestionDetector
from swarm_orchestrator.models import (
    CongestionEvent,
    OrchestratorConfig,
    PipelineOutcome,
    load_config,
    parse_scene_snapshot,
)
from swarm_orchestrator.presentation_order import (
    EpisodeOrderTracker,
    PresentationOrderPolicy,
    derive_order_seed,
)
from swarm_orchestrator.probe import (
    T0_PROBE_REASON,
    ProbeLedger,
    ProbeScheduler,
    probe_block_reason,
)
from swarm_orchestrator.reasoning_pipeline import (
    GroundingParamsSource,
    InProcessPipeline,
    LatestRawFrame,
    ReasoningPipeline,
    append_scene_log,
    attach_registry_assignments,
    build_failed_outcome,
    build_failure_contexts,
    build_reasoner_request,
    dump_frame_png,
    fan_out_command,
    load_grounding_source,
    raw_frame_dump_path,
    raw_frame_skew_sec,
    summarize_yield_grounding,
    write_decision_artifact,
)
from swarm_orchestrator.retreat_stage2 import format_stage2_log
from swarm_orchestrator.shadow_classical import (
    ClassicalShadow,
    ShadowClassicalRecord,
    format_shadow_log,
    load_shadow_params,
)
from swarm_orchestrator.stage2_marks import CandidateMarker, stage2_image_path
from swarm_orchestrator.state_machine import (
    DirectiveKind,
    OrchestratorState,
    OrchestratorStateMachine,
)
from swarm_orchestrator.task_registry import TaskRegistry


def _build_candidate_marker(config: OrchestratorConfig) -> CandidateMarker:
    """Load M1's calibration for the stage-2 letters; never raises.

    The default is the file perception.launch.py hands M1, so the letters are
    placed with the homography M1 measured the robot positions with.
    """
    path = config.stage2_calibration_path
    if path is None:
        try:
            from ament_index_python.packages import get_package_share_directory

            share = get_package_share_directory("swarm_perception")
        except Exception as exc:  # unmarked stage 2 beats a stopped M5
            return CandidateMarker.unavailable(
                f"calibration_unavailable: swarm_perception share not found: {exc}"
            )
        path = str(Path(share) / "config" / "calibration.yaml")
    return CandidateMarker.from_path(path)


def _build_default_pipeline(
    config: OrchestratorConfig,
    grounding: GroundingParamsSource,
    marker: CandidateMarker | None = None,
) -> ReasoningPipeline:
    reasoner_config, backend_config = _load_vlm_config(config.reasoning_backend_id)
    backend = build_backend(config.reasoning_backend_id, backend_config)
    # Described from the configs, not the backend, so every decision artifact
    # states the sampling parameters the call ran under (FR5.3.11).
    reasoner = Reasoner(
        backend,
        reasoner_config,
        describe_effective_sampling(reasoner_config, backend_config),
    )
    # Stage 2 runs on the stage-1 backend and config (timeout, attempt budget),
    # except for a mock, which answers stage 2 only from its own script.
    stage2_backend = build_retreat_choice_backend(config.reasoning_backend_id, backend)
    return InProcessPipeline(
        reasoner=reasoner,
        ground_fn=ground_reasoner_result,
        scene_geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        grounding_params=grounding.params,
        retreat_chooser=(
            None if stage2_backend is None else RetreatChooser(stage2_backend, reasoner_config)
        ),
        stage2_enabled=config.stage2_retreat_selection,
        candidate_marker=marker,
    )


def _build_shadow(config: OrchestratorConfig) -> ClassicalShadow | None:
    """Build the Arm B shadow, or None when disabled.

    Invalid `classical:` params raise here, stopping M5 at startup; a missing
    file or section is carried into every shadow record instead.
    """
    if not config.shadow_classical:
        return None
    return ClassicalShadow(
        load_shadow_params(Path(config.shadow_classical_params_path)),
        config.shadow_classical_zones,
        config.shadow_classical_window_sec,
        config.shadow_classical_sample_period_sec,
    )


@dataclass
class _PendingProbe:
    """One in-flight T0 probe; lives apart from the triggered-analysis slots."""

    request_id: str
    probe_index: int
    request: ReasonerRequest
    snapshot: Any
    future: Future[PipelineOutcome]
    shadow: ShadowClassicalRecord | None


def _raw_frame_qos() -> QoSProfile:
    """Best-effort, depth-1 QoS for the debug raw-camera subscription.

    The raw frame is evidence, not pipeline input: dropping one must never cost
    the node latency or memory, so nothing is queued or retransmitted.
    """
    return QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)


def _registry_qos() -> QoSProfile:
    return QoSProfile(
        depth=1,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        reliability=ReliabilityPolicy.RELIABLE,
    )


def _load_vlm_config(backend_id: str) -> tuple[ReasonerConfig, object | None]:
    path = Path("config/models.yaml")
    raw = yaml.safe_load(path.read_text()) if path.is_file() else {}
    vlm = (raw or {}).get("vlm", {})
    reasoner_config = resolve_reasoner_config(vlm, backend_id)

    backend_raw = backend_section(vlm, backend_id)
    if backend_id == "openai":
        backend_config = OpenAIBackendConfig(**backend_raw)
    elif backend_id == "llama_server":
        backend_config = LlamaServerBackendConfig(**backend_raw)
    elif backend_id == "anthropic":
        backend_config = AnthropicBackendConfig(**backend_raw)
    elif backend_id == "gemini":
        backend_config = GeminiBackendConfig(**backend_raw)
    elif backend_id == "mock":
        backend_config = None
    else:
        backend_config = backend_raw or None
    return reasoner_config, backend_config


class OrchestratorNode(Node):
    """Layer-2 controller: detect stalls, run reasoning off-thread, dispatch to M4."""

    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        pipeline: ReasoningPipeline | None = None,
    ) -> None:
        super().__init__("orchestrator_node")
        self.declare_parameter("config_file", "")
        self._config = config or self._load_config_from_param()
        # Fail fast: a missing file or an invalid `grounding:` section stops M5
        # here, since these parameters shape every command it dispatches.
        self._grounding = load_grounding_source(Path(self._config.grounding_params_path))
        # Only the default pipeline draws stage-2 letters; an injected one
        # brings its own marker (or none).
        self._marker = None if pipeline is not None else _build_candidate_marker(self._config)
        self._pipeline = pipeline or _build_default_pipeline(
            self._config, self._grounding, self._marker
        )

        self._detector = CongestionDetector(self._config)
        self._arrival = ArrivalGate(self._config, self._detector.mark_arrived)
        self._machine = OrchestratorStateMachine()
        self._tracker = CommandTracker()
        self._cooldown = CooldownTracker(self._config.cooldown_sec)
        self._attempts = AttemptMemory(self._config.failure_context_window_sec)
        self._registry = TaskRegistry()
        self._registry.load_initial(self._config)

        self._bridge = CvBridge()
        # rclpy.spin is single-threaded: _attempts and the _pending_* contexts are
        # touched only on the callback thread, and the worker reads captured locals.
        # A MultiThreadedExecutor would need a lock around them.
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._future: Future[PipelineOutcome] | None = None
        # Context attached to the in-flight request; consumed by _handle_outcome so
        # the decision artifact records exactly what the VLM was told.
        self._pending_failure_context: FailureContext | None = None
        self._pending_last_failed_context: FailureContext | None = None
        self._pending_request: ReasonerRequest | None = None
        self._pending_snapshot = None
        self._pending_distances: dict[str, float] = {}
        # Groups artifacts per M5 process; VGU_RUN_ID (set by the launcher) names
        # the scenario run across all modules.
        self._session_id = uuid.uuid4().hex
        self._run_id = os.environ.get("VGU_RUN_ID") or None
        self._order_seed = (
            self._config.prompt_robot_order_seed
            if self._config.prompt_robot_order_seed is not None
            else derive_order_seed(self._run_id, self._session_id)
        )
        self._episodes = EpisodeOrderTracker(
            PresentationOrderPolicy(
                mode=self._config.prompt_robot_order, seed=self._order_seed
            )
        )
        self._pending_episode_index: int | None = None
        self._shadow = _build_shadow(self._config)
        self._pending_shadow: ShadowClassicalRecord | None = None
        # T0 log-only probes. The ledger stays empty unless probe mode is on,
        # so the dispatch guard that reads it is inert by default.
        self._probe_ledger = ProbeLedger()
        self._probe: _PendingProbe | None = None
        self._probe_block: str | None = None
        self._probe_scheduler: ProbeScheduler | None = None
        self._probe_executor: ThreadPoolExecutor | None = None
        self._probe_order: PresentationOrderPolicy | None = None
        if self._config.t0_probe_mode:
            self._init_probe_mode()
        self._last_scene_log_at = float("-inf")
        self._frame_rgb = None
        self._frame_stamp: float | None = None
        self._raw_frame = LatestRawFrame()
        self._latest_snapshot = None
        # Monotonic receipt time of _latest_snapshot. M1 stamps are on a
        # different clock, so estimate age is measured from arrival here.
        self._latest_snapshot_at: float | None = None
        self.last_published_registry: str | None = None

        topics = self._config.topics
        self._cmd_pub = self.create_publisher(
            CoordinationCommand, topics["coordination_commands"], 10
        )
        self._tasks_pub = self.create_publisher(
            String, topics["coordination_tasks"], _registry_qos()
        )
        self.create_subscription(String, topics["scene_state"], self._on_scene_state, 10)
        self.create_subscription(Image, topics["annotated_frame"], self._on_frame, 10)
        if self._dumps_raw_frames():
            self.create_subscription(
                Image, self._config.raw_frame_topic, self._on_raw_frame, _raw_frame_qos()
            )
            self.get_logger().info(
                f"raw frame dumps enabled topic={self._config.raw_frame_topic}"
            )
        elif self._config.keep_raw_frames:
            self.get_logger().warning(
                "keep_raw_frames ignored: it requires keep_debug_frames, which owns "
                "frame retention"
            )
        self.create_subscription(
            CoordinationStatus, topics["coordination_status"], self._on_status, 10
        )
        self.create_service(
            TriggerCongestionAnalysis, topics["trigger_analysis"], self._on_trigger_analysis
        )
        self.create_timer(0.5, self._on_timer)

        Path(self._config.frame_dump_dir).mkdir(parents=True, exist_ok=True)
        Path(self._config.decision_log_dir).mkdir(parents=True, exist_ok=True)
        if self._config.scene_log_dir:
            Path(self._config.scene_log_dir).mkdir(parents=True, exist_ok=True)
        self.get_logger().info(f"session_id={self._session_id} run_id={self._run_id}")
        self.get_logger().info(
            f"grounding mode={self._grounding.params.mode} params={self._grounding.path} "
            f"section_present={self._grounding.section_present} "
            f"stage2_retreat_selection={self._config.stage2_retreat_selection}"
        )
        if self._marker is not None:
            if self._marker.available:
                self.get_logger().info("stage2 marks enabled: candidate letters drawn")
            else:
                self.get_logger().warning(
                    f"stage2 marks unavailable, stage 2 gets the unmarked frame: "
                    f"{self._marker.unavailable_reason}"
                )
        if not self._grounding.section_present:
            self.get_logger().warning(
                f"no `grounding:` section in {self._grounding.path}: grounding on the "
                "legacy defaults"
            )
        if self._shadow is not None:
            self.get_logger().info(
                f"classical shadow enabled params={self._config.shadow_classical_params_path} "
                f"window_sec={self._config.shadow_classical_window_sec} "
                f"sample_period_sec={self._config.shadow_classical_sample_period_sec}"
            )
            if self._shadow.params_error is not None:
                self.get_logger().warning(
                    f"classical shadow degraded: {self._shadow.params_error}"
                )
        self._publish_registry()

    # ---- config ----

    def _init_probe_mode(self) -> None:
        if not callable(getattr(self._pipeline, "analyze", None)):
            raise ValueError(
                "t0_probe_mode requires a pipeline with a stage-1 analyze(); "
                f"{type(self._pipeline).__name__} has none"
            )
        self._probe_scheduler = ProbeScheduler(
            self._config.t0_probe_interval_sec,
            self._config.t0_probe_max_probes,
            time.monotonic(),
        )
        # Its own worker, so a real trigger never queues behind a probe's VLM call.
        self._probe_executor = ThreadPoolExecutor(max_workers=1)
        # Each probe draws its own order from the same seeded policy, indexed
        # by probe number; EpisodeOrderTracker is never touched, so the draws
        # of real congestion episodes are the same with probes on or off.
        self._probe_order = PresentationOrderPolicy(
            mode=self._config.prompt_robot_order, seed=self._order_seed
        )
        self.get_logger().info(
            f"t0 probe mode enabled (log-only) interval_sec={self._config.t0_probe_interval_sec} "
            f"max_probes={self._config.t0_probe_max_probes}"
        )

    def _load_config_from_param(self) -> OrchestratorConfig:
        path = self.get_parameter("config_file").get_parameter_value().string_value
        if not path:
            raise ValueError("config_file parameter is required")
        with open(path) as handle:
            return load_config(yaml.safe_load(handle))

    # ---- callbacks (thin) ----

    def _on_frame(self, msg: Image) -> None:
        self._frame_rgb = self._bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")
        self._frame_stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

    def _on_raw_frame(self, msg: Image) -> None:
        self._raw_frame.update(
            self._bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8"),
            msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
        )

    def _on_scene_state(self, msg: String) -> None:
        try:
            snapshot = parse_scene_snapshot(msg.data)
        except ValueError as exc:
            self.get_logger().warning(f"skipping malformed SceneState: {exc}")
            return
        self._latest_snapshot = snapshot
        now = time.monotonic()
        self._latest_snapshot_at = now
        if self._shadow is not None:
            # Never raises; ingest failures surface in the next shadow record.
            self._shadow.observe(snapshot, self._effective_goal)
        if (
            self._config.scene_log_dir
            and now - self._last_scene_log_at >= self._config.scene_log_period_sec
        ):
            self._last_scene_log_at = now
            try:
                append_scene_log(
                    Path(self._config.scene_log_dir) / f"{self._session_id}.jsonl",
                    snapshot,
                    self._session_id,
                    self._run_id,
                    now,
                )
            except OSError as exc:
                self.get_logger().error(f"scene log write failed: {exc}")
        # Before the detector, so a late-accepted arrival suppresses stall
        # evidence from this same scene rather than the next one.
        for decision in self._arrival.on_scene(snapshot, self._effective_goal):
            self._apply_arrival(decision)
        event = self._detector.update(snapshot, self._effective_goal, now)
        if event is None:
            return
        frame_ready = self._frame_is_fresh(snapshot.stamp)
        directive = self._machine.on_event(
            event,
            cooldown_robots=self._cooldown.active_robots(now),
            busy_robots=self._busy_robots(),
            now=now,
            frame_ready=frame_ready,
        )
        if directive.kind is DirectiveKind.START_ANALYSIS:
            distances = {rid: round(d, 2) for rid, d in event.distance_to_goal_m.items()}
            # Logged after the submit because the episode's presentation order is
            # resolved there, and the line must name the order actually rendered.
            order = self._submit_pipeline(
                directive.request_id, snapshot, event.involved_robots, event.distance_to_goal_m
            )
            self.get_logger().info(
                f"starting analysis request={directive.request_id} robots={event.involved_robots} "
                f"reason={event.reason} order={order} distance_to_goal_m={distances}"
            )
        elif directive.kind is DirectiveKind.SUPPRESSED:
            self.get_logger().info(
                f"trigger suppressed robots={event.involved_robots} frame_ready={frame_ready}"
            )

    def _on_status(self, msg: CoordinationStatus) -> None:
        if msg.command_id == "base_mission":
            # M4's coordination client reports Nav2 success on a base goal; not a
            # coordination command, so it never reaches the tracker.
            if msg.status.upper() == "COMPLETED":
                goal = self._effective_goal(msg.robot_id)
                if goal is not None:
                    estimate, age = self._latest_estimate(msg.robot_id)
                    self._apply_arrival(
                        self._arrival.on_nav2_success(msg.robot_id, goal, estimate, age)
                    )
            return
        self._tracker.apply_status(msg.command_id, msg.robot_id, msg.status)
        if self._tracker.is_resolved(msg.command_id):
            self._resolve_command(msg.command_id)

    def _on_trigger_analysis(
        self,
        request: TriggerCongestionAnalysis.Request,
        response: TriggerCongestionAnalysis.Response,
    ) -> TriggerCongestionAnalysis.Response:
        """Operator/test hook to force an analysis cycle on the latest snapshot (spec §5).

        Bypasses the progress detector and the per-robot cooldown (a manual override),
        but still respects single-in-flight and active-command gating in the state
        machine, and the frame-freshness check.
        """
        snapshot = self._latest_snapshot
        if snapshot is None or not snapshot.robots:
            response.accepted = False
            response.analysis_id = ""
            response.message = "no scene snapshot available"
            return response
        now = time.monotonic()
        robots = [r.robot_id for r in snapshot.robots]
        event = CongestionEvent(
            involved_robots=robots,
            stall_durations_sec={rid: 0.0 for rid in robots},
            detected_at=now,
            reason=f"manual trigger: {request.reason}",
        )
        directive = self._machine.on_event(
            event,
            cooldown_robots=set(),  # operator override bypasses cooldown
            busy_robots=self._busy_robots(),
            now=now,
            frame_ready=self._frame_is_fresh(snapshot.stamp),
        )
        if directive.kind is DirectiveKind.START_ANALYSIS:
            self._submit_pipeline(directive.request_id, snapshot, event.involved_robots, {})
            response.accepted = True
            response.analysis_id = directive.request_id
            response.message = "analysis started"
        else:
            response.accepted = False
            response.analysis_id = ""
            response.message = f"trigger rejected: {directive.kind.value}"
        return response

    def _on_timer(self) -> None:
        now = time.monotonic()
        for command_id in self._tracker.check_timeouts(now):
            self.get_logger().warning(f"command {command_id} timed out")
            self._resolve_command(command_id)
        if self._future is not None and self._future.done():
            try:
                outcome = self._future.result()
            except Exception as exc:
                # Worker raised before producing an outcome (e.g. frame dump failed).
                # Never leave the machine stuck in ANALYZING — resolve the cycle.
                self.get_logger().error(f"reasoning worker failed: {exc}")
                outcome = build_failed_outcome("unknown", f"worker raised: {exc}")
            self._future = None
            self._handle_outcome(outcome, now)
        self._harvest_probe()
        if self._probe_scheduler is not None:
            self._maybe_start_probe(now)

    # ---- pipeline lifecycle ----

    def _submit_pipeline(
        self,
        request_id: str,
        snapshot,
        robots: list[str],
        distance_to_goal_m: dict[str, float],
    ) -> RobotPresentationOrder:
        """Build the request for one analysis and hand it to the worker thread.

        Args:
            request_id: Identifier the state machine minted for this cycle.
            snapshot: The M1 scene the request is built from.
            robots: Robots the congestion event involves.
            distance_to_goal_m: The detector's per-robot distance at trigger time.

        Returns:
            The presentation order this episode renders robots in, for the
            caller's log line.
        """
        frame = self._frame_rgb
        downscale = self._config.frame_downscale_width
        image_path = str(Path(self._config.frame_dump_dir) / f"{request_id}.png")
        now = time.monotonic()
        contexts = self._attempts.contexts_for(robots, now)
        failure_context, last_failed_context = build_failure_contexts(contexts, now)
        attempt, failed = contexts.latest, contexts.last_failed
        if attempt is not None:
            self.get_logger().info(
                f"request={request_id} failure_context attached command={attempt.command_id} "
                f"strategy={attempt.strategy} executed={attempt.executed_strategy} "
                f"outcome={attempt.outcome_status}"
            )
        if failed is not None:
            self.get_logger().info(
                f"request={request_id} last_failed_context attached "
                f"command={failed.command_id} strategy={failed.strategy} "
                f"yield_robot={failed.yield_robot} executed={failed.executed_strategy} "
                f"outcome={failed.outcome_status}"
            )
        episode_index, order = self._episodes.order_for(robots)
        # Registry goals/tasks ride on the snapshot so the stored `scene` alone
        # reconstructs the prompt; the shadow keeps its own goal lookup.
        snapshot = attach_registry_assignments(
            snapshot, self._effective_goal, self._registry.mission_task
        )
        # Built here, not in the worker, so the artifact can record the exact request.
        request = build_reasoner_request(
            request_id,
            snapshot,
            image_path,
            failure_context=failure_context,
            last_failed_context=last_failed_context,
            include_pairwise_geometry=self._config.prompt_pairwise_geometry,
            static_obstacles=self._config.static_obstacles,
            include_static_obstacles=self._config.prompt_static_obstacles,
            robot_presentation_order=order,
        )
        self._pending_failure_context = failure_context
        self._pending_last_failed_context = last_failed_context
        self._pending_request = request
        self._pending_snapshot = snapshot
        self._pending_distances = dict(distance_to_goal_m)
        self._pending_episode_index = episode_index
        # Snapshotted here, not read inside the worker: a newer camera message
        # may land before the worker runs, and the dump must be the frame whose
        # skew was logged.
        raw_dump = self._raw_frame_dump(request_id)

        def task() -> PipelineOutcome:
            dump_frame_png(frame, image_path, downscale)
            if raw_dump is not None:
                raw_frame, raw_path = raw_dump
                try:
                    # Same downscale as the annotated dump, so annotation is the
                    # only difference between the pair.
                    dump_frame_png(raw_frame, raw_path, downscale)
                except Exception as exc:  # debug evidence must never fail a cycle
                    self.get_logger().error(f"raw frame dump failed: {exc}")
            return self._pipeline.run(request)

        self._future = self._executor.submit(task)
        # After the submit so the shadow cannot delay the VLM call, and on the
        # same snapshot and episode the request was built from. It reads
        # nothing the request or dispatch path reads.
        self._pending_shadow = None
        if self._shadow is not None:
            try:
                self._pending_shadow = self._shadow.evaluate(
                    request_id, snapshot, self._effective_goal, episode_index
                )
            except Exception as exc:  # evaluate() records its own errors; last resort
                self.get_logger().error(
                    f"shadow request={request_id} evaluate failed: {type(exc).__name__}: {exc}"
                )
        return order

    def _handle_outcome(self, outcome: PipelineOutcome, now: float) -> None:
        failure_context = self._pending_failure_context
        last_failed_context = self._pending_last_failed_context
        request, snapshot = self._pending_request, self._pending_snapshot
        distances = self._pending_distances
        episode_index = self._pending_episode_index
        self._pending_failure_context = None
        self._pending_last_failed_context = None
        self._pending_request = None
        self._pending_snapshot = None
        self._pending_distances = {}
        self._pending_episode_index = None
        shadow_block = self._finalize_shadow(outcome)
        try:
            artifact_path = write_decision_artifact(
                self._config.decision_log_dir,
                outcome,
                failure_context=failure_context,
                last_failed_context=last_failed_context,
                request=request,
                snapshot=snapshot,
                distance_to_goal_m=distances,
                run_id=self._run_id,
                session_id=self._session_id,
                prompt_robot_order_mode=self._config.prompt_robot_order,
                prompt_robot_order_seed=self._order_seed,
                episode_index=episode_index,
                grounding_yield_feasibility=self._config.grounding_yield_feasibility,
                shadow_classical=shadow_block,
                grounding_source=self._grounding,
            )
            self.get_logger().info(f"decision artifact written: {artifact_path}")
        except OSError as exc:
            self.get_logger().error(f"decision artifact write failed: {exc}")

        # Surfaced in the live log too: the gate changes which robot executes,
        # so a run that swapped must be legible without opening the artifact.
        yield_grounding = summarize_yield_grounding(outcome.grounded_command)
        if yield_grounding.grounded_from is not None:
            self.get_logger().info(
                f"yield re-grounded request={outcome.request_id} "
                f"from={yield_grounding.grounded_from} to={yield_grounding.grounded_to} "
                f"reason={yield_grounding.regrounded_reason}"
            )
        if yield_grounding.refusal_reason is not None:
            self.get_logger().info(
                f"yield refused request={outcome.request_id} "
                f"reason={yield_grounding.refusal_reason}"
            )
        if outcome.stage2 is not None:
            self.get_logger().info(format_stage2_log(outcome.request_id, outcome.stage2))

        directive = self._machine.on_outcome(outcome, now)
        if directive.kind is DirectiveKind.DISPATCH and outcome.grounded_command is not None:
            self._dispatch(outcome)
        elif directive.kind is DirectiveKind.COOLDOWN:
            self._cooldown.start(directive.robots, now)
            self.get_logger().info(
                f"request={outcome.request_id} no dispatch "
                f"stage={outcome.terminal_stage.value} reason={outcome.failure_reason}"
            )
        self._cleanup_frame(outcome.request_id)

    def _finalize_shadow(self, outcome: PipelineOutcome) -> dict[str, Any] | None:
        """Compare the pending shadow with the VLM outcome and log one line.

        Returns the artifact block, or None when the shadow is disabled. Any
        failure here is recorded in the block, never raised: the outcome must
        reach the artifact write and the state machine unchanged.
        """
        record = self._pending_shadow
        self._pending_shadow = None
        return self._finalize_shadow_record(record, outcome)

    def _finalize_shadow_record(
        self, record: ShadowClassicalRecord | None, outcome: PipelineOutcome
    ) -> dict[str, Any] | None:
        if self._shadow is None:
            return None
        try:
            if record is None:
                raise RuntimeError("no shadow record was computed for this analysis (see log)")
            final = self._shadow.finalize(
                record, outcome.reasoner_result.decision, outcome.failure_reason
            )
            self.get_logger().info(format_shadow_log(final))
            return final.model_dump(mode="json")
        except Exception as exc:  # recorded in the artifact and the log
            error = f"{type(exc).__name__}: {exc}"
            self.get_logger().error(
                f"shadow request={outcome.request_id} finalize failed: {error}"
            )
            return {"request_id": outcome.request_id, "shadow_error": error}

    def _dispatch(self, outcome: PipelineOutcome) -> None:
        # Second no-dispatch layer: the probe path never reaches here, but a
        # probe outcome that somehow did is refused before anything is sent.
        if self._probe_ledger.is_probe(outcome.request_id):
            self.get_logger().error(
                f"refusing dispatch request={outcome.request_id}: "
                "t0 probe outcomes are log-only"
            )
            return
        grounded = filter_command_robot_ids(
            outcome.grounded_command,
            set(self._config.initial_tasks),
        )
        messages = fan_out_command(grounded, self._config.command_timeout_sec)
        robot_ids = [m[1] for m in messages]
        timeout = messages[0][4] if messages else self._config.command_timeout_sec
        self._tracker.register(
            CommandRecord(
                command_id=grounded["command_id"],
                robot_ids=robot_ids,
                dispatched_at=time.monotonic(),
                timeout_sec=timeout,
                fallback=grounded.get("fallback", ""),
                request_id=outcome.request_id,
            )
        )
        strategy = outcome.reasoner_result.decision.strategy
        yield_robot = next((m[1] for m in messages if m[2] == "yield"), None)
        self._attempts.record(
            grounded["command_id"],
            robot_ids,
            strategy,
            yield_robot,
            time.monotonic(),
            executed_strategy=summarize_executed_strategy([m[2] for m in messages], strategy),
        )
        for command_id, robot_id, action, params_json, _timeout in messages:
            msg = CoordinationCommand()
            msg.command_id = command_id
            msg.robot_id = robot_id
            msg.action = action
            # Inject the robot's current task goal into reroute params so the
            # command_bus can resume navigation to the original goal when M3
            # did not supply explicit waypoints (the common case for this grounder).
            goal = self._effective_goal(robot_id) or (0.0, 0.0)
            if action == "reroute":
                p = json.loads(params_json or "{}")
                p.setdefault("goal", {"x": goal[0], "y": goal[1]})
                params_json = json.dumps(p)
            msg.parameters_json = params_json
            msg.timeout_sec = _timeout
            self._cmd_pub.publish(msg)
            self._registry.set_override(robot_id, action, goal, command_id)
            self.get_logger().info(
                f"dispatch request={outcome.request_id} command={command_id} robot={robot_id}"
            )
        self._publish_registry()

    # ---- T0 log-only probes ----

    def _maybe_start_probe(self, now: float) -> None:
        """Start a due probe on the latest scene unless a real analysis runs."""
        scheduler = self._probe_scheduler
        if scheduler is None or not scheduler.due(now):
            return
        snapshot = self._latest_snapshot
        has_scene = snapshot is not None and bool(snapshot.robots)
        blocked = probe_block_reason(
            analysis_in_flight=(
                self._future is not None
                or self._machine.state is not OrchestratorState.MONITORING
            ),
            probe_in_flight=self._probe is not None,
            has_scene=has_scene,
            frame_ready=has_scene and self._frame_is_fresh(snapshot.stamp),
            snapshot_age_sec=(
                None if self._latest_snapshot_at is None else now - self._latest_snapshot_at
            ),
            max_snapshot_age_sec=self._config.t0_probe_max_snapshot_age_sec,
        )
        if blocked is not None:
            # Logged once per reason, not on every 0.5 s tick it stays blocked.
            if blocked != self._probe_block:
                self.get_logger().info(f"t0 probe deferred reason={blocked}")
            self._probe_block = blocked
            return
        self._probe_block = None
        probe_index = scheduler.record_probe(now)
        request_id = uuid.uuid4().hex
        self._probe_ledger.register(request_id)
        robots = sorted(r.robot_id for r in snapshot.robots)
        order = self._submit_probe(request_id, probe_index, snapshot)
        self.get_logger().info(
            f"starting analysis request={request_id} robots={robots} "
            f"reason={T0_PROBE_REASON} order={order} probe=true probe_index={probe_index}"
        )

    def _submit_probe(
        self, request_id: str, probe_index: int, snapshot
    ) -> RobotPresentationOrder:
        """Hand one probe's stage-1 analysis to the probe worker.

        Built like a triggered request, except that it carries no failure
        context: that block tells the VLM congestion was re-detected, which an
        off-trigger probe has not established, and reading AttemptMemory can
        clear it for the next real analysis.

        Returns:
            The presentation order the probe renders robots in.
        """
        image_path = str(Path(self._config.frame_dump_dir) / f"{request_id}.png")
        order = self._probe_order.order_for_episode(probe_index)
        snapshot = attach_registry_assignments(
            snapshot, self._effective_goal, self._registry.mission_task
        )
        request = build_reasoner_request(
            request_id,
            snapshot,
            image_path,
            include_pairwise_geometry=self._config.prompt_pairwise_geometry,
            static_obstacles=self._config.static_obstacles,
            include_static_obstacles=self._config.prompt_static_obstacles,
            robot_presentation_order=order,
        )
        frame = self._frame_rgb
        downscale = self._config.frame_downscale_width
        raw_dump = self._raw_frame_dump(request_id)
        # Bound here: the probe path holds the stage-1 entry point only, so it
        # has no route to grounding or dispatch (first no-dispatch layer).
        analyze = self._pipeline.analyze

        def task() -> PipelineOutcome:
            dump_frame_png(frame, image_path, downscale)
            if raw_dump is not None:
                raw_frame, raw_path = raw_dump
                try:
                    dump_frame_png(raw_frame, raw_path, downscale)
                except Exception as exc:  # debug evidence must never fail a probe
                    self.get_logger().error(f"raw frame dump failed: {exc}")
            return analyze(request)

        future = self._probe_executor.submit(task)
        shadow = None
        if self._shadow is not None:
            try:
                shadow = self._shadow.evaluate_probe(request_id, snapshot, self._effective_goal)
            except Exception as exc:  # evaluate_probe records its own errors; last resort
                self.get_logger().error(
                    f"shadow request={request_id} evaluate failed: {type(exc).__name__}: {exc}"
                )
        self._probe = _PendingProbe(request_id, probe_index, request, snapshot, future, shadow)
        return order

    def _harvest_probe(self) -> None:
        probe = self._probe
        if probe is None or not probe.future.done():
            return
        self._probe = None
        try:
            outcome = probe.future.result()
        except Exception as exc:
            self.get_logger().error(f"t0 probe worker failed request={probe.request_id}: {exc}")
            outcome = build_failed_outcome(probe.request_id, f"worker raised: {exc}")
        self._handle_probe_outcome(probe, outcome)

    def _handle_probe_outcome(self, probe: _PendingProbe, outcome: PipelineOutcome) -> None:
        """Record a finished probe; log-only, so it ends here.

        Deliberately never touches the state machine, cooldowns, AttemptMemory,
        the command tracker, the registry or `_dispatch`.
        """
        shadow_block = self._finalize_shadow_record(probe.shadow, outcome)
        try:
            artifact_path = write_decision_artifact(
                self._config.decision_log_dir,
                outcome,
                request=probe.request,
                snapshot=probe.snapshot,
                run_id=self._run_id,
                session_id=self._session_id,
                prompt_robot_order_mode=self._config.prompt_robot_order,
                prompt_robot_order_seed=self._order_seed,
                grounding_yield_feasibility=self._config.grounding_yield_feasibility,
                shadow_classical=shadow_block,
                probe_index=probe.probe_index,
                grounding_source=self._grounding,
            )
            self.get_logger().info(f"decision artifact written: {artifact_path}")
        except OSError as exc:
            self.get_logger().error(f"decision artifact write failed: {exc}")
        decision = outcome.reasoner_result.decision
        verdict = (
            "none"
            if decision is None
            else f"{str(decision.congestion_detected).lower()} type={decision.type} "
            f"strategy={decision.strategy}"
        )
        self.get_logger().info(
            f"t0 probe complete request={outcome.request_id} probe_index={probe.probe_index} "
            f"stage={outcome.terminal_stage.value} congestion_detected={verdict} "
            "(log-only, not dispatched)"
        )
        self._cleanup_frame(outcome.request_id)

    def _resolve_command(self, command_id: str) -> None:
        robots = self._tracker.robots_of(command_id)
        for robot_id in robots:
            self._registry.clear_override(robot_id)
        states = {
            r: s for r in robots if (s := self._tracker.state_of(command_id, r)) is not None
        }
        outcome_status = summarize_outcome(states)
        now = time.monotonic()
        self._attempts.resolve(command_id, outcome_status, now)
        self.get_logger().info(f"command {command_id} resolved status={outcome_status}")
        self._machine.on_command_resolved(robots, outcome_status == "completed")
        self._cooldown.start(robots, now)
        self._publish_registry()

    # ---- helpers ----

    def _effective_goal(self, robot_id: str):
        eff = self._registry.effective(robot_id)
        return None if eff is None else eff[1]

    def _latest_estimate(self, robot_id: str):
        """Return M1's latest view of a robot and its age in seconds, or (None, None)."""
        snapshot = self._latest_snapshot
        if snapshot is None or self._latest_snapshot_at is None:
            return None, None
        view = next((r for r in snapshot.robots if r.robot_id == robot_id), None)
        if view is None:
            return None, None
        return view, time.monotonic() - self._latest_snapshot_at

    def _apply_arrival(self, decision: ArrivalDecision) -> None:
        """Log one arrival verdict and close the episode when it is accepted.

        The gate has already marked the robot arrived (or deliberately not);
        this only mirrors the verdict into the episode tracker and the log.
        """
        check = decision.check
        if check is None:
            self._episodes.end_episode([decision.robot_id])
            self.get_logger().info(
                f"robot {decision.robot_id} arrived at base goal {decision.goal}"
            )
            return
        distance = "none" if check.distance_m is None else f"{check.distance_m:.2f}"
        # M5 publishes no diagnostics topic, so the running tallies ride on the
        # two lines that report a disagreement with Nav2; the last such line in
        # a run's log carries the run totals.
        counts = self._arrival.counts
        if not check.accepted:
            self.get_logger().warning(
                f"arrival rejected robot={decision.robot_id} distance_m={distance} "
                f"tolerance_m={self._config.arrival_position_tolerance_m} "
                f"reason={check.reason} (Nav2 reported success) counts={counts}"
            )
            return
        self._episodes.end_episode([decision.robot_id])
        if decision.late:
            self.get_logger().info(
                f"arrival accepted late robot={decision.robot_id} "
                f"distance_m={distance} counts={counts}"
            )
            return
        self.get_logger().info(
            f"robot {decision.robot_id} arrived at base goal {decision.goal} "
            f"distance_m={distance} check={check.reason}"
        )

    def _busy_robots(self) -> set[str]:
        busy: set[str] = set()
        for command_id in list(self._tracker._records):  # node-local read
            if not self._tracker.is_resolved(command_id):
                busy.update(self._tracker.robots_of(command_id))
        return busy

    def _dumps_raw_frames(self) -> bool:
        return self._config.keep_raw_frames and self._config.keep_debug_frames

    def _raw_frame_dump(self, request_id: str) -> tuple[object, str] | None:
        """Pick the raw frame to dump for one analysis and log its stamp skew.

        Args:
            request_id: Identifier of the analysis cycle.

        Returns:
            The `(frame_rgb, dest_path)` the worker should write, or None when
            raw dumps are off or no camera frame has arrived — a missing debug
            frame is skipped, never raised, so it cannot fail an analysis.
        """
        if not self._dumps_raw_frames():
            return None
        latest = self._raw_frame.latest()
        if latest is None:
            self.get_logger().warning(
                f"raw frame unavailable request={request_id} "
                f"topic={self._config.raw_frame_topic}"
            )
            return None
        raw_frame, raw_stamp = latest
        dest = raw_frame_dump_path(self._config.frame_dump_dir, request_id)
        skew = (
            None
            if self._frame_stamp is None
            else raw_frame_skew_sec(raw_stamp, self._frame_stamp)
        )
        self.get_logger().info(
            f"raw frame skew_sec={'none' if skew is None else f'{skew:+.3f}'} "
            f"request={request_id} path={dest}"
        )
        return raw_frame, str(dest)

    def _frame_is_fresh(self, scene_stamp: float) -> bool:
        if self._frame_rgb is None or self._frame_stamp is None:
            return False
        return abs(scene_stamp - self._frame_stamp) <= self._config.frame_scene_max_skew_sec

    def _cleanup_frame(self, request_id: str) -> None:
        if self._config.keep_debug_frames:
            return
        path = Path(self._config.frame_dump_dir) / f"{request_id}.png"
        path.unlink(missing_ok=True)
        Path(stage2_image_path(str(path), request_id)).unlink(missing_ok=True)

    def _publish_registry(self) -> None:
        payload = self._registry.to_json()
        self.last_published_registry = payload
        msg = String()
        msg.data = payload
        self._tasks_pub.publish(msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = OrchestratorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
