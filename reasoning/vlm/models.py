from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Order the prompt lists robots in. Counterbalancing it separates a positional
# default ("pick the robot presented first") from an ID or geometry preference.
RobotPresentationOrder = Literal["id_asc", "id_desc"]


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


class ReasonerRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1)
    image_path: str = Field(min_length=1)
    frame_id: str = Field(min_length=1)
    stamp: float = Field(ge=0)
    robot_states: list[RobotStateInput]
    failure_context: FailureContext | None = None
    # Ablation axis (rev-8 modality table): False withholds the derived pairwise
    # distance/facing lines so the VLM must judge geometry from coordinates + image.
    include_pairwise_geometry: bool = True
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
    robot_presentation_order: RobotPresentationOrder = "id_asc"


class PromptPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    system_prompt: str
    user_prompt: str
    image_path: str
    known_robot_ids: list[str]


class BackendResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    backend_id: str
    latency_ms: int | None = Field(default=None, ge=0)
    token_usage: dict[str, int] | None = None
    raw: dict[str, object] = Field(default_factory=dict)


class CongestionDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

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
    ]
    justification: str
    # The model's stated choice of yielder at decision time, distinct from
    # FailureContext.yield_robot (M5's record of who actually got dispatched).
    # Only meaningful when strategy == "yield"; never required, since older
    # artifacts and models that omit it must still parse.
    yield_robot: str | None = None

    @field_validator("type", "strategy", mode="before")
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


class OpenAIBackendConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_id: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"  # env var NAME holding the key; never the key itself
    organization: str | None = None


class AnthropicBackendConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_id: str = "claude-opus-4-8"
    base_url: str = "https://api.anthropic.com/v1"
    api_key_env: str = "ANTHROPIC_API_KEY"  # env var NAME holding the key; never the key itself


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
