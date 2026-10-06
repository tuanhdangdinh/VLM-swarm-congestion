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

# Order the prompt lists robots in. Counterbalancing it separates a positional
# default ("pick the robot presented first") from an ID or geometry preference.
RobotPresentationOrder = Literal["id_asc", "id_desc"]
# An explicit presentation order: robot ids, first listed first. M5's `random`
# mode draws one per episode once three or more robots are in the scene, where
# the two id sorts are only 2 of the N! orders (2026-09-28, T2b).
RobotPresentationPermutation = tuple[str, ...]
RobotOrder = RobotPresentationOrder | RobotPresentationPermutation

# What stands in a stalled robot's way (rev-8 stage-1 vocabulary), emitted by
# both arms on `CongestionDecision.blocker_kind` since the prompt-v2 bundle.
BlockerKind = Literal["robot", "object", "transient"]

# The grounded primitives a `proposed_plan` leg may name (prereg-v2 (a0),
# "Universal proposed_plan channel"): every value maps to a maneuver M3/M4 can
# already ground and execute. "continue" is the lenient-completion default for
# a tracked robot a plan omits.
PlanLegAction = Literal["yield", "reverse", "cross", "wait", "reroute", "continue"]

# Bound for `CongestionDecision.reasoning` (prompt v3's "bounded free-text
# reasoning field"). Sized generously for a few sentences of justification,
# not a full chain-of-thought transcript -- free-text spatial CoT is
# prohibited in the prompt apparatus (prereg-v2 rev 6), and this field is a
# short rationale, not that trace.
REASONING_MAX_LENGTH = 2000

# Prompt template the builder renders. 1 is the frozen pre-bundle template every
# artifact stored before 2026-09-27 was rendered with (`reasoning.vlm.prompt_v1`);
# 2 is the frozen prompt-v2 bundle (`reasoning.vlm.prompt_v2`); 3 is the
# plan-state / reasoning-first-JSON bundle (prereg-v2 rev 4/6). A Literal, so
# an unknown version fails validation instead of silently rendering the
# current template. `CURRENT_PROMPT_VERSION` stays 2, not 3: v3 is opt-in
# (M5 passes `prompt_version=3` explicitly, e.g. behind
# `orchestrator.yaml`'s `plan_channel_enabled`) so every existing caller that
# does not ask for it keeps rendering byte-identical prompts.
PromptVersion = Literal[1, 2, 3]
CURRENT_PROMPT_VERSION: PromptVersion = 2


class RobotStateInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    x: float
    y: float
    theta: float
    linear_velocity: float | None = None
    angular_velocity: float | None = None
    task: str | None = None
    status: str | None = None
    goal: tuple[float, float] | None = None


class SnapshotFrame(BaseModel):
    """One reasoning-side scene snapshot; M5 converts its SceneSnapshot to this."""

    model_config = ConfigDict(frozen=True)

    stamp: float = Field(ge=0)
    robots: list[RobotStateInput]
    # Robots whose base mission M5 still holds back at this frame's instant
    # (`start_pending` in its registry). Frame-level, not a RobotStateInput
    # field, so no prompt-rendered contract changes; read only by Arm B's
    # held-robot exclusion. Empty for every frame built before it existed.
    held_robot_ids: tuple[str, ...] = ()

    def find_robot(self, robot_id: str) -> RobotStateInput | None:
        """Return the state for `robot_id`.

        Args:
            robot_id: Robot to look up.

        Returns:
            The robot's state in this frame, or None if it is absent.
        """
        for state in self.robots:
            if state.robot_id == robot_id:
                return state
        return None


class MotionTableEntry(BaseModel):
    """Per-robot arrival evidence at a conflict zone, from the snapshot buffer."""

    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    # 1-based rank of arrival_stamp among robots that entered the zone.
    arrival_order: int | None = Field(default=None, ge=1)
    # Stamp of the first buffered frame with the robot inside the zone. A robot
    # already inside in the oldest frame gets that frame's stamp (left-censored).
    arrival_stamp: float | None = None


class MotionTable(BaseModel):
    """Derived temporal context over a snapshot window."""

    model_config = ConfigDict(frozen=True)

    window_sec: float = Field(ge=0.0)
    entries: list[MotionTableEntry]


