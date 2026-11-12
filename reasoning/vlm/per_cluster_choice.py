"""Per-cluster choice contract: one decision per observed group, from one M2 answer.

The v2 option list (`reasoning.rag.cluster_options.generate_cluster_candidates`)
is split into one slot per observed group (`build_slots`), and the answer's
`choices` object must have exactly the group labels as keys, each mapped to
one of that group's option ids or to `none_feasible`:

- each observed group is one slot, holding the options listed under that
  group;
- pairs spanning two groups are not offered; choosing one option in each
  group is the way to name both;
- robots in no group get no slot, except that a scene with no observed group
  keeps the v2 fallback: the outside section becomes the single slot
  `outside`.

Option ids are the v2 global numbers by default, or opaque per-item tokens
(`option_ids="opaque"`).

`VLMBackend.analyze(payload, config)` carries no response schema
(`PromptPayload` has no schema field), so the format is stated in the prompt
(`render_per_cluster_section`) and every reply is validated against a
per-item Pydantic model (`choices_model`: required group keys, `Literal` ids,
extra keys forbidden). This module imports nothing from `reasoning.rag`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from reasoning.vlm.executable_options import (
    OUTSIDE,
    ClusterCandidateSet,
    ClusterOption,
    shuffle_cluster_candidates,
)
from reasoning.vlm.models import PromptPayload

GENERATOR_VERSION_PER_CLUSTER = "gf-per-cluster-v1"
NONE_FEASIBLE = "none_feasible"
OptionIds = Literal["numbered", "opaque"]
SLOT_RULE = (
    "one slot per gf-candidates-v2 observed group (span and outside sections dropped); "
    "a scene with no observed group gets the single slot 'outside' (v2's fallback)"
)
ANSWER_KEYS_PREFIX = "Answer keys and allowed ids: "


class GroupSlot(BaseModel):
    """One observed group the answer must decide on, with its options in presented order."""

    model_config = ConfigDict(frozen=True)

    label: str
    robots: tuple[str, ...]
    option_ids: tuple[str, ...]
    options: tuple[ClusterOption, ...]

    def option(self, option_id: str) -> ClusterOption:
        """The option an id names.

        Args:
            option_id: One of `option_ids`.

        Returns:
            The option.
        """
        return self.options[self.option_ids.index(option_id)]


class PerClusterCandidateSet(BaseModel):
    """The v2 options of one item, split into one slot per observed group."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    generator_version: str = GENERATOR_VERSION_PER_CLUSTER
    base: ClusterCandidateSet
    slots: tuple[GroupSlot, ...]
    option_ids: OptionIds = "numbered"

    @property
    def labels(self) -> tuple[str, ...]:
        """The required answer keys, in slot order."""
        return tuple(s.label for s in self.slots)

    @property
    def n_options(self) -> int:
        """Options listed over every slot."""
        return sum(len(s.options) for s in self.slots)

    def allowed(self) -> dict[str, list[str]]:
        """Each slot's allowed answer values, `none_feasible` last.

        Returns:
            Label -> ids.
        """
        return {s.label: [*s.option_ids, NONE_FEASIBLE] for s in self.slots}

    def slot(self, label: str) -> GroupSlot:
        """The slot with this label.

        Args:
            label: A slot label.

        Returns:
            The slot.
        """
        return next(s for s in self.slots if s.label == label)


class PerClusterAnswer(BaseModel):
    """The model's per-group choices, validated, mapped back to options."""

    model_config = ConfigDict(frozen=True)

    status: Literal["choices", "parse_failure"]
    # Label -> option id or `none_feasible`; empty on a parse failure.
    choices: dict[str, str] = Field(default_factory=dict)
    error: str | None = None
    model_answer: dict[str, Any] = Field(default_factory=dict)


def opaque_id(item_id: str, key: Sequence[str], length: int = 3) -> str:
    """A short, stable, position-free option id: a hash of the item and the executed key.

    Args:
        item_id: The item id.
        key: The option's `executed_key_v2`.
        length: Characters after the leading letter.

    Returns:
        A lowercase token that starts with a letter, e.g. `k4xq`.
    """
    digest = hashlib.sha256(f"{item_id}:{'|'.join(key)}".encode()).digest()
    text = base64.b32encode(digest).decode().lower().rstrip("=")
    letter = next(c for c in text if c.isalpha())
    return letter + text[1 : 1 + length]


def _opaque_ids(item_id: str, options: Sequence[ClusterOption]) -> list[str]:
    for length in range(3, 12):
        ids = [opaque_id(item_id, o.key, length) for o in options]
        if len(set(ids)) == len(ids) and NONE_FEASIBLE not in ids:
            return ids
    raise ValueError(f"{item_id}: could not make unique opaque option ids")


