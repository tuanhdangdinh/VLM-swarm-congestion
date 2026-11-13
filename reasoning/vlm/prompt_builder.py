import json
import math

from reasoning.vlm.models import (
    CandidateOption,
    FailureContext,
    PlanStateContext,
    PlanStateLeg,
    PromptPayload,
    ReasonerRequest,
    RobotCandidateOptions,
    RobotOrder,
    RobotStateInput,
    StaticObstacleInput,
)
from reasoning.vlm.prompt_v1 import SYSTEM_PROMPT_V1, render_user_prompt_v1
from reasoning.vlm.prompt_v2 import SYSTEM_PROMPT_V2, render_user_prompt_v2

# "faces" = the robot's heading is within 60° of the direction to the other robot.
# Opposite headings alone cannot tell head-on from diverging; the VLM misread two
# robots driving apart as a deadlock when only |Δθ| ≈ π was offered (run 3, 2026-09-17).
_FACING_COS = 0.5
_PAIRWISE_GEOMETRY_HEADER = (
    "Pairwise geometry (faces = heading within 60° of the direction to the other robot):"
)
_STATIC_OBSTACLE_HEADER = "Static obstacles (world-frame axis-aligned boxes):"

# Cosmos Reason 2 is a chain-of-thought reasoning VLM built on Qwen3-VL. NVIDIA's
# prompt guide specifies a minimal system prompt ("we are more aligned with Qwen's
# use of system prompt ... different from Reason 1, where the system prompt was
# heavily used") and prompt-driven structured output. The task framing therefore
# lives in the user prompt, and the image is placed before the text by the backend.
# Ref: https://nvidia-cosmos.github.io/cosmos-cookbook/getting_started/prompt_guide/reason_guide.html
SYSTEM_PROMPT = "You are a helpful assistant."

