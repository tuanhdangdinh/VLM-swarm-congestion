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
    CURRENT_PROMPT_VERSION,
    AnthropicBackendConfig,
    FailureContext,
    GeminiBackendConfig,
    LlamaServerBackendConfig,
    OpenAIBackendConfig,
    ReasonerConfig,
    ReasonerRequest,
    RobotOrder,
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
from swarm_orchestrator.junction_phase_queue import JunctionPhaseAdvance, JunctionPhaseQueue
from swarm_orchestrator.models import (
    AnnotationOverlayReport,
    CongestionEvent,
    OrchestratorConfig,
    PipelineOutcome,
    load_config,
    parse_annotation_overlays,
    parse_scene_snapshot,
    registry_priorities,
)
from swarm_orchestrator.permutation_votes import permutation_votes_log
from swarm_orchestrator.plan_tracker import PlanTracker
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
    PromptConditions,
    ReasoningPipeline,
    apparatus_request_fields,
    append_scene_log,
    apply_aisle_x_band_override,
    apply_aisle_y_band_override,
    attach_registry_assignments,
    build_candidate_options,
    build_failed_outcome,
    build_failure_contexts,
    build_prompt_conditions,
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
    ClassicalRetreatContext,
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
from swarm_orchestrator.zoom_tile import ZoomTileRecord, write_zoom_tile, zoom_tile_path

# (a0) plan channel: M4's CoordinationStatus vocabulary (command_bus_node.py's
# `_publish_status` calls) translated to a plan leg's status vocabulary
# (`swarm_orchestrator.plan_tracker.PlanLegStatus`). A status this table does
# not name (there is none today) is left untranslated -- no leg update, not a
# crash -- rather than guessing.
_PLAN_LEG_STATUS_BY_COMMAND_STATUS: dict[str, str] = {
    "ACTIVE": "active",
    "COMPLETED": "done",
    "FAILED": "failed",
}


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
    letter_seed: int = 0,
    plan_tracker: PlanTracker | None = None,
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
    # Stage 2 runs on the stage-1 backend and sampling config, with its own
    # attempt/timeout budget; a mock answers stage 2 only from its own script.
    stage2_backend = build_retreat_choice_backend(config.reasoning_backend_id, backend)
    stage2_config = reasoner_config.model_copy(
        update={
            "max_attempts": config.stage2_max_attempts,
            "timeout_sec": config.stage2_timeout_sec,
        }
    )
    return InProcessPipeline(
        reasoner=reasoner,
        ground_fn=ground_reasoner_result,
        scene_geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        grounding_params=grounding.params,
        retreat_chooser=(
            None if stage2_backend is None else RetreatChooser(stage2_backend, stage2_config)
        ),
        stage2_enabled=config.stage2_retreat_selection,
        candidate_marker=marker,
        stage2_letter_seed=letter_seed,
        priorities=registry_priorities(config.initial_tasks),
        plan_tracker=plan_tracker,
        permutation_votes=config.prompt_permutation_votes,
        registry_order=tuple(config.initial_tasks),
    )


