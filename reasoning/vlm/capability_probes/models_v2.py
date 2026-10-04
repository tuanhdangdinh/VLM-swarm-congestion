"""Battery-v2 manifest contracts: the predictive/temporal probe items (2026-10-04).

A SEPARATE manifest from `manifest_v1.json` (which stays frozen and loads
through `models.ProbeManifest` unchanged), registered in
`docs/superpowers/specs/2026-09-30-prereg-v2-design.md` ("Battery v2 --
predictive/temporal probes"). Items reuse the v1 machinery -- seeded
lettering (`letters.py`), the frozen v1 prompt template (one question plus a
lettered option list fits yes/no and robot-id options alike), content-hash
frame references (`manifest_io.materialize_frame`) -- and add what dynamic
items need: where the frame came from (a decision dump or a periodic
snapshot), whether M1 drew motion trails on it, the trails-pair grouping, and
the GT derivation facts (margins, event times) the auditor re-checks.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ProbeTypeV2 = Literal["motion_direction", "conflict_prediction", "temporal_order"]
# `main`: the battery proper, trails-off frames only (the shipped M1 frame).
# `trails_pair`: the matched subset -- the same question on a trails-off and
# a trails-on frame of the same scene configuration, for the amortized
# temporal-context comparison.
Subset = Literal["main", "trails_pair"]
FrameCondition = Literal["trails_off", "trails_on"]
FrameSource = Literal["decision", "snapshot"]


class ProbeItemV2(BaseModel):
    """One frozen battery-v2 item: a frame, a dynamic question, and its GT answer.

    Field names shared with `models.ProbeItem` mean the same thing, so the
    v1 runner's preparation path (`materialize_frame`, `build_item_choices`,
    the v1 prompt builder) takes either item type unchanged.
    """

    model_config = ConfigDict(frozen=True)

    item_id: str = Field(min_length=1)
    probe_type: ProbeTypeV2
    subset: Subset
    pair_id: str | None = None
    frame_condition: FrameCondition
    run_id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    frame_source: FrameSource
    # The decision `request_id`, or the snapshot PNG file name.
    frame_ref: str = Field(min_length=1)
    frame_relpath: str = Field(min_length=1)
    frame_sha256: str = Field(min_length=64, max_length=64)
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    # The frame's own stamp (M1 scene stamp) and the GT row it was matched to.
    sim_time_sec: float = Field(ge=0)
    gt_sim_time_sec: float = Field(ge=0)
    # Machine-readable question identity, re-derived by the auditor:
    # motion_direction `robot:<id>` / `edge:<side>`; conflict_prediction
    # `<a>|<b>`; temporal_order `<goal|stop>:<a>|<b>` (ids sorted).
    question_key: str = Field(min_length=1)
    reference_robot_id: str | None = None
    question: str = Field(min_length=1)
    options: list[str] = Field(min_length=2)
    correct_answer: str = Field(min_length=1)
    # Always False: every v2 option is listed as text in the prompt.
    image_choices: Literal[False] = False
    seed: int
    m1_gt_max_disagreement_m: float = Field(ge=0)
    # GT facts behind the answer (speeds, angles' classes, distances, event
    # times), recorded so the inclusion rules are auditable from the manifest.
    derivation: dict[str, float | str | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_answer_and_subset(self) -> ProbeItemV2:
        if self.correct_answer not in self.options:
            raise ValueError(
                f"correct_answer {self.correct_answer!r} not in options {self.options!r}"
            )
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"options must be unique, got {self.options!r}")
        if self.subset == "main":
            if self.pair_id is not None or self.frame_condition != "trails_off":
                raise ValueError("main items are trails-off and unpaired")
        elif self.pair_id is None:
            raise ValueError("trails_pair items require a pair_id")
        return self


class ProbeManifestV2(BaseModel):
    """The frozen battery-v2 item set (checked into git; frames are gitignored)."""

    model_config = ConfigDict(frozen=True)

    manifest_version: Literal[2] = 2
    seed: int
    # The registered derivation constants the items were built under
    # (`dynamics.py` module constants), so a later constant change is
    # visible against the manifest instead of silently re-grading it.
    constants: dict[str, float] = Field(default_factory=dict)
    items: list[ProbeItemV2] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_ids_and_pairs(self) -> ProbeManifestV2:
        ids = [item.item_id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("manifest item_ids must be unique")
        pairs: dict[str, list[ProbeItemV2]] = defaultdict(list)
        for item in self.items:
            if item.pair_id is not None:
                pairs[item.pair_id].append(item)
        for pair_id, members in pairs.items():
            conditions = sorted(member.frame_condition for member in members)
            if conditions != ["trails_off", "trails_on"]:
                raise ValueError(
                    f"pair {pair_id!r} must have one trails_off and one trails_on item"
                )
            off, on = members
            same = (
                off.probe_type == on.probe_type
                and off.question == on.question
                and off.options == on.options
                and off.correct_answer == on.correct_answer
                and off.seed == on.seed
            )
            if not same:
                raise ValueError(f"pair {pair_id!r} items differ in question/options/answer/seed")
        return self
