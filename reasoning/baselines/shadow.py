"""Shadow comparison between Arm A (VLM) and Arm B (classical) decisions."""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from reasoning.vlm.models import BlockerKind, CongestionDecision


class DisagreementRecord(BaseModel):
    """Field-level agreement between the VLM (Arm A) and classical (Arm B) decisions.

    `strategy_match`, `type_match` and `yielder_match` are always judged.
    `blocker_kind_match` and `order_match` (prompt-v2 fields) are None when
    either side lacks the value: not comparable, which is not a disagreement.
    """

    model_config = ConfigDict(frozen=True)

    strategy_match: bool
    type_match: bool
    yielder_match: bool
    any_disagreement: bool
    # Defaulted so shadow blocks recorded before the prompt-v2 bundle validate.
    blocker_kind_match: bool | None = None
    order_match: bool | None = None


def _match(vlm_value: object, classical_value: object) -> bool | None:
    if vlm_value is None or classical_value is None:
        return None
    return vlm_value == classical_value


def compare_decisions(
    vlm: CongestionDecision,
    classical: CongestionDecision,
    *,
    classical_blocker_kind: BlockerKind | None = None,
    classical_passing_order: Sequence[str] | None = None,
) -> DisagreementRecord:
    """Compare the two arms' decisions; any mismatch is a first-class event.

    Free-text fields (`root_cause`, `justification`) are not compared. An
    absent `yield_robot` matches only an absent `yield_robot`. Blocker kind and
    crossing order are compared only when both sides carry one; a False match
    counts toward `any_disagreement`, a None match does not.

    Args:
        vlm: Arm A decision.
        classical: Arm B decision computed on the same inputs.
        classical_blocker_kind: Arm B's classification verdict; None reads
            `classical.blocker_kind` (Arm B fills it from the same verdict).
        classical_passing_order: Arm B's full FCFS passing order; None reads
            `classical.crossing_order`, which Arm B sets only at 3+ robots, so
            the shadow passes the full order to make two-robot orders
            comparable.

    Returns:
        Frozen record; `any_disagreement` is True when any compared field
        differs.
    """
    strategy_match = vlm.strategy == classical.strategy
    type_match = vlm.type == classical.type
    yielder_match = vlm.yield_robot == classical.yield_robot
    blocker_kind_match = _match(
        vlm.blocker_kind,
        classical_blocker_kind if classical_blocker_kind is not None else classical.blocker_kind,
    )
    classical_order = (
        list(classical_passing_order)
        if classical_passing_order is not None
        else classical.crossing_order
    )
    order_match = _match(vlm.crossing_order, classical_order)
    judged = [strategy_match, type_match, yielder_match, blocker_kind_match, order_match]
    return DisagreementRecord(
        strategy_match=strategy_match,
        type_match=type_match,
        yielder_match=yielder_match,
        blocker_kind_match=blocker_kind_match,
        order_match=order_match,
        any_disagreement=any(match is False for match in judged),
    )