def _build_shadow(
    config: OrchestratorConfig, grounding: GroundingParamsSource | None = None
) -> ClassicalShadow | None:
    """Build the Arm B shadow, or None when disabled.

    Invalid `classical:` params raise here, stopping M5 at startup; a missing
    file or section is carried into every shadow record instead. `grounding`
    gives Arm B's stage-2 answer the pipeline's own derived-mode inputs.
    """
    if not config.shadow_classical:
        return None
    retreat_context = (
        None
        if grounding is None
        else ClassicalRetreatContext(
            params=grounding.params,
            geometry=config.scenario_geometry,
            static_obstacles=config.static_obstacles,
            yield_feasibility_mode=config.grounding_yield_feasibility,
        )
    )
    return ClassicalShadow(
        load_shadow_params(Path(config.shadow_classical_params_path)),
        config.shadow_classical_zones,
        config.shadow_classical_window_sec,
        config.shadow_classical_sample_period_sec,
        retreat_context=retreat_context,
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
    prompt_conditions: Any = None


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
        if self._config.prompt_zoom_tile and self._config.reasoning_backend_id == "llama_server":
            # Fail fast: that backend refuses extra images (unverified
            # multi-image support), so every tile-on analysis would fail.
            raise ValueError("prompt_zoom_tile is not supported by the llama_server backend")
        # Fail fast: a missing file, an invalid `grounding:` section or an
        # inverted per-scenario band stops M5 here, since these parameters
        # shape every command it dispatches.
        self._grounding = apply_aisle_x_band_override(
            apply_aisle_y_band_override(
                load_grounding_source(Path(self._config.grounding_params_path)),
                self._config.grounding_aisle_y_band_m,
            ),
            self._config.grounding_aisle_x_band_m,
        )
        # Groups artifacts per M5 process; VGU_RUN_ID (set by the launcher) names
        # the scenario run across all modules. Set before the pipeline, whose
        # stage-2 letter draws derive from the same run seed.
        self._session_id = uuid.uuid4().hex
        self._run_id = os.environ.get("VGU_RUN_ID") or None
        self._order_seed = (
            self._config.prompt_robot_order_seed
            if self._config.prompt_robot_order_seed is not None
            else derive_order_seed(self._run_id, self._session_id)
        )
        # Only the default pipeline draws stage-2 letters; an injected one
        # brings its own marker (or none).
        self._marker = None if pipeline is not None else _build_candidate_marker(self._config)
        # (a0) plan channel (prereg-v2 rev 4, build-order step 4): None unless
        # `plan_channel_enabled`, so a flag-off pipeline never calls
        # `verify_and_repair_plan` and the dispatch path stays byte-identical
        # to before this channel existed. One tracker for the node's whole
        # session, matching how `self._attempts`/`self._tracker` are scoped.
        self._plan_tracker = PlanTracker() if self._config.plan_channel_enabled else None
        # Which plan_id was last shown in a rendered prompt's plan-state
        # block, so `PlanTracker.plan_state_context` reports an empty
        # `changed_robot_ids` on every invocation except the one right after
        # a supersession (see that method's docstring).
        self._last_shown_plan_id: int | None = None
        self._pipeline = pipeline or _build_default_pipeline(
            self._config, self._grounding, self._marker, self._order_seed, self._plan_tracker
        )
        # Prompt apparatus (prereg-v2 rev 6). The zoom tile is placed with M1's
        # calibration, shared with the stage-2 marker when there is one.
        self._tile_marker = (
            (self._marker or _build_candidate_marker(self._config))
            if self._config.prompt_zoom_tile
            else None
        )
        # What M1's latest scene says it drew; read on the callback thread only.
        self._latest_overlays = AnnotationOverlayReport()
        self._pending_prompt_conditions: PromptConditions | None = None

        self._detector = CongestionDetector(self._config)
        self._arrival = ArrivalGate(self._config, self._detector.mark_arrived)
        self._machine = OrchestratorStateMachine()
        self._tracker = CommandTracker()
        # (a0) plan channel: which plan a dispatched command_id serves, so
        # `_on_status` can route M4's per-robot status back onto the right
        # plan's leg. Every entry is set in `_dispatch`, never cleared (a
        # late/duplicate status for a long-resolved command_id still finds
        # its plan); unused unless `self._plan_tracker` is set.
        self._plan_id_by_command_id: dict[str, int] = {}
        # `junction_clear`'s M5 phase queue (prereg-v2 (a) M5, build-order
        # step 5), keyed by the CURRENT active command_id of each in-flight
        # resolution: looked up in `_on_status` to advance to the next
        # precomputed phase, or the fallback, on that command's terminal
        # status. Behind the SAME `plan_channel_enabled` flag `plan_info`
        # is -- only ever populated from `outcome.junction_phases`, which
        # `InProcessPipeline.run` sets only when `self._plan_tracker` is
        # not None. Re-keyed to the NEW active command_id on every advance
        # (`_advance_junction_phase`); the entry for a done queue is popped.
        self._junction_phase_queues: dict[str, JunctionPhaseQueue] = {}
        # Per active command_id, the robots THAT command addresses only to
        # hold (`JunctionClearPhase.held_robot_ids`): `_apply_plan_leg_status`
        # must never route one of their statuses onto the tracked plan's leg
        # for them from this command -- that leg's real action is dispatched
        # by a DIFFERENT (earlier-or-later) phase. Populated alongside
        # `_junction_phase_queues`, re-keyed the same way on every advance,
        # and popped together.
        self._junction_held_robots: dict[str, frozenset[str]] = {}
        # Maps a junction_clear phase's CURRENT command_id back to the
        # ORIGINAL (phase-0) command_id its `_attempts` entry was recorded
        # under, so the attempt is resolved ONCE, with the WHOLE sequence's
        # final outcome, never prematurely when an intermediate phase
        # resolves (`_resolve_command`).
        self._junction_original_command_id: dict[str, str] = {}
        self._cooldown = CooldownTracker(self._config.cooldown_sec)
        # Freeze-blocking finding 5 (step-7a fix): robots a `junction_clear`
        # fallback ALSO failed for. Permanent for the rest of the episode
        # (never cleared, unlike `_cooldown`'s time-bounded set) -- folded
        # into `cooldown_robots` at every trigger check so M5 stops
        # re-dispatching a conflict its own documented recovery already
        # exhausted, instead of re-triggering it every stall interval
        # forever.
        self._exhausted_robots: set[str] = set()
        self._attempts = AttemptMemory(self._config.failure_context_window_sec)
        self._registry = TaskRegistry()
        self._registry.load_initial(self._config, time.monotonic())

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
        # Step-7a fix 3 (freeze-blocking finding 3): the ORIGINAL congestion
        # event's robot set for the in-flight request, consumed by
        # `_handle_outcome` into `_last_trigger_robot_ids` right before
        # `_dispatch` -- `_with_plan_continue_partners` narrows the plan's
        # `continue` legs to this set so a scene-wide plan's lenient
        # completion (every untouched robot gets `continue`) does not turn
        # into a blanket same-scene exemption for every `reverse`.
        self._pending_trigger_robots: frozenset[str] = frozenset()
        self._last_trigger_robot_ids: frozenset[str] = frozenset()
        # Step-7b ruling (v): `_last_trigger_robot_ids` is cleared right after
        # the triggering dispatch (below) so a later, UNRELATED dispatch can
        # never read a stale leftover trigger set. A `junction_clear`
        # resolution's LATER phases (recede phase 2, release) are dispatched
        # from `_advance_junction_phase` -> `_dispatch_junction_phase`, a
        # separate synchronous call that runs well after that clear, so the
        # trigger set this resolution's `reverse` legs must keep reading is
        # instead bound to the plan (`outcome.plan.plan_id`, which every
        # later phase's command_id maps back to via
        # `_plan_id_by_command_id`), not to this transient attribute.
        self._trigger_robots_by_plan: dict[int, frozenset[str]] = {}
        self._episodes = EpisodeOrderTracker(
            PresentationOrderPolicy(
                mode=self._config.prompt_robot_order, seed=self._order_seed
            )
        )
        self._pending_episode_index: int | None = None
        self._shadow = _build_shadow(self._config, self._grounding)
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
            f"aisle_y_band_m={self._grounding.params.aisle_y_band_m} "
            f"band_override={self._grounding.aisle_y_band_override_m is not None} "
            + (
                ""
                if self._grounding.aisle_x_band_override_m is None
                else f"aisle_x_band_m={self._grounding.aisle_x_band_override_m} "
            )
            + f"stage2_retreat_selection={self._config.stage2_retreat_selection}"
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
        self._latest_overlays = parse_annotation_overlays(msg.data)
        now = time.monotonic()
        self._latest_snapshot_at = now
        if self._shadow is not None:
            # Never raises; ingest failures surface in the next shadow record.
            self._shadow.observe(snapshot, self._effective_goal, self._registry.is_pending)
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
        for decision in self._arrival.on_scene(snapshot, self._progress_goal):
            self._apply_arrival(decision)
        event = self._detector.update(snapshot, self._progress_goal, now)
        if event is None:
            return
        frame_ready = self._frame_is_fresh(snapshot.stamp)
        directive = self._machine.on_event(
            event,
            # `_exhausted_robots` folded in (step-7a fix, finding 5): a
            # permanent, never-expiring suppression, unlike `_cooldown`'s
            # time-bounded one -- the same gate, reused rather than a new
            # directive kind, for the robots a fallback already exhausted.
            cooldown_robots=self._cooldown.active_robots(now) | self._exhausted_robots,
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
        elif directive.kind is DirectiveKind.FOLDED:
            self._attempts.fold(event.involved_robots)
            # Logged once per follower: the stall re-fires on every scene.
            if self._episodes.fold(event.involved_robots):
                self.get_logger().info(
                    f"trigger folded into the in-flight episode robots={event.involved_robots} "
                    f"busy={sorted(self._busy_robots())} episode={self._episodes.episode_index}"
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
        self._apply_plan_leg_status(msg.command_id, msg.robot_id, msg.status)
        if self._tracker.is_resolved(msg.command_id):
            self._resolve_command(msg.command_id)

    def _apply_plan_leg_status(self, command_id: str, robot_id: str, status: str) -> None:
        """Route M4's per-robot command status onto its plan's leg, behind the flag.

        Never raises into `_on_status`: an unknown command_id (a plan-less
        dispatch, or one from before the plan channel was enabled), an
        untranslatable status, or an invalid transition (e.g. a duplicate
        terminal status racing itself) is logged and otherwise ignored,
        exactly like `_finalize_shadow_record`'s own failure handling.

        `junction_clear` exception: `robot_id` is skipped entirely when this
        command only HOLDS it (`self._junction_held_robots`) -- that robot's
        real plan leg is dispatched by a different phase, still `pending`;
        routing a hold's `COMPLETED` onto it would mark it `done` before it
        ever ran.
        """
        if self._plan_tracker is None:
            return
        if robot_id in self._junction_held_robots.get(command_id, frozenset()):
            return
        plan_id = self._plan_id_by_command_id.get(command_id)
        if plan_id is None:
            return
        mapped = _PLAN_LEG_STATUS_BY_COMMAND_STATUS.get(status.upper())
        if mapped is None:
            return
        try:
            self._plan_tracker.set_leg_status(plan_id, robot_id, mapped)
        except (KeyError, ValueError) as exc:
            self.get_logger().warning(
                f"plan leg status update failed plan={plan_id} robot={robot_id} "
                f"status={mapped}: {exc}"
            )

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
            self._submit_pipeline(
                directive.request_id,
                snapshot,
                event.involved_robots,
                {},
                # Manual trigger always reports EVERY snapshot robot as
                # "involved" (not the real conflict set) -- fails closed to
                # no-narrowing (v1) exemption scope rather than exempting the
                # whole scene (step-7a FOURTH CORRECTION).
                trigger_robots=frozenset(),
            )
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
        released = self._registry.release_due(now)
        if released:
            self.get_logger().info(f"start delay elapsed, base mission released robots={released}")
            self._publish_registry()
        for command_id in self._tracker.check_timeouts(now):
            self.get_logger().warning(f"command {command_id} timed out")
            # A timeout never goes through `_on_status`/`_apply_plan_leg_status`
            # (no CoordinationStatus arrives for a command M4 never received or
            # never finished), so without this the plan-state block would keep
            # telling the model a dead leg is still pending/active, and the
            # NEXT revision would misclassify as `unforced` (dithering) instead
            # of `evidence_driven` -- the exact distinction the plan-stability
            # metric is built on.
            for robot_id in self._tracker.robots_of(command_id):
                self._apply_plan_leg_status(command_id, robot_id, "FAILED")
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
        trigger_robots: frozenset[str] | None = None,
    ) -> RobotOrder:
        """Build the request for one analysis and hand it to the worker thread.

        Args:
            request_id: Identifier the state machine minted for this cycle.
            snapshot: The M1 scene the request is built from.
            robots: Robots the congestion event involves.
            distance_to_goal_m: The detector's per-robot distance at trigger time.
            trigger_robots: Overrides `_pending_trigger_robots` (fix 3's
                plan-continue exemption scope) when the caller's own `robots`
                is not the real conflict set -- e.g. the operator/test manual
                trigger (`_on_trigger_analysis`) always passes every snapshot
                robot as `robots`, so it must pass `frozenset()` here to fail
                closed to no-narrowing (v1) behavior instead of exempting the
                whole scene. `None` (the detector-driven path) keeps the
                existing `frozenset(robots)` derivation.

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
        episode_index, order = self._episodes.order_for(
            robots, [view.robot_id for view in snapshot.robots]
        )
        # Registry goals/tasks ride on the snapshot so the stored `scene` alone
        # reconstructs the prompt; the shadow keeps its own goal lookup.
        snapshot = attach_registry_assignments(
            snapshot, self._effective_goal, self._registry.mission_task
        )
        # (a0) plan channel: v3's plan-state block shows M2 its own active
        # plan; None (flag off, or no plan accepted yet) renders exactly like
        # today. `_last_shown_plan_id` is this analysis's own bookkeeping,
        # consumed and updated here only, so a request that is built but
        # never actually sent (an exception before dispatch) cannot desync it
        # from what the NEXT request shows.
        plan_state = None
        if self._plan_tracker is not None and self._plan_tracker.active_plan is not None:
            active_plan_id = self._plan_tracker.active_plan.plan_id
            plan_state = self._plan_tracker.plan_state_context(
                active_plan_id, since_plan_id=self._last_shown_plan_id
            )
            self._last_shown_plan_id = active_plan_id
        apparatus, zoom_record = self._apparatus_inputs(request_id, snapshot, robots, frame)
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
            prompt_version=3 if self._config.plan_channel_enabled else CURRENT_PROMPT_VERSION,
            plan_state=plan_state,
            **apparatus,
        )
        self._pending_prompt_conditions = self._prompt_conditions(
            request, zoom_record, self._config.prompt_permutation_votes
        )
        self._pending_failure_context = failure_context
        self._pending_last_failed_context = last_failed_context
        self._pending_request = request
        self._pending_snapshot = snapshot
        self._pending_distances = dict(distance_to_goal_m)
        self._pending_trigger_robots = (
            trigger_robots if trigger_robots is not None else frozenset(robots)
        )
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
                    request_id,
                    snapshot,
                    self._effective_goal,
                    episode_index,
                    self._registry.is_pending,
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
        prompt_conditions = self._pending_prompt_conditions
        self._pending_prompt_conditions = None
        # Step-7a fix 3: carried past the clear below (as `_last_trigger_
        # robot_ids`, not re-cleared here) so `_dispatch` -> `_publish_
        # fanned_out` -> `_with_plan_continue_partners`, later in this SAME
        # synchronous call, can narrow a reverse leg's plan-continue
        # exemption to the robots THIS congestion event actually involved.
        self._last_trigger_robot_ids = self._pending_trigger_robots
        self._pending_failure_context = None
        self._pending_last_failed_context = None
        self._pending_request = None
        self._pending_snapshot = None
        self._pending_distances = {}
        self._pending_trigger_robots = frozenset()
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
                prompt_conditions=prompt_conditions,
            )
            self.get_logger().info(f"decision artifact written: {artifact_path}")
        except OSError as exc:
            self.get_logger().error(f"decision artifact write failed: {exc}")
        if outcome.permutation_votes is not None:
            self.get_logger().info(
                permutation_votes_log(outcome.request_id, outcome.permutation_votes)
            )

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
        # Step-7b ruling (v): this outcome's one synchronous use of
        # `_last_trigger_robot_ids` (inside `_dispatch`, if it ran) is over by
        # now, and any plan-bound copy a junction_clear resolution's later
        # phases will need was already persisted into
        # `_trigger_robots_by_plan` above. Clearing here removes a latent
        # staleness window where a LATER, unrelated dispatch (e.g. a plain
        # `reverse` with no plan) could otherwise read this request's
        # leftover trigger set.
        self._last_trigger_robot_ids = frozenset()
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
                record,
                outcome.reasoner_result.decision,
                outcome.failure_reason,
                outcome.grounded_command,
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
        if outcome.plan is not None:
            self._plan_id_by_command_id[grounded["command_id"]] = outcome.plan.plan_id
            # Step-7b ruling (v): bind this resolution's trigger-robot set to
            # the plan BEFORE `_last_trigger_robot_ids` is cleared (by the
            # caller, `_handle_outcome`, right after this call returns) so
            # every later phase's `reverse` dispatch
            # (`_dispatch_junction_phase` -> `_publish_fanned_out` ->
            # `_with_plan_continue_partners`) still finds it.
            self._trigger_robots_by_plan[outcome.plan.plan_id] = self._last_trigger_robot_ids
        messages = fan_out_command(grounded, self._config.command_timeout_sec)
        robot_ids = [m[1] for m in messages]
        self._episodes.note_dispatch(robot_ids)
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
        self._publish_fanned_out(outcome.request_id, messages)
        if outcome.plan is not None and outcome.junction_phases is not None:
            # `junction_clear`'s M5 phase queue (prereg-v2 (a) M5,
            # build-order step 5): `grounded` above IS
            # `outcome.junction_phases.phases[0].command` already (M3's own
            # single-command contract for this strategy, "the NEXT
            # unresolved step" -- `command_grounder._ground_derived`'s
            # `junction_clear` branch), so `queue.start()`'s return is
            # discarded here, never re-dispatched; only its side effect
            # (recording the already-dispatched command_id as active)
            # matters.
            queue = JunctionPhaseQueue(outcome.junction_phases)
            queue.start()
            self._junction_phase_queues[grounded["command_id"]] = queue
            self._junction_held_robots[grounded["command_id"]] = frozenset(
                queue.active_held_robot_ids
            )

    def _publish_fanned_out(
        self,
        request_id: str,
        messages: list[tuple[str, str, str, str, float]],
    ) -> None:
        """Publish one fanned-out command's per-robot messages and log each dispatch.

        Shared by `_dispatch` (a fresh M2 decision's command) and
        `_dispatch_junction_phase` (a later `junction_clear` phase or its
        fallback, dispatched by M5 directly, no new M2 call): both need the
        IDENTICAL publish/override/log sequence, never two implementations
        that could drift.

        Args:
            request_id: Logged only (`request=` on every dispatch line): the
                triggering M2 request_id for `_dispatch`, or a
                `<previous_command_id>-phase` label for a phase advance.
            messages: `fan_out_command`'s per-robot tuples.
        """
        for command_id, robot_id, action, params_json, _timeout in messages:
            msg = CoordinationCommand()
            msg.command_id = command_id
            msg.robot_id = robot_id
            msg.action = action
            plan_id = self._plan_id_by_command_id.get(command_id)
            # Inject the robot's current task goal into reroute params so the
            # command_bus can resume navigation to the original goal when M3
            # did not supply explicit waypoints (the common case for this grounder).
            goal = self._effective_goal(robot_id) or (0.0, 0.0)
            if action == "reroute":
                p = json.loads(params_json or "{}")
                p.setdefault("goal", {"x": goal[0], "y": goal[1]})
                params_json = json.dumps(p)
            elif action == "reverse":
                params_json = self._with_plan_continue_partners(params_json, plan_id, robot_id)
            msg.parameters_json = params_json
            msg.timeout_sec = _timeout
            self._cmd_pub.publish(msg)
            self._registry.set_override(robot_id, action, goal, command_id)
            log_line = f"dispatch request={request_id} command={command_id} robot={robot_id}"
            if plan_id is not None:
                # Step-4 flag-3 mitigation: makes plan_id-on-commands
                # observable live, not just unit-tested
                # (`test_plan_tracker_enabled_assigns_a_plan_id_and_tags_every_action`).
                # Appended only when set, so a flag-off/plan-less dispatch's
                # log line is byte-identical to before this field existed.
                log_line += f" plan_id={plan_id}"
            self.get_logger().info(log_line)
        self._publish_registry()

    def _with_plan_continue_partners(
        self, params_json: str, plan_id: int | None, robot_id: str
    ) -> str:
        """Add the tracked plan's OTHER `continue` robots to a `reverse` leg's parameters.

        Freeze-blocking finding 3 (2026-10-02 IB10 composite smoke, episode
        1 decision 2): M4's `admitted_partners` (`swarm_execution.safety`)
        only exempts a `reverse` against the OTHER members of its OWN
        dispatched command -- a `continue` leg never gets a command at all,
        so a plan naming `{reverse: robot_3, reverse: robot_4, continue:
        robot_1, continue: robot_2}` leaves `robot_1` fully unexempted
        against `robot_4`'s `reverse`, even though both legs are part of the
        SAME accepted plan. There is no other channel carrying that
        membership to M4 (the wire `CoordinationCommand` has no `plan_id`
        field), so it travels on the reverse leg's own `parameters_json`
        instead -- untouched when `plan_id` is None (the v1, no-plan-channel
        path; a SINGLE `_handle_outcome`-to-`_dispatch` call never sets
        `_last_trigger_robot_ids` to anything the plan-less path reads).

        Narrowed to `_last_trigger_robot_ids` (pair-scope discipline, M4
        protocol note in `docs/implementation_notes.md`): plans are
        SCENE-WIDE (a0 rev 4) -- EVERY tracked robot the plan omits is
        lenient-completed to `continue`, whatever the plan's provenance
        (`PlanTracker.accept_plan` tracks `m3_default` plans too, not only
        VLM-authored ones). Without this narrowing, every `continue` robot
        in the WHOLE SCENE would be named here, making every `reverse`
        exempt against every other robot -- exactly the blanket exemption
        this fix must not be. Restricting to the ORIGINAL congestion
        event's own robot set (not `decision.involved_robots`, which the
        VLM may have narrowed further) keeps episode 1 decision 2's own
        case correct: the event was `['robot_1','robot_3','robot_4']`, so
        `robot_1` (`continue`, part of the event) stays exempt while
        `robot_2` (`continue`, never part of this event) does not.

        Step-7b ruling (v): reads `_trigger_robots_by_plan[plan_id]`, a copy
        of the triggering event's robot set bound to the plan when it was
        first dispatched (`_dispatch`), not the transient
        `_last_trigger_robot_ids` attribute — which `_handle_outcome` clears
        after every outcome so it cannot leak into a later, unrelated
        dispatch. A `junction_clear` resolution's LATER phases (recede phase
        2, release) call this same function well after that clear, so they
        need the plan-bound copy to still narrow correctly.

        Args:
            params_json: The reverse leg's own encoded parameters.
            plan_id: The dispatching command's tracked plan id, or None.
            robot_id: The reversing robot (excluded from its own partner list).

        Returns:
            `params_json` unchanged when there is no tracked plan, or it
            names no other `continue` robot that was also part of the
            triggering congestion event; otherwise with
            `plan_continue_partners` added.
        """
        if plan_id is None or self._plan_tracker is None:
            return params_json
        plan = self._plan_tracker.plan(plan_id)
        if plan is None:
            return params_json
        trigger_robot_ids = self._trigger_robots_by_plan.get(plan_id, frozenset())
        partners = [
            leg.robot_id
            for leg in plan.legs
            if leg.action == "continue"
            and leg.robot_id != robot_id
            and leg.robot_id in trigger_robot_ids
        ]
        if not partners:
            return params_json
        parameters = json.loads(params_json or "{}")
        parameters["plan_continue_partners"] = partners
        return json.dumps(parameters)

    def _advance_junction_phase(
        self, command_id: str, completed: bool
    ) -> JunctionPhaseAdvance | None:
        """Advance `junction_clear`'s M5 phase queue on a resolved command, if any.

        Called from `_resolve_command` for EVERY resolved command (both the
        `_on_status` and `_on_timer` paths funnel into it); a no-op unless
        `command_id` is the current active command of a tracked
        `JunctionPhaseQueue` (`_junction_phase_queues`, seeded in
        `_dispatch`). Never issues a new plan or calls M2 -- "phases advance
        by updating leg status... so no replan is counted" (prereg-v2 (a)
        M5): the plan_id this whole resolution serves is carried forward
        onto each later phase's command_id in `_dispatch_junction_phase`,
        exactly like `_apply_plan_leg_status` already routes each phase's
        own per-robot status onto that SAME plan's legs.

        Args:
            command_id: The just-resolved command's id.
            completed: True for an overall-COMPLETED resolution
                (`summarize_outcome(states) == "completed"`), False for any
                other terminal outcome (a timeout included).

        Returns:
            None when `command_id` names no tracked queue (the caller's
            attempt-resolution stays unaffected); otherwise the queue's own
            `JunctionPhaseAdvance`, so the caller (`_resolve_command`) can
            tell an INTERMEDIATE phase's resolution (`done=False`: defer
            the original attempt's resolution) from the sequence's own
            terminal one (`done=True`: resolve it now, with THIS outcome).
        """
        queue = self._junction_phase_queues.pop(command_id, None)
        if queue is None:
            return None
        advance = queue.on_resolved(command_id, completed)
        self.get_logger().info(
            f"junction_clear phase advance command={command_id} completed={completed} "
            f"phase_reached={advance.phase_reached} done={advance.done}"
        )
        if advance.command is not None:
            new_command_id = self._dispatch_junction_phase(
                command_id, advance.command, advance.held_robot_ids
            )
            if not advance.done:
                self._junction_phase_queues[new_command_id] = queue
        return advance

    def _dispatch_junction_phase(
        self,
        previous_command_id: str,
        command: dict[str, Any],
        held_robot_ids: tuple[str, ...],
    ) -> str:
        """Publish one precomputed `junction_clear` phase command (or its fallback).

        Mirrors `_dispatch`'s own per-robot publish/registry/tracker
        bookkeeping (`_publish_fanned_out`, `CommandTracker.register`,
        `_episodes.note_dispatch`) but deliberately never calls
        `self._attempts.record`: this is NOT a new M2 decision, so it must
        not add a second entry to the failure-context attempt history the
        NEXT ordinary analysis would read -- the original `_dispatch` call
        for phase 0 already recorded the one attempt this whole
        `junction_clear` resolution counts as (its OWN resolution is
        deferred by `_resolve_command` until the sequence finishes).

        Args:
            previous_command_id: The command this phase follows; its
                tracked `plan_id` (if any) carries forward onto the new
                command_id unchanged.
            command: The next phase's precomputed, schema-valid command
                (`JunctionPhaseAdvance.command`).
            held_robot_ids: `JunctionPhaseAdvance.held_robot_ids` for this
                SAME command -- recorded under the (possibly
                `filter_command_robot_ids`-filtered) dispatched command_id
                so `_apply_plan_leg_status` skips them for it.

        Returns:
            The dispatched command_id (post-`filter_command_robot_ids`).
        """
        grounded = filter_command_robot_ids(command, set(self._config.initial_tasks))
        command_id = grounded["command_id"]
        plan_id = self._plan_id_by_command_id.get(previous_command_id)
        if plan_id is not None:
            self._plan_id_by_command_id[command_id] = plan_id
        self._junction_held_robots[command_id] = frozenset(held_robot_ids)
        messages = fan_out_command(grounded, self._config.command_timeout_sec)
        robot_ids = [m[1] for m in messages]
        self._episodes.note_dispatch(robot_ids)
        timeout = messages[0][4] if messages else self._config.command_timeout_sec
        self._tracker.register(
            CommandRecord(
                command_id=command_id,
                robot_ids=robot_ids,
                dispatched_at=time.monotonic(),
                timeout_sec=timeout,
                fallback=grounded.get("fallback", ""),
                request_id=f"{previous_command_id}-phase",
            )
        )
        self._publish_fanned_out(f"{previous_command_id}-phase", messages)
        return command_id

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
    ) -> RobotOrder:
        """Hand one probe's stage-1 analysis to the probe worker.

        Built like a triggered request, except that it carries no failure
        context: that block tells the VLM congestion was re-detected, which an
        off-trigger probe has not established, and reading AttemptMemory can
        clear it for the next real analysis.

        Returns:
            The presentation order the probe renders robots in.
        """
        image_path = str(Path(self._config.frame_dump_dir) / f"{request_id}.png")
        order = self._probe_order.order_for_episode(
            probe_index, [view.robot_id for view in snapshot.robots]
        )
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
        # Probes render the frozen v2 template (no apparatus text) and never
        # vote (`analyze`), but M1's overlays still reach their image channel,
        # so the record states what the frame carried.
        probe_conditions = self._prompt_conditions(request, None, 1)
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
                shadow = self._shadow.evaluate_probe(
                    request_id, snapshot, self._effective_goal, self._registry.is_pending
                )
            except Exception as exc:  # evaluate_probe records its own errors; last resort
                self.get_logger().error(
                    f"shadow request={request_id} evaluate failed: {type(exc).__name__}: {exc}"
                )
        self._probe = _PendingProbe(
            request_id, probe_index, request, snapshot, future, shadow, probe_conditions
        )
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
                prompt_conditions=probe.prompt_conditions,
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
        # `junction_clear`'s M5 phase queue (build-order step 5): advanced
        # BEFORE `_publish_registry()` below, so a later phase's own
        # overrides (set inside `_dispatch_junction_phase`) are already in
        # effect when the registry topic reflects this resolution -- never
        # a published moment where every override reads cleared. A no-op
        # (`advance is None`) unless `command_id` is the active command of
        # a tracked queue.
        advance = self._advance_junction_phase(command_id, outcome_status == "completed")
        # Attempt bookkeeping: resolve the ORIGINAL (phase-0) command_id's
        # attempt record ONCE, with the WHOLE junction_clear sequence's
        # final outcome -- never prematurely when only an intermediate
        # phase resolves (`advance.done is False`), or the next ordinary
        # analysis's failure_context would see "junction_clear completed"
        # after just the first recede, even if a LATER phase goes on to
        # fail. `original_id == command_id` for a plan-less dispatch or
        # phase 0 itself (nothing was ever recorded under a DIFFERENT id).
        original_id = self._junction_original_command_id.pop(command_id, command_id)
        if advance is None or advance.done:
            self._attempts.resolve(original_id, outcome_status, now)
        elif advance.command is not None:
            self._junction_original_command_id[advance.command["command_id"]] = original_id
        # Freeze-blocking finding 5 (step-7a fix): `advance.phase_reached ==
        # "fallback" and advance.done` fires exactly once per sequence --
        # when the FALLBACK command's own terminal status (not its dispatch)
        # arrives. `outcome_status != "completed"` then means the composite's
        # own documented recovery path ALSO failed: mark it loudly and stop
        # re-dispatching for these robots, rather than leaving it indistinct
        # from an ordinary phase failure that a fallback still follows.
        if (
            advance is not None
            and advance.done
            and advance.phase_reached == "fallback"
            and outcome_status != "completed"
        ):
            self._mark_fallback_exhausted(command_id, robots)
        self.get_logger().info(f"command {command_id} resolved status={outcome_status}")
        self._machine.on_command_resolved(robots, outcome_status == "completed")
        self._cooldown.start(robots, now)
        self._publish_registry()

    def _mark_fallback_exhausted(self, command_id: str, robots: list[str]) -> None:
        """Terminal handling for a `junction_clear` fallback that ALSO failed.

        Freeze-blocking finding 5 (2026-10-02 IB10 composite smoke, episode
        2): a cross-phase failure's documented fallback (plain `yield`/
        `reroute`) can itself fail, leaving the M5 spec's "partial credit is
        scorable" provision with no description of what happens next. This
        logs the outcome loudly (`outcome=fallback_exhausted`, grep-able
        independent of any artifact), re-routes every one of this fallback's
        robots' plan legs from `failed` to the new terminal `exhausted`
        status (scorable going forward: `PlanStateContext`/decision artifacts
        already serialize whatever `PlanLegStatus` a tracked leg carries, so
        this needs no separate artifact field), and adds them to the
        permanent re-trigger suppression set (`_exhausted_robots`, folded
        into `cooldown_robots` at every future trigger check) so M5 stops
        re-dispatching for a conflict its own documented recovery already
        gave up on -- never an infinite retry loop, but also never silently
        indistinguishable from an ordinary failure.

        Args:
            command_id: The fallback command's own id.
            robots: Every robot the fallback command addressed.
        """
        self.get_logger().error(
            f"junction_clear fallback exhausted command={command_id} "
            f"robots={sorted(robots)} outcome=fallback_exhausted"
        )
        self._exhausted_robots.update(robots)
        if self._plan_tracker is None:
            return
        plan_id = self._plan_id_by_command_id.get(command_id)
        if plan_id is None:
            return
        for robot_id in robots:
            try:
                self._plan_tracker.set_leg_status(plan_id, robot_id, "exhausted")
            except (KeyError, ValueError) as exc:
                self.get_logger().warning(
                    f"plan leg exhaustion update failed plan={plan_id} robot={robot_id}: {exc}"
                )

    # ---- helpers ----

    def _effective_goal(self, robot_id: str):
        eff = self._registry.effective(robot_id)
        return None if eff is None else eff[1]

    def _progress_goal(self, robot_id: str):
        # A held-back robot is not driven yet, so standing still is not a
        # stall and it cannot be arriving. The prompt, the shadow and dispatch
        # still see its mission goal through _effective_goal.
        if self._registry.is_pending(robot_id):
            return None
        return self._effective_goal(robot_id)

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
        zoom_tile_path(self._config.frame_dump_dir, request_id).unlink(missing_ok=True)

    def _apparatus_inputs(
        self, request_id: str, snapshot, robots: list[str], frame
    ) -> tuple[dict[str, Any], ZoomTileRecord | None]:
        """Prompt-apparatus request fields for one triggered analysis.

        Grid/trail sentences are stated only when configured AND reported
        drawn by M1; the zoom tile is cut synchronously here (a sub-ms crop)
        so the request never names a tile that failed; the options block is
        derived from M3's audit on this snapshot. Never raises: any failure
        drops that one condition, logged and recorded.
        """
        config = self._config
        overlays = self._latest_overlays
        fields: dict[str, Any] = {}
        if config.plan_channel_enabled:
            fields.update(
                apparatus_request_fields(
                    prompt_metric_grid=config.prompt_metric_grid,
                    prompt_motion_trails=config.prompt_motion_trails,
                    overlays=overlays,
                )
            )
        for name, requested, drawn in (
            ("metric_grid", config.prompt_metric_grid, overlays.metric_grid),
            ("motion_trails", config.prompt_motion_trails, overlays.motion_trails),
        ):
            if requested != drawn:
                self.get_logger().warning(
                    f"apparatus mismatch request={request_id} overlay={name} "
                    f"prompt_flag={requested} m1_drawn={drawn}"
                )
        zoom_record: ZoomTileRecord | None = None
        if config.prompt_zoom_tile:
            # `robots` is the event's whole involved set (ruling 2026-10-04).
            positions = {r.robot_id: (r.x, r.y) for r in snapshot.robots if r.robot_id in robots}
            calibration = None if self._tile_marker is None else self._tile_marker.calibration
            zoom_record = write_zoom_tile(
                frame,
                request_id,
                config.frame_dump_dir,
                positions,
                calibration,
                config.prompt_zoom_tile_margin_m,
                config.prompt_zoom_tile_width_px,
            )
            if zoom_record.attached:
                fields["zoom_tile_path"] = zoom_record.path
            else:
                self.get_logger().warning(
                    f"zoom tile dropped request={request_id} reason={zoom_record.reason}"
                )
        if config.prompt_candidate_options:
            try:
                fields["candidate_options"] = build_candidate_options(
                    snapshot,
                    geometry=config.scenario_geometry,
                    static_obstacles=config.static_obstacles,
                    yield_feasibility_mode=config.grounding_yield_feasibility,
                    grounding_params=self._grounding.params,
                )
            except Exception as exc:  # the options block is dropped, never the analysis
                self.get_logger().error(
                    f"candidate options failed request={request_id}: {type(exc).__name__}: {exc}"
                )
        return fields, zoom_record

    def _prompt_conditions(
        self, request: ReasonerRequest, zoom_record: ZoomTileRecord | None, votes: int
    ) -> PromptConditions:
        return build_prompt_conditions(
            request=request,
            overlays=self._latest_overlays,
            prompt_metric_grid=self._config.prompt_metric_grid,
            prompt_motion_trails=self._config.prompt_motion_trails,
            prompt_zoom_tile=self._config.prompt_zoom_tile,
            zoom_tile=zoom_record,
            permutation_votes=votes,
            prompt_candidate_options=self._config.prompt_candidate_options,
        )

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