# Prompt v3 (prereg-v2 rev 4/6, 2026-10-02). Against v2 (`prompt_v2`, frozen)
# it generalizes the failure-context block into a scene-wide plan-state block
# (the active plan, per-leg status, what changed since the last invocation),
# adds the scenario-agnostic `proposed_plan` invitation and output bullet (the
# (a0) universal channel, previously accepted by the schema/parser but never
# mentioned in any prompt), and moves to reasoning-field-first JSON: a bounded
# free-text `reasoning` field opens the response schema, before any strict
# classification field (the premature-serialization effect, rev 6 "Prompt
# apparatus"). Goals and the task label render through
# `format_robot_state_lines` once M5 supplies them. Any edit to this template
# is a new prompt version: bump `PromptVersion`, freeze this one first.
# Exception, same as the step-5 `junction_clear` re-pin: v3 is not frozen
# until the prereg-v2 freeze, so pre-freeze revisions re-pin in place under
# `prompt_version=3`. Revision v3.1 (2026-10-03) adds `_PLAN_GRAMMAR` and a
# one-line gloss for every strategy token; v3.2 (same day, coordinator
# ruling) states the decision-field agreement rule and narrows the convoy
# gloss. v3.3 (2026-10-06, verbatim-pilot rulings A/B) adds the
# `_PLAN_GRAMMAR` list-order line and names the composite's inside yielder in
# the junction_clear gloss. v3.4 (2026-10-06, roster-validation ruling 1)
# removes the Cosmos-style `<think>...</think>` answer-format block: the
# bounded `reasoning` field above is the sanctioned reasoning channel, the
# block contradicted the registered spatial-CoT prohibition, its audience
# (Cosmos Reason 2) is deferred to v3, and Anthropic's documented
# `reasoning_extraction` trigger made Sonnet 5.5 refuse 91/96 attempts. The
# closing line is the JSON-only sentence the refusal diagnostic answered 3/3.
# Artifacts are told apart by `user_sha256` (baseline pins: v3.0
# 22baf2df... -> v3.1 42463ce2... -> v3.2 c3fb9fcf... -> v3.3 769802f0...
# -> v3.4 6d08540f...) or, per scene: v3.0-v3.2 lack the list-order line,
# v3.3 has it and the `<think>` block, v3.4 has it and no `<think>` block.
_USER_TEMPLATE = """You are a warehouse swarm robotics traffic controller. Analyze the \
overhead camera view together with the robot states below and detect congestion \
patterns such as deadlocks, bottlenecks, crowding, or anomalies.

Robot states:
{robot_state_block}
{pairwise_geometry_block}{static_obstacle_block}
Known robot IDs: {known_robot_ids_json}
{failure_context_block}
Guidance:
- Robots are roughly 0.3 m wide; treat any two robots within ~0.5 m of each \
other as physically conflicting. {geometry_use_clause}{obstacle_use_clause}
- theta is heading in radians: 0=east(+x), π/2=north(+y), π or -π=west(-x), \
-π/2=south(-y). Opposite headings alone do NOT mean head-on: two robots are \
head-on only when each faces the other {facing_source} AND they are within \
~0.5 m. Robots heading away from each other are diverging, not conflicting.
- deadlock: two or more robots each blocked by the other. The most common case \
is a head-on standoff — two robots within ~0.5 m, each facing the other, in the \
same narrow aisle, both STOPPED or STALE, unable to pass. This IS a deadlock \
even with only two robots. Two robots that are stopped but farther apart than \
~0.5 m, or not facing each other, are NOT deadlocked — answer \
congestion_detected=false unless another pattern applies. \
bottleneck: several robots queued waiting behind one slow robot or blocked passage \
(one-way congestion, not opposing). crowding: many robots packed into a small \
area. anomaly: unexpected or unsafe configuration.
- For head-on deadlock (two stopped/stale robots within ~0.5 m, each facing the \
other): classify as type="deadlock" and strategy="yield" (the robot named in \
yield_robot backs up) or strategy="reverse" (both back up to clear).
- For a simple bottleneck (robots queued in the same direction): classify as \
type="bottleneck" and strategy="temporary_wait" or "yield".
- Decide from the robot states (including their stated goals and tasks) and the \
image; do not assume intentions beyond what is stated.
{visual_crosscheck_block}
{plan_invitation}
{plan_grammar}
Produce a JSON object with exactly these fields:
- "reasoning": one to three sentences of your analysis, written before you commit \
to the fields below (what you see, why it is or is not congestion, and your plan \
if any)
- "congestion_detected": true or false
- "type": "none" | "deadlock" | "bottleneck" | "crowding" | "anomaly"
- "involved_robots": list of robot_id strings, from the known IDs only
- "root_cause": one sentence
- "strategy": one of
{strategy_option_lines}
- "justification": one or two sentences
- "yield_robot": the robot that should yield, or null when the strategy is not \
"yield"
- "blocker_kind": what is blocking the involved robots: "robot" when it is one of \
the robots listed above, "object" when it is a fixed obstacle, "transient" when it \
is a temporary obstruction expected to clear on its own; null when \
congestion_detected is false
- "crossing_order": when three or more robots must be ordered, every involved \
robot ID in the order they should pass, first to pass first (a robot that yields \
passes after the robots it yields to); otherwise null
- "proposed_plan": optional; your full proposed resolution as an ordered list of \
{{"robot_id": ..., "action": ...}}, action one of "yield", "reverse", "cross", \
"wait", "reroute", "continue" ("continue" for a known robot not part of the \
resolution); omit it, or set it to null, to let the system derive one for you

Rules:
- Only use robot IDs from the known list above.
- When congestion_detected is false: set type="none", strategy="none", involved_robots=[].
- When congestion_detected is true: type and strategy must not be "none", and \
involved_robots must be non-empty.

Write ONLY the final JSON object, with no surrounding text or markdown."""

# Wording for the two modality conditions of the derived-geometry ablation axis.
# `crosscheck_default_clause` is only consumed by _VISUAL_CROSSCHECK_TEMPLATE; it
# lives here because which channel is "the default source" depends on this axis.
_GEOMETRY_ON = {
    "geometry_use_clause": (
        "Use the pairwise geometry above; do not re-derive distances or facing from "
        "the coordinates."
    ),
    "facing_source": "(pairwise geometry)",
    "crosscheck_default_clause": (
        "The pairwise geometry above stays the default source for distance and "
        "facing: when the image and the states agree, use it and do not re-derive "
        "distances or facing from the coordinates."
    ),
}
_GEOMETRY_OFF = {
    "geometry_use_clause": "Compute distances and facing from the coordinates.",
    "facing_source": "(heading points toward the other robot)",
    "crosscheck_default_clause": (
        "The coordinates above stay the default source for distance and facing: "
        "when the image and the states agree, decide from them."
    ),
}

