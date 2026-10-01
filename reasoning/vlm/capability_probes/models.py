from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# The four registered probe types (prereg-v2 build-order step 10), exactly as
# named in the design spec: locate-robot-by-id, left-vs-right of aisle, robot
# count, nearest-first ordering.
ProbeType = Literal["locate_robot", "left_right", "robot_count", "nearest_first"]

# `locate_robot` answers are a 3x3 grid-cell index ("0".."8", row-major from
# the image's top-left) rather than a world coordinate, per the rev-6
# marked-choice rule ("never coordinates"). The grid partition itself is
# fixed; which physical cell shows which letter is randomized per item
# (`reasoning.vlm.capability_probes.grid`).
GRID_CELL_COUNT = 9

# Why a candidate was dropped while scanning run logs, recorded by
# `scripts/build_capability_probe_manifest.py` for the gap report (a probe
# type with too few eligible candidates is reported short, never padded with
# synthetic items). Advisory vocabulary -- the build script's `Counter` keys
# are plain strings, not validated against this Literal at runtime.
DropReason = Literal[
    "unparseable_decision",
    "no_matching_gt",
    "m1_gt_disagreement",
    "frame_missing",
    "calibration_scale_mismatch",
    "robot_count_out_of_scope",
    "scene_not_legible",
    "badge_occludes_label",
    "cell_not_unique",
    "m1_gt_answer_disagreement",
    "too_few_robots",
    "margin_too_small",
    "grid_boundary_too_close",
]


class ProbeItem(BaseModel):
    """One frozen capability-probe item: a frame, a question, and its answer.

    The correct answer is always machine-derived from the Isaac Sim ground
    truth log (`gt/ground_truth.jsonl`) matched to the frame's `sim_time_sec`,
    never hand-labeled. `options` lists the canonical (unlettered) answer
    values in a fixed, deterministic order; `seed` derives which letter each
    option is shown under and the order options are listed in
    (`reasoning.vlm.capability_probes.letters`), so the same item renders
    identically across backends and re-runs.
    """

    model_config = ConfigDict(frozen=True)

    item_id: str = Field(min_length=1)
    probe_type: ProbeType
    run_id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    # Path to the annotated frame, relative to the `--logs-root` the item was
    # built under (e.g. `t2b_smoke/R1_20260928_182427/frames/<id>.png`). Never
    # absolute: the frame directory is gitignored and re-materialized by path
    # relative to whatever `data/logs/vm_runs` the caller points at.
    frame_relpath: str = Field(min_length=1)
    frame_sha256: str = Field(min_length=64, max_length=64)
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    sim_time_sec: float = Field(ge=0)
    # The robot the question names, or None for `robot_count` (which names
    # none).
    reference_robot_id: str | None = None
    question: str = Field(min_length=1)
    # Canonical option values. For `locate_robot` these are grid-cell indices
    # ("0".."8"); for every other probe type they are the literal answer text
    # shown in the prompt.
    options: list[str] = Field(min_length=2)
    correct_answer: str = Field(min_length=1)
    # True for `locate_robot`: the options are drawn as lettered marks on the
    # image itself, so the prompt lists only the valid letters, never the
    # option text (there is none to leak).
    image_choices: bool
    seed: int
    # Max absolute per-axis disagreement (metres) between M1's estimate and
    # Isaac's ground truth for any robot in this frame, recorded so the
    # inclusion filter is auditable from the manifest alone.
    m1_gt_max_disagreement_m: float = Field(ge=0)

    @model_validator(mode="after")
    def _validate_correct_answer_is_an_option(self) -> "ProbeItem":
        if self.correct_answer not in self.options:
            raise ValueError(
                f"correct_answer {self.correct_answer!r} not in options {self.options!r}"
            )
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"options must be unique, got {self.options!r}")
        return self

    @model_validator(mode="after")
    def _validate_reference_robot_required(self) -> "ProbeItem":
        if self.probe_type == "robot_count" and self.reference_robot_id is not None:
            raise ValueError("robot_count items must not name a reference_robot_id")
        if self.probe_type != "robot_count" and self.reference_robot_id is None:
            raise ValueError(f"{self.probe_type} items require a reference_robot_id")
        return self

    @model_validator(mode="after")
    def _validate_image_choices_matches_probe_type(self) -> "ProbeItem":
        expected = self.probe_type == "locate_robot"
        if self.image_choices != expected:
            raise ValueError(
                f"image_choices must be {expected} for probe_type={self.probe_type!r}"
            )
        return self


class ProbeManifest(BaseModel):
    """The frozen capability-probe item set (one file, checked into git).

    Frames themselves are gitignored; this manifest stores each item's
    content hash and run-relative path so `manifest_io.materialize_frame`
    can re-locate and verify the source frame from any `--logs-root` that
    still holds the original `data/logs/vm_runs` tree.
    """

    model_config = ConfigDict(frozen=True)

    manifest_version: int = 1
    # The seed items were selected and lettered under; recorded so a rebuild
    # with the same seed and the same source logs reproduces this file byte
    # for byte.
    seed: int
    items: list[ProbeItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_unique_item_ids(self) -> "ProbeManifest":
        ids = [item.item_id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("manifest item_ids must be unique")
        return self


class ProbeAnswerRecord(BaseModel):
    """One scored probe call: what was asked, what came back, and the verdict."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    probe_type: ProbeType
    backend_id: str
    raw_text: str | None
    parsed_letter: str | None
    correct_letter: str = Field(min_length=1, max_length=1)
    correct: bool
    # None when a usable letter was parsed; otherwise why scoring counted this
    # as wrong (`reasoning.vlm.capability_probes.answer_parser`).
    failure_cause: str | None = None
    latency_ms: int | None = None
    attempts: int = Field(ge=1)
    # Populated only for `failure_cause == "backend_error"`: the exception
    # type/message from the failed `backend.analyze` call, so a run's JSONL
    # shows *why* a call failed, not just that it did (CLAUDE.md: runtime
    # failures from external systems belong in diagnostics, never swallowed
    # silently). Never set from a materialization failure -- those are not
    # caught here at all; `scripts/capability_probes.py`'s `run_battery`
    # prepares (materializes + builds the prompt for) every item before any
    # backend call, and raises past this model entirely on failure.
    error_type: str | None = None
    error_message: str | None = None


class ProbeTypeSummary(BaseModel):
    """Per-probe-type accuracy with a Wilson confidence interval."""

    model_config = ConfigDict(frozen=True)

    probe_type: ProbeType
    n: int = Field(ge=0)
    correct: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    wilson_lo: float = Field(ge=0.0, le=1.0)
    wilson_hi: float = Field(ge=0.0, le=1.0)
    # 1 / option_count for a fixed-cardinality type (robot_count, left_right,
    # locate_robot); for nearest_first, option count varies by item (more
    # robots in the scene -> more candidates), so this is the mean of
    # 1 / option_count across the type's items.
    chance_rate: float = Field(ge=0.0, le=1.0)
    # `ProbeAnswerRecord.failure_cause` (or "none" for a parsed, scored
    # answer -- right or wrong) -> count, for this probe type. Separates a
    # measured capability gap (a wrong-but-valid letter) from a refused or
    # unparseable response, so the latter cannot be misread as the former.
    failure_cause_counts: dict[str, int] = Field(default_factory=dict)


class ProbeRunSummary(BaseModel):
    """The whole scored run: one `ProbeTypeSummary` per probe type present."""

    model_config = ConfigDict(frozen=True)

    backend_id: str
    manifest_seed: int
    n_items: int = Field(ge=0)
    by_type: list[ProbeTypeSummary]
