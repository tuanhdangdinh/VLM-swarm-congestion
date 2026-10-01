"""M2 VLM semantic reasoning: prompt building, backend adapters, parsing, orchestration."""

from reasoning.vlm.anthropic_backend import AnthropicBackend
from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.backend_factory import (
    backend_section,
    build_backend,
    build_retreat_choice_backend,
    describe_effective_sampling,
    resolve_reasoner_config,
)
from reasoning.vlm.errors import (
    BackendTimeoutError,
    DecisionValidationError,
    RetreatLabelError,
    VLMOutputParseError,
)
from reasoning.vlm.gemini_backend import GeminiBackend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    AnthropicBackendConfig,
    BackendResponse,
    BlockerKind,
    CongestionDecision,
    EffectiveSamplingConfig,
    FailureContext,
    GeminiBackendConfig,
    LlamaServerBackendConfig,
    MotionTable,
    MotionTableEntry,
    OpenAIBackendConfig,
    PlanLegAction,
    PromptPayload,
    ProposedPlanLeg,
    ReasonerConfig,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
    RetreatCandidateOption,
    RetreatChoiceDecision,
    RetreatChoiceRequest,
    RetreatChoiceResult,
    RobotStateInput,
    SnapshotFrame,
)
from reasoning.vlm.motion_table import derive_motion_table
from reasoning.vlm.openai_backend import OpenAIBackend
from reasoning.vlm.output_parser import (
    parse_decision_text,
    parse_retreat_choice_text,
    validate_involved_robots,
)
from reasoning.vlm.prompt_builder import (
    build_prompt_payload,
    format_pairwise_geometry_lines,
    format_robot_state_lines,
    render_failure_context_block,
    render_last_failed_context_block,
)
from reasoning.vlm.reasoner import (
    Reasoner,
    attach_unsupported_sampling,
    build_failed_result,
    build_reask_prompt,
    invoke_backend,
    is_refusal,
    make_neutral_image,
    write_reasoner_log,
)
from reasoning.vlm.retreat_chooser import RetreatChooser
from reasoning.vlm.stage2_prompt import build_stage2_prompt_payload

__all__ = [
    "AnthropicBackend",
    "AnthropicBackendConfig",
    "BackendResponse",
    "BackendTimeoutError",
    "BlockerKind",
    "CongestionDecision",
    "DecisionValidationError",
    "EffectiveSamplingConfig",
    "FailureContext",
    "GeminiBackend",
    "GeminiBackendConfig",
    "LlamaServerBackend",
    "LlamaServerBackendConfig",
    "MockBackend",
    "MotionTable",
    "MotionTableEntry",
    "OpenAIBackend",
    "OpenAIBackendConfig",
    "PlanLegAction",
    "PromptPayload",
    "ProposedPlanLeg",
    "Reasoner",
    "ReasonerConfig",
    "ReasonerDiagnostics",
    "ReasonerRequest",
    "ReasonerResult",
    "RetreatCandidateOption",
    "RetreatChoiceDecision",
    "RetreatChoiceRequest",
    "RetreatChoiceResult",
    "RetreatChooser",
    "RetreatLabelError",
    "RobotStateInput",
    "SnapshotFrame",
    "VLMBackend",
    "VLMOutputParseError",
    "attach_unsupported_sampling",
    "backend_section",
    "build_backend",
    "build_failed_result",
    "build_prompt_payload",
    "build_reask_prompt",
    "build_retreat_choice_backend",
    "build_stage2_prompt_payload",
    "derive_motion_table",
    "describe_effective_sampling",
    "format_pairwise_geometry_lines",
    "format_robot_state_lines",
    "invoke_backend",
    "is_refusal",
    "make_neutral_image",
    "parse_decision_text",
    "parse_retreat_choice_text",
    "render_failure_context_block",
    "render_last_failed_context_block",
    "resolve_reasoner_config",
    "validate_involved_robots",
    "write_reasoner_log",
]