# Wording for the two modality conditions of the static-obstacle ablation axis.
# The ON clause states scene physics only: naming a robot, a maneuver or a
# blocked side would hand the model the answer the experiment measures — which
# is also why configured obstacle ids must stay non-semantic, since they render
# verbatim. The OFF value is the empty string (not a placeholder line) so the
# rendered prompt stays byte-identical to the pre-modality prompt; the leading
# space therefore lives inside the ON value.
_OBSTACLES_ON = {
    "obstacle_use_clause": (
        " Fixed obstacles in the scene are listed above and are the only ones "
        "present; a robot can neither occupy nor drive through one."
    ),
}
_OBSTACLES_OFF = {"obstacle_use_clause": ""}

# Opt-in modality block (`ReasonerRequest.include_visual_crosscheck`). It must
# establish precedence rather than contradict `geometry_use_clause`: giving the
# model licence to re-derive geometry from raw coordinates is exactly the run-3
# (2026-09-17) failure mode that `_FACING_COS` and that clause exist to prevent,
# so this asks only for a gross-contradiction check on what is visible, never for
# a measurement. Evidence for the block:
# docs/reports/2026-09-18-gemini-er2-image-grounding.md.
_VISUAL_CROSSCHECK_TEMPLATE = """Cross-check the states against the image:
- The robot states above come from an overhead camera tracker and can be wrong: \
a robot may be missed, a position may be stale, or two robot IDs may be swapped.
- {crosscheck_default_clause}
- Then look at the overhead image and check that it agrees with the states. Only \
a clear contradiction matters: robots obviously touching or nose-to-nose in the \
image while the states place them well apart, or obviously far apart in the image \
while the states place them in contact. In that case trust the image, decide from \
what you see, and say so in the justification, naming the disagreement between \
the image and the stated positions."""

_FAILURE_CONTEXT_ADVICE = (
    "If the congestion is no longer present, report congestion_detected=false. "
    "If it persists and the previous strategy did not clear it, prefer a different "
    "strategy unless the scene has changed."
)


# Generic on purpose, like _FAILURE_CONTEXT_ADVICE: the block already states which
# strategy and yielder failed, and naming an alternative would hand the model the
# answer the experiment measures.
_LAST_FAILED_CONTEXT_ADVICE = (
    "If the congestion persists, do not repeat this failed attempt unless the scene "
    "has changed."
)

# Scenario-agnostic (prereg-v2 (a0), "one scenario-agnostic invitation
# sentence in the prompt"): names the field and the division of labor
# (propose-verify), never a strategy or scenario, so it reads identically on
# every v3 decision regardless of what the scene turns out to be.
_PLAN_INVITATION = (
    "You may also propose the full multi-robot resolution yourself, as "
    '"proposed_plan" below: an ordered list naming every known robot. The '
    "system verifies it and, if needed, minimally repairs it before anything "
    "is dispatched; omitting it (or setting it to null) lets the system "
    "derive the resolution for you instead."
)