def build_slots(
    base: ClusterCandidateSet,
    option_ids: OptionIds = "numbered",
    shuffle_seed: int | None = None,
) -> tuple[PerClusterCandidateSet, tuple[int, ...] | None, int | None]:
    """Split a v2 option set into one slot per observed group.

    Args:
        base: The v2 options in generator order, both extra sections dropped
            (`generate_cluster_candidates(..., offgroup="drop", cross_group="drop")`);
            its `item_id` names the slot set and seeds opaque ids.
        option_ids: "numbered" (v2's global 1-based numbers) or "opaque".
        shuffle_seed: When set, permute options within each group
            (`shuffle_cluster_candidates`); numbered ids follow the presented
            order, opaque ids follow the option.

    Returns:
        The slots, the presented order as unshuffled 1-based v2 numbers (None
        when not shuffled) and the per-item shuffle seed (or None).
    """
    order: tuple[int, ...] | None = None
    item_seed: int | None = None
    if shuffle_seed is not None:
        base, order, item_seed = shuffle_cluster_candidates(base, shuffle_seed)
    ids = (
        [str(n) for n in range(1, len(base.options) + 1)]
        if option_ids == "numbered"
        else _opaque_ids(base.item_id, base.options)
    )
    by_section: dict[str, list[tuple[str, ClusterOption]]] = {}
    for option_id, option in zip(ids, base.options, strict=True):
        by_section.setdefault(option.section, []).append((option_id, option))
    slots: list[GroupSlot] = []
    for group in base.groups:
        entries = by_section.get(group.label, [])
        slots.append(_slot(group.label, group.robots, entries))
    if not base.groups and by_section.get(OUTSIDE):
        entries = by_section[OUTSIDE]
        robots = tuple(sorted({r for _, o in entries for r in o.robots}))
        slots.append(_slot(OUTSIDE, robots, entries))
    candidates = PerClusterCandidateSet(
        item_id=base.item_id, base=base, slots=tuple(slots), option_ids=option_ids
    )
    return candidates, order, item_seed


def _slot(
    label: str, robots: tuple[str, ...], entries: Sequence[tuple[str, ClusterOption]]
) -> GroupSlot:
    return GroupSlot(
        label=label,
        robots=robots,
        option_ids=tuple(i for i, _ in entries),
        options=tuple(o for _, o in entries),
    )


def choices_model(candidates: PerClusterCandidateSet) -> type[BaseModel]:
    """The per-item answer contract: every slot label required, ids limited to its slot.

    Args:
        candidates: The item's slots.

    Returns:
        A frozen Pydantic model with one required `Literal` field per slot
        and extra keys forbidden.
    """
    fields: dict[str, Any] = {
        label: (Literal[tuple(values)], ...)  # type: ignore[valid-type]
        for label, values in candidates.allowed().items()
    }
    return create_model(
        "PerClusterChoices",
        __config__=ConfigDict(frozen=True, extra="forbid"),
        **fields,
    )


def extract_json_object(text: str) -> dict[str, Any]:
    """The one JSON object in a reply (think blocks and fences tolerated).

    Args:
        text: The raw reply.

    Returns:
        The object.

    Raises:
        ValueError: When no JSON object can be read.
    """
    body = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", body, flags=re.DOTALL)
    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        start, end = body.find("{"), body.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("reply contains no JSON object") from None
        try:
            value = json.loads(body[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"reply is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("reply JSON is not an object")
    return value


def _normalize(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return value


def parse_per_cluster_answer(text: str, candidates: PerClusterCandidateSet) -> PerClusterAnswer:
    """Validate the reply's `choices` object against the item's slots.

    Integer ids are accepted for numbered ids (`3` reads as `"3"`); nothing
    else is coerced. Never raises.

    Args:
        text: The raw reply.
        candidates: The slots the prompt listed.

    Returns:
        `choices` with the label -> id map, or `parse_failure` with the error.
    """
    try:
        answer = extract_json_object(text)
    except ValueError as exc:
        return PerClusterAnswer(status="parse_failure", error=str(exc))
    raw = answer.get("choices")
    if not isinstance(raw, dict):
        return PerClusterAnswer(
            status="parse_failure",
            error='missing "choices" object (one key per group: '
            + ", ".join(candidates.labels)
            + ")",
            model_answer=answer,
        )
    if not candidates.slots:
        if raw:
            return PerClusterAnswer(
                status="parse_failure",
                error='"choices" must be {} when no group is listed',
                model_answer=answer,
            )
        return PerClusterAnswer(status="choices", choices={}, model_answer=answer)
    normalized = {str(k): _normalize(v) for k, v in raw.items()}
    try:
        validated = choices_model(candidates).model_validate(normalized)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'choices'}: {e['msg']}" for e in exc.errors()
        )
        return PerClusterAnswer(
            status="parse_failure", error=f'invalid "choices": {problems}', model_answer=answer
        )
    return PerClusterAnswer(
        status="choices", choices=dict(validated.model_dump()), model_answer=answer
    )


def group_decisions(
    candidates: PerClusterCandidateSet,
    choices: Mapping[str, str],
    model_answer: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any] | None]:
    """Each slot's chosen option as a decision dict, None for `none_feasible`.

    Args:
        candidates: The slots.
        choices: Validated label -> id.
        model_answer: The model's JSON object (its `type`, `root_cause` and
            `justification` are copied into each decision).

    Returns:
        Label -> decision or None, in slot order.
    """
    answer = dict(model_answer or {})
    out: dict[str, dict[str, Any] | None] = {}
    for slot in candidates.slots:
        chosen = choices[slot.label]
        out[slot.label] = None if chosen == NONE_FEASIBLE else slot.option(chosen).decision(answer)
    return out


