"""Grounding-first per-cluster choice: one decision per observed group (v4 lever 3).

v1 and v2 ask for one option per item, so a scene with two separate
conflicts needs one option that spans both, and the models rarely pick one
(docs/reports/2026-10-24-v4-gf-cluster-candidates.md, Rev 2). This variant
keeps v2's option list and asks for one choice per observed group instead:
the answer's `choices` object must have exactly the group labels as keys,
each mapped to one of that group's option ids or to `none_feasible`.

Groups and options are v2's (`gf_cluster.generate_cluster_candidates`, scene
state only, never `item.gt`), with both extra sections dropped:

- each observed group is one slot, holding the options v2 lists under that
  group (every one probed with the real offline M3 and kept only when it
  executes as asked);
- pairs spanning two groups are not offered; choosing one option in each
  group is this variant's way of naming both;
- robots in no group get no slot (v2's default `--gf-offgroup drop`), except
  that a scene with no observed group keeps v2's fallback: the outside
  section becomes the single slot `outside`.

Option ids are v2's global numbers by default (the same text and numbers as
an R5/R6 prompt), or opaque per-item tokens (`option_ids="opaque"`).

Delivery of the answer format: `VLMBackend.analyze(payload, config)` carries
no response schema (`PromptPayload` has no schema field, the Gemini adapter's
`force_schema` loads one static file at construction and is off on the pinned
arm, and the Anthropic adapter sends none). The format is therefore stated in
the prompt and every reply is validated against a per-item Pydantic model
(`choices_model`: required group keys, `Literal` ids, extra keys forbidden),
with the production re-ask on a failure.

`joint_check` reports what can be checked offline when the chosen commands
would be issued together; the live M5 dispatches one grounded command per
analysis, so nothing here is executable live as one decision.
"""

from __future__ import annotations

import base64
import hashlib
import itertools
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from benchmarks.vlm_bench.grounder_offline import ground_command, item_config
from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.variants.base import ReplayContext, VariantAnswer
from benchmarks.vlm_bench.variants.gf_cluster import (
    GROUPING_RULE,
    OUTSIDE,
    ClusterCandidateSet,
    ClusterOption,
    generate_cluster_candidates,
    shuffle_cluster_candidates,
)
from benchmarks.vlm_bench.variants.grounding_first import extract_json_object
from reasoning.rag.retreat_shield import retreat_corridor, segment_distance
from reasoning.vlm.models import (
    BackendResponse,
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
)
from reasoning.vlm.prompt_builder import build_prompt_payload
from reasoning.vlm.reasoner import build_reask_prompt, invoke_backend
from reasoning.vlm.retry_policy import DEFAULT_RETRY_POLICY, classify_failure

PER_CLUSTER_VARIANT = "grounding_first_per_cluster"
GENERATOR_VERSION_PER_CLUSTER = "gf-per-cluster-v1"
NONE_FEASIBLE = "none_feasible"
OptionIds = Literal["numbered", "opaque"]
SLOT_RULE = (
    "one slot per gf-candidates-v2 observed group (span and outside sections dropped); "
    "a scene with no observed group gets the single slot 'outside' (v2's fallback)"
)
ANSWER_KEYS_PREFIX = "Answer keys and allowed ids: "
_DEFAULT_SAFETY_RADIUS_M = 0.45


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