# Prompt v3.1 plan grammar: the operational meaning of each plan action and the
# consistency contract M3 enforces (`command_grounder._is_consistent`, the (a0)
# "Consistency rule"), stated so a plan is not discarded for a rule the model
# was never shown. Generic on purpose, like `_PLAN_INVITATION`: a static
# constant outside every conditional block, so it renders byte-identically on
# every v3 decision in every scenario. It states the contract, never which
# strategy or action fits a scene -- no examples, scene references or robot
# counts. The rule lines must track `_is_consistent` exactly, plus the second
# "inconsistent" path (`_plan_disagrees_with_decision_fields`: a yield leg or
# cross order that contradicts the same answer's yield_robot/crossing_order),
# stated on the "yield" line because that check runs for strategy "yield"
# only (v3.2 re-pin, 2026-10-03 ruling). The list-order line (v3.3, verbatim
# pilot ruling A) states the convention `_plan_problems`' reorder audit
# already enforces: the pilot's reorder-only repairs listed a releasing leg
# after the cross it releases.
# Its em dash is the spec wording verbatim (the template already carries
# non-ASCII), so the pin covers it byte for byte.
_PLAN_GRAMMAR_TEMPLATE = """Plan actions, for "proposed_plan":
- "yield": back up, step aside, and hold until the passing robots have cleared
- "reverse": back straight out along its own lane
- "cross": proceed through in its assigned turn (the plan's list order)
- "wait": hold in place
- "reroute": take an alternative path
- "continue": proceed unchanged; not part of the resolution
The list order is the execution order — the robot that acts first comes first.
A proposed plan must refine the chosen strategy; a plan that does not is \
ignored and the system derives the resolution instead:
{plan_rule_lines}
- any other strategy: no constraint on the legs"""

# The v3 strategy list and plan-grammar rule lines, one per strategy token in
# enum order, joined into `_USER_TEMPLATE` / `_PLAN_GRAMMAR` (v4 refusal
# feedback Change 1). With every token offered they join to the v3.4 text
# byte for byte; `ReasonerRequest.offered_strategies` drops the lines of a
# token M3 cannot ground on the scene. "none" is always offered.
_STRATEGY_OPTION_LINES: dict[str, str] = {
    "none": '  - "none": no congestion to resolve',
    "yield": '  - "yield": one robot (yield_robot) backs up and steps aside while the others pass',
    "reroute": '  - "reroute": a robot takes an alternative path around the blockage',
    "convoy": (
        '  - "convoy": robots heading the same way pass through in single file, in order, '
        "while an opposing robot gives way"
    ),
    "priority_override": (
        '  - "priority_override": the higher-priority robot passes first; the others give way'
    ),
    "temporary_wait": (
        '  - "temporary_wait": the involved robots hold in place until the way clears'
    ),
    "reverse": '  - "reverse": the involved robots back straight out along their own lanes',
    "junction_clear": (
        '  - "junction_clear": multi-robot junction recovery: some robots first back out, '
        "one inside robot yields, then an ordered crossing"
    ),
}
_PLAN_RULE_LINES: dict[str, str] = {
    "yield": (
        '- strategy "yield": exactly one "yield" leg, and the plan must agree with your own '
        "yield_robot and crossing_order answers"
    ),
    "temporary_wait": '- strategy "temporary_wait": at least one "wait" leg',
    "reroute": '- strategy "reroute": at least one "reroute" leg',
    "junction_clear": '- strategy "junction_clear": at least one "reverse" or "yield" leg',
}


def _offered_tokens(offered: tuple[str, ...] | None) -> set[str]:
    if offered is None:
        return set(_STRATEGY_OPTION_LINES)
    return {"none", *offered}


def render_strategy_option_lines(offered: tuple[str, ...] | None) -> str:
    """Render the v3 `"strategy": one of` list for the offered strategies.

    Args:
        offered: `ReasonerRequest.offered_strategies`; None offers every token.

    Returns:
        One line per offered token in enum order, "none" first; no trailing newline.
    """
    tokens = _offered_tokens(offered)
    return "\n".join(line for token, line in _STRATEGY_OPTION_LINES.items() if token in tokens)


def render_plan_grammar(offered: tuple[str, ...] | None) -> str:
    """Render `_PLAN_GRAMMAR` with the consistency rules of the offered strategies only.

    Args:
        offered: `ReasonerRequest.offered_strategies`; None offers every token.

    Returns:
        The plan-grammar block; byte-identical to v3.4 when every token is offered.
    """
    tokens = _offered_tokens(offered)
    rules = "\n".join(line for token, line in _PLAN_RULE_LINES.items() if token in tokens)
    return _PLAN_GRAMMAR_TEMPLATE.format(plan_rule_lines=rules)


# The v3.4 plan grammar with every strategy offered (the pinned text).
_PLAN_GRAMMAR = render_plan_grammar(None)

