"""Capability-probe battery (prereg-v2 build-order step 10).

Per-backend probes on PROJECT frames, run once before v2 collection and
frozen with the battery (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`,
"Capability-probe battery"). Four probe types: locate-robot-by-id,
left-vs-right of aisle, robot count, nearest-first ordering. Rationale:
Garg et al. pre-test model capabilities before trusting them, and published
benchmarks put left/right discrimination near chance (LRR-Bench); probe
results make plan-metric failures attributable to measured primitive
deficits rather than speculation.

This package is a separate instrument from the stage-1/stage-2 reasoning
prompts: it shares `reasoning.vlm.backend_base.VLMBackend` and
`reasoning.vlm.backend_factory.build_backend` for transport, but its own
prompt (`capability_probes.prompt`) is frozen independently of
`PromptVersion`/`Stage2PromptVersion`. Deliberately not re-exported from
`reasoning.vlm`'s own `__init__.py`: this is a separate instrument, not part
of the stage-1/stage-2 reasoning surface every other M2 caller imports.
"""
from reasoning.vlm.capability_probes.answer_parser import parse_probe_answer
from reasoning.vlm.capability_probes.ground_truth import (
    grid_cell_answer,
    left_right_answer,
    max_m1_gt_disagreement_m,
    nearest_first_answer,
    robot_count_answer,
)
from reasoning.vlm.capability_probes.letters import ItemChoices, build_item_choices
from reasoning.vlm.capability_probes.manifest_io import (
    load_manifest,
    materialize_frame,
    save_manifest,
    sha256_file,
)
from reasoning.vlm.capability_probes.models import (
    ProbeAnswerRecord,
    ProbeItem,
    ProbeManifest,
    ProbeRunSummary,
    ProbeType,
    ProbeTypeSummary,
)
from reasoning.vlm.capability_probes.prompt import (
    CAPABILITY_PROBE_PROMPT_V1,
    CAPABILITY_PROBE_PROMPT_VERSION,
    CAPABILITY_PROBE_SYSTEM_PROMPT,
    build_capability_probe_prompt_payload,
)
from reasoning.vlm.capability_probes.scorer import score_records, wilson_interval

__all__ = [
    "CAPABILITY_PROBE_PROMPT_V1",
    "CAPABILITY_PROBE_PROMPT_VERSION",
    "CAPABILITY_PROBE_SYSTEM_PROMPT",
    "ItemChoices",
    "ProbeAnswerRecord",
    "ProbeItem",
    "ProbeManifest",
    "ProbeRunSummary",
    "ProbeType",
    "ProbeTypeSummary",
    "build_capability_probe_prompt_payload",
    "build_item_choices",
    "grid_cell_answer",
    "left_right_answer",
    "load_manifest",
    "materialize_frame",
    "max_m1_gt_disagreement_m",
    "nearest_first_answer",
    "parse_probe_answer",
    "robot_count_answer",
    "save_manifest",
    "score_records",
    "sha256_file",
    "wilson_interval",
]