def per_cluster_candidates(
    item: BenchItem,
    include_wait: bool = True,
    option_ids: OptionIds = "numbered",
    shuffle_seed: int | None = None,
) -> tuple[PerClusterCandidateSet, tuple[int, ...] | None, int | None]:
    """Split the item's v2 options into one slot per observed group.

    Reads only what `generate_cluster_candidates` reads (scene state, recorded
    params and overlay, recorded classical `r_conflict_m`); never `item.gt`.

    Args:
        item: The bench item.
        include_wait: List `temporary_wait` options too.
        option_ids: "numbered" (v2's global 1-based numbers) or "opaque".
        shuffle_seed: When set, permute options within each group
            (`shuffle_cluster_candidates`); numbered ids follow the presented
            order, opaque ids follow the option.

    Returns:
        The slots, the presented order as unshuffled 1-based v2 numbers (None
        when not shuffled) and the per-item shuffle seed (or None).
    """
    base = generate_cluster_candidates(item, include_wait, "drop", "drop")
    order: tuple[int, ...] | None = None
    item_seed: int | None = None
    if shuffle_seed is not None:
        base, order, item_seed = shuffle_cluster_candidates(base, shuffle_seed)
    ids = (
        [str(n) for n in range(1, len(base.options) + 1)]
        if option_ids == "numbered"
        else _opaque_ids(item.item_id, base.options)
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
        item_id=item.item_id, base=base, slots=tuple(slots), option_ids=option_ids
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


class JointCheck(BaseModel):
    """What can be checked offline when the chosen commands are issued together."""

    model_config = ConfigDict(frozen=True)

    n_commands: int
    # Exact, from the grounded commands: a robot addressed by two commands
    # (including a hold in one and a move in the other).
    shared_robots: tuple[str, ...] = ()
    # Exact: two yield retreat points closer than the safety radius.
    retreat_clashes: tuple[tuple[str, str], ...] = ()
    # Heuristic, timing-free: straight-line motion segments of one command
    # within the safety radius of another command's segments or robots.
    path_proximity: tuple[tuple[str, str], ...] = ()
    safety_radius_m: float

    @property
    def exact_conflict(self) -> bool:
        """Whether an exact check fired."""
        return bool(self.shared_robots or self.retreat_clashes)


_Segment = tuple[tuple[float, float], tuple[float, float]]


def _addressed(command: dict[str, Any]) -> set[str]:
    return {a["robot_id"] for a in command.get("actions") or []}


def _motions(item: BenchItem, command: dict[str, Any]) -> list[_Segment]:
    pose = {r["robot_id"]: r for r in item.scene["robots"]}
    out: list[_Segment] = []
    for action in command.get("actions") or []:
        robot = pose.get(action["robot_id"])
        if robot is None:
            continue
        start = (float(robot["x"]), float(robot["y"]))
        params = action.get("parameters") or {}
        kind = action.get("action")
        if kind == "yield" and params.get("retreat_x_m") is not None:
            facing = params.get("backup_facing_rad", robot["theta"])
            out += retreat_corridor(
                start,
                float(facing),
                float(params.get("backup_distance_m") or 0.0),
                (float(params["retreat_x_m"]), float(params["retreat_y_m"])),
            )
            order = params.get("crossing_order") or [params.get("passer_robot_id")]
            headings = params.get("crossing_escort_heading_rad") or [
                params.get("passer_escort_heading_rad")
            ]
            escorts = params.get("crossing_escort_m") or [params.get("passer_escort_distance_m")]
            for passer, heading, dist in zip(order, headings, escorts, strict=False):
                other = pose.get(passer)
                if other is None or heading is None or not dist:
                    continue
                p = (float(other["x"]), float(other["y"]))
                end = (p[0] + dist * math.cos(heading), p[1] + dist * math.sin(heading))
                out.append((p, end))
        elif kind == "reverse":
            dist = float(params.get("backup_distance_m") or 0.0)
            theta = float(robot["theta"])
            end = (start[0] - dist * math.cos(theta), start[1] - dist * math.sin(theta))
            out.append((start, end))
        elif kind == "reroute":
            points = [start] + [(float(w[0]), float(w[1])) for w in params.get("waypoints") or []]
            out += list(itertools.pairwise(points))
    return out


def _stations(item: BenchItem, command: dict[str, Any]) -> list[_Segment]:
    pose = {r["robot_id"]: (float(r["x"]), float(r["y"])) for r in item.scene["robots"]}
    return [(pose[r], pose[r]) for r in sorted(_addressed(command)) if r in pose]


def joint_check(item: BenchItem, chosen: Mapping[str, ClusterOption | None]) -> JointCheck:
    """Check the chosen options against each other as if issued together (scene only).

    Each chosen option is grounded again with the offline M3 (each one alone,
    as M3 always grounds). Reads the scene and the episode geometry, never
    `item.gt`.

    Args:
        item: The bench item.
        chosen: Label -> chosen option (None for `none_feasible`).

    Returns:
        The exact checks (shared robots, retreat clashes) and the heuristic
        path-proximity pairs.
    """
    geometry = item_config(item).scenario_geometry
    radius = geometry.robot.safety_radius_m if geometry is not None else _DEFAULT_SAFETY_RADIUS_M
    commands = {
        label: ground_command(item, option.decision())
        for label, option in chosen.items()
        if option is not None
    }
    shared: set[str] = set()
    clashes: list[tuple[str, str]] = []
    near: list[tuple[str, str]] = []
    for (la, ca), (lb, cb) in itertools.combinations(commands.items(), 2):
        shared |= _addressed(ca) & _addressed(cb)
        ra = _retreat(ca)
        rb = _retreat(cb)
        if ra is not None and rb is not None and math.dist(ra, rb) < radius:
            clashes.append((la, lb))
        ma, mb = _motions(item, ca), _motions(item, cb)
        sa, sb = ma + _stations(item, ca), mb + _stations(item, cb)
        close = any(segment_distance(*x, *y) < radius for x in ma for y in sb) or any(
            segment_distance(*x, *y) < radius for x in mb for y in sa
        )
        if close:
            near.append((la, lb))
    return JointCheck(
        n_commands=len(commands),
        shared_robots=tuple(sorted(shared)),
        retreat_clashes=tuple(clashes),
        path_proximity=tuple(near),
        safety_radius_m=radius,
    )


def _retreat(command: dict[str, Any]) -> tuple[float, float] | None:
    for action in command.get("actions") or []:
        params = action.get("parameters") or {}
        if action.get("action") == "yield" and params.get("retreat_x_m") is not None:
            return (float(params["retreat_x_m"]), float(params["retreat_y_m"]))
    return None


class GroundingFirstPerClusterVariant:
    """v2 options split per observed group; the reply's `choices` give one decision per group."""

    name = PER_CLUSTER_VARIANT
    generator_version: str | None = GENERATOR_VERSION_PER_CLUSTER

    def __init__(
        self,
        include_wait: bool = True,
        shuffle_seed: int | None = None,
        option_ids: OptionIds = "numbered",
    ) -> None:
        """Configure the variant.

        Args:
            include_wait: List `temporary_wait` options too.
            shuffle_seed: When set, shuffle options within each group.
            option_ids: "numbered" (v2 numbers) or "opaque" per-item tokens.
        """
        self.include_wait = include_wait
        self.shuffle_seed = shuffle_seed
        self.option_ids = option_ids

    def candidate_set(
        self, item: BenchItem
    ) -> tuple[PerClusterCandidateSet, tuple[int, ...] | None, int | None]:
        """The item's slots as presented, with the shuffle order and per-item seed.

        Args:
            item: The bench item.

        Returns:
            See `per_cluster_candidates`.
        """
        return per_cluster_candidates(item, self.include_wait, self.option_ids, self.shuffle_seed)

    def answer_extra(
        self,
        item: BenchItem,
        candidates: PerClusterCandidateSet,
        choices: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        """Per-item run-config record: groups, option ids, the choices and the joint check.

        Args:
            item: The bench item.
            candidates: The presented slots.
            choices: The validated choices, or None on a parse failure.

        Returns:
            A JSON-safe dict.
        """
        record: dict[str, Any] = {
            "grouping_threshold_m": candidates.base.threshold_m,
            "groups": {g.label: list(g.robots) for g in candidates.base.groups},
            "slots": {s.label: list(s.option_ids) for s in candidates.slots},
            "choices": None if choices is None else dict(choices),
        }
        if choices is not None:
            chosen = chosen_options(candidates, choices)
            record["chosen_v2_numbers"] = {
                label: None if o is None else candidates.base.options.index(o) + 1
                for label, o in chosen.items()
            }
            record["joint_check"] = joint_check(item, chosen).model_dump(mode="json")
        return record

    def run_info(self) -> dict[str, Any]:
        """Run-level settings for the run config.

        Returns:
            The grouping and slot rules and the flags.
        """
        return {
            "grouping_rule": GROUPING_RULE,
            "grouping_threshold_source": "item.classical.params.r_conflict_m",
            "slot_rule": SLOT_RULE,
            "offgroup": "drop",
            "cross_group": "drop",
            "include_wait": self.include_wait,
            "option_ids": self.option_ids,
            "schema_delivery": "prompt-stated keys + per-item Pydantic validation + re-ask",
        }

    def answer(
        self, item: BenchItem, request: ReasonerRequest, context: ReplayContext
    ) -> VariantAnswer:
        """Ask once per attempt with the composed prompt; re-ask on invalid choices.

        Backend errors back off as the production `Reasoner` does
        (`DEFAULT_RETRY_POLICY`); a deterministic 4xx ends the call.

        Args:
            item: The bench item.
            request: The rebuilt live request.
            context: Backend (cached) and reasoner config.

        Returns:
            `group_decisions` (label -> decision or None) on a valid reply;
            `decision=None` with `parse_status="failed"` after `max_attempts`.
        """
        candidates, order, item_seed = self.candidate_set(item)
        first = compose_per_cluster_payload(build_prompt_payload(request), candidates)
        sha = hashlib.sha256(first.user_prompt.encode()).hexdigest()
        config = context.reasoner_config
        payload = first
        attempts = 0
        waited = 0.0
        failed_once = False
        last: BackendResponse | None = None
        error: str | None = None
        while attempts < config.max_attempts:
            attempts += 1
            try:
                last = invoke_backend(context.backend, payload, config)
            except Exception as exc:  # one recorded attempt, as in `Reasoner.run`
                error = f"{type(exc).__name__}: {exc}"
                if classify_failure(exc) == "stop":
                    break
                if attempts < config.max_attempts:
                    waited += DEFAULT_RETRY_POLICY.wait_before_retry(exc, attempts, waited)
                continue
            parsed = parse_per_cluster_answer(last.text, candidates)
            if parsed.status == "choices":
                decisions = group_decisions(candidates, parsed.choices, parsed.model_answer)
                n_none = sum(1 for d in decisions.values() if d is None)
                return VariantAnswer(
                    decision=None,
                    group_decisions=decisions,
                    prompt_sha256=sha,
                    attempts=attempts,
                    parse_status="invalid" if failed_once else "valid",
                    raw_text=last.text,
                    n_candidates=candidates.n_options,
                    token_usage=last.token_usage,
                    latency_ms=last.latency_ms,
                    note=(
                        "choices="
                        + ",".join(f"{k}:{v}" for k, v in parsed.choices.items())
                        + f"; none_feasible={n_none}/{len(decisions)}"
                    ),
                    option_order=order,
                    shuffle_item_seed=item_seed,
                    extra=self.answer_extra(item, candidates, parsed.choices),
                )
            failed_once = True
            error = parsed.error
            if config.allow_reask:
                payload = build_reask_prompt(first, error or "invalid choices")
        return VariantAnswer(
            decision=None,
            prompt_sha256=sha,
            attempts=attempts,
            parse_status="failed",
            raw_text=None if last is None else last.text,
            n_candidates=candidates.n_options,
            token_usage=None if last is None else last.token_usage,
            latency_ms=None if last is None else last.latency_ms,
            note=f"parse_failure: {error}",
            option_order=order,
            shuffle_item_seed=item_seed,
            extra=self.answer_extra(item, candidates, None),
        )


class FixedGroupChoiceBackend:
    """A zero-network backend that answers the same rule in every group (sanity chooser).

    It reads the slot labels and allowed ids from the composed prompt's
    stated answer keys, so it needs no item.
    """

    def __init__(self, policy: Literal["first", "none_feasible"] = "first") -> None:
        """Fix the rule.

        Args:
            policy: "first" (the first listed option of every group) or
                "none_feasible" (every group).
        """
        self.policy = policy
        self.calls = 0

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Answer the rule's choice for every stated group.

        Args:
            payload: The composed payload.
            config: Ignored.

        Returns:
            The reply in the decision JSON shape plus `choices`.
        """
        self.calls += 1
        keys = read_answer_keys(payload.user_prompt)
        choices = {
            label: ids[0] if self.policy == "first" else NONE_FEASIBLE
            for label, ids in keys.items()
        }
        text = json.dumps(
            {
                "congestion_detected": True,
                "type": "deadlock",
                "involved_robots": [],
                "root_cause": "fixed-group-choice sanity backend",
                "strategy": "yield",
                "justification": "fixed-group-choice sanity backend",
                "choices": choices,
            }
        )
        return BackendResponse(text=text, backend_id="fixed-group-choice")


__all__ = [
    "ANSWER_KEYS_PREFIX",
    "FixedGroupChoiceBackend",
    "GENERATOR_VERSION_PER_CLUSTER",
    "GroundingFirstPerClusterVariant",
    "GroupSlot",
    "JointCheck",
    "NONE_FEASIBLE",
    "PER_CLUSTER_VARIANT",
    "PerClusterAnswer",
    "PerClusterCandidateSet",
    "choices_model",
    "chosen_options",
    "compose_per_cluster_payload",
    "group_decisions",
    "joint_check",
    "opaque_id",
    "parse_per_cluster_answer",
    "per_cluster_candidates",
    "read_answer_keys",
    "render_per_cluster_section",
]
