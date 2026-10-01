"""Pydantic contract validation for the capability-probe manifest."""
import pytest
from pydantic import ValidationError

from reasoning.vlm.capability_probes.models import ProbeItem, ProbeManifest


def _item(**overrides) -> ProbeItem:
    fields = dict(
        item_id="robot_count_000",
        probe_type="robot_count",
        run_id="t2b_smoke/R1_20260928_182427",
        scenario="head_on_asymmetric",
        request_id="abc123",
        frame_relpath="t2b_smoke/R1_20260928_182427/frames/abc123.png",
        frame_sha256="a" * 64,
        image_width=1280,
        image_height=960,
        sim_time_sec=12.3,
        reference_robot_id=None,
        question="How many robots are visible in the image?",
        options=["1", "2", "3", "4", "5"],
        correct_answer="3",
        image_choices=False,
        seed=12345,
        m1_gt_max_disagreement_m=0.01,
    )
    fields.update(overrides)
    return ProbeItem(**fields)


class TestProbeItemValidation:
    def test_valid_robot_count_item_constructs(self):
        _item()

    def test_correct_answer_must_be_an_option(self):
        with pytest.raises(ValidationError, match="not in options"):
            _item(correct_answer="9")

    def test_options_must_be_unique(self):
        with pytest.raises(ValidationError, match="unique"):
            _item(options=["1", "1", "2"], correct_answer="2")

    def test_robot_count_must_not_name_a_reference_robot(self):
        with pytest.raises(ValidationError, match="must not name"):
            _item(reference_robot_id="robot_1")

    def test_left_right_requires_a_reference_robot(self):
        with pytest.raises(ValidationError, match="require a reference_robot_id"):
            _item(
                probe_type="left_right",
                options=["left", "right"],
                correct_answer="left",
                reference_robot_id=None,
            )

    def test_locate_robot_requires_image_choices_true(self):
        with pytest.raises(ValidationError, match="image_choices must be True"):
            _item(
                probe_type="locate_robot",
                reference_robot_id="robot_1",
                options=[str(i) for i in range(9)],
                correct_answer="4",
                image_choices=False,
            )

    def test_non_locate_robot_requires_image_choices_false(self):
        with pytest.raises(ValidationError, match="image_choices must be False"):
            _item(image_choices=True)

    def test_locate_robot_with_image_choices_true_is_valid(self):
        _item(
            probe_type="locate_robot",
            reference_robot_id="robot_1",
            options=[str(i) for i in range(9)],
            correct_answer="4",
            image_choices=True,
        )


class TestProbeManifestValidation:
    def test_unique_item_ids_required(self):
        with pytest.raises(ValidationError, match="unique"):
            ProbeManifest(seed=1, items=[_item(), _item()])

    def test_distinct_item_ids_is_valid(self):
        manifest = ProbeManifest(
            seed=1, items=[_item(item_id="a"), _item(item_id="b")]
        )
        assert len(manifest.items) == 2

    def test_round_trips_through_json(self):
        manifest = ProbeManifest(seed=1, items=[_item()])
        restored = ProbeManifest.model_validate_json(manifest.model_dump_json())
        assert restored == manifest
