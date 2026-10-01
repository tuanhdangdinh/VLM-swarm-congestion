"""Seeded letter assignment and listing order for the capability-probe battery."""
import pytest

from reasoning.vlm.capability_probes.letters import (
    assign_letters,
    build_item_choices,
    draw_listing_order,
    letter_seed,
    listing_seed,
)


class TestSeedDerivation:
    def test_letter_and_listing_seeds_differ(self):
        assert letter_seed(42) != listing_seed(42)

    def test_same_item_seed_is_reproducible(self):
        assert letter_seed(42) == letter_seed(42)
        assert listing_seed(42) == listing_seed(42)

    def test_different_item_seeds_differ(self):
        assert letter_seed(42) != letter_seed(43)


class TestAssignLetters:
    def test_is_a_permutation(self):
        order = assign_letters(5, seed=123)
        assert sorted(order) == [0, 1, 2, 3, 4]

    def test_reproducible_for_same_seed(self):
        assert assign_letters(5, seed=123) == assign_letters(5, seed=123)

    def test_different_seeds_can_differ(self):
        orders = {tuple(assign_letters(5, seed=s)) for s in range(10)}
        assert len(orders) > 1

    def test_rejects_fewer_than_two_options(self):
        with pytest.raises(ValueError, match="at least 2"):
            assign_letters(1, seed=1)


class TestDrawListingOrder:
    def test_is_a_permutation_of_sorted_letters(self):
        order = draw_listing_order(["C", "A", "B"], seed=7)
        assert sorted(order) == ["A", "B", "C"]

    def test_reproducible_for_same_seed(self):
        assert draw_listing_order(["A", "B", "C"], seed=7) == draw_listing_order(
            ["A", "B", "C"], seed=7
        )


class TestBuildItemChoices:
    def test_every_option_gets_a_distinct_letter(self):
        choices = build_item_choices(["left", "right"], "left", item_seed=99)
        assert sorted(choices.option_by_letter) == ["A", "B"]
        assert set(choices.option_by_letter.values()) == {"left", "right"}

    def test_correct_letter_maps_back_to_the_correct_answer(self):
        choices = build_item_choices(["left", "right"], "right", item_seed=99)
        assert choices.option_by_letter[choices.correct_letter] == "right"

    def test_listing_order_is_a_permutation_of_the_letters(self):
        choices = build_item_choices(["1", "2", "3", "4", "5"], "3", item_seed=5)
        assert sorted(choices.listing_order) == ["A", "B", "C", "D", "E"]

    def test_reproducible_for_same_inputs(self):
        a = build_item_choices(["left", "right"], "left", item_seed=99)
        b = build_item_choices(["left", "right"], "left", item_seed=99)
        assert a.option_by_letter == b.option_by_letter
        assert a.correct_letter == b.correct_letter
        assert a.listing_order == b.listing_order

    def test_correct_letter_is_not_always_a_across_many_items(self):
        # Regression guard for the positional-default confound this battery
        # exists to avoid measuring by accident: the correct letter must vary
        # with the seed, not collapse to a fixed slot.
        letters = {
            build_item_choices(["left", "right"], "left", item_seed=seed).correct_letter
            for seed in range(30)
        }
        assert letters == {"A", "B"}