def chosen_options(
    candidates: PerClusterCandidateSet, choices: Mapping[str, str]
) -> dict[str, ClusterOption | None]:
    """Each slot's chosen option, None for `none_feasible`.

    Args:
        candidates: The slots.
        choices: Validated label -> id.

    Returns:
        Label -> option or None, in slot order.
    """
    return {
        s.label: None if choices[s.label] == NONE_FEASIBLE else s.option(choices[s.label])
        for s in candidates.slots
    }


def _option_line(option_id: str, option: ClusterOption, numbered: bool) -> str:
    return f"{option_id}) {option.text}" if numbered else f"[{option_id}] {option.text}"


def render_per_cluster_section(candidates: PerClusterCandidateSet) -> str:
    """The per-group option lists and the answer instruction appended to the live prompt.

    Args:
        candidates: The item's slots.

    Returns:
        The section text.
    """
    base = candidates.base
    numbered = candidates.option_ids == "numbered"
    lines = [
        "Executable options, grouped by observed group. A group is robots that are "
        f"stopped, slow or stale within {base.threshold_m:.2f} m of each other (a moving "
        "robot that close joins the group). Each option below was checked on its own on "
        "this exact scene by the motion planner that will execute your answer; any other "
        "choice would be refused or would not move a robot. Decide each group separately: "
        "choose one option for every group, or none_feasible for a group where no listed "
        "option should be executed."
    ]
    if not candidates.slots:
        lines.append("(no observed group and no executable option was found for this scene)")
    for slot in candidates.slots:
        if slot.label == OUTSIDE:
            title = "No observed group in this scene; robots " + ", ".join(slot.robots)
        else:
            title = f"Group {slot.label}: {', '.join(slot.robots)}"
        if numbered and slot.option_ids:
            first, last = slot.option_ids[0], slot.option_ids[-1]
            span = f"option {first}" if first == last else f"options {first}-{last}"
            title += f" ({span})"
        lines.append(title)
        lines += [
            _option_line(i, o, numbered) for i, o in zip(slot.option_ids, slot.options, strict=True)
        ]
        none = f"{NONE_FEASIBLE})" if numbered else f"[{NONE_FEASIBLE}]"
        lines.append(f"{none} no listed option for this group should be executed")
    keys = ", ".join(f'"{label}"' for label in candidates.labels)
    allowed = json.dumps(candidates.allowed(), separators=(", ", ": "))
    lines += [
        "",
        'Your strategy MUST come from the options above. Add one more field to the JSON '
        "object:",
        f'- "choices": an object with exactly these keys: {keys or "(none)"}. Each value is '
        "the id of one option listed under that group, as a string, or "
        f'"{NONE_FEASIBLE}". Every key is required; an option listed under one group cannot '
        "be chosen for another.",
        ANSWER_KEYS_PREFIX + allowed,
        'State the reason for your choices in "justification". The chosen options\' robots, '
        'strategies and yield robots are what will be executed; your own "involved_robots", '
        '"strategy" and "yield_robot" are not used.',
    ]
    return "\n".join(lines)


def compose_per_cluster_payload(
    base: PromptPayload, candidates: PerClusterCandidateSet
) -> PromptPayload:
    """The live payload with the per-group section appended to its user prompt.

    Args:
        base: The live builder's payload, unchanged.
        candidates: The item's slots.

    Returns:
        The composed payload (system prompt and images unchanged).
    """
    user = f"{base.user_prompt}\n\n{render_per_cluster_section(candidates)}"
    return base.model_copy(update={"user_prompt": user})


def read_answer_keys(user_prompt: str) -> dict[str, list[str]]:
    """The slot labels and allowed ids stated in a composed prompt (last statement wins).

    Args:
        user_prompt: A prompt composed by `compose_per_cluster_payload`.

    Returns:
        Label -> allowed ids (`none_feasible` included).

    Raises:
        ValueError: When the prompt states no answer keys.
    """
    found = re.findall(rf"^{re.escape(ANSWER_KEYS_PREFIX)}(\{{.*\}})$", user_prompt, re.M)
    if not found:
        raise ValueError("prompt states no per-cluster answer keys")
    return json.loads(found[-1])


__all__ = [
    "ANSWER_KEYS_PREFIX",
    "GENERATOR_VERSION_PER_CLUSTER",
    "NONE_FEASIBLE",
    "SLOT_RULE",
    "GroupSlot",
    "OptionIds",
    "PerClusterAnswer",
    "PerClusterCandidateSet",
    "build_slots",
    "choices_model",
    "chosen_options",
    "compose_per_cluster_payload",
    "extract_json_object",
    "group_decisions",
    "opaque_id",
    "parse_per_cluster_answer",
    "read_answer_keys",
    "render_per_cluster_section",
]
