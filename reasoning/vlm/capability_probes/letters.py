"""Seeded option lettering, following the stage-2 set-of-mark precedent.

Mirrors `swarm_orchestrator.retreat_stage2`'s letter/listing split (SHA-256
derived seeds, `random.Random(seed).shuffle`, never `hash()`, so paired runs
draw the same letters): which option each letter shows and the order options
are listed are drawn from independent streams, so letter A is not always the
first-listed or semantically "first" option. Reimplemented here rather than
imported, because `swarm_orchestrator` is a ROS2 (M5) package and this
reasoning-side (M2) probe battery must not depend on it.
"""
from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence
from dataclasses import dataclass

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _sha256_seed(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def letter_seed(item_seed: int) -> int:
    """Derive the seed of one item's letter-assignment draw.

    Args:
        item_seed: The `ProbeItem.seed`.

    Returns:
        A 64-bit seed, independent of `listing_seed` for the same item.
    """
    return _sha256_seed(f"{item_seed}:letters")


def listing_seed(item_seed: int) -> int:
    """Derive the seed of one item's option-listing-order draw.

    Args:
        item_seed: The `ProbeItem.seed`.

    Returns:
        A 64-bit seed, independent of `letter_seed` for the same item.
    """
    return _sha256_seed(f"{item_seed}:listing")


def assign_letters(option_count: int, seed: int) -> list[int]:
    """Draw which option index each letter shows.

    Args:
        option_count: Number of canonical options.
        seed: The draw's seed (`letter_seed`).

    Returns:
        `order` with `order[i]` the option index shown under the i-th letter
        (A, B, ...); a uniform random permutation, so any one option index
        lands on each letter equally often across items.
    """
    if option_count < 2:
        raise ValueError(f"need at least 2 options to letter, got {option_count}")
    if option_count > len(_LETTERS):
        raise ValueError(f"too many options to letter with A-Z: {option_count}")
    order = list(range(option_count))
    random.Random(seed).shuffle(order)
    return order


def draw_listing_order(letters: Sequence[str], seed: int) -> list[str]:
    """Draw the order a prompt lists a set of letters in.

    Args:
        letters: The letters to list, in any order.
        seed: The draw's seed (`listing_seed`).

    Returns:
        The letters as a uniform random permutation of their sorted order.
    """
    order = sorted(letters)
    random.Random(seed).shuffle(order)
    return order


@dataclass(frozen=True)
class ItemChoices:
    """The rendered lettering for one `ProbeItem`, derived from its seed."""

    # Letter -> canonical option value (e.g. {"A": "left", "B": "right"}, or
    # for `locate_robot` {"A": "4", "B": "0", ...} grid-cell indices).
    option_by_letter: dict[str, str]
    # The letter the item's `correct_answer` is shown under this draw.
    correct_letter: str
    # The order letters are listed in the prompt (independent of the letter
    # draw above).
    listing_order: list[str]


def build_item_choices(options: Sequence[str], correct_answer: str, item_seed: int) -> ItemChoices:
    """Compute one item's letter assignment and listing order from its seed.

    Args:
        options: The item's canonical option values, in manifest order.
        correct_answer: Which of `options` is correct.
        item_seed: The `ProbeItem.seed` this item was frozen with.

    Returns:
        The letters to render, reproducible for the same `options` and
        `item_seed` across every run and backend.
    """
    letters = list(_LETTERS[: len(options)])
    assigned = assign_letters(len(options), letter_seed(item_seed))
    option_by_letter = {letters[i]: options[assigned[i]] for i in range(len(options))}
    letter_by_option_index = {option_index: letters[i] for i, option_index in enumerate(assigned)}
    correct_index = options.index(correct_answer)
    correct_letter = letter_by_option_index[correct_index]
    listing_order = draw_listing_order(letters, listing_seed(item_seed))
    return ItemChoices(
        option_by_letter=option_by_letter,
        correct_letter=correct_letter,
        listing_order=listing_order,
    )
