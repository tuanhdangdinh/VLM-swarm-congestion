"""Which VLM backend answered an M5 decision artifact (forcing-audit A2, 2026-10-07).

Shared by the scorers that read decision artifacts
(`scripts/coverage_scene_scores.py`, `scripts/strategy_regret.py regret`):
before this check none of them read `diagnostics.backend_id`, so a bundle
produced by the key-less mock backend scored exactly like a live one.
Stdlib only.
"""
from __future__ import annotations

from typing import Any

# `reasoning.vlm.backend_factory`'s scripted backend: its artifacts are never
# confirmatory evidence.
MOCK_BACKEND_ID = "mock"


class MockBackendError(ValueError):
    """A decision answered by the mock backend was offered for scoring."""


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def record_backend_id(record: dict[str, Any]) -> str | None:
    """The backend id one decision artifact records.

    Args:
        record: A decision artifact as JSON.

    Returns:
        `reasoner_config_effective.backend_id` (the arm id), else
        `diagnostics.backend_id` (pre-F09 successes carry the provider model
        id there); None when neither is recorded (e.g. a bare decision).
    """
    effective = _text((record.get("reasoner_config_effective") or {}).get("backend_id"))
    return effective or _text((record.get("diagnostics") or {}).get("backend_id"))


def record_is_mock(record: dict[str, Any]) -> bool:
    """Whether either backend field of a decision artifact names the mock backend.

    Args:
        record: A decision artifact as JSON.

    Returns:
        True when `reasoner_config_effective.backend_id` or
        `diagnostics.backend_id` is `"mock"`.
    """
    return MOCK_BACKEND_ID in (
        _text((record.get("reasoner_config_effective") or {}).get("backend_id")),
        _text((record.get("diagnostics") or {}).get("backend_id")),
    )