class StaticObstacleInput(BaseModel):
    """One fixed, axis-aligned obstacle in the world frame (centre plus extent)."""

    model_config = ConfigDict(frozen=True)

    obstacle_id: str = Field(min_length=1)
    x: float
    y: float
    size_x_m: float = Field(gt=0)
    size_y_m: float = Field(gt=0)


class FailureContext(BaseModel):
    """Prior-attempt summary injected into re-analysis prompts (Reflexion-lite)."""

    model_config = ConfigDict(frozen=True)

    strategy: str = Field(min_length=1)
    yield_robot: str | None = None
    crossing_order: list[str] | None = None
    outcome_status: str = Field(min_length=1)
    failure_detail: str = Field(min_length=1)


# M5's per-leg execution status (prereg-v2 rev 4, "Plan lifecycle"); owned by
# `swarm_orchestrator.plan_tracker.PlanTracker`, mirrored here only as the
# vocabulary the prompt-v3 plan-state block renders. `exhausted` (step-7a
# fix, freeze-blocking finding 5): the `junction_clear` composite's own
# documented fallback ALSO failed, after an earlier phase already had -- a
# terminal outcome distinct from plain `failed` (which a fallback dispatch
# may still follow), so M5 stops re-dispatching for it and it is scorable
# as its own outcome, not folded into ordinary failure.
PlanLegStatus = Literal["pending", "active", "done", "failed", "exhausted"]


class PlanStateLeg(BaseModel):
    """One leg of the active plan, as M5 reports its execution status."""

    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    action: PlanLegAction
    status: PlanLegStatus


class PlanStateContext(BaseModel):
    """What M2 is shown of its own active plan (prereg-v2 rev 4 plan-state block).

    Generalizes `FailureContext` from "the previous single-conflict attempt"
    to "the scene-wide plan M5 is currently executing": the active plan's
    `plan_id`, every leg's current status, and which robots' legs changed
    since the last invocation that produced this plan (`changed_robot_ids` --
    empty for the plan's first rendering). Optional on `ReasonerRequest` so a
    request that predates plan tracking, or one built with
    `plan_channel_enabled=False`, renders byte-identically to before this
    field existed.
    """

    model_config = ConfigDict(frozen=True)

    plan_id: int = Field(ge=1)
    legs: list[PlanStateLeg]
    changed_robot_ids: tuple[str, ...] = ()


class CandidateOption(BaseModel):
    """One plan action the verifier accepts for one robot in the current scene.

    A plain projection of M3's candidate-option derivation
    (`reasoning.rag.command_grounder.derive_candidate_options`), so M2 never
    imports M3 -- same pattern as `RetreatCandidateOption`.
    """

    model_config = ConfigDict(frozen=True)

    action: PlanLegAction
    # Short scene-derived qualifier rendered in parentheses after the action
    # (e.g. "south arm" for a reverse along a declared junction arm); None
    # renders the bare action.
    detail: str | None = None


class RobotCandidateOptions(BaseModel):
    """Every action the verifier accepts for one robot, in vocabulary order."""

    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    options: list[CandidateOption]


class ReasonerRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1)
    image_path: str = Field(min_length=1)
    frame_id: str = Field(min_length=1)
    stamp: float = Field(ge=0)
    robot_states: list[RobotStateInput]
    # The most recent resolved attempt in the episode.
    failure_context: FailureContext | None = None
    # The most recent FAILED attempt, set only when it is not the attempt in
    # `failure_context`, so a completed maneuver cannot displace a failure from
    # the prompt (failure-context depth policy, 2026-09-27). Default None renders
    # byte-identically to every prompt stored before the field existed.
    last_failed_context: FailureContext | None = None
    # Prompt-v3 plan-state block (prereg-v2 rev 4): the active plan M5 is
    # executing, generalizing `failure_context`. Independent of it -- a
    # request may carry both, or neither. None renders byte-identically to
    # every request built before plan tracking existed; only rendered by the
    # v3 template (prompt_version == 3), so a v1/v2 request carrying it is a
    # caller error the prompt silently ignores rather than a render-time one.
    plan_state: PlanStateContext | None = None
    # Ablation axis (rev-8 modality table): False withholds the derived pairwise
    # distance/facing lines so the VLM must judge geometry from coordinates + image.
    include_pairwise_geometry: bool = True
    # Opt-in ablation axis (2026-09-18): True appends a block that gives the image
    # precedence over the state block on a clear contradiction, without licensing
    # re-derivation of geometry from raw coordinates. Default False so every
    # pre-existing run and artifact stays comparable; see
    # docs/reports/2026-09-18-gemini-er2-image-grounding.md.
    include_visual_crosscheck: bool = False
    # Fixed obstacles M5 declares for the scene, rendered only when the modality
    # below is on.
    static_obstacles: list[StaticObstacleInput] = Field(default_factory=list)
    # Ablation axis: default False because every decision artifact collected so
    # far was produced without an obstacle channel; switching it on by default
    # would silently break comparability with all of them.
    include_static_obstacles: bool = False
    # Ablation axis: the order robots are presented in. Default "id_asc" keeps
    # every prompt rendered so far byte-identical; "id_desc" is the
    # counterbalanced condition that breaks the presentation-order confound.
    # A tuple of robot ids is an explicit order (listed robots first, in that
    # order; any robot it does not name follows in ascending id).
    robot_presentation_order: RobotOrder = "id_asc"
    # Which prompt template renders this request. New requests get the current
    # template; the replay program sets 1 for artifacts that predate the field,
    # so their stored prompts still reconstruct byte-identically.
    prompt_version: PromptVersion = CURRENT_PROMPT_VERSION
    # Prompt-apparatus conditions (prereg-v2 rev 6, 2026-10-04; A/B cells,
    # never defaults). Each records what the request ACTUALLY carries -- M5
    # sets them from what M1 drew / what M5 attached, not from config alone --
    # and each is rendered by the v3 template only (v1/v2 are frozen and
    # ignore them, like `plan_state`). All unset = byte-identical prompt.
    # Spacing of the labeled metric grid M1 drew on the frame; None = no grid.
    metric_grid_spacing_m: float | None = Field(default=None, gt=0)
    # Whether M1 drew motion trails on the frame.
    motion_trails_drawn: bool = False
    # Second image: an enlarged crop of the annotated frame around the
    # robots this analysis was triggered for; None = single-image request.
    zoom_tile_path: str | None = Field(default=None, min_length=1)
    # Verifier-candidate-options condition: per-robot actions M3's own audit
    # accepts in this scene. CONSTRUCT CHANGE when set -- the plan channel
    # measures constrained selection, not free planning.
    candidate_options: list[RobotCandidateOptions] | None = None

    @model_validator(mode="after")
    def _validate_last_failed_needs_latest(self) -> "ReasonerRequest":
        if self.last_failed_context is not None and self.failure_context is None:
            raise ValueError("last_failed_context requires failure_context")
        return self

    @field_validator("robot_presentation_order")
    @classmethod
    def _validate_explicit_order(cls, value: RobotOrder) -> RobotOrder:
        if isinstance(value, tuple) and (not value or len(set(value)) != len(value)):
            raise ValueError(
                f"an explicit robot_presentation_order must list distinct robot ids; got {value}"
            )
        return value


class PromptPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    system_prompt: str
    user_prompt: str
    image_path: str
    known_robot_ids: list[str]
    # Further images sent after `image_path`, in order (prompt-apparatus zoom
    # tile). Empty for every single-image request, which every backend then
    # sends exactly as before this field existed.
    extra_image_paths: list[str] = Field(default_factory=list)


class BackendResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    backend_id: str
    latency_ms: int | None = Field(default=None, ge=0)
    token_usage: dict[str, int] | None = None
    raw: dict[str, object] = Field(default_factory=dict)
    # The model string the provider says actually served the call (OpenAI
    # answers the alias `gpt-4o` with a dated snapshot), or None when the
    # provider response carries none. Parsed by each backend, never guessed.
    served_model: str | None = None
    # A structured provider refusal (Anthropic: HTTP 200 with
    # `stop_reason: "refusal"`). Callers treat it exactly like a text refusal
    # matched by `reasoner.is_refusal`, so the standard refusal accounting and
    # mitigation see it even when the refusal carries no text at all.
    refusal: bool = False
    # The provider's refusal category (`stop_details.category`), when given.
    refusal_category: str | None = None


