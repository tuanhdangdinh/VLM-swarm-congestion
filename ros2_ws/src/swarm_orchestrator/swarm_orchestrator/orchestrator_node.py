"""Thin ROS2 node wiring M5's pure logic to topics, services, and a worker thread."""
from __future__ import annotations

import json
import os
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

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
from reasoning.vlm import backend_section, build_backend, resolve_reasoner_config
from reasoning.vlm.models import (
    AnthropicBackendConfig,
    FailureContext,
    LlamaServerBackendConfig,
    OpenAIBackendConfig,
    ReasonerConfig,
    ReasonerRequest,
    RobotPresentationOrder,
)
from reasoning.vlm.reasoner import Reasoner
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
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    ReasoningPipeline,
    append_scene_log,
    build_failed_outcome,
    build_failure_context,
    build_reasoner_request,
    dump_frame_png,
    fan_out_command,
    write_decision_artifact,
)
from swarm_orchestrator.state_machine import (
    DirectiveKind,
    OrchestratorStateMachine,
)
from swarm_orchestrator.task_registry import TaskRegistry


def _build_default_pipeline(config: OrchestratorConfig) -> ReasoningPipeline:
    reasoner_config, backend_config = _load_vlm_config(config.reasoning_backend_id)
    backend = build_backend(config.reasoning_backend_id, backend_config)
    reasoner = Reasoner(backend, reasoner_config)
    return InProcessPipeline(
        reasoner=reasoner,
        ground_fn=ground_reasoner_result,
        scene_geometry=config.scenario_geometry,
    )


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
        self._pipeline = pipeline or _build_default_pipeline(self._config)

        self._detector = CongestionDetector(self._config)
        self._machine = OrchestratorStateMachine()
        self._tracker = CommandTracker()
        self._cooldown = CooldownTracker(self._config.cooldown_sec)
        self._attempts = AttemptMemory(self._config.failure_context_window_sec)
        self._registry = TaskRegistry()
        self._registry.load_initial(self._config)

        self._bridge = CvBridge()
        # rclpy.spin is single-threaded: _attempts and _pending_failure_context are
        # touched only on the callback thread, and the worker reads captured locals.
        # A MultiThreadedExecutor would need a lock around both.
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._future: Future[PipelineOutcome] | None = None
        # Context attached to the in-flight request; consumed by _handle_outcome so
        # the decision artifact records exactly what the VLM was told.
        self._pending_failure_context: FailureContext | None = None
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
        self._last_scene_log_at = float("-inf")
        self._frame_rgb = None
        self._frame_stamp: float | None = None
        self._latest_snapshot = None
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
        self._publish_registry()

    # ---- config ----

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

    def _on_scene_state(self, msg: String) -> None:
        try:
            snapshot = parse_scene_snapshot(msg.data)
        except ValueError as exc:
            self.get_logger().warning(f"skipping malformed SceneState: {exc}")
            return
        self._latest_snapshot = snapshot
        now = time.monotonic()
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
                    self._detector.mark_arrived(msg.robot_id, goal)
                    self._episodes.end_episode([msg.robot_id])
                    self.get_logger().info(f"robot {msg.robot_id} arrived at base goal {goal}")
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
        attempt = self._attempts.context_for(robots, now)
        failure_context = None if attempt is None else build_failure_context(attempt, now)
        if attempt is not None:
            self.get_logger().info(
                f"request={request_id} failure_context attached command={attempt.command_id} "
                f"strategy={attempt.strategy} executed={attempt.executed_strategy} "
                f"outcome={attempt.outcome_status}"
            )
        episode_index, order = self._episodes.order_for(robots)
        # Built here, not in the worker, so the artifact can record the exact request.
        request = build_reasoner_request(
            request_id,
            snapshot,
            image_path,
            failure_context=failure_context,
            include_pairwise_geometry=self._config.prompt_pairwise_geometry,
            static_obstacles=self._config.static_obstacles,
            include_static_obstacles=self._config.prompt_static_obstacles,
            robot_presentation_order=order,
        )
        self._pending_failure_context = failure_context
        self._pending_request = request
        self._pending_snapshot = snapshot
        self._pending_distances = dict(distance_to_goal_m)
        self._pending_episode_index = episode_index

        def task() -> PipelineOutcome:
            dump_frame_png(frame, image_path, downscale)
            return self._pipeline.run(request)

        self._future = self._executor.submit(task)
        return order

    def _handle_outcome(self, outcome: PipelineOutcome, now: float) -> None:
        failure_context = self._pending_failure_context
        request, snapshot = self._pending_request, self._pending_snapshot
        distances = self._pending_distances
        episode_index = self._pending_episode_index
        self._pending_failure_context = None
        self._pending_request = None
        self._pending_snapshot = None
        self._pending_distances = {}
        self._pending_episode_index = None
        try:
            artifact_path = write_decision_artifact(
                self._config.decision_log_dir,
                outcome,
                failure_context=failure_context,
                request=request,
                snapshot=snapshot,
                distance_to_goal_m=distances,
                run_id=self._run_id,
                session_id=self._session_id,
                prompt_robot_order_mode=self._config.prompt_robot_order,
                prompt_robot_order_seed=self._order_seed,
                episode_index=episode_index,
            )
            self.get_logger().info(f"decision artifact written: {artifact_path}")
        except OSError as exc:
            self.get_logger().error(f"decision artifact write failed: {exc}")

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

    def _dispatch(self, outcome: PipelineOutcome) -> None:
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

    def _busy_robots(self) -> set[str]:
        busy: set[str] = set()
        for command_id in list(self._tracker._records):  # node-local read
            if not self._tracker.is_resolved(command_id):
                busy.update(self._tracker.robots_of(command_id))
        return busy

    def _frame_is_fresh(self, scene_stamp: float) -> bool:
        if self._frame_rgb is None or self._frame_stamp is None:
            return False
        return abs(scene_stamp - self._frame_stamp) <= self._config.frame_scene_max_skew_sec

    def _cleanup_frame(self, request_id: str) -> None:
        if self._config.keep_debug_frames:
            return
        path = Path(self._config.frame_dump_dir) / f"{request_id}.png"
        path.unlink(missing_ok=True)

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
