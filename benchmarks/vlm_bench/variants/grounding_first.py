"""The `grounding-first` variant: the VLM picks from M3-executable options (v4 lever 1).

Before the model is asked, the item's executable action set is enumerated with
the real offline M3 (`grounder_offline.ground_command`, the episode's params,
no network, stage 2 not run). The set is rendered as a numbered list appended
to the live prompt, and the model's option number is mapped back to a decision
in the existing schema, so every bench metric scores it unchanged.

Enumeration (`generate_candidates`), per item, over the snapshot robots:

- `yield(Y, P)` for every ordered pair: kept when M3 grounds a `yield` action
  for Y itself (not refused, not swapped, not degraded to a reroute), the
  geometry oracle's rule (`grounder_offline.executable_yielders`).
- `reverse(a, b)` for every unordered pair: kept when the command carries a
  `reverse` action and no `reverse=infeasible` tag (a refused reverse becomes
  a wait the bench metric would still call feasible).
- `reroute(r)`: kept only when every reroute action carries waypoints (a
  waypoint-less reroute is an M4 no-op).
- `temporary_wait(a, b)`: always grounds; listed last, and only with
  `include_wait`.

Options are deduplicated on what M3 executes (`executed_key`). `junction_clear`,
`convoy` and `priority_override` are not offered: junction_clear falls back
to a yield on every S1b scene (`junction_geometry=shipped_unsolved`), and the
other two either alias to a yield already listed or degrade to a wait.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from benchmarks.vlm_bench.grounder_offline import ground_command, outcome_of
from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.variants.base import ReplayContext, VariantAnswer
from reasoning.vlm.models import (
    BackendResponse,
    CongestionDecision,
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
)
from reasoning.vlm.prompt_builder import build_prompt_payload
from reasoning.vlm.reasoner import build_reask_prompt, invoke_backend
from reasoning.vlm.retry_policy import DEFAULT_RETRY_POLICY, classify_failure

GENERATOR_VERSION = "gf-candidates-v1"
OptionStrategy = Literal["yield", "reverse", "reroute", "temporary_wait"]
_RESOLVING: frozenset[str] = frozenset({"yield", "reverse", "reroute"})
_TYPES: frozenset[str] = frozenset({"deadlock", "bottleneck", "crowding", "anomaly"})
_NONE_WORDS: frozenset[str] = frozenset({"none", "none of the above"})


class RetreatPark(BaseModel):
    """The retreat M3 dispatches for a yield option (default stage-2 letter)."""

    model_config = ConfigDict(frozen=True)

    label: str | None = None
    x: float | None = None
    y: float | None = None
    backup_m: float | None = None
    lateral_m: float | None = None


class ExecutableOption(BaseModel):
    """One action M3 executes as asked on the item's scene."""

    model_config = ConfigDict(frozen=True)

    strategy: OptionStrategy
    # The probed `involved_robots`, in probe order; the mapped decision uses it verbatim.
    robots: tuple[str, ...]
    yield_robot: str | None = None
    # What M3 executes (`executed_key`); options are deduplicated on it.
    key: tuple[str, ...]
    separation_m: float
    park: RetreatPark | None = None
    text: str

    @property
    def resolving(self) -> bool:
        """Whether the option moves a robot (not a hold)."""
        return self.strategy in _RESOLVING

    def decision(self, model_answer: dict[str, Any] | None = None) -> dict[str, Any]:
        """This option as a decision dict in the existing schema.

        Only `type`, `root_cause` and `justification` come from the model;
        the involved set, strategy and yielder are the probe's, so the
        decision grounds exactly as the probe did.

        Args:
            model_answer: The model's parsed JSON object, or None.

        Returns:
            A validated `CongestionDecision` dump.
        """
        answer = model_answer or {}
        kind = answer.get("type")
        kind = kind.lower() if isinstance(kind, str) else None
        return CongestionDecision(
            congestion_detected=True,
            type=kind if kind in _TYPES else "deadlock",
            involved_robots=list(self.robots),
            root_cause=_text(answer.get("root_cause"), self.text),
            strategy=self.strategy,
            justification=_text(answer.get("justification"), self.text),
            yield_robot=self.yield_robot,
        ).model_dump(mode="json")