class ProposedPlanLeg(BaseModel):
    """One robot's leg in a `CongestionDecision.proposed_plan` (a0 contract).

    A plain `{robot_id, action}` pair; list position in the owning
    `proposed_plan` is the proposed execution order, not encoded on the leg
    itself.
    """

    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    action: PlanLegAction

    @field_validator("action", mode="before")
    @classmethod
    def _lowercase_action(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value


class CongestionDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Prompt v3 "reasoning-field-first JSON" (prereg-v2 rev 6, "Prompt
    # apparatus"): a bounded free-text field the v3 schema asks for FIRST,
    # before any strict classification field, so the model writes its
    # reasoning before committing to one (the premature-serialization
    # effect). Declared first here too, so `model_dump`/the JSON schema
    # property order matches what v3 asks the model to emit; every other
    # field's strictness and validation are unchanged. `max_length` is the
    # "bounded" in "bounded free-text reasoning field" (mirrored in
    # `reasoning/schemas/vlm_decision.schema.json`'s `maxLength`); absent on
    # every v1/v2 artifact and never required, so it costs nothing when the
    # backend or prompt version does not ask for it. An over-length raw
    # value is TRUNCATED to the bound before construction, never rejected,
    # by `output_parser._sanitize_optional_fields` (tag `reasoning=truncated`),
    # so this constraint is never what actually raises; a non-string value is
    # nulled instead (tag `reasoning=default:invalid_type`), same pattern as
    # `blocker_kind`.
    reasoning: str | None = Field(default=None, max_length=REASONING_MAX_LENGTH)
    congestion_detected: bool
    type: Literal["none", "deadlock", "bottleneck", "crowding", "anomaly"]
    involved_robots: list[str]
    root_cause: str
    strategy: Literal[
        "none",
        "yield",
        "reroute",
        "convoy",
        "priority_override",
        "temporary_wait",
        "reverse",
        # Composite recede-then-yield for a formed multi-robot junction jam
        # (prereg-v2 (a), build-order step 5). Prompt v1/v2 never mention it
        # (frozen); only prompt v3's strategy list offers it
        # (`reasoning.vlm.prompt_builder._USER_TEMPLATE`). Shared Literal
        # with v1/v2, same precedent as `blocker_kind`/`crossing_order`/
        # `proposed_plan` (all v2+-only prompt fields the parser already
        # accepts at every prompt version): a v1/v2-prompted response that
        # happened to emit this string parses instead of raising, consistent
        # with how every other v2+-only field already behaves, not a new
        # inconsistency this token introduces.
        "junction_clear",
    ]
    justification: str
    # The model's stated choice of yielder at decision time, distinct from
    # FailureContext.yield_robot (M5's record of who actually got dispatched).
    # Only meaningful when strategy == "yield"; never required, since older
    # artifacts and models that omit it must still parse.
    yield_robot: str | None = None
    # Prompt-v2 bundle fields, optional for the same reason as `yield_robot`.
    # What blocks the stalled robots (T3a scores it against Arm B's verdict).
    blocker_kind: BlockerKind | None = None
    # Every involved robot in the order they should pass, first entry first; a
    # yielder passes after the robots it yields to. Asked for at 3+ robots (T2b).
    crossing_order: list[str] | None = None
    # (a0) universal proposed_plan channel (prereg-v2 rev 4, "Universal
    # proposed_plan channel"): the VLM's full scene-wide resolution sequence,
    # carried on the stage-1 response for every strategy and scenario, not
    # just this decision's own involved robots. Optional so every artifact and
    # backend that predates the field, and every re-ask that omits it, still
    # parses byte-identically; `reasoning.rag.command_grounder`'s verify/repair
    # engine audits it leg-by-leg before anything is dispatched, and a `None`
    # here degrades to that engine's own derived plan (provenance
    # `m3_default`) in every scenario, same as v1's behaviour before this
    # field existed. Structural defects in raw VLM text (a duplicate robot, an
    # unrecognised action, an unknown shape) are nulled to `None` by
    # `output_parser._sanitize_optional_fields` with a logged degradation tag,
    # same pattern as `blocker_kind`/`crossing_order`; this field's own
    # validator is the backstop for direct construction.
    proposed_plan: list[ProposedPlanLeg] | None = None

    @field_validator("type", "strategy", "blocker_kind", mode="before")
    @classmethod
    def _lowercase_enum(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value

    @field_validator("involved_robots", mode="after")
    @classmethod
    def _dedupe_involved_robots(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for robot_id in value:
            if robot_id not in seen:
                seen.append(robot_id)
        return seen

    @model_validator(mode="after")
    def _validate_yield_robot_is_involved(self) -> "CongestionDecision":
        if self.yield_robot is not None and self.yield_robot not in self.involved_robots:
            raise ValueError(
                f"yield_robot {self.yield_robot!r} is not in involved_robots "
                f"{self.involved_robots!r}"
            )
        return self

    @model_validator(mode="after")
    def _validate_crossing_order_is_permutation(self) -> "CongestionDecision":
        if self.crossing_order is not None and not is_permutation(
            self.crossing_order, self.involved_robots
        ):
            raise ValueError(
                f"crossing_order {self.crossing_order!r} is not a permutation of "
                f"involved_robots {self.involved_robots!r}"
            )
        return self

    @model_validator(mode="after")
    def _validate_proposed_plan_robot_ids_unique(self) -> "CongestionDecision":
        # Schema-level invariant ("each robot at most once"); unknown
        # robot_ids and strategy-consistency are checked later by M3's
        # verify/repair engine, which alone knows the tracked robot roster.
        if self.proposed_plan is not None:
            robot_ids = [leg.robot_id for leg in self.proposed_plan]
            if len(robot_ids) != len(set(robot_ids)):
                raise ValueError(
                    f"proposed_plan lists a robot more than once: {robot_ids!r}"
                )
        return self

    @model_serializer(mode="wrap")
    def _omit_unset_reasoning(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # `reasoning` (prompt v3) is None for every v1/v2 decision -- every
        # decision ever collected, and every decision a flag-off run produces
        # from here on. Dropping the key then (same pattern as
        # `GroundingParamsSource._omit_unset_x_band`) keeps a flag-off
        # artifact's `decision` block, and the replay reconstructor's
        # re-rendering of it, byte-identical to one written before this field
        # existed; a v3 decision that DOES state a reasoning value still
        # carries the key.
        data = handler(self)
        if data.get("reasoning") is None:
            data.pop("reasoning", None)
        return data


def is_permutation(order: list[str], robot_ids: list[str]) -> bool:
    """Return whether `order` lists every robot of `robot_ids` exactly once.

    Args:
        order: Candidate ordering.
        robot_ids: The robots it must cover (assumed duplicate-free).

    Returns:
        True when `order` is a rearrangement of `robot_ids`.
    """
    return len(order) == len(robot_ids) and set(order) == set(robot_ids)


class RetreatChoiceDecision(BaseModel):
    """Stage-2 VLM output: one set-of-mark candidate letter plus one clause."""

    model_config = ConfigDict(frozen=True)

    retreat_choice: str = Field(min_length=1, max_length=1)
    justification: str

    @field_validator("retreat_choice", mode="before")
    @classmethod
    def _uppercase_label(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value


# Stage-2 (retreat-choice) prompt template. Versioned apart from the stage-1
# `PromptVersion`: the two templates change independently. Pinned by SHA in
# tests/unit/test_stage2_prompt.py; any edit is a new version, not a re-pin.
# Version 1 (text-only letters, e358229) never rendered a live call: it was
# committed on an unpushed branch, never deployed, and no artifact carries a
# `stage2` block, so it was retired rather than frozen (2026-09-28 notes).
# Version 2 lists the candidates in letter order, so letter A is always the
# first-listed slot. It is frozen history, not retired: the six funded stage-2
# calls of the 2026-09-28 calibration mini-pilot (data/logs/vm_runs/calibration/
# 20260928_104408 .. 20260928_122832) were rendered with it. Version 3
# (amendments item 26) lists them in a seeded order independent of the letters
# (`RetreatChoiceRequest.listing_order`); its text is v2's, so v3 given the
# letter-order listing renders v2 byte for byte.
Stage2PromptVersion = Literal[2, 3]
CURRENT_STAGE2_PROMPT_VERSION: Stage2PromptVersion = 3

# Why a stage-2 call produced no rendered letter, in the measurement plan's
# vocabulary where one exists (`invalid_label`, `parse_failure`); `refusal`,
# `timeout` and `backend_error` are the transport-level reasons behind a
# `retreat=default:no_choice` grounding.
Stage2FailureCause = Literal[
    "invalid_label", "parse_failure", "refusal", "timeout", "backend_error"
]


class RetreatCandidateOption(BaseModel):
    """One lettered retreat pose as the stage-2 prompt presents it.

    A plain projection of M3's `RetreatCandidate`, so M2 need not import M3.
    """

    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1, max_length=1)
    # World-frame pose after the backup and the sidestep, in metres.
    x: float
    y: float
    backup_m: float = Field(ge=0)
    # Signed robot-frame lateral offset (positive = left).
    lateral_m: float


class RetreatChoiceRequest(BaseModel):
    """Stage-2 input: the grounded yielder, who passes, and the lettered candidates."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1)
    # The image the call sends: the stage-1 decision frame with the candidate
    # letters drawn on it (`marks_drawn`), or that frame unmarked when the
    # drawing degraded.
    image_path: str = Field(min_length=1)
    # Whether `image_path` carries the letters; the prompt says which.
    marks_drawn: bool = False
    yielder_id: str = Field(min_length=1)
    # Robots that pass while the yielder waits, first to pass first.
    crossing_order: list[str]
    robot_states: list[RobotStateInput]
    candidates: list[RetreatCandidateOption] = Field(min_length=1)
    # The letters in the order the prompt lists them (version 3 only). Required
    # under v3, so a caller cannot silently fall back to letter order and
    # re-confound letter A with the first-listed slot; absent under v2, which
    # always lists in letter order.
    listing_order: list[str] | None = None
    prompt_version: Stage2PromptVersion = CURRENT_STAGE2_PROMPT_VERSION

    @model_validator(mode="after")
    def _validate_unique_labels(self) -> "RetreatChoiceRequest":
        labels = [candidate.label for candidate in self.candidates]
        if len(labels) != len(set(labels)):
            raise ValueError(f"candidate labels must be unique, got {labels}")
        return self

    @model_validator(mode="after")
    def _validate_listing_order(self) -> "RetreatChoiceRequest":
        if self.prompt_version == 2:
            if self.listing_order is not None:
                raise ValueError("stage-2 prompt v2 lists in letter order; listing_order unset")
            return self
        if self.listing_order is None:
            raise ValueError(f"stage-2 prompt v{self.prompt_version} requires listing_order")
        labels = sorted(candidate.label for candidate in self.candidates)
        if sorted(self.listing_order) != labels:
            raise ValueError(
                f"listing_order must be a permutation of {labels}, got {self.listing_order}"
            )
        return self


class RetreatChoiceResult(BaseModel):
    """Outcome of one stage-2 call: a letter, or why none usable came back."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    backend_id: str
    # The parsed answer. With `failure_cause == "invalid_label"` it names a
    # letter that was not rendered, and is kept so the grounder can tag it.
    choice: RetreatChoiceDecision | None
    raw_text: str | None
    attempts: int = Field(ge=1)
    latency_ms: int | None = Field(default=None, ge=0)
    failure_cause: Stage2FailureCause | None = None
    error_type: str | None = None
    error_message: str | None = None
    refusal_attempts: int = Field(default=0, ge=0)
    # The budget the call ran under (`RetreatChooser`'s config), so an
    # artifact shows the stage-2 bound apart from stage 1's.
    max_attempts: int | None = Field(default=None, ge=1)
    timeout_sec: float | None = Field(default=None, gt=0)


class EffectiveSamplingConfig(BaseModel):
    """The sampling settings actually in force for one reasoning call.

    Every field is the *configured* value (from `ReasonerConfig` plus the
    backend's own config), never a value echoed back by a provider: the point is
    to prove from an artifact alone which decoding parameters a run was
    collected under. A backend that drops some of them still records them here,
    with the dropped subset repeated in `unsupported_sampling`. The two
    per-call exceptions, both filled from the response rather than the config,
    are `unsupported_sampling` and `served_model`.
    """

    model_config = ConfigDict(frozen=True)

    backend_id: str = Field(min_length=1)
    # None when the backend takes no model id (e.g. "mock").
    model_id: str | None = None
    temperature: float
    top_p: float
    top_k: int
    presence_penalty: float
    max_attempts: int = Field(ge=1)
    max_tokens: int = Field(ge=1)
    # The refusal-mitigation threshold as configured; None means the mitigation
    # was off (every backend but openai in the shipped config). Defaults to None
    # so blocks recorded before this field existed still parse, although those
    # runs cannot be told apart from mitigation-off runs by this field alone.
    image_fallback_after_attempts: int | None = Field(default=None, ge=1)
    # Gemini-only: the Interactions API exposes no temperature/top_p/top_k, so
    # these two are the only decoding controls it honours. None elsewhere.
    seed: int | None = None
    thinking_level: str | None = None
    # OpenAI-compatible reasoning control (gpt-5.1 pilot: "none"); None when
    # the request carries no `reasoning_effort` field.
    reasoning_effort: str | None = None
    # Provider thinking mode as configured: Anthropic `thinking.type`
    # ("adaptive" / "between_tools") or the DeepSeek `thinking.type`
    # ("enabled" / "disabled"); None when the request carries no thinking field.
    thinking_mode: str | None = None
    # Anthropic `output_config.effort`; None when not sent.
    effort: str | None = None
    # Mirrors `ReasonerDiagnostics.unsupported_sampling`, so the configured
    # values and the subset the backend could not honour read off one block.
    unsupported_sampling: dict[str, float] | None = None
    # Mirrors `ReasonerDiagnostics.served_model`, so the configured `model_id`
    # (possibly an alias) and the snapshot that answered read off one block.
    served_model: str | None = None


class ReasonerDiagnostics(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    backend_id: str
    attempts: int = Field(ge=1)
    latency_ms: int | None = Field(default=None, ge=0)
    token_usage: dict[str, int] | None = None
    parse_status: Literal["valid", "invalid", "failed"]
    error_type: str | None = None
    error_message: str | None = None
    # None means the backend honoured every ReasonerConfig sampling field it was
    # given (or did not report otherwise) -- distinct from an empty dict, which
    # would mean "the backend reported and dropped nothing." See
    # `reasoning.vlm.gemini_backend.GeminiBackend` for a backend that populates
    # this from `BackendResponse.raw["unsupported_sampling"]`.
    unsupported_sampling: dict[str, float] | None = None
    # `BackendResponse.served_model` of the last response the backend returned
    # (a refused or unparseable one included), or None when no response came
    # back or the backend reports no model string.
    served_model: str | None = None
    # None when the caller did not describe the effective config (e.g. a test
    # harness or a script that constructs a Reasoner without one); additive, so
    # artifacts written before this field existed stay readable.
    reasoner_config_effective: EffectiveSamplingConfig | None = None
    # Number of attempts whose assistant text was a safety refusal (`is_refusal`).
    # Distinct from `attempts`: a refusal is one kind of parse failure, and the
    # mitigation below keys off refusals alone.
    refusal_attempts: int = Field(default=0, ge=0)
    # The provider's category for the most recent structured refusal
    # (`BackendResponse.refusal_category`), or None when no attempt carried one.
    refusal_category: str | None = None
    # True when the refusal mitigation fired: a later attempt re-sent the same
    # prompt text with the camera frame replaced by a neutral image. The decision
    # for that call was made without the image channel, so an audit must be able
    # to see it from the artifact alone.
    image_fallback_used: bool = False
    # 1-based index of the attempt that carried the neutral image, or None when
    # the mitigation did not fire.
    image_fallback_attempt: int | None = Field(default=None, ge=1)
    # Optional decision fields the parser nulled because the model's value was
    # invalid (tag vocabulary: `output_parser.DECISION_DEGRADATION_TAGS`). The
    # decision itself stayed valid; an absent field is not listed here.
    decision_degradations: list[str] = Field(default_factory=list)


class ReasonerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    decision: CongestionDecision | None
    raw_text: str | None
    diagnostics: ReasonerDiagnostics


class LlamaServerBackendConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str = "http://127.0.0.1:8080/v1"
    model_id: str = Field(min_length=1)
    model_path: str | None = None  # server-startup concern; not used per-request
    mmproj_path: str | None = None  # path to mmproj GGUF for vision; None = text-only
    # Send `PromptPayload.extra_image_paths` (the zoom tile) as further
    # `image_url` parts. False refuses them, as before this field existed:
    # multi-image through llama-server's mtmd path must be smoke-verified per
    # served model before a config turns it on.
    multi_image: bool = False


class OpenAIBackendConfig(BaseModel):
    """Config for any OpenAI-compatible Chat Completions provider.

    Every optional request field defaults to absent, so the gpt-4o pin's
    request body is byte-identical to the one sent before these fields existed.
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"  # env var NAME holding the key; never the key itself
    organization: str | None = None
    # OpenAI reasoning models (gpt-5.1): "none" keeps temperature/top_p legal
    # and bills no reasoning tokens. None omits the field.
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high"] | None = None
    # Reasoning-family models reject `max_tokens` in favour of
    # `max_completion_tokens`; the name is config so the pin decides it.
    max_tokens_param: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    # DeepSeek's `thinking: {"type": ...}` extension; temperature has no effect
    # while thinking is enabled (its default). None omits the field.
    thinking_type: Literal["enabled", "disabled"] | None = None


class AnthropicBackendConfig(BaseModel):
    """Config for the Anthropic Messages API backend."""

    model_config = ConfigDict(frozen=True)

    model_id: str = "claude-opus-4-8"
    base_url: str = "https://api.anthropic.com/v1"
    api_key_env: str = "ANTHROPIC_API_KEY"  # env var NAME holding the key; never the key itself
    # Sent as `thinking: {"type": ...}`. On Sonnet 5.5 an omitted field runs
    # adaptive thinking (billed as output); "between_tools" turns it off and is
    # accepted only at effort high or below. None omits the field.
    thinking_type: Literal["adaptive", "between_tools"] | None = None
    # Sent as `output_config.effort`; None omits it (provider default).
    effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None


class GeminiBackendConfig(BaseModel):
    """Config for the Gemini Interactions API backend (Robotics-ER 2 preview).

    See `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`
    for the transport delta against the OpenAI/Anthropic backends.
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = "gemini-robotics-er-2-preview"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    api_key_env: str = "GEMINI_API_KEY"  # env var NAME holding the key; never the key itself
    thinking_level: Literal["low", "high"] = "low"
    # False: the live probe (2026-09-18) proved ER-2 satisfies vlm_decision.schema.json
    # without response_format, and the house precedent (llama_server_backend.py:38-41)
    # deliberately omits response_format so a reasoning trace is not suppressed. True
    # attaches response_format with reasoning/schemas/vlm_decision.schema.json.
    force_schema: bool = False
    # The only reproducibility control the Interactions API offers: it has no
    # temperature/top_p/top_k fields at all. Sent as generation_config.seed only
    # when set; None omits the field rather than sending a null.
    seed: int | None = None


class ReasonerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend_id: str = Field(min_length=1)
    timeout_sec: float = Field(default=30.0, gt=0)
    max_attempts: int = Field(default=2, ge=1)
    # Sampling defaults follow NVIDIA's Cosmos Reason 2 prompt guide (Qwen3 "with
    # reasoning" preset): temperature 0.6, top_p 0.95, top_k 20, presence_penalty 0.0.
    # This intentionally overrides the project's default-0.0 classification setting
    # because Cosmos Reason 2 is a chain-of-thought model that degrades at temp 0.0.
    temperature: float = Field(default=0.6, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, gt=0.0, le=1.0)
    top_k: int = Field(default=20, ge=1)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    # Large enough to hold the <think> reasoning trace plus the final JSON answer.
    max_tokens: int = Field(default=2048, ge=1)
    allow_reask: bool = True
    # Refusal mitigation. gpt-4o refuses on 19-38% of first attempts in the live
    # M2 loop, and the trigger is the annotated camera frame rather than the
    # prompt text (docs/reports/2026-09-25-frame-replay.md rev 2-3). When this is
    # set and attempt `k >= image_fallback_after_attempts` was refused, the next
    # attempt re-sends the unchanged prompt with a neutral image in place of the
    # frame. None disables the mitigation, which is the default so that backends
    # that never refuse (gemini, llama_server) keep the image channel on every
    # attempt.
    image_fallback_after_attempts: int | None = Field(default=None, ge=1)