# Prompt-apparatus sentences (prereg-v2 rev 6 + round-3 deltas, 2026-10-04).
# Each is an A/B condition, never a default, and renders only when the request
# says the frame/attachment ACTUALLY carries the thing it names (M5 sets the
# request fields from what M1 drew and what M5 attached, the same "gate on what
# was rendered" rule `_OBSTACLES_ON` follows). Static, scenario-agnostic text:
# they name a convention, never a robot, a scene or a strategy. All are
# appended into the cross-check slot of `_USER_TEMPLATE`, so with every
# condition off the slot renders exactly as before and the six v3 pins hold.
_METRIC_GRID_SENTENCE = (
    "The overhead image carries a labeled metric grid on the floor, one line "
    "every {spacing} m: columns are lettered from west to east and rows are "
    "numbered from north to south along the image margins, and a cell is named "
    "by its column letter and row number, e.g. C4."
)
_MOTION_TRAILS_SENTENCE = (
    "Each robot's recently detected positions are drawn behind it as a fading "
    "trail in its status color: the faint end is the oldest position, the solid "
    "end the most recent."
)
_ZOOM_TILE_SENTENCE = (
    "A second image follows the overhead view: an enlarged crop of the same "
    "annotated frame around the robots this analysis was triggered for. It shows "
    "part of the same scene at higher magnification, not additional robots."
)
# Verifier-candidate-options condition (round-3 "constraints-in-prompt"
# recipe, arXiv:2401.03630): ONE framing sentence, then one line per robot
# listing the actions M3's own audit accepts in this scene. This changes the
# measured construct from free planning to constrained selection -- recorded
# per decision in the artifact's `prompt_conditions`.
_CANDIDATE_OPTIONS_HEADER = (
    "Plan actions the system's verifier accepts for each robot in the current "
    "scene (a plan leg outside these is repaired or the plan is replaced):"
)

_PLAN_STATE_HEADER = "Active plan (plan_id={plan_id}):"

# Generic on purpose, like _FAILURE_CONTEXT_ADVICE: naming which strategy to
# pick next would hand the model the answer the experiment measures. A
# revision is always legal; this only says when the scene gives evidence for
# one.
_PLAN_STATE_ADVICE = (
    "Hold this plan unless the scene has changed or a leg above is failed: "
    'propose a new "proposed_plan" only when you are revising it for a '
    "reason, not by default."
)


def _render_plan_state_leg_line(leg: PlanStateLeg) -> str:
    return f"- {leg.robot_id}: {leg.action} ({leg.status})"


def render_plan_state_block(context: PlanStateContext) -> str:
    """Render the active-plan block for prompt v3 (rev 4 "plan-state block").

    Generalizes `render_failure_context_block` from "the previous
    single-conflict attempt" to "the scene-wide plan M5 is currently
    executing": every leg's current status, plus which robots' legs changed
    since the last invocation that produced this plan.

    Args:
        context: M5's current plan state for this request.

    Returns:
        A multi-line block with no leading or trailing newline.
    """
    lines = [_PLAN_STATE_HEADER.format(plan_id=context.plan_id)]
    lines.extend(_render_plan_state_leg_line(leg) for leg in context.legs)
    if context.changed_robot_ids:
        lines.append(
            "Changed since the last invocation: " + ", ".join(context.changed_robot_ids)
        )
    else:
        lines.append("Nothing has changed since this plan was accepted.")
    lines.append(_PLAN_STATE_ADVICE)
    return "\n".join(lines)


def _render_attempt_lines(context: FailureContext) -> list[str]:
    attempt = f"strategy={context.strategy}"
    if context.yield_robot is not None:
        attempt += f", yield_robot={context.yield_robot}"
    attempt += f", outcome={context.outcome_status}"
    # crossing_order is accepted on FailureContext but not rendered in this slice
    # (Phase 1 plan Task 5 adds the ordered-crossing prompt block).
    return [f"- {attempt}", f"- detail: {context.failure_detail}"]


def _render_option(option: CandidateOption) -> str:
    return option.action if option.detail is None else f"{option.action} ({option.detail})"


