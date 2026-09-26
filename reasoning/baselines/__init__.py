"""Arm B classical reasoner and shadow comparison (rev-8 experiment control)."""

from reasoning.baselines.classical_reasoner import (
    ClassicalClassification,
    ClassicalParams,
    ClassicalResolution,
    ConflictZone,
    classify_scene,
    decide_classical,
    load_classical_params,
    resolve_classical,
)
from reasoning.baselines.shadow import DisagreementRecord, compare_decisions

__all__ = [
    "ClassicalClassification",
    "ClassicalParams",
    "ClassicalResolution",
    "ConflictZone",
    "DisagreementRecord",
    "classify_scene",
    "compare_decisions",
    "decide_classical",
    "load_classical_params",
    "resolve_classical",
]
