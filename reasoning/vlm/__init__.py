"""M2 VLM semantic reasoning: prompt building, backend adapters, parsing, orchestration."""

from reasoning.vlm.anthropic_backend import AnthropicBackend
from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.backend_factory import backend_section, build_backend, resolve_reasoner_config
from reasoning.vlm.errors import (
    BackendTimeoutError,
    DecisionValidationError,
    VLMOutputParseError,
)
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    AnthropicBackendConfig,
    BackendResponse,
    CongestionDecision,
    FailureContext,
    LlamaServerBackendConfig,
    OpenAIBackendConfig,
    PromptPayload,
    ReasonerConfig,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
    RobotStateInput,
)
from reasoning.vlm.openai_backend import OpenAIBackend
from reasoning.vlm.output_parser import parse_decision_text, validate_involved_robots
from reasoning.vlm.prompt_builder import (
    build_prompt_payload,
    format_pairwise_geometry_lines,
    format_robot_state_lines,
    render_failure_context_block,
)
from reasoning.vlm.reasoner import (
    Reasoner,
    build_failed_result,
    build_reask_prompt,
    invoke_backend,
    write_reasoner_log,
)

__all__ = [
    "AnthropicBackend",
    "AnthropicBackendConfig",
    "BackendResponse",
    "BackendTimeoutError",
    "CongestionDecision",
    "DecisionValidationError",
    "FailureContext",
    "LlamaServerBackend",
    "LlamaServerBackendConfig",
    "MockBackend",
    "OpenAIBackend",
    "OpenAIBackendConfig",
    "PromptPayload",
    "Reasoner",
    "ReasonerConfig",
    "ReasonerDiagnostics",
    "ReasonerRequest",
    "ReasonerResult",
    "RobotStateInput",
    "VLMBackend",
    "VLMOutputParseError",
    "backend_section",
    "build_backend",
    "build_failed_result",
    "build_prompt_payload",
    "build_reask_prompt",
    "format_pairwise_geometry_lines",
    "format_robot_state_lines",
    "invoke_backend",
    "parse_decision_text",
    "render_failure_context_block",
    "resolve_reasoner_config",
    "validate_involved_robots",
    "write_reasoner_log",
]