def render_candidate_options_block(
    candidate_options: list[RobotCandidateOptions], robot_order: list[str]
) -> str:
    """Render the verifier-candidate-options block (prompt v3 A/B condition).

    Args:
        candidate_options: Per-robot accepted actions, from M3 via M5.
        robot_order: Presentation order of the prompt's robot list; the block
            follows it so a presentation-order shift rotates this block too.

    Returns:
        A multi-line block with no leading or trailing newline.
    """
    by_robot = {entry.robot_id: entry for entry in candidate_options}
    ordered = [by_robot[rid] for rid in robot_order if rid in by_robot] + [
        entry for entry in candidate_options if entry.robot_id not in robot_order
    ]
    lines = [_CANDIDATE_OPTIONS_HEADER]
    for entry in ordered:
        rendered = ", ".join(_render_option(option) for option in entry.options) or "none"
        lines.append(f"- {entry.robot_id}: {rendered}")
    return "\n".join(lines)


def render_visual_apparatus_block(request: ReasonerRequest) -> str:
    """Render the image-convention sentences for whatever the request carries.

    Args:
        request: The request; reads `metric_grid_spacing_m`,
            `motion_trails_drawn` and `zoom_tile_path`.

    Returns:
        The sentences, one per line, or "" when the request carries none.
    """
    sentences = []
    if request.metric_grid_spacing_m is not None:
        sentences.append(
            _METRIC_GRID_SENTENCE.format(spacing=f"{request.metric_grid_spacing_m:g}")
        )
    if request.motion_trails_drawn:
        sentences.append(_MOTION_TRAILS_SENTENCE)
    if request.zoom_tile_path is not None:
        sentences.append(_ZOOM_TILE_SENTENCE)
    return "\n".join(sentences)


def render_failure_context_block(context: FailureContext) -> str:
    """Render the previous-attempt block for a re-analysis prompt (rev-8 A.1).

    Args:
        context: Prior-attempt summary supplied by M5.

    Returns:
        A multi-line block with no leading or trailing newline.
    """
    return "\n".join(
        [
            "Previous attempt in this episode:",
            *_render_attempt_lines(context),
            _FAILURE_CONTEXT_ADVICE,
        ]
    )


def render_last_failed_context_block(context: FailureContext) -> str:
    """Render the earlier-failed-attempt block that follows the previous-attempt block.

    Rendered only when M5's most recent failed attempt is not the previous
    attempt itself, so a completed maneuver cannot displace the failure from the
    prompt (failure-context depth policy, 2026-09-27).

    Args:
        context: Summary of the most recent failed attempt, supplied by M5.

    Returns:
        A multi-line block with no leading or trailing newline.
    """
    return "\n".join(
        [
            "Earlier failed attempt in this episode:",
            *_render_attempt_lines(context),
            _LAST_FAILED_CONTEXT_ADVICE,
        ]
    )


def render_visual_crosscheck_block(include_pairwise_geometry: bool) -> str:
    """Render the image/state cross-check block for the opt-in modality condition.

    Args:
        include_pairwise_geometry: Whether the prompt carries the derived
            pairwise-geometry lines, which decides which channel the block names
            as the default source for distance and facing.

    Returns:
        A multi-line block with no leading or trailing newline.
    """
    wording = _GEOMETRY_ON if include_pairwise_geometry else _GEOMETRY_OFF
    return _VISUAL_CROSSCHECK_TEMPLATE.format(
        crosscheck_default_clause=wording["crosscheck_default_clause"]
    )


def format_robot_state_lines(robot_states: list[RobotStateInput]) -> list[str]:
    """Render robot states as deterministic key=value lines for the prompt.

    Args:
        robot_states: Robot states to render (caller sorts beforehand).

    Returns:
        One comma-separated line per robot; optional fields omitted when None.
    """
    lines: list[str] = []
    for state in robot_states:
        parts = [
            f"robot_id={state.robot_id}",
            f"x={state.x:.2f}",
            f"y={state.y:.2f}",
            f"theta={state.theta:.2f}",
        ]
        if state.status is not None:
            parts.append(f"status={state.status}")
        if state.goal is not None:
            parts.append(f"goal_x={state.goal[0]:.2f}, goal_y={state.goal[1]:.2f}")
        if state.task is not None:
            parts.append(f"task={state.task}")
        if state.linear_velocity is not None:
            parts.append(f"linear_velocity={state.linear_velocity:.2f}")
        if state.angular_velocity is not None:
            parts.append(f"angular_velocity={state.angular_velocity:.2f}")
        lines.append(", ".join(parts))
    return lines


