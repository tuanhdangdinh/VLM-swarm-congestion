from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class ReasonerRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1)
    image_path: str = Field(min_length=1)
    frame_id: str = Field(min_length=1)
    stamp: float = Field(ge=0)
    robot_states: list[RobotStateInput]
    prompt_context: dict[str, object] = Field(default_factory=dict)


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


class ReasonerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend_id: str = Field(min_length=1)
    timeout_sec: float = Field(default=30.0, gt=0)
    max_attempts: int = Field(default=2, ge=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)
    allow_reask: bool = True