class CandidateSet(BaseModel):
    """The numbered executable options of one item."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    generator_version: str = GENERATOR_VERSION
    include_wait: bool = True
    options: tuple[ExecutableOption, ...] = ()

    @property
    def keys(self) -> frozenset[tuple[str, ...]]:
        """Executed keys of every option."""
        return frozenset(o.key for o in self.options)

    @property
    def resolving_keys(self) -> frozenset[tuple[str, ...]]:
        """Executed keys of the options that move a robot."""
        return frozenset(o.key for o in self.options if o.resolving)


class OptionAnswer(BaseModel):
    """The model's option choice mapped back to a decision."""

    model_config = ConfigDict(frozen=True)

    status: Literal["option", "none", "parse_failure"]
    option_number: int | None = None
    decision: dict[str, Any] | None = None
    error: str | None = None
    model_involved: tuple[str, ...] = ()


def _text(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and value.strip() else fallback


def _probe(strategy: str, robots: tuple[str, ...], yielder: str | None = None) -> dict[str, Any]:
    return {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": list(robots),
        "root_cause": "grounding-first candidate probe",
        "strategy": strategy,
        "justification": "grounding-first candidate probe",
        "yield_robot": yielder,
    }


def executed_key(strategy: str, command: dict[str, Any]) -> tuple[str, ...] | None:
    """What a grounded command executes, or None when it does not execute as asked.

    Args:
        strategy: The decision's strategy.
        command: The grounded command.

    Returns:
        `("yield", yielder, *crossing_order)`, `("reverse", *movers)`,
        `("reroute", *robots)` (waypoints on every reroute),
        `("temporary_wait", *robots)` (a wait the decision asked for), else
        None: refused, swapped-away, degraded or no-op commands.
    """
    if not outcome_of(command).feasible:
        return None
    actions = command.get("actions") or []
    tags = command.get("degradations") or []
    yields = [a for a in actions if a.get("action") == "yield"]
    if yields:
        params = yields[0].get("parameters") or {}
        order = params.get("crossing_order") or [params.get("passer_robot_id")]
        return ("yield", yields[0]["robot_id"], *(str(r) for r in order if r))
    reroutes = [a for a in actions if a.get("action") == "reroute"]
    if reroutes:
        if all((a.get("parameters") or {}).get("waypoints") for a in reroutes):
            return ("reroute", *sorted(a["robot_id"] for a in reroutes))
        return None
    reverses = [a for a in actions if a.get("action") == "reverse"]
    if reverses:
        if any(t.startswith("reverse=infeasible") for t in tags):
            return None
        return ("reverse", *sorted(a["robot_id"] for a in reverses))
    if strategy == "temporary_wait" and actions and all(
        a.get("action") == "temporary_wait" for a in actions
    ):
        return ("temporary_wait", *sorted(a["robot_id"] for a in actions))
    return None


def _separation(item: BenchItem, robots: tuple[str, ...]) -> float:
    pose = {r["robot_id"]: (r["x"], r["y"]) for r in item.scene["robots"]}
    pts = [pose[r] for r in robots if r in pose]
    if len(pts) < 2:
        return 0.0
    return min(math.dist(a, b) for a, b in itertools.combinations(pts, 2))


def _yield_text(yielder: str, passer: str, park: RetreatPark, sep: float) -> str:
    where = (
        f"park {park.label or '?'} at ({park.x:.2f}, {park.y:.2f})"
        if park.x is not None and park.y is not None
        else "default park"
    )
    moves = ""
    if park.backup_m is not None:
        moves = f"; back {park.backup_m:.2f} m"
        if park.lateral_m:
            moves += f", side-step {park.lateral_m:+.2f} m"
    return (
        f"yield: {yielder} backs up and steps aside so {passer} can pass "
        f"({where}{moves}) [{sep:.2f} m apart]"
    )


def _reverse_text(robots: tuple[str, ...], movers: tuple[str, ...], sep: float) -> str:
    held = [r for r in robots if r not in movers]
    verb = "backs" if len(movers) == 1 else "back"
    text = f"reverse: {' and '.join(movers)} {verb} straight out along the lane"
    if held:
        text += f" ({' and '.join(held)} not moved)"
    return f"{text} [{sep:.2f} m apart]"


def _option(
    item: BenchItem, strategy: OptionStrategy, robots: tuple[str, ...], yielder: str | None
) -> ExecutableOption | None:
    try:
        command = ground_command(item, _probe(strategy, robots, yielder))
    except Exception:  # an exception is a refusal for enumeration purposes
        return None
    key = executed_key(strategy, command)
    if key is None or key[0] != strategy:
        return None
    sep = _separation(item, robots)
    park = None
    if strategy == "yield":
        if key[1] != yielder:
            return None
        action = next(a for a in command["actions"] if a.get("action") == "yield")
        params = action.get("parameters") or {}
        park = RetreatPark(
            label=params.get("retreat_choice"),
            x=params.get("retreat_x_m"),
            y=params.get("retreat_y_m"),
            backup_m=params.get("backup_distance_m"),
            lateral_m=params.get("pull_off_lateral_m"),
        )
        text = _yield_text(yielder, ", ".join(key[2:]), park, sep)
    elif strategy == "reverse":
        text = _reverse_text(robots, key[1:], sep)
    elif strategy == "reroute":
        text = f"reroute: {' and '.join(key[1:])} follows the declared detour"
    else:
        text = f"temporary_wait: {' and '.join(robots)} hold in place until the way clears"
        text += f" [{sep:.2f} m apart]"
    return ExecutableOption(
        strategy=strategy,
        robots=robots,
        yield_robot=yielder,
        key=key,
        separation_m=round(sep, 3),
        park=park,
        text=text,
    )


def generate_candidates(item: BenchItem, include_wait: bool = True) -> CandidateSet:
    """Enumerate the item's executable options with the real offline M3.

    Args:
        item: The bench item (scene, overlay, recorded grounding params).
        include_wait: Also list `temporary_wait` pairs (always executable).

    Returns:
        Yields, then reverses, then reroutes, then waits, each closest pair
        first; deduplicated on the executed key. Empty for a scene with no
        executable option (e.g. a single robot).
    """
    ids = [r["robot_id"] for r in item.scene["robots"]]
    groups: list[list[ExecutableOption]] = [[], [], [], []]
    for yielder, passer in itertools.permutations(ids, 2):
        groups[0].append(_option(item, "yield", (yielder, passer), yielder))
    for pair in itertools.combinations(ids, 2):
        groups[1].append(_option(item, "reverse", pair, None))
    for robot in ids:
        groups[2].append(_option(item, "reroute", (robot,), None))
    if include_wait:
        for pair in itertools.combinations(ids, 2):
            groups[3].append(_option(item, "temporary_wait", pair, None))
    seen: set[tuple[str, ...]] = set()
    options: list[ExecutableOption] = []
    for group in groups:
        for option in sorted(
            (o for o in group if o is not None), key=lambda o: (o.separation_m, o.robots)
        ):
            if option.key not in seen:
                seen.add(option.key)
                options.append(option)
    return CandidateSet(item_id=item.item_id, include_wait=include_wait, options=tuple(options))


def render_candidate_section(candidates: CandidateSet) -> str:
    """The numbered option list and the answer instruction appended to the live prompt.

    Args:
        candidates: The item's options.

    Returns:
        The section text; the last number is always "none of the above".
    """
    lines = [
        "Executable options. Each one below was checked on this exact scene by the motion "
        "planner that will execute your answer; any other choice would be refused or "
        "would not move a robot:"
    ]
    if not candidates.options:
        lines.append("(no executable option was found for this scene)")
    for number, option in enumerate(candidates.options, start=1):
        lines.append(f"{number}) {option.text}")
    none_number = len(candidates.options) + 1
    lines.append(
        f"{none_number}) none of the above: there is no congestion, or no listed option "
        "resolves it"
    )
    lines += [
        "",
        'Your strategy MUST be one of the numbered options above, or "none". Add one more '
        "field to the JSON object:",
        f'- "option": the number of the option you choose (1-{none_number}), or "none"',
        'State the reason for your choice in "justification". The chosen option\'s robots, '
        'strategy and yield robot are what will be executed; your own "involved_robots", '
        '"strategy" and "yield_robot" are not used.',
    ]
    return "\n".join(lines)


def compose_payload(base: PromptPayload, candidates: CandidateSet) -> PromptPayload:
    """The live payload with the candidate section appended to its user prompt.

    Args:
        base: The live builder's payload, unchanged.
        candidates: The item's options.

    Returns:
        The composed payload (system prompt and images unchanged).
    """
    user = f"{base.user_prompt}\n\n{render_candidate_section(candidates)}"
    return base.model_copy(update={"user_prompt": user})


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


def _negative(answer: dict[str, Any]) -> dict[str, Any]:
    return CongestionDecision(
        congestion_detected=False,
        type="none",
        involved_robots=[],
        root_cause=_text(answer.get("root_cause"), "none of the executable options chosen"),
        strategy="none",
        justification=_text(answer.get("justification"), "option none"),
    ).model_dump(mode="json")


def parse_option_answer(text: str, candidates: CandidateSet) -> OptionAnswer:
    """Map the model's `option` field back to a decision.

    Args:
        text: The raw reply.
        candidates: The options the prompt listed.

    Returns:
        `option` with the option's decision; `none` (the word, or the
        none-of-the-above number) with a negative decision; `parse_failure`
        with the error for anything else. Never raises.
    """
    try:
        answer = extract_json_object(text)
    except ValueError as exc:
        return OptionAnswer(status="parse_failure", error=str(exc))
    involved = answer.get("involved_robots")
    model_involved = (
        tuple(str(r) for r in involved) if isinstance(involved, list) else ()
    )
    if "option" not in answer:
        return OptionAnswer(
            status="parse_failure", error='missing "option" field', model_involved=model_involved
        )
    raw = answer["option"]
    number: int | None = None
    if isinstance(raw, str):
        word = raw.strip().lower().rstrip(".")
        if word in _NONE_WORDS:
            return OptionAnswer(
                status="none", decision=_negative(answer), model_involved=model_involved
            )
        if word.isdigit():
            number = int(word)
    elif isinstance(raw, int) and not isinstance(raw, bool):
        number = raw
    none_number = len(candidates.options) + 1
    if number is None or not 1 <= number <= none_number:
        return OptionAnswer(
            status="parse_failure",
            error=f'"option" must be a number from 1 to {none_number} or "none", got {raw!r}',
            model_involved=model_involved,
        )
    if number == none_number:
        return OptionAnswer(
            status="none",
            option_number=number,
            decision=_negative(answer),
            model_involved=model_involved,
        )
    return OptionAnswer(
        status="option",
        option_number=number,
        decision=candidates.options[number - 1].decision(answer),
        model_involved=model_involved,
    )


class GroundingFirstVariant:
    """Live prompt + M3-executable option list; the reply's option number is the decision."""

    name = "grounding_first"
    generator_version: str | None = GENERATOR_VERSION

    def __init__(self, include_wait: bool = True) -> None:
        """Configure the variant.

        Args:
            include_wait: List `temporary_wait` options too.
        """
        self.include_wait = include_wait

    def answer(
        self, item: BenchItem, request: ReasonerRequest, context: ReplayContext
    ) -> VariantAnswer:
        """Ask once per attempt with the composed prompt; re-ask on an unreadable option.

        Backend errors back off as the production `Reasoner` does
        (`DEFAULT_RETRY_POLICY`); a deterministic 4xx ends the call.

        Args:
            item: The bench item.
            request: The rebuilt live request.
            context: Backend (cached) and reasoner config.

        Returns:
            The mapped decision; `decision=None` with `parse_status="failed"`
            after `max_attempts` unreadable replies or backend errors.
        """
        candidates = generate_candidates(item, include_wait=self.include_wait)
        first = compose_payload(build_prompt_payload(request), candidates)
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
            parsed = parse_option_answer(last.text, candidates)
            if parsed.status != "parse_failure":
                return VariantAnswer(
                    decision=parsed.decision,
                    prompt_sha256=sha,
                    attempts=attempts,
                    parse_status="invalid" if failed_once else "valid",
                    raw_text=last.text,
                    n_candidates=len(candidates.options),
                    token_usage=last.token_usage,
                    latency_ms=last.latency_ms,
                    note=(
                        f"option={parsed.option_number or 'none'}/{len(candidates.options)}; "
                        f"model_involved={','.join(parsed.model_involved)}"
                    ),
                )
            failed_once = True
            error = parsed.error
            if config.allow_reask:
                payload = build_reask_prompt(first, error or "unreadable option")
        return VariantAnswer(
            decision=None,
            prompt_sha256=sha,
            attempts=attempts,
            parse_status="failed",
            raw_text=None if last is None else last.text,
            n_candidates=len(candidates.options),
            token_usage=None if last is None else last.token_usage,
            latency_ms=None if last is None else last.latency_ms,
            note=f"parse_failure: {error}",
        )


class FixedOptionBackend:
    """A zero-network backend that always answers one option number (sanity ceiling)."""

    def __init__(self, option: int | str = 1) -> None:
        """Fix the answer.

        Args:
            option: The option number (or "none") every reply names.
        """
        self.option = option
        self.calls = 0

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Answer the fixed option in the decision JSON shape.

        Args:
            payload: Ignored.
            config: Ignored.

        Returns:
            The reply.
        """
        self.calls += 1
        text = json.dumps(
            {
                "congestion_detected": True,
                "type": "deadlock",
                "involved_robots": [],
                "root_cause": "fixed-option sanity backend",
                "strategy": "yield",
                "justification": "fixed-option sanity backend",
                "option": self.option,
            }
        )
        return BackendResponse(text=text, backend_id="fixed-option")