def order_robot_states(
    robot_states: list[RobotStateInput],
    order: RobotOrder = "id_asc",
) -> list[RobotStateInput]:
    """Put robot states into the requested presentation order.

    Args:
        robot_states: Robot states in arbitrary order.
        order: `"id_asc"` for ascending robot ID, `"id_desc"` for descending,
            or a tuple of robot ids listed first in that order (robots it does
            not name follow in ascending ID).

    Returns:
        A new list; the input is left untouched.
    """
    if isinstance(order, tuple):
        rank = {robot_id: index for index, robot_id in enumerate(order)}
        return sorted(robot_states, key=lambda s: (rank.get(s.robot_id, len(rank)), s.robot_id))
    return sorted(robot_states, key=lambda s: s.robot_id, reverse=order == "id_desc")


def _faces(theta: float, dx: float, dy: float, distance: float) -> bool:
    if distance < 1e-6:
        return False
    return (math.cos(theta) * dx + math.sin(theta) * dy) / distance >= _FACING_COS


def format_pairwise_geometry_lines(
    robot_states: list[RobotStateInput],
    order: RobotOrder = "id_asc",
) -> list[str]:
    """Render distance and mutual facing for every robot pair, in presentation order.

    The order decides which robot of a pair takes the `first` role, so it must
    match the order the robot-state list uses or the prompt would present the
    same pair two different ways.

    Args:
        robot_states: Robot states; pairs are formed in the requested order.
        order: As `order_robot_states`.

    Returns:
        One line per pair, e.g. `robot_1 <-> robot_2: distance 1.00 m;
        robot_1 faces robot_2: yes; robot_2 faces robot_1: no`; empty with fewer
        than two robots.
    """
    ordered = order_robot_states(robot_states, order)
    lines: list[str] = []
    for index, first in enumerate(ordered):
        for second in ordered[index + 1 :]:
            dx, dy = second.x - first.x, second.y - first.y
            distance = math.hypot(dx, dy)
            first_faces = "yes" if _faces(first.theta, dx, dy, distance) else "no"
            second_faces = "yes" if _faces(second.theta, -dx, -dy, distance) else "no"
            lines.append(
                f"{first.robot_id} <-> {second.robot_id}: distance {distance:.2f} m; "
                f"{first.robot_id} faces {second.robot_id}: {first_faces}; "
                f"{second.robot_id} faces {first.robot_id}: {second_faces}"
            )
    return lines


def format_static_obstacle_lines(obstacles: list[StaticObstacleInput]) -> list[str]:
    """Render fixed obstacles as world-frame boxes, sorted by obstacle ID.

    Args:
        obstacles: Declared static obstacles; order is normalized here.

    Returns:
        One line per obstacle, e.g. `obstacle_1: centre (-1.85, 0.00) m,
        extent 0.30 x 0.30 m`; empty when no obstacles are declared.
    """
    return [
        f"{obstacle.obstacle_id}: centre ({obstacle.x:.2f}, {obstacle.y:.2f}) m, "
        f"extent {obstacle.size_x_m:.2f} x {obstacle.size_y_m:.2f} m"
        for obstacle in sorted(obstacles, key=lambda o: o.obstacle_id)
    ]


