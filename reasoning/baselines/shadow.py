"""Shadow comparison between Arm A (VLM) and Arm B (classical) decisions."""

from pydantic import BaseModel, ConfigDict

from reasoning.vlm.models import CongestionDecision


class DisagreementRecord(BaseModel):
    """Field-level agreement between the VLM (Arm A) and classical (Arm B) decisions.

    Only fields both arms can emit through `CongestionDecision` are compared.
    Blocker kind and multi-robot crossing order are not on that contract yet,
    so they are not part of this record.
    """

    model_config = ConfigDict(frozen=True)

    strategy_match: bool
    type_match: bool
    yielder_match: bool
    any_disagreement: bool


def compare_decisions(vlm: CongestionDecision, classical: CongestionDecision) -> DisagreementRecord:
    """Compare the two arms' decisions; any mismatch is a first-class event.

    Free-text fields (`root_cause`, `justification`) are not compared. An
    absent `yield_robot` matches only an absent `yield_robot`.

    Args:
        vlm: Arm A decision.
        classical: Arm B decision computed on the same inputs.

    Returns:
        Frozen record; `any_disagreement` is True when any compared field
        differs.
    """
    strategy_match = vlm.strategy == classical.strategy
    type_match = vlm.type == classical.type
    yielder_match = vlm.yield_robot == classical.yield_robot
    return DisagreementRecord(
        strategy_match=strategy_match,
        type_match=type_match,
        yielder_match=yielder_match,
        any_disagreement=not (strategy_match and type_match and yielder_match),
    )