def build_prompt_payload(request: ReasonerRequest) -> PromptPayload:
    """Build a deterministic, fully-rendered prompt payload from a request.

    `request.prompt_version` selects the template: 1 renders through the
    frozen `prompt_v1` module (byte-identical to every pre-bundle artifact),
    2 through the frozen `prompt_v2` module (byte-identical to every
    prompt-v2-bundle artifact), 3 (the current template) through this
    module's own text. The prompt-apparatus fields (metric grid, motion
    trails, zoom tile, candidate options) are v3-only: v1/v2 render neither
    their sentences nor the zoom tile attachment.

    Args:
        request: Validated reasoning request from M5/M1.

    Returns:
        Frozen `PromptPayload` with fixed system prompt and dynamic user prompt.
    """
    order = request.robot_presentation_order
    sorted_states = order_robot_states(request.robot_states, order)
    known_ids = [s.robot_id for s in sorted_states]
    if request.prompt_version == 1:
        return PromptPayload(
            system_prompt=SYSTEM_PROMPT_V1,
            user_prompt=render_user_prompt_v1(request),
            image_path=request.image_path,
            known_robot_ids=known_ids,
        )
    if request.prompt_version == 2:
        return PromptPayload(
            system_prompt=SYSTEM_PROMPT_V2,
            user_prompt=render_user_prompt_v2(request),
            image_path=request.image_path,
            known_robot_ids=known_ids,
        )
    lines = format_robot_state_lines(sorted_states)
    block = "\n".join(f"- {line}" for line in lines) or "- no robots observed"
    geometry_lines = (
        format_pairwise_geometry_lines(sorted_states, order)
        if request.include_pairwise_geometry
        else []
    )
    geometry_block = ""
    if geometry_lines:
        bullets = [f"- {line}" for line in geometry_lines]
        geometry_block = "\n" + "\n".join([_PAIRWISE_GEOMETRY_HEADER, *bullets]) + "\n"
    obstacle_lines = (
        format_static_obstacle_lines(request.static_obstacles)
        if request.include_static_obstacles
        else []
    )
    obstacle_block = ""
    if obstacle_lines:
        bullets = [f"- {line}" for line in obstacle_lines]
        obstacle_block = "\n" + "\n".join([_STATIC_OBSTACLE_HEADER, *bullets]) + "\n"
    failure_block = (
        ""
        if request.failure_context is None
        else "\n" + render_failure_context_block(request.failure_context) + "\n"
    )
    # Appended only when set, so a request without it renders byte-identically to
    # every prompt stored before the field existed.
    if request.last_failed_context is not None:
        failure_block += (
            "\n" + render_last_failed_context_block(request.last_failed_context) + "\n"
        )
    # Plan-state block (rev 4): independent of failure_context/last_failed_context
    # above -- a request may carry either, both, or neither. Appended after them
    # so a plan-tracking caller that ALSO attaches a failure context (e.g. a
    # non-plan-tracked re-ask mixed into a plan-tracked episode) sees both, most
    # specific last.
    if request.plan_state is not None:
        failure_block += "\n" + render_plan_state_block(request.plan_state) + "\n"
    crosscheck_block = (
        "\n" + render_visual_crosscheck_block(request.include_pairwise_geometry) + "\n"
        if request.include_visual_crosscheck
        else ""
    )
    # Prompt-apparatus conditions share the cross-check slot (after it), each
    # as its own blank-line-separated block, so an all-off request adds
    # nothing and renders byte-identically.
    apparatus = render_visual_apparatus_block(request)
    if apparatus:
        crosscheck_block += "\n" + apparatus + "\n"
    if request.candidate_options is not None:
        crosscheck_block += (
            "\n" + render_candidate_options_block(request.candidate_options, known_ids) + "\n"
        )
    user_prompt = _USER_TEMPLATE.format(
        robot_state_block=block,
        known_robot_ids_json=json.dumps(known_ids),
        pairwise_geometry_block=geometry_block,
        static_obstacle_block=obstacle_block,
        failure_context_block=failure_block,
        visual_crosscheck_block=crosscheck_block,
        plan_invitation=_PLAN_INVITATION,
        plan_grammar=render_plan_grammar(request.offered_strategies),
        strategy_option_lines=render_strategy_option_lines(request.offered_strategies),
        **(_GEOMETRY_ON if request.include_pairwise_geometry else _GEOMETRY_OFF),
        # Gated on the rendered lines, not on the flag: the ON clause asserts the
        # listed obstacles are the only ones present, which with an empty list
        # would affirm an empty scene that the flag alone cannot vouch for.
        **(_OBSTACLES_ON if obstacle_lines else _OBSTACLES_OFF),
    )
    return PromptPayload(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        image_path=request.image_path,
        known_robot_ids=known_ids,
        extra_image_paths=[] if request.zoom_tile_path is None else [request.zoom_tile_path],
    )
